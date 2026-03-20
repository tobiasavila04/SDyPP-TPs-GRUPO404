# HIT #6 - Registro de Contactos (Nodo D)

## Descripción

Introduce un nuevo tipo de nodo: **D**, que actúa como registro de contactos.

- **Node D** expone un servidor **TCP** (puerto 9000) donde los nodos C se registran,
  y un servidor **HTTP** (puerto 8080) con endpoints de estado y listado.
- **Node C** ya no necesita saber las IPs de sus pares. Solo conoce a D. Al iniciarse,
  C elige un puerto aleatorio, se registra en D y recibe la lista de peers activos
  a los que les envía un saludo JSON.

## Diagrama de Arquitectura

```
                         ┌──────────────────────────────────────┐
                         │           Nodo D (EC2)               │
  curl /health ─────────►│  HTTP :8080  /health  /nodes         │
  curl /nodes  ─────────►│                                      │
                         │  TCP  :9000  ← registro de nodos C   │
                         └──────────┬───────────────────────────┘
                                    │ devuelve lista de peers
              ┌─────────────────────┼──────────────────────┐
              │                     │                      │
              ▼                     ▼                      ▼
     ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
     │  Nodo C #1     │   │  Nodo C #2     │   │  Nodo C #3     │
     │  puerto random │◄──│  saluda a C#1  │   │  saluda a C#1  │
     │                │──►│                │   │  saluda a C#2  │
     └────────────────┘   └────────────────┘   └────────────────┘
```

## Endpoints HTTP de Node D

| Método | Ruta      | Descripción                                      |
|--------|-----------|--------------------------------------------------|
| GET    | `/`       | Estado general del servicio                      |
| GET    | `/health` | Uptime, nodos registrados, puerto TCP            |
| GET    | `/nodes`  | Lista completa de nodos C registrados            |
| DELETE | `/nodes`  | Limpia el registro (para testing)                |

### Ejemplo `/health`

```json
{
  "status": "healthy",
  "registered_nodes": 2,
  "uptime_seconds": 142.3,
  "tcp_registry_port": 9000,
  "timestamp": "2026-03-15T12:01:23+00:00"
}
```

## Cómo ejecutar

### Local

```bash
# Terminal 1 — Node D
uvicorn tp1.HIT6.node_d:app --host 0.0.0.0 --port 8080

# Terminales 2, 3, 4 — instancias de Node C
python3 tp1/HIT6/node_c.py --local    # conecta a 127.0.0.1:5005
```

### Verificar el estado local

```bash
curl http://localhost:8080/health
curl http://localhost:8080/nodes
```

## Deploy en EC2

Node D corre como servicio systemd `hit6-node-d`.

| Componente | Puerto |
|-----------|--------|
| TCP registro (node_c conecta aquí) | **5005** |
| HTTP FastAPI (interno) | 8086 |

El pipeline CI/CD (`scripts/deploy.sh`) hace `git pull` + `pip install` y reinicia
todos los servicios HIT en cada push a `main`.

### Iniciar Node C contra EC2

```bash
python3 tp1/HIT6/node_c.py --remote
```

### Ver logs en EC2

```bash
ssh -i clave-grupo404.pem ubuntu@3.144.148.19 "journalctl -fu hit6-node-d"
```

### Flags del cliente

| Flag | Host registro | Puerto | Cuándo usar |
|------|--------------|--------|-------------|
| `--local` | 127.0.0.1 | 5005 | Node D corriendo localmente |
| `--remote` | 3.144.148.19 | 5005 | Node D en EC2 |
| `--registry-host X --registry-port Y` | manual | manual | Cualquier otro destino |

## Decisiones de Diseño

- **Thread por conexión en D**: cada registro de C se maneja en su propio thread,
  evitando que un C lento bloquee a los demás.
- **Puerto aleatorio en C**: C hace `bind("0.0.0.0", 0)` y lee el puerto asignado
  por el SO, eliminando la necesidad de coordinación manual de puertos.
- **`_registry_lock`**: protege la lista compartida de accesos concurrentes entre
  threads de registro.
- **`_get_own_ip()`**: detecta la IP saliente de C conectándose (sin datos) a
  `8.8.8.8`, que es la IP que D necesita para que otros C puedan alcanzar a este C.
