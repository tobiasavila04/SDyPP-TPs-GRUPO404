# HIT #1 - Comunicación TCP básica: Cliente A y Servidor B

## Descripción

Implementación de comunicación TCP entre dos nodos:
- **Nodo B** (`server_b.py`): servidor TCP que espera el saludo de A y responde.
- **Nodo A** (`client_a.py`): cliente TCP que se conecta a B y lo saluda.

## Diagrama de Arquitectura

```
┌─────────────────┐        TCP (port 9000)         ┌─────────────────┐
│    Nodo A       │ ─────── "Hola B, soy A!" ─────►│    Nodo B       │
│  (client_a.py)  │ ◄── "Hola A, soy B. Saludo ─── │  (server_b.py)  │
│                 │          recibido!"            │                 │
└─────────────────┘                                └─────────────────┘
```

## Cómo ejecutar

Requiere Python 3.x (sin dependencias externas, solo stdlib).

### 1. Iniciar el servidor B (en una terminal)

```bash
python3 tp1/HIT1/server_b.py
```

Salida esperada:
```
[B] Servidor escuchando en 0.0.0.0:9000
```

### 2. Iniciar el cliente A (en otra terminal)

```bash
python3 tp1/HIT1/client_a.py
```

Salida esperada del cliente:
```
[A] Conectando a 127.0.0.1:9000...
[A] Conexion establecida.
[A] Saludo enviado: Hola B, soy A!
[A] Respuesta de B: Hola A, soy B. Saludo recibido!
[A] Conexion cerrada.
```

Salida esperada del servidor:
```
[B] Conexion aceptada desde ('127.0.0.1', <puerto_efimero>)
[B] Recibi: Hola B, soy A!
[B] Respuesta enviada: Hola A, soy B. Saludo recibido!
[B] Conexion cerrada.
```

## Deploy en EC2

El servidor corre como servicio systemd en EC2 en el **puerto TCP 5000**.

```bash
# Verificar que el servicio está activo
ssh -i clave-grupo404.pem ubuntu@3.144.148.19 "systemctl status hit1-server"

# Ver logs en tiempo real
ssh -i clave-grupo404.pem ubuntu@3.144.148.19 "journalctl -fu hit1-server"
```

### Flags del cliente

| Flag | Host | Puerto | Cuándo usar |
|------|------|--------|-------------|
| *(ninguno)* | 127.0.0.1 | 9000 | Testing local / retrocompatible |
| `--local` | 127.0.0.1 | 5000 | Local con el mismo puerto que EC2 |
| `--remote` | 3.144.148.19 | 5000 | Contra el servidor en EC2 |

```bash
# Probar contra EC2 (servidor ya corriendo)
python3 tp1/HIT1/client_a.py --remote

# Probar local con mismo puerto que EC2
PORT=5000 python3 tp1/HIT1/server_b.py &
python3 tp1/HIT1/client_a.py --local
```