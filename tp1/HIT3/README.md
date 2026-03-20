# HIT #3 - Servidor B robusto ante desconexiones de A

## Descripción

Extensión del HIT #2: ahora el foco está en el **nodo B**. Si A se desconecta
abruptamente (proceso matado, crash, corte de red), B captura la excepción y
**continúa escuchando** nuevas conexiones sin necesidad de reiniciarse.

El nodo A se mantiene conectado en un loop luego del saludo, permitiendo simular
una desconexión abrupta matando su proceso.

## Diagrama de Arquitectura

```
[B escuchando]
      │
      ▼
┌─────────────────┐   conexión #1   ┌─────────────────┐
│    Nodo B       │◄────────────────│    Nodo A       │
│  (server_b.py)  │────────────────►│  (client_a.py)  │
│                 │                 │  [kill -9 A]    │
│  captura error  │                 └─────────────────┘
│  sigue en loop  │
│                 │   conexión #2   ┌─────────────────┐
│                 │◄────────────────│    Nodo A       │
│                 │────────────────►│  (nueva inst.)  │
└─────────────────┘                 └─────────────────┘
```

## Cómo ejecutar

Requiere Python 3.x (sin dependencias externas, solo stdlib).

### 1. Iniciar el servidor B

```bash
python3 tp1/HIT3/server_b.py
```

### 2. Iniciar el cliente A (en otra terminal)

```bash
python3 tp1/HIT3/client_a.py
```

A saluda a B y queda en espera (simulando un proceso activo).

### 3. Probar la robustez de B

Matá el proceso A con `Ctrl+C`. B mostrará:

```
[B] A se desconecto abruptamente: ...
[B] Conexion con A cerrada. Esperando nueva conexion...
```

B sigue corriendo. Si se levanta una nueva instancia de A, se va a ver que B la atiende
normalmente.

## Decisiones de Diseño

- **`listen(5)`**: se aumenta el backlog a 5 para que el SO pueda encolar conexiones
  entrantes mientras B procesa la actual (útil si varios A intentan conectarse seguido).
  
- **`BrokenPipeError` y `ConnectionResetError`**: cubren los dos escenarios principales
  de desconexión abrupta — escritura en socket cerrado y reset por el par remoto,
  respectivamente.

## Deploy en EC2

El servidor corre como servicio systemd en EC2 en el **puerto TCP 5002**.

```bash
# Ver logs en tiempo real
ssh -i clave-grupo404.pem ubuntu@3.144.148.19 "journalctl -fu hit3-server"
```

### Flags del cliente

| Flag | Host | Puerto | Cuándo usar |
|------|------|--------|-------------|
| *(ninguno)* | 127.0.0.1 | 9000 | Testing local / retrocompatible |
| `--local` | 127.0.0.1 | 5002 | Local con el mismo puerto que EC2 |
| `--remote` | 3.144.148.19 | 5002 | Contra el servidor en EC2 |

```bash
# Conectar al servidor en EC2 y luego matar el cliente con Ctrl+C para probar robustez
python3 tp1/HIT3/client_a.py --remote
```
