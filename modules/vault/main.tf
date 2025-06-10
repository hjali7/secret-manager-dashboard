resource "kubernetes_config_map" "vault_config" {
  metadata {
    name      = "vault-config"
    namespace = var.namespace
  }
  data = {
    "vault.hcl" = <<-EOT
      ui = true
      
      storage "raft" {
        path    = "/vault/data"
        node_id = "vault-node-1"
      }
      
      listener "tcp" {
        address     = "0.0.0.0:8200"
        tls_disable = true
      }
      api_addr = "http://vault-service.${var.namespace}.svc.cluster.local:8200"
      cluster_addr = "http://vault-service.${var.namespace}.svc.cluster.local:8201"
    EOT
  }
}

resource "kubernetes_persistent_volume_claim" "vault_pvc" {
  metadata {
    name      = "vault-pvc"
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

resource "kubernetes_service_account" "vault" {
  metadata {
    name      = "vault"
    namespace = var.namespace
  }
}

resource "kubernetes_deployment" "vault" {
  metadata {
    name      = "vault-deployment"
    namespace = var.namespace
  }
  spec {
    replicas = 1
    selector {
      match_labels = {
        app = "vault"
      }
    }
    template {
      metadata {
        labels = {
          app = "vault"
        }
      }
      spec {
        service_account_name = kubernetes_service_account.vault.metadata[0].name
        container {
          name  = "vault"
          image = "hashicorp/vault:1.16"

          command = [
            "vault",
            "server",
            "-config=/vault/config/vault.hcl"
          ]

          port {
            container_port = 8200
          }

          security_context {
            capabilities {
              add = ["IPC_LOCK"]
            }
          }

          volume_mount {
            name       = "vault-config-volume"
            mount_path = "/vault/config"
          }
          volume_mount {
            name       = "vault-data-volume"
            mount_path = "/vault/data"
          }
        }

        volume {
          name = "vault-config-volume"
          config_map {
            name = kubernetes_config_map.vault_config.metadata[0].name
          }
        }
        volume {
          name = "vault-data-volume"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.vault_pvc.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "vault_service" {
  metadata {
    name      = "vault-service"
    namespace = var.namespace
  }
  spec {
    selector = {
      app = "vault"
    }
    port {
      name        = "api"
      protocol    = "TCP"
      port        = 8200
      target_port = 8200
    }
    port {
      name        = "cluster"
      protocol    = "TCP"
      port        = 8201
      target_port = 8201
    }
    type = "ClusterIP"
  }
}