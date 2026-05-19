resource "google_compute_instance" "worker" {
  count        = var.worker_count
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
    
    # Asignamos una IP pública efímera para que pueda descargar Docker y salir a internet (conectar a Ngrok)
    access_config {
      network_tier = "PREMIUM"
    }
  }

  # Script de inicio para instalar dependencias y ejecutar la carga de trabajo
  metadata_startup_script = <<-EOF
    #!/bin/bash
    set -e
    
    # Actualizar e instalar Docker
    apt-get update
    apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io

    # Descargar y ejecutar la imagen del worker
    # Corregimos la inyección de variables de Terraform
    docker run -d --name sobel-worker --restart unless-stopped \
      -e RABBIT_HOST="${var.rabbitmq_host}" \
      ${var.worker_image}
  EOF

  tags = ["sobel-worker"]
}
