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

  namespace   = var.app_namespace
  db_user     = var.db_user
  db_password = var.db_password
  db_name     = var.db_name

  depends_on = [kubernetes_namespace.app_namespace]
}

module "backend_app" {
  source = "../../modules/app/backend"

  namespace  = var.app_namespace
  image_name = "alihajizadeh/secret-backend:v2.2.1"
  replicas   = 1
  depends_on = [module.database]
}

module "redis" {
  source = "../../modules/redis"
  namespace = var.app_namespace
  depends_on = [kubernetes_namespace.app_namespace]
}