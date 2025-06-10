ui = true
storage "raft" {
    path = "/vault/data"
    node_id = "vault-node-1"
}

listener "tcp" {
    address = "0.0.0.0:8200"
    tls_disable = true
}