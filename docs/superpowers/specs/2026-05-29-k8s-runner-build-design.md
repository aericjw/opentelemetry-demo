# Build Images on Kubernetes Runners — Design

**Date:** 2026-05-29
**Status:** Approved (pending spec review)

## Goal

Build all OpenTelemetry Demo service images on self-hosted GitHub Actions
runners that run inside the user's Kubernetes cluster, and push them to Docker
Hub. The current pipeline builds on GitHub-hosted `ubuntu-latest` runners; this
moves the same build onto the cluster.

## Decisions

| Topic | Decision |
|-------|----------|
| Runner platform | Actions Runner Controller (ARC) **runner scale sets** (gha-runner-scale-set Helm charts) — manifests provided, not yet installed |
| Build engine | ARC **DinD container mode** (`containerMode.type: dind`) — privileged Docker-in-Docker sidecar per ephemeral runner pod |
| Build scope | All ~24 service images (mirror the existing `component-build-images.yml` matrix) |
| Registry | Docker Hub only (`DOCKER_USERNAME` / `DOCKER_PASSWORD` secrets) |
| Platforms | `linux/amd64,linux/arm64` via QEMU (matches existing workflow) |
| ARC auth | GitHub App (recommended; documented) |
| Trigger | `workflow_dispatch` only (manual), with a `version` input |

## Architecture

```
GitHub repo (aericjw/opentelemetry-demo)
        │  workflow_dispatch
        ▼
ARC controller (in cluster) ──► spins ephemeral runner pod
        │                         ├─ runner container (runs the job)
        │                         └─ dind sidecar (privileged docker daemon)
        ▼
runner pod executes k8s-build-images.yml matrix
        │  docker buildx (QEMU multi-arch)
        ▼
Docker Hub (otel/demo:<version>-<service>, latest-<service>)
```

## Components

### 1. ARC install manifests — `kubernetes/arc/`

- **`README.md`** — step-by-step:
  1. Create a GitHub App (permissions: Actions read/write, Administration
     read/write or Self-hosted runners, Metadata read), install it on the repo,
     note App ID / installation ID / private key.
  2. Create the `githubConfigSecret` in the cluster from those values.
  3. `helm install` the controller (`gha-runner-scale-set-controller`).
  4. `helm install` the runner scale set using `runner-scale-set-values.yaml`.
  5. Verify runners register (listener pod + `EphemeralRunnerSet`).
- **`runner-scale-set-values.yaml`** — Helm values:
  - `githubConfigUrl: https://github.com/aericjw/opentelemetry-demo`
  - `githubConfigSecret: arc-github-app` (App-based secret)
  - scale set name → installed as release `otel-demo-builders` (this becomes the
    `runs-on` label)
  - `containerMode.type: dind`
  - `minRunners` / `maxRunners` (e.g. 0 / 3)
  - resource requests/limits sized for image builds (e.g. 2 CPU / 4Gi requests)
- Replace the malformed experiment `kubernetes/docker-build-pod.yaml` (DinD mode
  supersedes it). **Confirm with user before deleting.**

### 2. Build workflow — `.github/workflows/k8s-build-images.yml`

New self-contained workflow (does **not** modify the upstream reusable
`component-build-images.yml`):

- `on: workflow_dispatch` with inputs:
  - `version` (default `dev`) — image tag prefix
  - `dockerhub_repo` (default `otel/demo`)
- `jobs.build_and_push_images`:
  - `runs-on: otel-demo-builders`
  - `strategy.matrix` — same ~24 `file` / `tag_suffix` / `context` entries as the
    existing workflow.
  - Steps:
    1. `actions/checkout` (fetch-depth 0)
    2. Load `.env` into `$GITHUB_ENV` (same grep logic as existing workflow)
    3. Log in to Docker Hub (`DOCKER_USERNAME` / `DOCKER_PASSWORD`)
    4. Set up QEMU (binfmt) — for arm64 emulation
    5. Set up Docker Buildx (DinD daemon from sidecar)
    6. `docker/build-push-action`: `platforms: linux/amd64,linux/arm64`,
       `push: true`, same `build-args` (OTEL_JAVA_AGENT_VERSION, etc.), tags:
       - `<dockerhub_repo>:<version>-<tag_suffix>`
       - `<dockerhub_repo>:latest-<tag_suffix>`
       - `cache-from`/`cache-to: type=gha`
- Pinned action SHAs reused from the existing workflow.

## Data Flow

1. User triggers `k8s-build-images.yml` (manual, optional version).
2. ARC controller sees a queued job for `otel-demo-builders`, creates an
   ephemeral runner pod with a DinD sidecar.
3. Job checks out the repo, loads `.env`, logs into Docker Hub.
4. buildx builds each matrix service for amd64+arm64 and pushes to Docker Hub.
5. Runner pod is torn down after the job.

## Error Handling

- `fail-fast: false` so one failing service doesn't cancel the others (matches
  existing behavior).
- Docker Hub login failure / missing secrets surface as a failed login step.
- GHA cache (`type=gha`) speeds repeat builds; safe to fail open.

## Secrets Required

| Secret | Purpose | Where |
|--------|---------|-------|
| `DOCKER_USERNAME` / `DOCKER_PASSWORD` | Docker Hub push | GitHub repo secrets |
| `arc-github-app` (App ID, installation ID, private key) | ARC runner registration | Kubernetes Secret in the ARC namespace |

## Testing / Validation

- After ARC install: confirm the controller and listener pods are `Running` and
  the scale set appears under repo → Settings → Actions → Runners.
- Dry run: trigger the workflow for a single service first by temporarily
  narrowing the matrix (or rely on `fail-fast: false`) and confirm a pushed
  image appears on Docker Hub.
- Full run: trigger with a real `version` and confirm all images push.

## Out of Scope (YAGNI)

- `push`/PR auto-triggers (manual only for now).
- GHCR / custom-registry push.
- Native multi-arch via the buildx kubernetes driver (QEMU is sufficient).
- Changed-only service detection.
