"""
HIT #3 - Nodo A: Cliente TCP
Se conecta a B, saluda y queda en espera.
Matar este proceso (Ctrl+C / kill) simula una desconexion abrupta
para probar que B sigue funcionando.

Uso:
    python3 client_a.py             # local en 127.0.0.1:9000 (retrocompatible)
    python3 client_a.py --local     # local en 127.0.0.1:5002 (mismo puerto que EC2)
    python3 client_a.py --remote    # conecta a EC2 (3.144.148.19:5002)
"""

import argparse
import socket
import time

EC2_HOST = "3.144.148.19"
EC2_PORT = 5002
LOCAL_HOST = "127.0.0.1"
DEFAULT_PORT = 9000


def main():
    parser = argparse.ArgumentParser(description="Nodo A — Cliente TCP (HIT #3)")
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

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        print(f"[A] Conectando a {host}:{port}...")
        sock.connect((host, port))
        print("[A] Conexion establecida.")

        saludo = "Hola B, soy A!"
        sock.sendall(saludo.encode())
        print(f"[A] Saludo enviado: {saludo}")

        respuesta = sock.recv(1024)
        print(f"[A] Respuesta de B: {respuesta.decode()}")

        print("[A] Manteniendo conexion abierta... (mata este proceso para probar HIT #3)")
        while True:
            time.sleep(1)


if __name__ == "__main__":
    main()
