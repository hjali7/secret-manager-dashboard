# Phase 2: CI/CD Pipeline Implementation

## 1. Summary

This phase focused on automating the build and release process of our backend application, transitioning from manual local builds to a structured, repeatable, and automated workflow. We implemented a **Continuous Integration (CI)** pipeline using GitHub Actions and established a **Continuous Delivery (CD)** process based on conscious, declarative updates via Terraform.

## 2. Key Objectives Achieved

-   **Automated Docker Builds:** Created a GitHub Actions workflow (`backend-ci.yaml`) that automatically builds a new Docker image of the backend application whenever a new Git tag is pushed.
-   **Automated Image Publishing:** The CI workflow automatically pushes the newly built image to a container registry (Docker Hub).
-   **Dynamic & Semantic Versioning:** Implemented a smart tagging strategy using `docker/metadata-action`. Each image is tagged with the specific Git tag (e.g., `v1.4.0`), providing clear versioning and traceability. The `:latest` tag is also updated to point to the most recent official release.
-   **Secure Credential Management in CI/CD:** Utilized GitHub Secrets (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`) to securely provide credentials to the workflow, avoiding hardcoded secrets in the code.
-   **Semi-Automated Deployment (Continuous Delivery):** Established a safe and deliberate deployment process. The CI pipeline prepares the release artifact (the Docker image), but the final deployment is a conscious act performed by the engineer. This is achieved by:
    1.  Automatically building the image via a Git tag push.
    2.  Manually updating the image tag in the root Terraform configuration (`main.tf`).
    3.  Committing this change to Git to keep the repository as the single source of truth.
    4.  Running `terraform apply` from the local machine to roll out the new version.

## 3. Core Technologies & Tools

-   **CI/CD Platform:** GitHub Actions
-   **Versioning Strategy:** Git Tags (for triggering releases)
-   **Key GitHub Actions:**
    -   `actions/checkout@v4`
    -   `docker/login-action@v3`
    -   `docker/metadata-action@v5`
    -   `docker/build-push-action@v5`

## 4. Challenges & Solutions

-   **Git Authentication Failure:** The initial attempt to `git push` a new tag failed due to GitHub's deprecation of password-based authentication for Git operations.
    -   **Solution:** A **Personal Access Token (PAT)** with `repo` scope was generated in GitHub settings and used in place of the account password on the command line.

-   **CI Workflow `invalid tag` Error:** The first run of the workflow failed because the Docker image tag was being generated without the Docker Hub username.
    -   **Solution:** The root cause was a missing or incorrectly named `DOCKER_USERNAME` secret in the repository's settings. By creating the secret with the correct name and value, the `docker/metadata-action` was able to generate the proper, fully-qualified image tag (`username/repo:tag`).