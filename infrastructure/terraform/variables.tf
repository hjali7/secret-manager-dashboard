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