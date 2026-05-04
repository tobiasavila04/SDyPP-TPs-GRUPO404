import pika
import os

RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")
connection = pika.BlockingConnection(pika.ConnectionParameters(RABBIT_HOST))
channel = connection.channel()

# Declaramos la cola principal
channel.queue_declare(queue="cola_principal_retry")

print(" Enviando tarea suicida...")

# Enviamos el mensaje con un header personalizado para contar los intentos
propiedades = pika.BasicProperties(headers={"retry_count": 0})

channel.basic_publish(exchange="", routing_key="cola_principal_retry", body="Generar reporte pesado", properties=propiedades)

print(" [x] Tarea enviada. ¡Suerte con eso!")
connection.close()
