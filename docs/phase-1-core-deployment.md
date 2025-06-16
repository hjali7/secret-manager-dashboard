# Phase 1: Core Application & Infrastructure Deployment

## 1. Summary

This initial phase focused on establishing a robust, secure, and automated foundation for the "Secret Manager Dashboard" project. The primary goal was to deploy the core application components—a PostgreSQL database, a HashiCorp Vault server, and a Python-based backend API—onto a local Kubernetes cluster (Minikube). All infrastructure was defined as code using Terraform, and secrets management was handled by a production-style Vault installation, configured to integrate securely with Kubernetes.

## 2. Key Objectives Achieved

- **Infrastructure as Code (IaC):** Deployed all Kubernetes resources declaratively using a modular Terraform project structure.
- **Stateful Application Deployment:** Successfully deployed a PostgreSQL database with persistent storage using `PersistentVolumeClaim` (PVC) to ensure data durability across pod restarts.
- **Secure Secrets Management:** Deployed a production-ready, HA-capable HashiCorp Vault server using the official Helm chart.
- **Dynamic Secret Injection:** Implemented a secure pattern where the backend application fetches database credentials dynamically from Vault at runtime, using the Vault Agent Sidecar model. No secrets are hardcoded or stored in Kubernetes Secrets for the application.
- **Kubernetes & Vault Integration:** Configured a secure authentication mechanism between Kubernetes and Vault, allowing pods to authenticate using their Kubernetes Service Account identity.
- **Basic CI Pipeline:** Established a Continuous Integration pipeline using GitHub Actions to automatically build and push versioned Docker images to Docker Hub upon new Git tags.

## 3. Final Architecture

The architecture at the end of Phase 1 consists of three main services running in a dedicated namespace (`secret-manager-ns`) within the Kubernetes cluster.

**Logical Flow:**
`[Backend Pod]` <--> `[Vault Agent Sidecar]` <--> `[Vault Server]` ---> `[PostgreSQL Pod]`

- The **Backend Pod** contains two containers.
- The **Vault Agent Sidecar** authenticates with the Vault Server using the pod's Service Account.
- It retrieves the database credentials from Vault and writes them to a shared in-memory volume.
- The **Backend Application Container** reads the credentials from the shared volume and uses them to connect to the **PostgreSQL** database.

## 4. Core Technologies & Tools

- **Containerization:** Docker
- **Orchestration:** Kubernetes (via Minikube)
- **Infrastructure as Code:** Terraform
- **Package Management:** Helm (for Vault deployment)
- **Secrets Management:** HashiCorp Vault
- **Application Backend:** Python (FastAPI)
- **Database:** PostgreSQL
- **CI/CD:** GitHub Actions

## 5. Key Challenges & Solutions

This phase involved significant real-world troubleshooting, leading to a deeper understanding of the ecosystem.

- **Vault K8s Auth `Permission Denied`:** The Vault Agent consistently failed to authenticate. The root cause was an incomplete configuration of the Kubernetes Auth Method in Vault.
    - **Solution:** The issue was definitively resolved by `exec`-ing into the Vault server pod and running the `vault write auth/kubernetes/config ...` command from within the cluster. This allowed Vault to automatically discover the necessary K8s API information, including the correct `issuer`, and establish a trusted relationship.

- **Pod `Init:0/1` Status:** The backend pods were stuck in an `Init` state because the injected `vault-agent-init` container could not complete its task (due to the permission error above). This taught us how to debug multi-container pods by checking the logs of specific init containers (`kubectl logs -c vault-agent-init ...`).

- **Git Authentication:** Standard password authentication for `git push` was deprecated by GitHub.
    - **Solution:** A Personal Access Token (PAT) with `repo` scope was created and used in place of the account password for all Git command-line operations.