output "service_name" {
  description = "The name of the backend service."
  value       = kubernetes_service.backend_service.metadata[0].name
}