output "worker_ips" {
  description = "Direcciones IP públicas de los workers de Sobel"
  value       = google_compute_instance.worker[*].network_interface[0].access_config[0].nat_ip
}

output "worker_names" {
  description = "Nombres de los workers creados"
  value       = google_compute_instance.worker[*].name
}
