resource "kubernetes_service_account" "backend_sa" {
  metadata {
    name      = "backend-sa"
    namespace = var.namespace
  }
}

resource "kubernetes_deployment" "backend" {
  metadata {
    name      = "backend-deployment"
    namespace = var.namespace
  }

  spec {
    replicas = 1
    selector {
      match_labels = {
        app = "backend"
      }
    }
    template {
      metadata {
        labels = {
          app = "backend"
        }
        annotations = {
          "vault.hashicorp.com/agent-inject"                 = "true"
          "vault.hashicorp.com/role"                         = "backend-role"
          "vault.hashicorp.com/agent-inject-secret-db-creds"   = "secret/data/database/postgres-creds"
          "vault.hashicorp.com/agent-inject-template-db-creds" = <<-EOT
            {{- with secret "secret/data/database/postgres-creds" -}}
            DB_USER={{ .Data.data.db_user }}
            DB_PASSWORD={{ .Data.data.db_password }}
            {{- end -}}
          EOT
        }
      }
      spec {
        service_account_name = kubernetes_service_account.backend_sa.metadata[0].name
        container {
          name  = "backend-container"
          image = var.image_name
          port {
            container_port = 8000
          }
          env {
            name = "DB_HOST"
            value = "postgres-service"
          }
          env {
            name = "DB_NAME"
            value = "secrets_db"
          }
          env {
            name  = "REDIS_HOST"
            value = "redis-service"
          }
          readiness_probe {
            http_get {
              path = "/health"
              port = 8000
            }
            initial_delay_seconds = 20
            period_seconds        = 10
            failure_threshold     = 6
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "backend_service" {
  metadata {
    name      = "backend-service"
    namespace = var.namespace
  }
  spec {
    selector = {
      app = "backend"
    }
    port {
      protocol    = "TCP"
      port        = 80
      target_port = 8000
    }
    type = "ClusterIP"
  }
}