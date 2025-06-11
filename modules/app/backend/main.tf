resource "kubernetes_deployment" "backend" {
  metadata {
    name      = "backend-deployment"
    namespace = var.namespce
    labels = {
      app = "backend"
    }
  }

  spec {
    replicas = var.replicas

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
      }
      spec {
        container {
          name  = "backend-container"
          image = var.image_name 

          port {
            container_port = 8000
          }
          env {
            # نام متغیری که اپلیکیشن پایتون انتظار دارد
            name = "DB_USER"
            value_from {
              secret_key_ref {
                # ارجاع به سکرت دیتابیس
                name = "postgres-secret"
                # کلیدی که در آن سکرت وجود دارد
                key  = "POSTGRES_USER"
              }
            }
          }

          env {
            name = "DB_PASSWORD"
            value_from {
              secret_key_ref {
                name = "postgres-secret"
                key  = "POSTGRES_PASSWORD"
              }
            }
          }

          env {
            name = "DB_NAME"
            value_from {
              secret_key_ref {
                name = "postgres-secret"
                key  = "POSTGRES_DB"
              }
            }
          }

          env {
            name  = "DB_HOST"
            value = "postgres-service"
          }

          readiness_probe {
            http_get {
              path = "/health"
              port = 8000
            }
            initial_delay_seconds = 5
            period_seconds        = 10
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "backend_service" {
  metadata {
    name      = "backend-service"
    namespace = var.namespce
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