import json
import os
import time

import pika

RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")

print("--- Iniciando DLQ Monitor ---")

# --- Exponential Backoff para la conexión ---
def connect_to_rabbit(host):
    max_retries = 5
    base_delay = 1
    max_delay = 30
    for attempt in range(max_retries):
        try:
            print(f" [*] Intentando conectar a RabbitMQ en {host} (Intento {attempt+1}/{max_retries})")
            connection = pika.BlockingConnection(pika.ConnectionParameters(host))
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            delay = min(base_delay * (2 ** attempt), max_delay)
            print(f" [X] Error conectando: {e}. Reintentando en {delay}s...")
            time.sleep(delay)
    print(" [X] Falla crítica: No se pudo conectar a RabbitMQ después de varios reintentos.")
    exit(1)

connection = connect_to_rabbit(RABBIT_HOST)
channel = connection.channel()

channel.exchange_declare(exchange='dlx_tareas', exchange_type='direct')
channel.queue_declare(queue='tareas_sobel_dlq', durable=True)
channel.queue_bind(exchange='dlx_tareas', queue='tareas_sobel_dlq', routing_key='tareas_sobel_dlq')

channel.queue_declare(queue="tareas_sobel", durable=True, arguments={
    'x-dead-letter-exchange': 'dlx_tareas',
    'x-dead-letter-routing-key': 'tareas_sobel_dlq'
})

def callback(ch, method, properties, body):
    datos = json.loads(body.decode())
    chunk_id = datos.get("chunk_id", "Desconocido")
    
    print(f" [!] Recibido mensaje fallido de DLQ. Chunk ID: {chunk_id}")
    
    death_count = 0
    if properties.headers and 'x-death' in properties.headers:
        # RabbitMQ guarda el historial de muertes en x-death (una lista de diccionarios)
        try:
            death_count = properties.headers['x-death'][0]['count']
        except (IndexError, KeyError):
            pass

    if death_count >= 3:
        print(f" [X] ALERTA (Poison Pill): El chunk {chunk_id} falló {death_count} veces. Descartando definitivamente.")
        # Le damos ACK para que se borre de la DLQ y no vuelva nunca más a la principal.
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return
    
    print(f" [*] Re-encolando chunk {chunk_id} a 'tareas_sobel' (Intento previo de falla: {death_count})...")
    time.sleep(2) 
    
    # Re-publicar a la cola principal
    ch.basic_publish(exchange="", routing_key="tareas_sobel", body=body)
    
    # Confirmar que procesamos (y sacamos) el mensaje de la DLQ
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue="tareas_sobel_dlq", on_message_callback=callback, auto_ack=False)

print(" [*] Monitor DLQ esperando mensajes fallidos...")
channel.start_consuming()
