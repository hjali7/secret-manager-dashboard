variable "db_user" {}
variable "db_password" {}
variable "db_name" {}

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

  namespace = var.app_namespace
  db_user     = var.db_user
  db_password = var.db_password
  db_name     = var.db_name
  
  depends_on = [
    kubernetes_namespace.app_namespace
  ]
}

module "vault" {
  source = "../../modules/vault"
  namespace = kubernetes_namespace.app_namespace.metadata[0].name
  depends_on = [
    kubernetes_namespace.app_namespace
  ]
}

module "backend_app" {
  source = "../../modules/app/backend"

  namespce  = kubernetes_namespace.app_namespace.metadata[0].name
  image_name = "alihajizadeh/secret-backend:1.1.0"
  replicas   = 2

  depends_on = [
    module.database,
    module.vault
  ]
}