resource "google_compute_network" "vpc" {
  name                    = "${var.cluster_name}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${var.cluster_name}-subnet"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.10.0.0/24"
}

# GKE Cluster
resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.zone

  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name

  # Configuraciones básicas para simplificar
  deletion_protection = false
}

# Nodegroup de Infraestructura (RabbitMQ, Redis)
resource "google_container_node_pool" "infra_nodes" {
  name       = "infra-pool"
  location   = var.zone
  cluster    = google_container_cluster.primary.name
  node_count = 1

  node_config {
    preemptible  = false # No queremos que la cola de mensajes muera al azar
    machine_type = "e2-medium"
    
    labels = {
      role = "infra"
    }

    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
  }
}

# Nodegroup de Aplicaciones (Splitter, Joiner, Backend)
resource "google_container_node_pool" "app_nodes" {
  name       = "app-pool"
  location   = var.zone
  cluster    = google_container_cluster.primary.name
  
  autoscaling {
    min_node_count = 1
    max_node_count = 3
  }

  node_config {
    preemptible  = true # Las apps son stateless, pueden correr en nodos baratos
    machine_type = "e2-medium"

    labels = {
      role = "apps"
    }

    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
  }
}
