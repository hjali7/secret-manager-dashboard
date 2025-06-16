resource "kubernetes_deployment" "redis" {
  metadata {
    name      = "redis-deployment"
    namespace = var.namespace
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "redis" } }
    template {
      metadata { labels = { app = "redis" } }
      spec {
        container {
          name  = "redis"
          image = "redis:7-alpine"
          port { container_port = 6379 }

          readiness_probe {
            tcp_socket { port = 6379 }
            initial_delay_seconds = 5
            period_seconds        = 10
          }
          liveness_probe {
            tcp_socket { port = 6379 }
            initial_delay_seconds = 15
            period_seconds        = 20
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "redis_service" {
  metadata {
    name      = "redis-service"
    namespace = var.namespace
  }
  spec {
    selector = { app = "redis" }
    port {
      protocol = "TCP"
      port = 6379
      target_port = 6379
    }
    type = "ClusterIP"
  }
}