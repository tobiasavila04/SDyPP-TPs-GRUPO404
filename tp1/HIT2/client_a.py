"""
HIT #2 - Nodo A: Cliente TCP con reconexion automatica
Se conecta a B, saluda, y si B cierra la conexion (o no esta disponible)
reintenta automaticamente hasta restablecer la comunicacion.

Uso:
    python3 client_a.py             # local en 127.0.0.1:9000 (retrocompatible)
    python3 client_a.py --local     # local en 127.0.0.1:5001 (mismo puerto que EC2)
    python3 client_a.py --remote    # conecta a EC2 (3.144.148.19:5001)
"""

import argparse
import socket
import time

EC2_HOST = "3.144.148.19"
EC2_PORT = 5001
LOCAL_HOST = "127.0.0.1"
DEFAULT_PORT = 9000
RECONNECT_DELAY = 3


def saludar(sock):
    saludo = "Hola B, soy A!"
    sock.sendall(saludo.encode())
    print(f"[A] Saludo enviado: {saludo}")

    respuesta = sock.recv(1024)
    if not respuesta:
        raise ConnectionError("B cerro la conexion sin responder.")
    print(f"[A] Respuesta de B: {respuesta.decode()}")


def main():
    parser = argparse.ArgumentParser(description="Nodo A — Cliente TCP con reconexion (HIT #2)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--local", action="store_true", help=f"Conectar a {LOCAL_HOST}:{EC2_PORT} (servidor local en puerto EC2)")
    group.add_argument("--remote", action="store_true", help=f"Conectar a {EC2_HOST}:{EC2_PORT} (servidor en EC2)")
    args = parser.parse_args()

    if args.remote:
        host, port = EC2_HOST, EC2_PORT
    elif args.local:
        host, port = LOCAL_HOST, EC2_PORT
    else:
        host, port = LOCAL_HOST, DEFAULT_PORT  # retrocompatible

    intento = 1
    while True:
        print(f"[A] Intento #{intento} — conectando a {host}:{port}...")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, port))
                print("[A] Conexion establecida.")
                saludar(sock)
                print("[A] Intercambio completado. Esperando para reconectar...\n")
        except (ConnectionRefusedError, ConnectionResetError, ConnectionError, OSError) as e:
            print(f"[A] Error de conexion: {e}")
            print(f"[A] Reintentando en {RECONNECT_DELAY} segundos...\n")

        intento += 1
        time.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    main()
