import base64
import json
import os
import time

import cv2
import numpy as np
import pika

nombre_imagen = os.getenv("IMAGEN", "imagen_prueba.jpg")
CANTIDAD_CHUNKS = int(os.getenv("CANTIDAD_CHUNKS", "4"))
RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")

print("--- Iniciando Splitter ---")

if not os.path.exists(nombre_imagen):
    print(f"[X] Error: No se encontró '{nombre_imagen}'.")
    exit()

# 1. Conectamos a RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(RABBIT_HOST))
channel = connection.channel()
channel.queue_declare(queue="tareas_sobel")

# 2. Leemos la imagen en grises
imagen = cv2.imread(nombre_imagen, cv2.IMREAD_GRAYSCALE)
alto, ancho = imagen.shape
alto_chunk = alto // CANTIDAD_CHUNKS

print(f"[*] Imagen original: {ancho}x{alto}. Cortando en {CANTIDAD_CHUNKS} pedazos...")

# 3. Cortamos y enviamos
start_time = time.time()

for i in range(CANTIDAD_CHUNKS):
    y_inicio = i * alto_chunk
    y_fin = alto if i == CANTIDAD_CHUNKS - 1 else (i + 1) * alto_chunk

    # Cortamos la franja (slicing de arrays en numpy)
    pedazo = imagen[y_inicio:y_fin, :]

    # Codificamos a Base64
    _, buffer = cv2.imencode(".jpg", pedazo)
    img_b64 = base64.b64encode(buffer).decode("utf-8")

    # Armamos el mensaje
    mensaje = {
        "chunk_id": i,
        "total_chunks": CANTIDAD_CHUNKS,
        "image_data": img_b64,
        "start_time": start_time,  # Le pasamos el tiempo inicial al joiner para que calcule el total
    }

    channel.basic_publish(exchange="", routing_key="tareas_sobel", body=json.dumps(mensaje))
    print(f" [x] Enviado Chunk {i}")

connection.close()
print(" [*] Todos los pedazos fueron enviados a la cola.")
