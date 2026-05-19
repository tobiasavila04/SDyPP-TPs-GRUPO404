output "cluster_name" {
  description = "Nombre del cluster K8s"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "Endpoint del cluster"
  value       = google_container_cluster.primary.endpoint
}
