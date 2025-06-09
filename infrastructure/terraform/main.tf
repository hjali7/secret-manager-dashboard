provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = var.k8s_context
}

resource "kubernetes_namespace" "app_namespace" {
  metadata {
    name = var.app_namespace
  }
}

module "database" {
  source = "../../modules/database"

  namespace = kubernetes_namespace.app_namespace.metadata[0].name

  depends_on = [
    kubernetes_namespace.app_namespace
  ]
}