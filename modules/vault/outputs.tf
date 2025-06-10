# modules/vault/outputs.tf

output "service_name" {
  description = "The name of the Vault service."
  value       = kubernetes_service.vault_service.metadata[0].name
}

output "cluster_ip" {
  description = "The ClusterIP of the Vault service."
  value       = kubernetes_service.vault_service.spec[0].cluster_ip
}