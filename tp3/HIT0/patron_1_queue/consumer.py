import pika
import time
import os

RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")
connection = pika.BlockingConnection(pika.ConnectionParameters(RABBIT_HOST))
channel = connection.channel()

# Declaramos la cola de nuevo. Esto es una buena práctica por si
# ejecutamos el consumidor antes que el productor.
channel.queue_declare(queue="cola_tareas")


# Esta función se ejecuta cada vez que llega un mensaje
def callback(ch, method, properties, body):
    mensaje = body.decode()
    print(f" [x] Recibido {mensaje}")
    time.sleep(1)  # Simulamos que procesar la tarea lleva 1 segundo
    print(f" [v] {mensaje} terminada!")


# Le decimos a RabbitMQ que use la función callback cuando lleguen mensajes
channel.basic_consume(queue="cola_tareas", auto_ack=True, on_message_callback=callback)

print(" [*] Esperando mensajes. Para salir presiona CTRL+C")
channel.start_consuming()
