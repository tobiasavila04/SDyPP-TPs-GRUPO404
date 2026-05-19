# Resumen de Implementación - HIT #2 (Cloud Bursting)

Acá dejamos anotado todo el flujo del sistema de offloading (cloud-bursting) que armamos para el Hit 2. La idea de este archivo es que cualquiera del grupo entienda qué hace cada script y cómo se levantan las máquinas en GCP.

---

## 1. El Flujo de nuestra solución

Imagínense que estamos procesando un montón de imágenes en la notebook de alguno de nosotros (On-premise) y de repente la cola de RabbitMQ se rebalza de tareas. Para solucionar esto armamos el patrón de **Cloud Bursting** (Desbordamiento a la nube) que funciona así:

1. **Invocamos al Orquestador:** Corremos a mano el archivo `orquestador.py` en nuestra terminal.
2. **Aprovisionamiento (Provisioning):** El orquestador tira los comandos de Terraform (`init` y `apply`) por atrás. Terraform va, habla con Google Cloud (GCP) y nos pide la creación de las VMs que le hayamos configurado.
3. **Inicialización (Bootstrap):** Ni bien prenden las VMs en Google, se corre un script de inicio (`metadata_startup_script` en el archivo `main.tf`). Este script actualiza el Linux de la máquina, le instala Docker y baja nuestra imagen con el código del worker de Sobel.
4. **Despliegue y Conexión (Deploy & Join):** El contenedor Docker arranca y se conecta al toque a nuestro RabbitMQ local (pasando por el túnel de Ngrok). Ni bien se conecta, arranca a "robar" trabajo de la cola, le manda CPU al filtro Sobel y devuelve los pedazos de la imagen listos.
5. **Destrucción (Teardown):** Cuando vemos que ya se vació la cola y el Joiner armó la foto, volvemos a la terminal del orquestador y apretamos ENTER. Ahí se corre un `terraform destroy`, GCP apaga y borra las VMs y dejamos de gastar plata.

---

## 2. Los archivos que armamos (Explicación paso a paso)

### `terraform/provider.tf`
**¿Qué hace?** Le avisa a Terraform que vamos a laburar con Google Cloud. También le configura el backend "remoto". Esto significa que el `.tfstate` (el archivo que recuerda qué máquinas están prendidas) se guarda en un Bucket de GCS en la nube. Así, si otro del grupo corre el orquestador, Terraform lee el mismo estado y no arma un lío.

```hcl
terraform {
  required_version = ">= 1.3.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "sdypp-terraform-state-bucket" # El bucket que creamos en GCP
    prefix = "terraform/state/hit2"
  }
}

provider "google" {
  project = var.project_id # Sacamos el ID de nuestro proyecto
  region  = var.region
  zone    = var.zone
}
```

### `terraform/variables.tf`
**¿Qué hace?** Acá dejamos todos los parámetros parametrizados para no tener que andar hardcodeando valores adentro del `main.tf`.

```hcl
variable "project_id" {
  description = "ID del proyecto de GCP"
  type        = string
}

variable "region" {
  description = "Región de GCP"                  
  type        = string                           
  default     = "us-central1"
}

variable "zone" {
  description = "Zona de GCP"                    
  type        = string                           
  default     = "us-central1-a"                  
}

variable "machine_type" {
  description = "Tipo de máquina para los workers"
  type        = string                           
  default     = "e2-micro" # Usamos la más barata para no quemar saldo
}

variable "worker_count" {
  description = "Cantidad de nodos worker"
  type        = number                           
  default     = 2 # Levantamos 2 por defecto
}

variable "rabbitmq_host" {
  description = "IP/Dominio de Ngrok"
  type        = string                           
}

variable "worker_image" {
  description = "Imagen Docker del worker"
  type        = string                           
  default     = "miusuario/sobel-worker:latest"
}
```

### `terraform/main.tf`
**¿Qué hace?** Este es el archivo groso. Acá definimos las VMs que Google nos tiene que crear.

```hcl
resource "google_compute_instance" "worker" {
  count        = var.worker_count # Creamos tantas VMs como diga la variable
  name         = "sobel-worker-${count.index + 1}"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 10
    }
  }

  network_interface {
    network = "default"
    
    access_config {
      network_tier = "PREMIUM" # Le pedimos IP pública para poder salir a internet y llegar a Ngrok
    }
  }

  # El script que corre Google automáticamente apenas prende la VM
  metadata_startup_script = <<-EOF
    #!/bin/bash
    set -e
    
    # Bajamos e instalamos Docker
    apt-get update                               
    apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io

    # Corremos nuestro contenedor pasándole la URL de ngrok en la variable RABBIT_HOST
    docker run -d --name sobel-worker --restart unless-stopped \
      -e RABBIT_HOST="${var.rabbitmq_host}" \
      ${var.worker_image}
  EOF

  tags = ["sobel-worker"]
}
```

### `terraform/outputs.tf`
**¿Qué hace?** Cuando Terraform termina de hacer la magia, esto escupe en la terminal información que nos sirve (las IPs que nos dieron).

```hcl
output "worker_ips" {
  description = "IPs públicas de los workers"
  value       = google_compute_instance.worker[*].network_interface[0].access_config[0].nat_ip
}

output "worker_names" {
  description = "Nombres de los workers creados"
  value       = google_compute_instance.worker[*].name
}
```

### `orquestador.py`
**¿Qué hace?** Es el script en Python que usamos localmente para automatizar los comandos de Terraform. Así no tenemos que tipear a mano la inyección de las variables.

```python
import os
import subprocess
import sys
import time

def run_command(command, cwd=None):
    print(f"\n--- Ejecutando: {' '.join(command)} ---")
    result = subprocess.run(command, cwd=cwd)
    if result.returncode != 0:
        print(f"Error al ejecutar el comando: {' '.join(command)}")
        sys.exit(result.returncode)
    return result.returncode

def main():
    print("Iniciando Orquestador Cloud Bursting - HIT #2")

    # Nos aseguramos de tener seteadas las credenciales y el host local
    if "TF_VAR_project_id" not in os.environ:    
        print("ERROR: Falta TF_VAR_project_id")
        sys.exit(1)
        
    if "TF_VAR_rabbitmq_host" not in os.environ:
        print("ERROR: Falta TF_VAR_rabbitmq_host")
        sys.exit(1)

    terraform_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "terraform")

    print("\n[Paso 1] Levantando workers...")
    run_command(["terraform", "init"], cwd=terraform_dir)
    run_command(["terraform", "apply", "-auto-approve"], cwd=terraform_dir)

    print("\n[INFO] Esperando un ratito a que instalen Docker...")
    time.sleep(60)

    print("\n[Paso 2] Listo. Ya podés correr el splitter y el joiner en la otra consola.")
    print("Cuando quieras apagar los workers para no gastar, apretá ENTER acá...")
    input() # Queda colgado hasta que le demos ENTER

    print("\n[Paso 3] Destruyendo todo...")
    run_command(["terraform", "destroy", "-auto-approve"], cwd=terraform_dir)

if __name__ == "__main__":
    main()
```

### `.github/workflows/terraform_hit2.yml` (Nuestra action de validación)
**¿Qué hace?** Armamos una GitHub Action para que, cuando alguno de nosotros mande un Pull Request tocando la carpeta `terraform/`, un runner se encargue de validar que el código no esté roto. 

**¿Qué hace exactamente la Action?**
1. Clona el repo y baja Terraform.
2. Revisa que el código esté bien formateado (`terraform fmt`).
3. Hace un chequeo de sintaxis (`terraform validate`).
4. Corre un simulacro (`terraform plan`) y nos comenta en el PR qué cosas cambiarían si mergeamos.
5. *(Nota: Decidimos NO meter un paso de `terraform apply` automático acá, porque los workers de este Hit necesitan la URL temporal de Ngrok de nuestra compu local, y el pipeline de Github no tiene forma de saber cuál es. Así que el despliegue real siempre lo manejamos desde la compu local con el orquestador).*
