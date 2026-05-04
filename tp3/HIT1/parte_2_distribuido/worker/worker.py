import base64
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2
import numpy as np
import pika

def _start_health_server(port=8080):
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                body = json.dumps({"service": "sobel-worker", "status": "ok"}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass

    threading.Thread(target=HTTPServer(("0.0.0.0", port), _Handler).serve_forever, daemon=True).start()


print(" [*] Iniciando Worker Sobel en Docker...")

# Buscamos RabbitMQ (por defecto usa host.docker.internal para llegar a tu compu)
RABBIT_HOST = os.getenv("RABBIT_HOST", "host.docker.internal")

_start_health_server()

try:
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBIT_HOST))
    channel = connection.channel()

    channel.queue_declare(queue="tareas_sobel", durable=True)
    channel.queue_declare(queue="resultados_sobel", durable=True)
except Exception as e:
    print(f" [X] Error conectando a RabbitMQ: {e}")
    exit(1)


def callback(ch, method, properties, body):
    # 1. Leer el mensaje y decodificar la imagen de Base64
    datos = json.loads(body.decode())
    chunk_id = datos["chunk_id"]
    img_b64 = datos["image_data"]

    print(f" [->] Recibido chunk {chunk_id}")

    img_bytes = base64.b64decode(img_b64)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    imagen = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)

    # 2. Aplicar Filtro Sobel (lo mismo que hiciste en la Parte 1)
    sobel_x = cv2.Sobel(imagen, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(imagen, cv2.CV_64F, 0, 1, ksize=3)
    sobel_combinado = cv2.magnitude(sobel_x, sobel_y)
    sobel_normalizado = np.uint8(np.absolute(sobel_combinado))

    # 3. Volver a codificar a Base64
    _, buffer = cv2.imencode(".jpg", sobel_normalizado)
    res_b64 = base64.b64encode(buffer).decode("utf-8")

    # 4. Enviar resultado a la cola de resultados
    mensaje_resultado = {"chunk_id": chunk_id, "image_data": res_b64}
    ch.basic_publish(exchange="", routing_key="resultados_sobel", body=json.dumps(mensaje_resultado))

    # 5. Confirmar que la tarea terminó (ACK)
    ch.basic_ack(delivery_tag=method.delivery_tag)
    print(f" [<-] Chunk {chunk_id} procesado y enviado.")


channel.basic_consume(queue="tareas_sobel", on_message_callback=callback, auto_ack=False)

print(" [*] Worker listo y esperando chunks...")
channel.start_consuming()
