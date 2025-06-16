# Secret Manager Dashboard: A Cloud-Native Showcase Project

## 1. Overview

This project demonstrates a complete, secure, and automated workflow for deploying a multi-component application on Kubernetes. It serves as a comprehensive portfolio piece showcasing modern DevOps principles and Cloud-Native technologies.

The core application is a "Secret Manager Dashboard" built with a Python-based stack. The architecture emphasizes security, scalability, and automation, utilizing industry-standard tools like Terraform for Infrastructure as Code, Helm for package management, and HashiCorp Vault for state-of-the-art secrets management.

**Current Status (End of Phase 1):** The core backend infrastructure is fully deployed and operational. This includes a persistent PostgreSQL database, a production-style Vault server, and a backend API capable of securely and dynamically fetching database credentials from Vault.

## 2. Final Architecture (End of Project)

The target architecture consists of multiple services communicating securely within a Kubernetes cluster, with a single entry point for external traffic managed by an Ingress Controller.



\+-----------------------------------------------------------------------------------+
|  Kubernetes Cluster (Minikube)                                                    |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |  User via Browser                                                           |  |
|  +-----------------------------------------------------------------------------+  |
|        |                                                                        |
|        | [http://secret-manager.local](https://www.google.com/search?q=http://secret-manager.local)                                            |
|        v                                                                        |
|  +-----------------------------------------------------------------------------+  |
|  |  Ingress Controller (e.g., Nginx)                                           |  |
|  |  - Routes '/' to Frontend                                                   |  |
|  |  - Routes '/api' to Backend                                                 |  |
|  +-----------------------------------------------------------------------------+  |
|        |                          |                                             |
|        |                          |                                             |
|        v                          v                                             |
|  +------------------------+     +------------------------+                        |
|  |  Frontend Service (CIP) |     |   Backend Service (CIP)  |                        |
|  +------------------------+     +------------------------+                        |
|        |                          |                                             |
|        |                          |                                             |
|  +------------------------+     +------------------------+   +----------------+ |
|  | [Frontend Pod (NiceGUI)] |\<---\>|  [Backend Pod (API)]   |--\>| [Postgres Pod] | |
|  |                        |     |  + [Vault Agent Sidecar] |   +----------------+ |
|  +------------------------+     +------------------------+          |          |
|                                     |                             |          |
|                                     | (Auth via K8s Service Acct) | (PVC)      |
|                                     v                             v          |
|                                  +------------------------+  [Persistent Disk] |
|                                  | [Vault Server Pod (HA)]|                    |
|                                  +------------------------+                    |
|                                            |                                   |
|                                            | (PVC)                               |
|                                            v                                   |
|                                     [Persistent Disk]                          |
|                                                                                   |
\+-----------------------------------------------------------------------------------+


## 3. Prerequisites

Ensure you have the following tools installed and configured on your local machine (WSL2 is recommended on Windows):

**Minikube:** For running a local Kubernetes cluster.
**kubectl:** For interacting with the Kubernetes cluster.
**Docker:** For building and managing container images.
**Terraform (v1.3.0+):** For Infrastructure as Code.
**Helm (v3+):** For managing Kubernetes packages (used for Vault).
**Git:** For version control.
**A Docker Hub Account:** To store and pull container images.

## 4. Setup & Deployment (Phase 1 Guide)

This guide covers all steps to deploy the core infrastructure (PostgreSQL, Vault) and the backend application.

### Step 1: Clone the Repository

```bash
git clone [https://github.com/your-username/secret-manager-project.git](https://github.com/your-username/secret-manager-project.git)
cd secret-manager-project
````

### Step 2: Start the Local Kubernetes Cluster

This command creates a dedicated Minikube cluster (profile) for our project with the required resources.

```bash
minikube start -p secret-manager-cluster --driver=docker --memory=6g --cpus=4 --kubernetes-version=v1.28.3
```

### Step 3: Deploy HashiCorp Vault using Helm

We use the official HashiCorp Helm chart to deploy a production-ready, HA-capable Vault cluster with a persistent Raft storage backend.

```bash
# Add the HashiCorp Helm repository
helm repo add hashicorp [https://helm.releases.hashicorp.com](https://helm.releases.hashicorp.com)
helm repo update

# Install the Vault chart in its own namespace
helm install vault hashicorp/vault --namespace vault --create-namespace \
  --set "server.ha.enabled=true" \
  --set "server.ha.raft.enabled=true"
```

### Step 4: The Vault "Day-1 Ceremony" (Initialize & Unseal)

This is a **critical one-time setup** for a new, persistent Vault server.

1.Get a shell inside the `vault-0` pod:

    ```bash
    kubectl exec -it vault-0 -n vault -- /bin/sh
    ```

2.From inside the pod, initialize Vault:

    ```sh
    vault operator init
    ```

3.EXTREMELY IMPORTANT:** Copy the output of this command, which contains **5 Unseal Keys** and the **Initial Root Token**. Store these in a secure password manager. They are required to unseal Vault after every restart and cannot be recovered if lost.

4. Unseal the Vault by running the `vault operator unseal` command three times, each time with a different Unseal Key.

    ```sh
    vault operator unseal <UNSEAL_KEY_1>
    vault operator unseal <UNSEAL_KEY_2>
    vault operator unseal <UNSEAL_KEY_3>
    ```

5.  Verify the status. The `Sealed` status should now be `false`.

    ```sh
    vault status
    ```

6.  Exit the pod shell with `exit`.

### Step 5: Configure Vault for Kubernetes Authentication

This configures Vault to trust our application pods.

1.  **Port-forward** the Vault service in a dedicated terminal:

    ```bash
    kubectl port-forward service/vault 8200:8200 -n vault
    ```

2.  In a **new terminal**, set your environment variables. Use the Initial Root Token you saved from the previous step.

    ```bash
    export VAULT_ADDR='[http://127.0.0.1:8200](http://127.0.0.1:8200)'
    export VAULT_TOKEN=<YOUR_INITIAL_ROOT_TOKEN>
    ```

3.  Run the following commands to configure the K8s auth method, a policy for database access, and a role that links a Kubernetes Service Account to that policy.

    ```bash
    # Enable the K8s auth method
    vault auth enable kubernetes

    # Configure the auth method
    vault write auth/kubernetes/config \
        issuer="[https://kubernetes.default.svc](https://kubernetes.default.svc)" \
        kubernetes_host="[https://kubernetes.default.svc](https://kubernetes.default.svc)" \
        kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
        token_reviewer_jwt=@/var/run/secrets/kubernetes.io/serviceaccount/token

    # Create the policy
    vault policy write backend-db-policy - <<EOF
    path "secret/data/database/postgres-creds" {
      capabilities = ["read"]
    }
    EOF

    # Create the role
    vault write auth/kubernetes/role/backend-role \
        bound_service_account_names=backend-sa \
        bound_service_account_namespaces=secret-manager-ns \
        policies=backend-db-policy \
        ttl=24h

    # Create the secret our application will read
    vault kv put secret/database/postgres-creds db_user="padmin" db_password="SuperSecretPassword123"
    ```

### Step 6: Deploy Applications with Terraform

Now that the core security and database infrastructure is ready, we deploy our applications using Terraform.

1.  Navigate to the Terraform directory:
    ```bash
    cd infra/terraform
    ```
2.  Create a `terraform.tfvars` file with the required variables (database credentials).
3.  Initialize Terraform:
    ```bash
    terraform init
    ```
4.  Apply the configuration:
    ```bash
    terraform apply
    ```

## 5\. Verification

After a successful `terraform apply`:

1.  Check that all pods are running and ready in our application namespace:

    ```bash
    kubectl get pods -n secret-manager-ns
    ```

    You should see the `postgres-deployment` and `backend-deployment` pods in a `Running` state. The backend pod should be `READY 2/2`.

2.  Test the database connection via the backend API:

    ```bash
    # In one terminal:
    kubectl port-forward service/backend-service 8080:80 -n secret-manager-ns

    # In another terminal:
    curl http://localhost:8080/db-status
    ```

    The expected successful output is: `{"db_status":"connected_successfully_via_vault"}`.

<!-- end list -->