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
