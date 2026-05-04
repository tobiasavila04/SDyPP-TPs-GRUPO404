# HIT #1 — Parte 3: Tolerancia a Fallos (Fault Tolerant)

## Objetivo

Extender la arquitectura distribuida de la Parte 2 incorporando **detección activa de fallos a nivel aplicación**. Si un worker no responde en un tiempo configurado, el **Master** detecta el timeout, lo registra, y reasigna el chunk a otro worker disponible — sin intervención humana.

## Diferencia clave respecto a la Parte 2

| | Parte 2 | Parte 3 |
|---|---|---|
| Detección de fallo | Pasiva (RabbitMQ redeliver al caer TCP) | Activa (Master detecta timeout) |
| Worker lento (no caído) | No detectado | Detectado y reasignado |
| Log de fallo | No | Sí, con chunk ID y número de intento |
| Proceso maestro | Splitter + Joiner separados | Master unificado (split + monitor + join) |

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                       MASTER                            │
│  ┌──────────┐   tareas_sobel_ft    ┌─────────────────┐  │
│  │  Splitter │ ─────────────────►  │  Worker 1 (k8s) │  │
│  │  (split)  │                     └────────┬────────┘  │
│  └──────────┘   resultados_sobel_ft         │           │
│       │    ◄────────────────────────────────┘           │
│  ┌────▼──────────────────────────────────────────────┐  │
│  │  Monitor Thread                                    │  │
│  │  Cada 5s: ¿chunk_i sin respuesta por >15s?        │  │
│  │  SÍ → log "[!] FALLO DETECTADO" + re-encolar      │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌──────────┐                      ┌─────────────────┐  │
│  │  Joiner  │ ◄──────────────────  │  Worker 2 (k8s) │  │
│  │  (join)  │                      └─────────────────┘  │
│  └──────────┘                                           │
└─────────────────────────────────────────────────────────┘
```

## Ejecución local (Docker)

### 1. Preparar la imagen de prueba
```bash
cp ../parte_2_distribuido/imagen_prueba.jpg .
```

### 2. Construir las imágenes Docker

```bash
# Worker
cd worker
docker build -t sobel-worker-ft .
cd ..

# Master (requiere imagen_prueba.jpg en el directorio)
docker build -t sobel-master-ft .
```

### 3. Levantar RabbitMQ

```bash
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

### 4. Levantar los Workers

```bash
# Worker normal
docker run -d --name worker-ft-1 --net host -e RABBIT_HOST=localhost -e WORKER_ID=worker-1 sobel-worker-ft

# Worker lento (simulará un fallo/timeout para la demo)
docker run -d --name worker-ft-slow --net host \
  -e RABBIT_HOST=localhost \
  -e WORKER_ID=worker-slow \
  -e SIMULATE_SLOW=1 \
  -e SLOW_DELAY=30 \
  sobel-worker-ft
```

### 5. Ejecutar el Master

```bash
# Con entorno virtual activo
pip install -r requirements.txt
python master.py
```

### Demo de tolerancia a fallos

Con `SIMULATE_SLOW=1` el worker lento tardará 30 segundos por chunk. El Master detecta el timeout a los 15s y re-encola ese chunk. El worker normal lo procesa y el sistema completa la imagen exitosamente.

Salida esperada:
```
 [->] Chunk 0 enviado
 [->] Chunk 1 enviado  ← este lo toma el worker lento
 ...
 [!] FALLO DETECTADO — Chunk 1 sin respuesta por >15s. Reasignando (intento #1)...
 [v] Chunk 1 recibido (3/4)
 [V] Imagen guardada como 'resultado_ft.jpg'
```

---

## Ejecución en Kubernetes (local — microk8s / k3s)

### 1. Importar imágenes al cluster

**microk8s:**
```bash
docker save sobel-worker-ft | microk8s ctr image import -
docker save sobel-master-ft | microk8s ctr image import -
```

**k3s:**
```bash
docker save sobel-worker-ft | k3s ctr images import -
docker save sobel-master-ft | k3s ctr images import -
```

### 2. Desplegar

```bash
# RabbitMQ
kubectl apply -f k8s/rabbitmq.yaml

# Esperar a que RabbitMQ esté listo
kubectl wait --for=condition=available deployment/rabbitmq --timeout=60s

# Workers (2 réplicas por defecto)
kubectl apply -f k8s/worker-deployment.yaml

# Master (Job)
kubectl apply -f k8s/master-job.yaml
```

### 3. Ver logs

```bash
# Logs del master
kubectl logs -f job/sobel-master-ft

# Logs de los workers
kubectl logs -f deployment/sobel-worker-ft
```

### 4. Simular fallo en k8s

```bash
# Escalar a 0 un worker mientras procesa (simula crash)
kubectl scale deployment sobel-worker-ft --replicas=0

# El Master detecta el timeout y lo re-encola.
# Volver a escalar para que otro worker tome el trabajo:
kubectl scale deployment sobel-worker-ft --replicas=2
```

### 5. Limpiar

```bash
kubectl delete -f k8s/
```

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `RABBIT_HOST` | `localhost` | Hostname del broker RabbitMQ |
| `CANTIDAD_CHUNKS` | `4` | Número de partes en que se divide la imagen |
| `TIMEOUT_SEGUNDOS` | `15` | Segundos antes de considerar un chunk fallido |
| `IMAGEN` | `imagen_prueba.jpg` | Ruta de la imagen de entrada |
| `WORKER_ID` | `worker-0` | Identificador del worker (en k8s: `metadata.name`) |
| `SIMULATE_SLOW` | `0` | Poner en `1` para simular un worker lento (demo) |
| `SLOW_DELAY` | `30` | Segundos de demora en modo `SIMULATE_SLOW` |
