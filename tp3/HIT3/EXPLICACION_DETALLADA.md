# Resumen de Implementación - HIT #3 (Kubernetes y Resiliencia)

Acá dejamos anotado cómo armamos todo el Hit #3 para que cualquiera del grupo (o el profe al corregir) entienda rápido qué hay en cada archivo, en qué orden se levanta todo y qué le modificamos al código de Python.

---

## 1. Estructura de Archivos (Para no perdernos)

Como no queríamos pisar el código original del Hit #1, agarramos la carpeta entera de la app y la copiamos acá. Por eso hay un montón de archivos nuevos sin trackear en Git. Se dividen así:

* **Los que no tocamos (Copia exacta del Hit 1)**: `app/imagen_prueba.jpg`, `app/resultado_distribuido.jpg`, `app/requirements.txt`, `app/worker/Dockerfile`, `app/worker/requirements.txt`.
* **Los que modificamos (Para sumarle resiliencia)**: `app/worker/worker.py`, `app/joiner.py`, `app/splitter.py`.
* **Los que creamos desde cero**:
  * `app/dlq_monitor.py` (Un script nuevo para vigilar los errores).
  * `app/Dockerfile` (Un Dockerfile genérico para subir la app a K8s).
  * `terraform/gke/...` (Los `.tf` para levantar el cluster en Google).
  * `terraform/workers/...` (Los `.tf` para levantar las VMs dinámicas).
  * `k8s/...` (Los manifiestos `.yaml` de Kubernetes).
  * `.github/workflows/...` (Las Github Actions).

---

## 2. ¿Cómo es el flujo y el orden de ejecución?

Si bajamos el repo y queremos correr todo desde cero, este es el paso a paso que armamos:

### PASO 1: Levantar la Infra (Pipeline 1)
1. Corremos la Action **Pipeline 1** (`terraform_hit3_gke.yml`).
2. Terraform lee `gke/main.tf` y nos levanta un cluster de Kubernetes vacío en GCP con dos NodePools (`infra-pool` y `app-pool`).

### PASO 2: Desplegar los Servicios (Pipeline 1.1 y 1.2)
1. Corremos la Action `deploy_k8s_apps.yml`.
2. Github buildea nuestra imagen de Python y la pushea a Docker Hub.
3. El pipeline hace los `kubectl apply`. Primero levanta **RabbitMQ** en el `infra-pool`.
4. Después levanta los deployments del **Joiner** y del **DLQ Monitor** en el `app-pool`. Estos se quedan colgados esperando que llegue trabajo.

### PASO 3: Mandar el Trabajo
1. El mismo pipeline anterior ejecuta el job del **Splitter** (`k8s/splitter.yaml`).
2. El Splitter corre una sola vez, agarra la imagen, la corta y le llena la cola `tareas_sobel` a RabbitMQ. Cuando termina, el pod se muere solito (porque es un Job, no un Deployment).

### PASO 4: Levantar los Workers Dinámicos (Cloud Bursting)
1. Ahora tenemos la cola llena pero nadie la procesa. Nos vamos a Github Actions y ejecutamos a mano el **Pipeline 2** (`terraform_hit3_workers.yml`), pasándole por parámetro cuántos workers queremos (ej: 5).
2. El pipeline se fija qué IP pública le dio K8s a nuestro RabbitMQ.
3. Llama a Terraform (`workers/main.tf`) y levanta 5 máquinas de Compute Engine comunes y corrientes afuera del cluster.
4. Las máquinas instalan Docker, se bajan el código y arrancan el worker conectándose a la IP de RabbitMQ.

### PASO 5: El Procesamiento
1. Los 5 workers le dan con todo a la cola `tareas_sobel` y aplican OpenCV.
2. Si un chunk tira error de memoria (cae en el `except`), el worker hace un NACK y el mensaje cae en la DLQ. El **DLQ Monitor** lo ataja y lo devuelve a la fila principal para reintentar.
3. Si procesa bien, el worker publica el resultado en el exchange `resultados_exchange`.
4. El **Joiner**, que estaba escuchando ese exchange, agarra los pedazos, los concatena y guarda la imagen final.

### PASO 6: Apagar todo
1. Corremos el **Pipeline 2** pero en modo "destroy" para matar las VMs de los workers y no gastar créditos de más.

---

## 3. ¿Qué le cambiamos al código de Python?

El TP pedía sumarle resiliencia. Acá dejamos explicado qué hace cada cambio que metimos:

### A. Exponential Backoff (En `worker.py`, `joiner.py`, `splitter.py`)
Nos pasaba que si un pod arrancaba más rápido que RabbitMQ, la conexión de `pika` tiraba error y el contenedor se reiniciaba de golpe. Armamos esta función para que espere un ratito y reintente conectarse alargando la espera cada vez más (1s, 2s, 4s, 8s...).
```python
def connect_to_rabbit(host):
    max_retries = 5
    base_delay = 1
    max_delay = 30
    for attempt in range(max_retries):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host))
            return connection 
        except pika.exceptions.AMQPConnectionError as e:
            delay = min(base_delay * (2 ** attempt), max_delay)
            time.sleep(delay) 
    exit(1)
```

### B. Dead Letter Queue (`splitter.py`)
El Splitter es el que crea las colas. Le pasamos argumentos para que Rabbit sepa a dónde mandar los mensajes que los workers rechazan.
```python
# 1. Armamos el exchange direct y la cola para la DLQ
channel.exchange_declare(exchange='dlx_tareas', exchange_type='direct')
channel.queue_declare(queue='tareas_sobel_dlq', durable=True)
channel.queue_bind(exchange='dlx_tareas', queue='tareas_sobel_dlq', routing_key='tareas_sobel_dlq')

# 2. Le inyectamos los argumentos a la cola normal para vincularla a la DLQ
channel.queue_declare(queue="tareas_sobel", durable=True, arguments={
    'x-dead-letter-exchange': 'dlx_tareas',
    'x-dead-letter-routing-key': 'tareas_sobel_dlq'
})
```

### C. NACK en los Workers (`worker.py`)
Metimos el procesamiento de OpenCV adentro de un `try/except`. Si falla, tiramos un NACK sin requeue. Automáticamente Rabbit lo patea a la DLQ que armamos arriba.
```python
channel.exchange_declare(exchange='resultados_exchange', exchange_type='fanout')

def callback(ch, method, properties, body):
    try:
        # .. magia de OpenCV ...
        
        # En vez de mandar a una cola directa, publicamos en el exchange fanout
        ch.basic_publish(exchange="resultados_exchange", routing_key="", body=json.dumps(mensaje_resultado))
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        # Si tira error, le damos NACK y requeue=False para que caiga en la DLQ
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
```

### D. Pub/Sub con Fanout (`joiner.py`)
Para desacoplar el Joiner, ahora escucha un exchange de tipo Fanout (como si fuera un broadcast).
```python
channel.exchange_declare(exchange='resultados_exchange', exchange_type='fanout')

# Creamos una cola con nombre random que muere cuando el Joiner se apaga (exclusive=True)
result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue

# Bindeamos esta cola anónima al exchange para escuchar los resultados
channel.queue_bind(exchange='resultados_exchange', queue=queue_name)
channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
```

### E. El DLQ Monitor (`dlq_monitor.py`)
Este es un script nuevo que se queda escuchando la cola de errores `tareas_sobel_dlq`. Agarra el mensaje roto, espera 2 segundos, y lo vuelve a pushear a `tareas_sobel` para darle otra chance.
```python
def callback(ch, method, properties, body):
    time.sleep(2) 
    # Lo vuelve a meter en la principal
    ch.basic_publish(exchange="", routing_key="tareas_sobel", body=body)
    ch.basic_ack(delivery_tag=method.delivery_tag)
```

---

## 4. Los manifiestos de K8s (`k8s/`)

Armamos los yaml para levantar todo. Un ejemplo clave es el de RabbitMQ:
```yaml
apiVersion: apps/v1
kind: StatefulSet # Usamos StatefulSet porque Rabbit tiene estado (las colas)
metadata:
  name: rabbitmq
spec:
  replicas: 1
  template:
    spec:
      nodeSelector: 
        role: infra # Lo atamos al NodePool que NO es preemptible
      containers:
      - name: rabbitmq
        image: rabbitmq:3-management
        ports:
        - containerPort: 5672 
---
apiVersion: v1
kind: Service
metadata:
  name: rabbitmq
spec:
  type: LoadBalancer # Le pedimos a GCP una IP pública para que los workers externos lo vean
```

---

## 5. El Terraform del Cluster (`terraform/gke/main.tf`)

El cluster se arma separando la infra de la app, cumpliendo con la idea de Borg:
```hcl
resource "google_container_cluster" "primary" {
  name     = "sobel-cluster" 
  location = "us-central1-a" 
  remove_default_node_pool = true 
}

# NodePool de la App
resource "google_container_node_pool" "app_nodes" {
  name       = "app-pool"
  cluster    = google_container_cluster.primary.name
  
  autoscaling {
    min_node_count = 1 
    max_node_count = 3 
  }

  node_config {
    preemptible  = true # Usamos instancias spot baratas para los workers de python
    machine_type = "e2-medium" 
  }
}
```

---

## 6. La automatización del Hit 3 (Pipeline 2)

Para los workers elásticos usamos workflow_dispatch en Github Actions. Lo clave acá es el bucle que metimos para esperar a que Google nos asigne la IP del LoadBalancer antes de correr Terraform:
```yaml
    steps:
      - name: Obtener IP de RabbitMQ
        run: |
          IP=""
          # Nos quedamos loopeando hasta que devuelva una IP válida (porque GCP tarda unos minutos)
          while [ -z $IP ]; do
            IP=$(kubectl get svc rabbitmq -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
            [ -z "$IP" ] && sleep 5
          done
          echo "RABBIT_HOST=$IP" >> $GITHUB_ENV 

      - name: Terraform Apply
        if: inputs.action == 'apply' 
        run: terraform apply -auto-approve 
        env:
          TF_VAR_rabbitmq_host: ${{ env.RABBIT_HOST }} # Se lo pasamos a las VMs
```

---

## 💡 Nota / Pro-Tip sobre el DLQ Monitor
Para que no nos critiquen en la entrega: Si un chunk de imagen viene totalmente corrupto, va a fallar siempre. Si nuestro DLQ Monitor lo reencola ciegamente, vamos a generar un bucle infinito (*Poison Pill*). 
**Lo solucionamos** agregándole lógica al callback de `dlq_monitor.py` para que lea los headers `x-death` de RabbitMQ. Si vemos que el `count` llegó a 3, tiramos un log de "ALERTA" y le hacemos ACK de una para que muera definitivamente y no sature el cluster.

---

## 💡 Pro-Tip de Seguridad (Keyless Auth)
Como un extra para la arquitectura, decidimos **NO** usar claves JSON estáticas para que GitHub Actions se conecte a Google Cloud. Si un JSON se filtra, es un agujero de seguridad gravísimo. 
En su lugar, armamos todo usando **Workload Identity Federation (WIF / OIDC)**. Con esto, GitHub y GCP generan tokens temporales efímeros (que duran 1 horita y se autodestruyen) sin tener que guardar contraseñas fijas en los secretos del repo. ¡Un detalle de SRE puro!