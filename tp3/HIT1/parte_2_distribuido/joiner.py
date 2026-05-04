import base64
import json
import os
import time

import cv2
import numpy as np
import pika

RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")
CANTIDAD_CHUNKS = int(os.getenv("CANTIDAD_CHUNKS", "4"))

print("--- Iniciando Joiner ---")

connection = pika.BlockingConnection(pika.ConnectionParameters(RABBIT_HOST))
channel = connection.channel()
channel.queue_declare(queue="resultados_sobel", durable=True)

pedazos_recibidos = {}
tiempo_inicio = None  # <-- Variable para nuestro cronómetro


def callback(ch, method, properties, body):
    global tiempo_inicio

    # Si es el primer pedazo que llega, arrancamos el cronómetro
    if tiempo_inicio is None:
        tiempo_inicio = time.time()

    datos = json.loads(body.decode())
    chunk_id = datos["chunk_id"]
    img_b64 = datos["image_data"]

    print(f" [v] Recibido chunk procesado {chunk_id}")

    img_bytes = base64.b64decode(img_b64)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    pedazo = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)

    pedazos_recibidos[chunk_id] = pedazo
    ch.basic_ack(delivery_tag=method.delivery_tag)

    if len(pedazos_recibidos) == CANTIDAD_CHUNKS:
        print("\n [*] ¡Todos los pedazos recibidos! Unificando...")

        pedazos_ordenados = [pedazos_recibidos[i] for i in range(CANTIDAD_CHUNKS)]
        imagen_final = np.vstack(pedazos_ordenados)

        # Paramos el reloj justo después de pegar la imagen
        tiempo_total = time.time() - tiempo_inicio

        cv2.imwrite("resultado_distribuido.jpg", imagen_final)
        print(" [V] ¡Éxito! Imagen guardada como 'resultado_distribuido.jpg'")
        print(f" [*] TIEMPO TOTAL DISTRIBUIDO: {tiempo_total:.4f} segundos")  # <-- Acá está tu tiempo

        channel.stop_consuming()


channel.basic_consume(queue="resultados_sobel", on_message_callback=callback, auto_ack=False)

print(" [*] Esperando pedazos procesados...")
channel.start_consuming()
