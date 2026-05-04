import pika
import time
import os

RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")
connection = pika.BlockingConnection(pika.ConnectionParameters(RABBIT_HOST))
channel = connection.channel()

# Declaramos la cola a la que vamos a enviar los mensajes
channel.queue_declare(queue="cola_tareas")

print(" Empezando a enviar tareas...")

# Enviamos 10 tareas numeradas
for i in range(1, 11):
    mensaje = f"Tarea #{i}"
    # En el patrón punto a punto, usamos el exchange por defecto (string vacío)
    # y el routing_key es el nombre de la cola.
    channel.basic_publish(exchange="", routing_key="cola_tareas", body=mensaje)
    print(f" [x] Enviado '{mensaje}'")
    time.sleep(0.5)  # Un pequeño delay para que se note el envío

connection.close()
