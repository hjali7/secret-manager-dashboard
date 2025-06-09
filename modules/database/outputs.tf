output "service_name" {
  description = "The name of the PostgreSQL service."
  value       = kubernetes_service.postgres_service.metadata[0].name
}