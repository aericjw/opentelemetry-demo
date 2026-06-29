# AKS profiling -- self-hosted Pyroscope

Continuous OTLP profiling for the AKS demo deployment, decoupled from the
existing Bindplane gateway pipeline.

## Architecture

```text
[ eBPF Profiler DaemonSet ]  --OTLP/gRPC-->  [ Demo otel-collector ]
                                                 |-- traces/metrics/logs -> Bindplane (unchanged)
                                                 +-- profiles ------------> Pyroscope (OTLP/HTTP :4040)
                                                                              |
                                                                              v
                                                                       Pyroscope UI / Grafana datasource
```

- **eBPF Profiler** (`10-ebpf-profiler.yaml`): privileged DaemonSet on every
  Linux node. Samples on-CPU stacks at 19 Hz from every process on the host
  and ships them as OTLP profiles to the demo's `otel-collector` Service.
- **Pyroscope** (`00-pyroscope.yaml`): single-binary Deployment with PVC,
  exposes OTLP profile ingest on `:4040` (HTTP, path `/v1/profiles`) plus
  the UI on the same port.

The demo's `otel-collector` is patched (via `kubernetes/my-values-file.yaml`)
to enable the `service.profilesSupport` feature gate, add an
`otlphttp/pyroscope` exporter, and add a `profiles` pipeline.

## Prerequisites

1. **Linux nodepool.** Windows nodes won't run the profiler (nodeSelector
   enforces this).
2. **Privileged Pod Security Admission.** The DaemonSet needs `hostPID`,
   `privileged: true`, and hostPath mounts of `/sys/kernel/debug`,
   `/sys/kernel/tracing`, `/sys/fs/cgroup`, `/proc`. If your demo namespace
   enforces `baseline` or `restricted`, relabel it:

   ```sh
   kubectl label ns <demo-namespace> \
     pod-security.kubernetes.io/enforce=privileged --overwrite
   ```

3. **Default StorageClass** for the Pyroscope PVC, or uncomment
   `storageClassName: managed-csi` in `00-pyroscope.yaml`.
4. **Demo collector reachable as `otel-collector:4317`.** This is the chart's
   default Service name. If your Helm release uses a different
   `fullnameOverride`, edit the `OTEL_COLLECTOR_HOST` env var in
   `10-ebpf-profiler.yaml`.

## Install

```sh
# 1. Apply the Helm release with the patched values file (adds the
#    profiles pipeline + service.profilesSupport feature gate).
#
#    NOTE: deploy from the vendored chart at kubernetes/_chart-cache, NOT the
#    remote `open-telemetry/opentelemetry-demo` repo. The vendored copy is the
#    same chart version but relaxes the `components` JSON schema so the
#    repo-custom services (telemetry-docs, firepit, agent, mcp, chatbot) pass
#    validation. Using the remote chart fails with:
#      at '/components': additional properties '...' not allowed
helm upgrade --install <release> kubernetes/_chart-cache/opentelemetry-demo \
  -n <demo-namespace> \
  -f kubernetes/my-values-file.yaml

# 2. Apply the profiling components into the same namespace.
kubectl apply -n <demo-namespace> -f kubernetes/profiling/
```

## Verify

```sh
# DaemonSet is running on each Linux node
kubectl -n <demo-namespace> get ds otel-ebpf-profiler

# Profiler is sending data (look for "profiles" exporter activity)
kubectl -n <demo-namespace> logs -l app.kubernetes.io/name=otel-ebpf-profiler --tail=50

# Demo collector is receiving + forwarding profiles
kubectl -n <demo-namespace> logs -l app.kubernetes.io/name=opentelemetry-collector --tail=100 | grep -i profile

# Pyroscope is ingesting (UI + API)
kubectl -n <demo-namespace> port-forward svc/pyroscope 4040:4040
# Then browse to http://localhost:4040
```

You should see services appearing in the Pyroscope app list within ~1 minute,
labeled by `service.name` matching each demo workload's `OTEL_SERVICE_NAME`
env var (set by the `transform/set_service_name` processor in the profiler).

## Grafana integration (optional)

Add the Pyroscope datasource to your existing Grafana (the demo's bundled
Grafana is disabled in your values file, so add it to whichever Grafana you
use to view dashboards):

```yaml
apiVersion: 1
datasources:
  - name: Pyroscope
    type: grafana-pyroscope-datasource
    access: proxy
    url: http://pyroscope.<demo-namespace>.svc.cluster.local:4040
    jsonData:
      keepCookies: []
```

## Tuning

- **Sample rate**: edit `samples_per_second` in
  `otel-ebpf-profiler-config` ConfigMap (default 19 Hz, matches compose).
- **Storage**: Pyroscope PVC is 10Gi. Bump in `00-pyroscope.yaml` and
  `kubectl edit pvc pyroscope-data` (PVCs can grow if the StorageClass
  supports expansion).
- **Retention**: `max_query_lookback: 7d` in the Pyroscope config. There's no
  separate retention policy in single-binary mode -- disk fills up over time.
  For longer retention switch to Pyroscope microservices mode with object
  storage (out of scope here).

## Teardown

```sh
kubectl delete -n <demo-namespace> -f kubernetes/profiling/
kubectl delete -n <demo-namespace> pvc pyroscope-data
```

Then revert the `profiles` pipeline / feature gate from
`kubernetes/my-values-file.yaml` and `helm upgrade` again.
