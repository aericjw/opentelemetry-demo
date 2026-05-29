# Build Images on Kubernetes Runners Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build all OpenTelemetry Demo service images on self-hosted GitHub Actions runners running in the user's Kubernetes cluster (ARC + DinD) and push them to Docker Hub.

**Architecture:** Install Actions Runner Controller (ARC) runner scale sets via Helm, configured in DinD container mode so each ephemeral runner pod gets a privileged Docker-in-Docker sidecar. A new manual workflow targets that scale set (`runs-on: otel-demo-builders`) and runs the existing ~24-service `docker buildx` multi-arch matrix, pushing to Docker Hub.

**Tech Stack:** GitHub Actions, Actions Runner Controller (gha-runner-scale-set Helm charts), Docker Buildx + QEMU, Helm, Kubernetes.

**Note on testing:** This plan produces YAML config (Helm values, a workflow, a README), not application code — there are no unit tests. "Verification" steps are YAML syntax checks (`python3 -c 'yaml.safe_load'`) and a `helm template` dry-run, which is the appropriate validation for this artifact type.

**Reference — pinned action SHAs (reuse verbatim from `.github/workflows/component-build-images.yml`):**
- `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd`  # v6.0.2
- `docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121`  # v4.1.0
- `docker/setup-qemu-action@ce360397dd3f832beb865e1373c09c0e9f86d70a`  # v4.0.0
- `docker/setup-buildx-action@4d04d5d9486b7bd6fa91e7baf45bbb4f8b9deedd`  # v4.0.0
- `docker/build-push-action@bcafcacb16a39f128d818304e6c9c0c18556b85f`  # v7.1.0

---

### Task 1: ARC runner scale set Helm values

**Files:**
- Create: `kubernetes/arc/runner-scale-set-values.yaml`

- [ ] **Step 1: Write the values file**

```yaml
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Helm values for the gha-runner-scale-set chart.
# Installed as release name "otel-demo-builders" -> this is the `runs-on` label.
#   helm install otel-demo-builders \
#     oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
#     --namespace arc-runners --create-namespace \
#     -f kubernetes/arc/runner-scale-set-values.yaml

# Repository (or org) the runners attach to.
githubConfigUrl: "https://github.com/aericjw/opentelemetry-demo"

# Kubernetes Secret holding the GitHub App credentials (created in the README).
githubConfigSecret: arc-github-app

# Scale bounds. minRunners: 0 keeps the cluster idle-cost-free; bump if you
# want warm runners. maxRunners caps concurrent build pods.
minRunners: 0
maxRunners: 3

# DinD container mode: each runner pod gets a privileged docker:dind sidecar,
# so `docker buildx` works exactly like on GitHub-hosted runners.
containerMode:
  type: dind

# Give the runner container enough headroom for multi-arch image builds.
template:
  spec:
    containers:
      - name: runner
        image: ghcr.io/actions/actions-runner:latest
        command: ["/home/runner/run.sh"]
        resources:
          requests:
            cpu: "2"
            memory: 4Gi
          limits:
            cpu: "4"
            memory: 8Gi
```

- [ ] **Step 2: Verify YAML syntax**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('kubernetes/arc/runner-scale-set-values.yaml')); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add kubernetes/arc/runner-scale-set-values.yaml
git commit -m "feat(arc): runner scale set Helm values (DinD mode)"
```

---

### Task 2: Validate values against the real chart

**Files:** none (validation only)

- [ ] **Step 1: Render the chart with these values (dry-run)**

Run:
```bash
helm template otel-demo-builders \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
  --namespace arc-runners \
  -f kubernetes/arc/runner-scale-set-values.yaml \
  --set githubConfigSecret.github_token=dummy \
  > /tmp/arc-render.yaml 2>/tmp/arc-render.err; echo "exit=$?"
```
Expected: `exit=0`. If Helm reports an unknown/invalid value key, fix `runner-scale-set-values.yaml` to match the chart's schema, then re-run.

Note: the `--set githubConfigSecret.github_token=dummy` only satisfies the chart's render-time validation; the real secret is the App-based `arc-github-app` referenced by name in the values file.

- [ ] **Step 2: Sanity-check the rendered output mentions DinD**

Run: `grep -c "dind" /tmp/arc-render.yaml`
Expected: a number `>= 1` (the dind sidecar is present).

- [ ] **Step 3: No commit** (validation produced no file changes).

---

### Task 3: ARC install README

**Files:**
- Create: `kubernetes/arc/README.md`

- [ ] **Step 1: Write the README**

````markdown
# GitHub Actions Runners on Kubernetes (ARC)

Runs the image-build workflow (`.github/workflows/k8s-build-images.yml`) on
self-hosted runners in this cluster, using Actions Runner Controller (ARC) in
DinD mode.

## 1. Create a GitHub App

In **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**:

- **Repository permissions:** Actions: Read and write, Administration: Read and
  write (for self-hosted runner registration), Metadata: Read-only.
- No webhook needed (uncheck Active).
- Create the app, then **Install** it on `aericjw/opentelemetry-demo`.
- Record the **App ID**, the **Installation ID** (from the install URL), and
  generate + download a **private key** (`.pem`).

## 2. Create the credentials Secret

```bash
kubectl create namespace arc-runners

kubectl create secret generic arc-github-app \
  --namespace arc-runners \
  --from-literal=github_app_id=<APP_ID> \
  --from-literal=github_app_installation_id=<INSTALLATION_ID> \
  --from-file=github_app_private_key=<PATH_TO_PEM>
```

(PAT alternative — simpler, less secure: replace the three literals above with
`--from-literal=github_token=<PAT_WITH_REPO_SCOPE>`.)

## 3. Install the controller

```bash
helm install arc \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller \
  --namespace arc-systems --create-namespace
```

## 4. Install the runner scale set

```bash
helm install otel-demo-builders \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
  --namespace arc-runners \
  -f runner-scale-set-values.yaml
```

The release name `otel-demo-builders` is the `runs-on` label the workflow uses.

## 5. Verify

```bash
kubectl get pods -n arc-systems          # controller + listener Running
kubectl get autoscalingrunnerset -n arc-runners
```

In the repo: **Settings → Actions → Runners** should list `otel-demo-builders`.

## 6. Required GitHub repo secrets

The build workflow pushes to Docker Hub. Add under **Settings → Secrets and
variables → Actions**:

- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`

## Trigger a build

**Actions → "Build images on Kubernetes runners" → Run workflow.**
````

- [ ] **Step 2: Commit**

```bash
git add kubernetes/arc/README.md
git commit -m "docs(arc): install guide for Kubernetes runners"
```

---

### Task 4: The build workflow

**Files:**
- Create: `.github/workflows/k8s-build-images.yml`

- [ ] **Step 1: Write the workflow**

Copy the matrix block (the ~24 `file_tag` entries) verbatim from
`.github/workflows/component-build-images.yml:56-152`. The full file:

```yaml
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
name: Build images on Kubernetes runners

on:
  workflow_dispatch:
    inputs:
      version:
        description: The version used when tagging the image
        default: 'dev'
        required: false
        type: string
      dockerhub_repo:
        description: Docker Hub repository
        default: 'otel/demo'
        required: false
        type: string

permissions:
  contents: read

jobs:
  build_and_push_images:
    runs-on: otel-demo-builders
    strategy:
      fail-fast: false
      matrix:
        file_tag:
          - file: ./src/accounting/Dockerfile
            tag_suffix: accounting
            context: ./
          - file: ./src/ad/Dockerfile
            tag_suffix: ad
            context: ./
          - file: ./src/cart/src/Dockerfile
            tag_suffix: cart
            context: ./
          - file: ./src/checkout/Dockerfile
            tag_suffix: checkout
            context: ./
          - file: ./src/currency/Dockerfile
            tag_suffix: currency
            context: ./
          - file: ./src/email/Dockerfile
            tag_suffix: email
            context: ./
          - file: ./src/flagd-ui/Dockerfile
            tag_suffix: flagd-ui
            context: ./
          - file: ./src/fraud-detection/Dockerfile
            tag_suffix: fraud-detection
            context: ./
          - file: ./src/frontend/Dockerfile
            tag_suffix: frontend
            context: ./
          - file: ./src/frontend-proxy/Dockerfile
            tag_suffix: frontend-proxy
            context: ./
          - file: ./src/frontend/Dockerfile.cypress
            tag_suffix: frontend-tests
            context: ./
          - file: ./src/image-provider/Dockerfile
            tag_suffix: image-provider
            context: ./
          - file: ./src/kafka/Dockerfile
            tag_suffix: kafka
            context: ./
          - file: ./src/llm/Dockerfile
            tag_suffix: llm
            context: ./
          - file: ./src/load-generator/Dockerfile
            tag_suffix: load-generator
            context: ./
          - file: ./src/opensearch/Dockerfile
            tag_suffix: opensearch
            context: ./
          - file: ./src/payment/Dockerfile
            tag_suffix: payment
            context: ./
          - file: ./src/product-catalog/Dockerfile
            tag_suffix: product-catalog
            context: ./
          - file: ./src/product-reviews/Dockerfile
            tag_suffix: product-reviews
            context: ./
          - file: ./src/quote/Dockerfile
            tag_suffix: quote
            context: ./
          - file: ./src/recommendation/Dockerfile
            tag_suffix: recommendation
            context: ./
          - file: ./src/shipping/Dockerfile
            tag_suffix: shipping
            context: ./
          - file: ./src/telemetry-docs/Dockerfile
            tag_suffix: telemetry-docs
            context: ./
          - file: ./test/tracetesting/Dockerfile
            tag_suffix: traceBasedTests
            context: ./

    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Load environment variables from .env file
        run: |
          if [ -f .env ]; then
            grep -vE '^\s*#|^\s*$' .env | while read -r line; do
              echo "$line" >> $GITHUB_ENV
            done
          else
            echo ".env file not found!"
            exit 1
          fi
      - name: Log in to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121  # v4.1.0
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Set up QEMU
        uses: docker/setup-qemu-action@ce360397dd3f832beb865e1373c09c0e9f86d70a  # v4.0.0
        with:
          image: tonistiigi/binfmt:master
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@4d04d5d9486b7bd6fa91e7baf45bbb4f8b9deedd  # v4.0.0
        with:
          buildkitd-config-inline: |
            [worker.oci]
            max-parallelism = 2
      - name: Build and push demo image
        uses: docker/build-push-action@bcafcacb16a39f128d818304e6c9c0c18556b85f  # v7.1.0
        with:
          context: ${{ matrix.file_tag.context }}
          file: ${{ matrix.file_tag.file }}
          platforms: linux/amd64,linux/arm64
          push: true
          build-args: |
            OTEL_JAVA_AGENT_VERSION=${{ env.OTEL_JAVA_AGENT_VERSION }}
            OPENTELEMETRY_CPP_VERSION=${{ env.OPENTELEMETRY_CPP_VERSION }}
            TRACETEST_IMAGE_VERSION=${{ env.TRACETEST_IMAGE_VERSION }}
            OPENSEARCH_IMAGE=${{ env.OPENSEARCH_IMAGE }}
          tags: |
            ${{ inputs.dockerhub_repo }}:${{ inputs.version }}-${{ matrix.file_tag.tag_suffix }}
            ${{ inputs.dockerhub_repo }}:latest-${{ matrix.file_tag.tag_suffix }}
          cache-from: type=gha
          cache-to: type=gha
```

- [ ] **Step 2: Verify YAML syntax**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/k8s-build-images.yml')); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Verify the matrix has all 24 services**

Run: `grep -c 'tag_suffix:' .github/workflows/k8s-build-images.yml`
Expected: `24`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/k8s-build-images.yml
git commit -m "feat(ci): build images on Kubernetes runners workflow"
```

---

### Task 5: Remove the superseded experiment manifest

**Files:**
- Delete: `kubernetes/docker-build-pod.yaml`

- [ ] **Step 1: Confirm it is the malformed experiment**

Run: `cat kubernetes/docker-build-pod.yaml`
Expected: the broken `docker-build-pod` Deployment/DinD manifest (bad indentation, `kind: Deployment` with `spec.containers`). This is superseded by ARC DinD mode. (User already approved deletion during brainstorming.)

- [ ] **Step 2: Delete and commit**

```bash
git rm kubernetes/docker-build-pod.yaml
git commit -m "chore: remove superseded docker-build-pod experiment (replaced by ARC)"
```

---

## Self-Review

- **Spec coverage:**
  - ARC install manifests (`kubernetes/arc/`) → Tasks 1, 3 ✓
  - Helm values with DinD, scale set name, App auth, resources → Task 1, validated Task 2 ✓
  - Build workflow targeting scale set, manual trigger, version input → Task 4 ✓
  - 24-service matrix, .env load, QEMU+Buildx, Docker Hub push, multi-arch tags → Task 4 ✓
  - GitHub App auth + Docker Hub secrets documented → Task 3 ✓
  - Remove `docker-build-pod.yaml` → Task 5 ✓
- **Placeholder scan:** none — every file's full content is shown.
- **Type/name consistency:** scale set release name `otel-demo-builders` is identical across the values file (Task 1), README (Task 3), and the workflow's `runs-on` (Task 4). Secret name `arc-github-app` matches between Task 1 (`githubConfigSecret`) and Task 3 (`kubectl create secret`). ✓
