import base64
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2
import numpy as np
import pika

RABBIT_HOST = os.getenv("RABBIT_HOST", "host.docker.internal")
WORKER_ID = os.getenv("WORKER_ID", "worker-0")
# Poner SIMULATE_SLOW=1 para simular un worker lento (no responde dentro del timeout)
SIMULATE_SLOW = os.getenv("SIMULATE_SLOW", "0") == "1"
SLOW_DELAY = int(os.getenv("SLOW_DELAY", "30"))

QUEUE_TAREAS = "tareas_sobel_ft"
QUEUE_RESULTADOS = "resultados_sobel_ft"

def _start_health_server(worker_id, port=8080):
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                body = json.dumps({"service": f"sobel-worker-ft/{worker_id}", "status": "ok"}).encode()
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


print(f" [*] Worker [{WORKER_ID}] iniciando...")
if SIMULATE_SLOW:
    print(f" [!] Modo LENTO activado — simulará {SLOW_DELAY}s de demora (para demo de fault tolerance)")


def connect():
    params = pika.ConnectionParameters(
        host=RABBIT_HOST,
        heartbeat=600,
        blocked_connection_timeout=300,
    )
    return pika.BlockingConnection(params)


_start_health_server(WORKER_ID)

try:
    connection = connect()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_TAREAS)
    channel.queue_declare(queue=QUEUE_RESULTADOS)
except Exception as e:
    print(f" [X] [{WORKER_ID}] Error conectando a RabbitMQ en '{RABBIT_HOST}': {e}")
    exit(1)


def callback(ch, method, properties, body):
    datos = json.loads(body.decode())
    chunk_id = datos["chunk_id"]

    print(f" [->] [{WORKER_ID}] Chunk {chunk_id} recibido. Procesando...")

    if SIMULATE_SLOW:
        print(f" [!] [{WORKER_ID}] Simulando demora de {SLOW_DELAY}s en chunk {chunk_id}...")
        time.sleep(SLOW_DELAY)

    img_bytes = base64.b64decode(datos["image_data"])
    np_arr = np.frombuffer(img_bytes, np.uint8)
    imagen = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)

    sobel_x = cv2.Sobel(imagen, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(imagen, cv2.CV_64F, 0, 1, ksize=3)
    sobel_combinado = cv2.magnitude(sobel_x, sobel_y)
    resultado = np.uint8(np.absolute(sobel_combinado))

    _, buffer = cv2.imencode(".jpg", resultado)
    res_b64 = base64.b64encode(buffer).decode("utf-8")

    ch.basic_publish(
        exchange="",
        routing_key=QUEUE_RESULTADOS,
        body=json.dumps({"chunk_id": chunk_id, "image_data": res_b64}),
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)
    print(f" [<-] [{WORKER_ID}] Chunk {chunk_id} procesado y enviado.")


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=QUEUE_TAREAS, on_message_callback=callback, auto_ack=False)

print(f" [*] [{WORKER_ID}] Esperando chunks...")
channel.start_consuming()
