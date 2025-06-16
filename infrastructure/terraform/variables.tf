# infra/terraform/variables.tf

variable "app_namespace" {
  description = "The Kubernetes namespace for the entire application."
  type        = string
  default     = "secret-manager-ns"
}

variable "k8s_context" {
  description = "The kubectl context to use."
  type        = string
  default     = "secret-manager-cluster"
}

variable "db_user" {
  description = "The root user for the database."
  type        = string
  sensitive   = true 
}

variable "db_password" {
  description = "The root password for the database."
  type        = string
  sensitive   = true 
}

variable "db_name" {
  description = "The name of the database."
  type        = string
}