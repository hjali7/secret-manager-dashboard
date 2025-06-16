output "service_name" {
  description = "The name of the Redis service."
  value       = kubernetes_service.redis_service.metadata[0].name
}