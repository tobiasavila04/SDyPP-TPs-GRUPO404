"""
HIT #1 - Nodo A: Cliente TCP
Se conecta con B y le envía un saludo.

Uso:
    python3 client_a.py             # local en 127.0.0.1:9000 (retrocompatible)
    python3 client_a.py --local     # local en 127.0.0.1:5000 (mismo puerto que EC2)
    python3 client_a.py --remote    # conecta a EC2 (3.144.148.19:5000)
"""

import argparse
import socket

EC2_HOST = "3.144.148.19"
EC2_PORT = 5000
LOCAL_HOST = "127.0.0.1"
DEFAULT_PORT = 9000


def main():
    parser = argparse.ArgumentParser(description="Nodo A — Cliente TCP (HIT #1)")
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

    print("[A] Conexion cerrada.")


if __name__ == "__main__":
    main()
