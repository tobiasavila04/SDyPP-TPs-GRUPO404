# Deploy en k3d-sobel (cluster local)

Todos los comandos usan `--context k3d-sobel` para no afectar el cluster de la empresa.

**Arquitectura:** RabbitMQ + Workers corren en k8s. El **splitter y el joiner corren local** y se conectan a RabbitMQ via port-forward. Así el `resultado_distribuido.jpg` queda directo en tu máquina.

## Prerequisitos

- k3d cluster `k3d-sobel` corriendo (`k3d cluster list`)
- Docker disponible
- Python con dependencias instaladas (`pip install pika opencv-python-headless numpy`)
- Estar parado en `tp3/HIT1/parte_2_distribuido/`

---

## Paso 1: Build de las imágenes

Solo el worker necesita imagen Docker. k3d no puede usar imágenes locales de Docker directamente — hay que importarlas.

```bash
# Worker (el Dockerfile está dentro de worker/)
docker build -f worker/Dockerfile -t sobel-worker:latest ./worker
```

Importar la imagen al cluster local:

```bash
k3d image import sobel-worker:latest -c sobel
```

---

## Paso 2: Deploy de los componentes en k8s

```bash
# RabbitMQ + Service
kubectl --context k3d-sobel apply -f k8s/rabbitmq.yaml

# Esperar que RabbitMQ esté listo antes de continuar
kubectl --context k3d-sobel wait --for=condition=available deployment/rabbitmq --timeout=90s

# Workers (2 réplicas)
kubectl --context k3d-sobel apply -f k8s/worker-deployment.yaml

# Esperar que los workers estén listos
kubectl --context k3d-sobel wait --for=condition=available deployment/sobel-worker --timeout=60s
```

---

## Paso 3: Port-forward de RabbitMQ

En una terminal aparte, dejá corriendo el port-forward para que el splitter y el joiner locales puedan conectarse:

```bash
kubectl --context k3d-sobel port-forward svc/rabbitmq-service 5672:5672
```

> Dejá esta terminal abierta mientras dure la ejecución.

---

## Paso 4: Correr el joiner local

En otra terminal, con el venv activado, desde `parte_2_distribuido/`:

```bash
RABBIT_HOST=localhost CANTIDAD_CHUNKS=4 python joiner.py
```

> El joiner tiene que estar escuchando **antes** de que el splitter envíe los chunks.

---

## Paso 5: Correr el splitter local

En otra terminal (o esperá que el joiner imprima `Esperando pedazos procesados`):

```bash
RABBIT_HOST=localhost CANTIDAD_CHUNKS=4 python splitter.py
```

El splitter parte la imagen y envía los chunks. Los workers los procesan con Sobel y el joiner ensambla el resultado.

---

## Paso 6: Resultado

Cuando el joiner imprima `¡Éxito! Imagen guardada`, el archivo queda en:

```
parte_2_distribuido/resultado_distribuido.jpg
```

Para ver los logs de los workers mientras procesa:

```bash
kubectl --context k3d-sobel logs -f deployment/sobel-worker
```

---

## Limpieza

```bash
kubectl --context k3d-sobel delete deployment sobel-worker rabbitmq
kubectl --context k3d-sobel delete service rabbitmq-service
```

Para re-correr simplemente volvé al Paso 4 (RabbitMQ y workers ya están corriendo).
