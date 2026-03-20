# HIT #4 - Nodo C Bidireccional

## Descripción

Refactorización de A y B en un único programa `node_c.py` que opera
**simultáneamente** como cliente y servidor mediante dos threads:

- **Thread servidor**: escucha en su propio puerto y responde saludos entrantes.
- **Thread cliente**: se conecta al otro nodo C y le envía un saludo, con reintentos
  automáticos si el par aún no está disponible.

Con dos instancias corriendo, cada una apuntando a la otra, ambas se saludan
mutuamente de forma independiente.

## Diagrama de Arquitectura

```
Instancia C1                               Instancia C2
(listen: 9001, remote: 9002)               (listen: 9002, remote: 9001)

┌──────────────────────────┐               ┌──────────────────────────┐
│  Thread SERVER :9001     │◄──────────────│  Thread CLIENT → :9001   │
│                          │               │                          │
│  Thread CLIENT → :9002   │──────────────►│  Thread SERVER :9002     │
└──────────────────────────┘               └──────────────────────────┘
```

## Cómo ejecutar

Requiere Python 3.x (sin dependencias externas, solo stdlib).

### Local (ambas instancias en la misma máquina)

```bash
# Terminal 1 — C1
python3 tp1/HIT4/node_c.py --listen-port 9001 --remote-host 127.0.0.1 --remote-port 9002

# Terminal 2 — C2
python3 tp1/HIT4/node_c.py --listen-port 9002 --remote-host 127.0.0.1 --remote-port 9001
```

También con `--local` (usa el mismo puerto que EC2):

```bash
# Terminal 1 — C1 local
python3 tp1/HIT4/node_c.py --local --listen-port 5004   # conecta a 127.0.0.1:5003

# Terminal 2 — C2 local
python3 tp1/HIT4/node_c.py --listen-port 5003 --remote-host 127.0.0.1 --remote-port 5004
```

Las dos instancias se pueden iniciar en cualquier orden. El thread cliente reintenta
cada 2 segundos hasta que el par esté disponible.

### Salida esperada (C1)

```
[C-SERVER] Escuchando en 0.0.0.0:9001
[C-CLIENT] Intento #1 conectando a 127.0.0.1:9002...
[C-CLIENT] Error: [Errno 61] Connection refused. Reintentando en 2s...
[C-CLIENT] Intento #2 conectando a 127.0.0.1:9002...
[C-CLIENT] Saludo enviado: Hola! Soy C en puerto 9001.
[C-SERVER] Recibi de ('127.0.0.1', ...): Hola! Soy C en puerto 9002.
[C-CLIENT] Respuesta de 127.0.0.1:9002: Hola! Soy C en puerto 9002. Saludo recibido.
[C-SERVER] Respuesta enviada a ('127.0.0.1', ...)
```

## Decisiones de Diseño

- **Un thread por rol**: el servidor y el cliente corren en threads separados para
  operar de forma verdaderamente concurrente. Usar `daemon=True` garantiza que
  los threads se terminan cuando el proceso principal recibe `Ctrl+C`.
- **Reintentos en el cliente**: se hereda la lógica del HIT #2. Cualquier instancia
  puede iniciarse primero; el cliente del que arranca antes simplemente espera
  hasta que el par esté listo.
- **Cliente termina tras el saludo**: el thread cliente hace su trabajo (conectar,
  saludar, recibir respuesta) y finaliza. El servidor sigue corriendo para aceptar
  futuros saludos.
- **`argparse`**: los parámetros se pasan por línea de comandos para poder levantar
  múltiples instancias con distintas configuraciones sin tocar el código.

## Deploy en EC2

En EC2 corren dos instancias del nodo como servicios systemd:

| Servicio | Puerto | Conecta a |
|----------|--------|-----------|
| `hit4-node-c1` | TCP **5003** | localhost:5004 |
| `hit4-node-c2` | TCP **5004** | localhost:5003 |

```bash
# Ver logs
ssh -i clave-grupo404.pem ubuntu@3.144.148.19 "journalctl -fu hit4-node-c1"
```

### Flags del cliente

| Flag | Efecto |
|------|--------|
| `--local` | `--remote-host 127.0.0.1 --remote-port 5003` |
| `--remote` | `--remote-host 3.144.148.19 --remote-port 5003` |

```bash
# Conectar al nodo C1 de EC2 desde local
python3 tp1/HIT4/node_c.py --remote --listen-port 9099
```
