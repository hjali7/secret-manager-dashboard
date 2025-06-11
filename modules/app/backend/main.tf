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