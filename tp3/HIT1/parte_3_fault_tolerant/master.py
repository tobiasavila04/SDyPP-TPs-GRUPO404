import base64
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2
import numpy as np
import pika

RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")
CANTIDAD_CHUNKS = int(os.getenv("CANTIDAD_CHUNKS", "4"))
TIMEOUT_SEGUNDOS = int(os.getenv("TIMEOUT_SEGUNDOS", "15"))
IMAGEN = os.getenv("IMAGEN", "imagen_prueba.jpg")

QUEUE_TAREAS = "tareas_sobel_ft"
QUEUE_RESULTADOS = "resultados_sobel_ft"

# Estado compartido entre el hilo principal y el monitor
pending_lock = threading.Lock()
pending_chunks = {}   # chunk_id -> {"body": str, "sent_at": float, "retries": int}
received_chunks = {}  # chunk_id -> np.ndarray
all_done = threading.Event()


def _start_health_server(port=8080):
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                body = json.dumps({"service": "sobel-master-ft", "status": "ok"}).encode()
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
    print(f" [*] Health-check: http://0.0.0.0:{port}/health")


def connect():
    params = pika.ConnectionParameters(
        host=RABBIT_HOST,
        heartbeat=600,
        blocked_connection_timeout=300,
    )
    return pika.BlockingConnection(params)


def build_chunk_body(chunk_id, image_slice, total_chunks):
    _, buffer = cv2.imencode(".jpg", image_slice)
    img_b64 = base64.b64encode(buffer).decode("utf-8")
    return json.dumps({
        "chunk_id": chunk_id,
        "total_chunks": total_chunks,
        "image_data": img_b64,
    })


def monitor_timeouts():
    """
    Hilo de monitoreo activo: detecta chunks que superaron el timeout y los
    re-encola para que otro worker los procese (fault tolerance a nivel aplicación).
    """
    print(f" [MONITOR] Activo. Timeout configurado: {TIMEOUT_SEGUNDOS}s por chunk.")
    while not all_done.wait(timeout=5):
        now = time.time()
        chunks_a_reencolar = []

        with pending_lock:
            for chunk_id, info in list(pending_chunks.items()):
                if now - info["sent_at"] > TIMEOUT_SEGUNDOS:
                    chunks_a_reencolar.append((chunk_id, info))

        if not chunks_a_reencolar:
            continue

        try:
            conn = connect()
            ch = conn.channel()
            ch.queue_declare(queue=QUEUE_TAREAS)
            for chunk_id, info in chunks_a_reencolar:
                with pending_lock:
                    info["retries"] += 1
                    info["sent_at"] = time.time()

                print(
                    f"\n [!] FALLO DETECTADO — Chunk {chunk_id} sin respuesta por "
                    f">{TIMEOUT_SEGUNDOS}s. Reasignando (intento #{info['retries']})..."
                )
                ch.basic_publish(exchange="", routing_key=QUEUE_TAREAS, body=info["body"])
            conn.close()
        except Exception as e:
            print(f" [MONITOR] Error al re-encolar: {e}")

    print(" [MONITOR] Todos los chunks recibidos. Finalizando.")


def result_callback(ch, method, properties, body):
    datos = json.loads(body.decode())
    chunk_id = datos["chunk_id"]

    # Si ya lo recibimos (duplicado por re-encolar), ignorar
    with pending_lock:
        if chunk_id in received_chunks:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f" [~] Chunk {chunk_id} duplicado ignorado.")
            return

    img_bytes = base64.b64decode(datos["image_data"])
    np_arr = np.frombuffer(img_bytes, np.uint8)
    pedazo = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)

    with pending_lock:
        pending_chunks.pop(chunk_id, None)
        received_chunks[chunk_id] = pedazo

    ch.basic_ack(delivery_tag=method.delivery_tag)
    print(f" [v] Chunk {chunk_id} recibido ({len(received_chunks)}/{CANTIDAD_CHUNKS})")

    if len(received_chunks) == CANTIDAD_CHUNKS:
        all_done.set()
        ch.stop_consuming()


def main():
    _start_health_server()
    print("=" * 50)
    print("   MASTER — Procesamiento Distribuido Tolerante a Fallos")
    print("=" * 50)

    if not os.path.exists(IMAGEN):
        print(f"[X] Error: No se encontró '{IMAGEN}'.")
        return

    conn = connect()
    channel = conn.channel()
    channel.queue_declare(queue=QUEUE_TAREAS)
    channel.queue_declare(queue=QUEUE_RESULTADOS)

    imagen = cv2.imread(IMAGEN, cv2.IMREAD_GRAYSCALE)
    alto, ancho = imagen.shape
    alto_chunk = alto // CANTIDAD_CHUNKS
    print(f"[*] Imagen: {ancho}x{alto}px | Chunks: {CANTIDAD_CHUNKS} | Timeout: {TIMEOUT_SEGUNDOS}s\n")

    t0 = time.time()

    # Enviar todos los chunks y registrarlos como pendientes
    for i in range(CANTIDAD_CHUNKS):
        y_inicio = i * alto_chunk
        y_fin = alto if i == CANTIDAD_CHUNKS - 1 else (i + 1) * alto_chunk
        body = build_chunk_body(i, imagen[y_inicio:y_fin, :], CANTIDAD_CHUNKS)

        with pending_lock:
            pending_chunks[i] = {"body": body, "sent_at": time.time(), "retries": 0}

        channel.basic_publish(exchange="", routing_key=QUEUE_TAREAS, body=body)
        print(f" [->] Chunk {i} enviado")

    # Arrancar el hilo monitor antes de bloquear en el consumo de resultados
    monitor_thread = threading.Thread(target=monitor_timeouts, daemon=True)
    monitor_thread.start()

    print(f"\n [*] Esperando resultados (detectando fallos cada 5s)...")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_RESULTADOS, on_message_callback=result_callback, auto_ack=False)
    channel.start_consuming()
    conn.close()

    # Ensamblar imagen final
    tiempo_total = time.time() - t0
    print("\n [*] Ensamblando imagen final...")
    imagen_final = np.vstack([received_chunks[i] for i in range(CANTIDAD_CHUNKS)])
    cv2.imwrite("resultado_ft.jpg", imagen_final)
    print(f" [V] Imagen guardada como 'resultado_ft.jpg'")
    print(f" [*] TIEMPO TOTAL: {tiempo_total:.4f}s\n")


if __name__ == "__main__":
    main()
