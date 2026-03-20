# HIT #5 - Serialización JSON

## Descripción

Extensión del HIT #4: todos los mensajes entre nodos C se envían y reciben
**en formato JSON**. Se agregan dos funciones de bajo nivel (`send_json` /
`recv_json`) que encapsulan la serialización y el framing TCP.

## Estructura del mensaje

### Saludo (`greeting`)

```json
{
  "type": "greeting",
  "from_port": 9001,
  "message": "Hola! Soy C en puerto 9001.",
  "timestamp": "2026-03-15T12:00:00+00:00"
}
```

### Respuesta (`greeting_response`)

```json
{
  "type": "greeting_response",
  "from_port": 9002,
  "message": "Saludo recibido de puerto 9001.",
  "timestamp": "2026-03-15T12:00:00.123+00:00"
}
```

## Diagrama de Arquitectura

```
Instancia C1                                    Instancia C2
(listen: 9001, remote: 9002)                    (listen: 9002, remote: 9001)

┌────────────────────────────┐                  ┌────────────────────────────┐
│ Thread SERVER :9001        │◄── JSON greeting ─│ Thread CLIENT → :9001      │
│   recv_json() → dict       │                  │   send_json(greeting)      │
│   send_json(response)      │── JSON response ─►│   recv_json() → dict       │
│                            │                  │                            │
│ Thread CLIENT → :9002      │── JSON greeting ─►│ Thread SERVER :9002        │
│   send_json(greeting)      │                  │   recv_json() → dict       │
│   recv_json() → dict       │◄── JSON response ─│   send_json(response)      │
└────────────────────────────┘                  └────────────────────────────┘
```

## Cómo ejecutar

Requiere Python 3.x (sin dependencias externas, solo stdlib).

### Local (ambas instancias en la misma máquina)

```bash
# Terminal 1 — C1
python3 tp1/HIT5/node_c.py --listen-port 9001 --remote-host 127.0.0.1 --remote-port 9002

# Terminal 2 — C2
python3 tp1/HIT5/node_c.py --listen-port 9002 --remote-host 127.0.0.1 --remote-port 9001
```

También con `--local`:

```bash
python3 tp1/HIT5/node_c.py --local  --listen-port 5004   # conecta a 127.0.0.1:5004
python3 tp1/HIT5/node_c.py --listen-port 5003 --remote-host 127.0.0.1 --remote-port 5004
```

### Salida esperada (C1)

```
[C-SERVER] Escuchando en 0.0.0.0:9001
[C-CLIENT] Intento #1 conectando a 127.0.0.1:9002...
[C-CLIENT] JSON enviado: {"type": "greeting", "from_port": 9001, ...}
[C-SERVER] JSON recibido de ('127.0.0.1', ...): {"type": "greeting", "from_port": 9002, ...}
[C-CLIENT] JSON recibido: {"type": "greeting_response", "from_port": 9002, ...}
[C-SERVER] JSON enviado a ('127.0.0.1', ...): {"type": "greeting_response", "from_port": 9001, ...}
```

## Decisiones de Diseño

- **Newline como delimitador de mensajes**: TCP es un protocolo de stream, no de
  mensajes. Sin framing, un `recv()` puede traer un mensaje parcial o varios juntos.
  Terminar cada JSON con `\n` y leer hasta encontrar ese carácter resuelve el problema
  de forma simple sin añadir dependencias.
- **`send_json` / `recv_json` como helpers**: encapsular la serialización en dos
  funciones hace que el resto del código trabaje solo con dicts de Python, sin mezclar
  lógica de negocio con lógica de transporte.
- **Campo `timestamp` en UTC (ISO 8601)**: facilita correlacionar eventos entre nodos
  en distintas zonas horarias y es el formato estándar en sistemas distribuidos.
- **Campo `type`**: permite extender el protocolo en HITs futuros (ej. mensajes de
  registro, heartbeat) sin romper compatibilidad.

## Deploy en EC2

Igual que HIT4, corren dos instancias en EC2:

| Servicio | Puerto | Conecta a |
|----------|--------|-----------|
| `hit5-node-c1` | TCP **5003** | localhost:5004 |
| `hit5-node-c2` | TCP **5004** | localhost:5003 |

### Flags del cliente

| Flag | Efecto |
|------|--------|
| `--local` | `--remote-host 127.0.0.1 --remote-port 5004` |
| `--remote` | `--remote-host 3.144.148.19 --remote-port 5004` |

```bash
# Conectar al nodo C1 de EC2 y ver el intercambio JSON
python3 tp1/HIT5/node_c.py --remote --listen-port 9099
```
