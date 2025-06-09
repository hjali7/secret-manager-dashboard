provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "secret-manager-cluster"
}

resource "kubernetes_namespace" "app_namespace" {
  metadata {
    name = var.app_namespace
  }
}