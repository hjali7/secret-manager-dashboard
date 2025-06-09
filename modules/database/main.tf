resource "kubernetes_secret" "postgres_secret" {
  metadata {
    name      = "postgres-secret"
    namespace = var.namespace
  }
  data = {
    "POSTGRES_USER"     = "padmin"
    "POSTGRES_PASSWORD" = "SuperSecretPassword123" # در پروژه واقعی این باید از جای امن‌تری بیاید
    "POSTGrofoam_DB"        = "secrets_db"
  }
  type = "Opaque"
}

resource "kubernetes_persistent_volume_claim" "postgres_pvc" {
  metadata {
    name      = "postgres-pvc"
    namespace = var.namespace
  }
  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = "1Gi"
      }
    }
  }
}

resource "kubernetes_deployment" "postgres" {
  metadata {
    name      = "postgres-deployment"
    namespace = var.namespace
  }
  spec {
    replicas = 1
    selector {
      match_labels = {
        app = "postgres"
      }
    }
    template {
      metadata {
        labels = {
          app = "postgres"
        }
      }
      spec {
        container {
          name  = "postgres"
          image = "postgres:14-alpine"
          port {
            container_port = 5432
          }
          env_from {
            secret_ref {
              name = kubernetes_secret.postgres_secret.metadata[0].name
            }
          }
          volume_mount {
            name       = "postgres-storage"
            mount_path = "/var/lib/postgresql/data"
          }
        }
        volume {
          name = "postgres-storage"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.postgres_pvc.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "postgres_service" {
  metadata {
    name      = "postgres-service"
    namespace = var.namespace
  }
  spec {
    selector = {
      app = "postgres"
    }
    port {
      protocol    = "TCP"
      port        = 5432
      target_port = 5432
    }
    type = "ClusterIP"
  }
}