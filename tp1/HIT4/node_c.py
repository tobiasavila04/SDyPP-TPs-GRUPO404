"""
HIT #4 - Nodo C: Cliente y Servidor TCP simultaneos
Funciona como servidor (escucha saludos) y como cliente (saluda al otro C)
al mismo tiempo, usando un thread por rol.

Uso:
    python3 node_c.py --listen-port <puerto_propio> \
                      --remote-host <ip_otro_c>     \
                      --remote-port <puerto_otro_c>
"""

import argparse
import socket
import threading
import time

RECONNECT_DELAY = 2


def server_thread(listen_host, listen_port):
    """Escucha conexiones entrantes y responde saludos indefinidamente."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((listen_host, listen_port))
        srv.listen(5)
        print(f"[C-SERVER] Escuchando en {listen_host}:{listen_port}")

        while True:
            try:
                conn, addr = srv.accept()
                with conn:
                    data = conn.recv(1024)
                    if not data:
                        continue
                    mensaje = data.decode()
                    print(f"[C-SERVER] Recibi de {addr}: {mensaje}")
                    respuesta = f"Hola! Soy C en puerto {listen_port}. Saludo recibido."
                    conn.sendall(respuesta.encode())
                    print(f"[C-SERVER] Respuesta enviada a {addr}")
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                print(f"[C-SERVER] Error con cliente: {e}")


def client_thread(remote_host, remote_port, own_port):
    """Se conecta al otro nodo C y le envia un saludo.

    Reintenta si no esta disponible.
    """
    attempt = 1
    while True:
        print(f"[C-CLIENT] Intento #{attempt} conectando a {remote_host}:{remote_port}...")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((remote_host, remote_port))
                saludo = f"Hola! Soy C en puerto {own_port}."
                sock.sendall(saludo.encode())
                print(f"[C-CLIENT] Saludo enviado: {saludo}")
                respuesta = sock.recv(1024)
                print(f"[C-CLIENT] Respuesta de {remote_host}:{remote_port}: {respuesta.decode()}")
                return  # saludo completado, el cliente termina
        except (ConnectionRefusedError, ConnectionResetError, OSError) as e:
            print(f"[C-CLIENT] Error: {e}. Reintentando en {RECONNECT_DELAY}s...")
            attempt += 1
            time.sleep(RECONNECT_DELAY)


EC2_HOST = "3.144.148.19"
EC2_PORT = 5003  # puerto donde escucha el nodo C en EC2


def main():
    parser = argparse.ArgumentParser(
        description="Nodo C bidireccional (HIT #4)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  --local  --listen-port 5004          # prueba local: este nodo en 5004, par en 127.0.0.1:5003\n"
            "  --remote --listen-port 5004          # conecta al nodo C en EC2 (3.144.148.19:5003)\n"
            "  --remote-host 1.2.3.4 --remote-port 5003 --listen-port 5004  # manual"
        ),
    )
    parser.add_argument("--listen-host", default="0.0.0.0", help="IP donde escuchar (default: 0.0.0.0)")
    parser.add_argument("--listen-port", type=int, required=True, help="Puerto propio de escucha")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--local", action="store_true", help=f"Par en 127.0.0.1:{EC2_PORT}")
    group.add_argument("--remote", action="store_true", help=f"Par en EC2 ({EC2_HOST}:{EC2_PORT})")

    parser.add_argument("--remote-host", default=None, help="IP del otro nodo C (manual)")
    parser.add_argument("--remote-port", type=int, default=None, help="Puerto del otro nodo C (manual)")
    args = parser.parse_args()

    if args.local:
        args.remote_host = "127.0.0.1"
        args.remote_port = EC2_PORT
    elif args.remote:
        args.remote_host = EC2_HOST
        args.remote_port = EC2_PORT
    elif args.remote_host is None or args.remote_port is None:
        parser.error("Especificá --local, --remote, o bien --remote-host y --remote-port manualmente.")

    srv = threading.Thread(
        target=server_thread,
        args=(args.listen_host, args.listen_port),
        daemon=True,
        name="server",
    )
    cli = threading.Thread(
        target=client_thread,
        args=(args.remote_host, args.remote_port, args.listen_port),
        daemon=True,
        name="client",
    )

    srv.start()
    cli.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[C] Terminando.")


if __name__ == "__main__":
    main()
