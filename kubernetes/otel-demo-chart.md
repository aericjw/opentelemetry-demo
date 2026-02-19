apiVersion: v2
appVersion: 2.1.3
dependencies:
- condition: opentelemetry-collector.enabled
  name: opentelemetry-collector
  repository: https://open-telemetry.github.io/opentelemetry-helm-charts
  version: 0.134.0
- condition: jaeger.enabled
  name: jaeger
  repository: https://jaegertracing.github.io/helm-charts
  version: 3.4.1
- condition: prometheus.enabled
  name: prometheus
  repository: https://prometheus-community.github.io/helm-charts
  version: 27.39.0
- condition: grafana.enabled
  name: grafana
  repository: https://grafana.github.io/helm-charts
  version: 10.1.2
- condition: opensearch.enabled
  name: opensearch
  repository: https://opensearch-project.github.io/helm-charts/
  version: 3.2.1
description: opentelemetry demo helm chart
home: https://opentelemetry.io/
icon: https://opentelemetry.io/img/logos/opentelemetry-logo-nav.png
maintainers:
- name: dmitryax
- name: jaronoff97
- name: julianocosta89
- name: puckpuck
- name: tylerhelmuth
name: opentelemetry-demo
sources:
- https://github.com/open-telemetry/opentelemetry-demo
type: application
version: 0.38.6

---
# yaml-language-server: $schema=./values.schema.json
default:
  # List of environment variables applied to all components
  env:
    - name: OTEL_SERVICE_NAME
      valueFrom:
        fieldRef:
          apiVersion: v1
          fieldPath: "metadata.labels['app.kubernetes.io/component']"
    - name: OTEL_COLLECTOR_NAME
      value: otel-collector
    - name: OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE
      value: cumulative
    - name: OTEL_RESOURCE_ATTRIBUTES
      value: 'service.name=$(OTEL_SERVICE_NAME),service.namespace=opentelemetry-demo,service.version={{ .Chart.AppVersion }}'
  # Allows overriding and additions to .Values.default.env
  envOverrides: []
  #  - name: OTEL_K8S_NODE_NAME
  #    value: "someConstantValue"
  image:
    repository: ghcr.io/open-telemetry/demo
    # Overrides the image tag whose default is the chart appVersion.
    # The service's name will be applied to the end of this value.
    tag: ""
    pullPolicy: IfNotPresent
    pullSecrets: []
  # Default # of replicas for all components
  replicas: 1
  # default revisionHistoryLimit for all components (number of old ReplicaSets to retain)
  revisionHistoryLimit: 10
  # Default schedulingRules for all components
  schedulingRules:
    nodeSelector: {}
    affinity: {}
    tolerations: []
  # Default securityContext for all components
  securityContext: {}

serviceAccount:
  # Specifies whether a service account should be created
  create: true
  # Annotations to add to the service account
  annotations: {}
  # The name of the service account to use.
  # If not set and create is true, a name is generated using the fullname template
  name: ""

components:
  ## Demo Components are named objects (services) with several properties
  # demoService:
  ## Enable the component (service)
  #   enabled: true
  #   useDefault:
  ## Use default environment variables
  #     env: true
  ## Override Image repository and Tag. Tag will use appVersion as default.
  ## Component's name will be applied to end of this value.
  #   imageOverride: {}
  ## Optional service definitions to apply
  #   service:
  ## Service Type to use for this component. Default is ClusterIP.
  #     type: ClusterIP
  ## Service Port to use to expose this component. Default is nil
  #     port: 8080
  ## Service Node Port to use to expose this component on a NodePort service. Default is nil
  #     nodePort: 30080
  ## Service Annotations to add to this component
  #     annotations: {}
  ## Additional service ports to use to expose this component
  #   ports:
  #     - name: extraServicePort
  #       value: 8081
  ## Environment variables to add to the component's pod
  #   env:
  ## Environment variables that upsert (append + merge) into the `env` specification for this component.
  ## A variable named OTEL_RESOURCE_ATTRIBUTES_EXTRA will have its value appended to the OTEL_RESOURCE_ATTRIBUTES value.
  #   envOverrides:
  ## Pod Scheduling rules for nodeSelector, affinity, or tolerations.
  #   schedulingRules:
  #     nodeSelector: {}
  #     affinity: {}
  #     tolerations: []
  ## Pod Annotations to add to this component
  #   podAnnotations: {}
  ## Resources for this component
  #   resources: {}
  ## Container security context for setting user ID (UID), group ID (GID) and other security policies
  #   securityContext:
  ## Ingresses rules to add for the to the component
  # ingress:
  ## Enable the creation of Ingress rules. Default is false
  #   enabled: false
  ## Annotations to add to the ingress rule
  #   annotations: {}
  ## Which Ingress class (controller) to use. Default is unspecified.
  #   ingressClassName: nginx
  ## Hosts definitions for the Ingress rule
  #   hosts:
  #     - host: demo.example.com
  ## Each host can have multiple paths/routes
  #       paths:
  #         - path: /
  #           pathType: Prefix
  #           port: 8080
  ## Optional TLS specifications for the Ingress rule
  #   tls:
  #     - secretName: demo-tls
  #       hosts:
  #         - demo.example.com
  ## Additional ingresses - only created if ingress.enabled is true
  ## Useful for when differently annotated ingress services are required
  ## Each additional ingress needs key "name" set to something unique
  #   additionalIngresses: []
  #     - name: extra-demo-ingress
  #       ingressClassName: nginx
  #       annotations: {}
  #       hosts:
  #         - host: demo.example.com
  #           paths:
  #             - path: /
  #               pathType: Prefix
  #               port: 8080
  #       tls:
  #         - secretName: demo-tls
  #           hosts:
  #             - demo.example.com
  ## Command to use in the container spec, in case you don't want to go with the default command from the image.
  #   command: []
  ## Configuration to for this component; will create a Volume, and Mount backed by an optionally created ConfigMap.
  ## The name, mountPath are required, and one of existingConfigMap or data is required.
  ## If an existing ConfigMap is not provided, the contents under data will be used for the created ConfigMap.
  #   mountedConfigMaps: []
  #     - name: my-config
  #       mountPath: /etc/config
  #       subPath:
  #       existingConfigMap: my-configmap
  #       data:
  #         my-config.yaml: |
  #           key: value
  ## Configuration to create an custom Volume
  #   additionalVolumes:
  #     - name: nginx-logs
  #       hostPath:
  #         path: /var/log/nginx
  #       type: ""
  ## Configuration to mount the custom Volume to the container
  # additionalVolumeMounts:
  #     - name: nginx-logs
  #       mountPath: /var/log/nginx
  # # Kubernetes container health check options
  #   livenessProbe: {}
  # # Optional init container to run before the pod starts.
  #   initContainers:
  #     - name: <init-container-name>
  #       image: <init-container-image>
  #       command: [list of commands for the init container to run]
  # # Replicas for the component
  #  replicas: 1
  # # Number of old ReplicaSets to retain
  #  revisionHistoryLimit: 10
  # # Optional pod security context for setting user ID (UID), group ID (GID) and other security policies
  # # This will be applied at pod level, can be applied globally for all pods: .Values.default.podSecurityContext
  # # Or it can be applied to a specific component: .Values.components.<component-name>.podSecurityContext
  #    podSecurityContext:
  #      runAsGroup: 65534
  #      runAsNonRoot: true
  #      runAsUser: 65534

  accounting:
    enabled: true
    useDefault:
      env: true
    env:
      - name: KAFKA_ADDR
        value: kafka:9092
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4318
      - name: DB_CONNECTION_STRING
        value: Host=postgresql;Username=otelu;Password=otelp;Database=otel
      - name: OTEL_DOTNET_AUTO_TRACES_ENTITYFRAMEWORKCORE_INSTRUMENTATION_ENABLED
        value: "false"
    resources:
      limits:
        memory: 120Mi
    initContainers:
      - name: wait-for-kafka
        image: busybox:latest
        command: ["sh", "-c", "until nc -z -v -w30 kafka 9092; do echo waiting for kafka; sleep 2; done;"]

  ad:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8080
    env:
      - name: AD_PORT
        value: "8080"
      - name: FLAGD_HOST
        value: flagd
      - name: FLAGD_PORT
        value: "8013"
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4318
      - name: OTEL_LOGS_EXPORTER
        value: otlp
    resources:
      limits:
        memory: 300Mi

  cart:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8080
    env:
      - name: CART_PORT
        value: "8080"
      - name: ASPNETCORE_URLS
        value: http://*:$(CART_PORT)
      - name: VALKEY_ADDR
        value: valkey-cart:6379
      - name: FLAGD_HOST
        value: flagd
      - name: FLAGD_PORT
        value: "8013"
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4317
    resources:
      limits:
        memory: 160Mi
    initContainers:
      - name: wait-for-valkey-cart
        image: busybox:latest
        command: ["sh", "-c", "until nc -z -v -w30 valkey-cart 6379; do echo waiting for valkey-cart; sleep 2; done;"]

  checkout:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8080
    env:
      - name: CHECKOUT_PORT
        value: "8080"
      - name: CART_ADDR
        value: cart:8080
      - name: CURRENCY_ADDR
        value: currency:8080
      - name: EMAIL_ADDR
        value: http://email:8080
      - name: PAYMENT_ADDR
        value: payment:8080
      - name: PRODUCT_CATALOG_ADDR
        value: product-catalog:8080
      - name: SHIPPING_ADDR
        value: http://shipping:8080
      - name: KAFKA_ADDR
        value: kafka:9092
      - name: FLAGD_HOST
        value: flagd
      - name: FLAGD_PORT
        value: "8013"
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4317
      - name: GOMEMLIMIT
        value: 16MiB
    resources:
      limits:
        memory: 20Mi
    initContainers:
      - name: wait-for-kafka
        image: busybox:latest
        command: ["sh", "-c", "until nc -z -v -w30 kafka 9092; do echo waiting for kafka; sleep 2; done;"]

  currency:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8080
    env:
      - name: CURRENCY_PORT
        value: "8080"
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4317
      - name: VERSION
        value: "{{ .Chart.AppVersion }}"
    resources:
      limits:
        memory: 20Mi

  email:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8080
    env:
      - name: EMAIL_PORT
        value: "8080"
      - name: APP_ENV
        value: production
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4318
      - name: FLAGD_HOST
        value: flagd
      - name: FLAGD_PORT
        value: "8013"
    resources:
      limits:
        memory: 100Mi

  fraud-detection:
    enabled: true
    useDefault:
      env: true
    env:
      - name: KAFKA_ADDR
        value: kafka:9092
      - name: FLAGD_HOST
        value: flagd
      - name: FLAGD_PORT
        value: "8013"
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4318
      - name: OTEL_INSTRUMENTATION_KAFKA_EXPERIMENTAL_SPAN_ATTRIBUTES
        value: "true"
      - name: OTEL_INSTRUMENTATION_MESSAGING_EXPERIMENTAL_RECEIVE_TELEMETRY_ENABLED
        value: "true"
    resources:
      limits:
        memory: 300Mi
    initContainers:
      - name: wait-for-kafka
        image: busybox:latest
        command: ["sh", "-c", "until nc -z -v -w30 kafka 9092; do echo waiting for kafka; sleep 2; done;"]

  frontend:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8080
    env:
      - name: FRONTEND_PORT
        value: "8080"
      - name: PORT
        value: $(FRONTEND_PORT)
      - name: FRONTEND_ADDR
        value: :8080
      - name: AD_ADDR
        value: ad:8080
      - name: CART_ADDR
        value: cart:8080
      - name: CHECKOUT_ADDR
        value: checkout:8080
      - name: CURRENCY_ADDR
        value: currency:8080
      - name: PRODUCT_CATALOG_ADDR
        value: product-catalog:8080
      - name: RECOMMENDATION_ADDR
        value: recommendation:8080
      - name: SHIPPING_ADDR
        value: http://shipping:8080
      - name: FLAGD_HOST
        value: flagd
      - name: FLAGD_PORT
        value: "8013"
      - name: ENV_PLATFORM
        value: kubernetes
      - name: OTEL_COLLECTOR_HOST
        value: $(OTEL_COLLECTOR_NAME)
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4317
      - name: WEB_OTEL_SERVICE_NAME
        value: frontend-web
      - name: PUBLIC_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT
        value: http://localhost:8080/otlp-http/v1/traces             # This expects users to use `kubectl port-forward ...`
    resources:
      limits:
        memory: 250Mi
    securityContext:
      runAsUser: 1001  # nextjs
      runAsGroup: 1001
      runAsNonRoot: true

  frontend-proxy:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8080
    env:
      - name: ENVOY_PORT
        value: "8080"
      - name: ENVOY_ADMIN_PORT
        value: "10000"
      - name: FLAGD_HOST
        value: flagd
      - name: FLAGD_PORT
        value: "8013"
      - name: FLAGD_UI_HOST
        value: flagd
      - name: FLAGD_UI_PORT
        value: "4000"
      - name: FRONTEND_HOST
        value: frontend
      - name: FRONTEND_PORT
        value: "8080"
      - name: GRAFANA_HOST
        value: grafana
      - name: GRAFANA_PORT
        value: "80"
      - name: IMAGE_PROVIDER_HOST
        value: image-provider
      - name: IMAGE_PROVIDER_PORT
        value: "8081"
      - name: JAEGER_HOST
        value: jaeger-query
      - name: JAEGER_UI_PORT
        value: "16686"
      - name: LOCUST_WEB_HOST
        value: load-generator
      - name: LOCUST_WEB_PORT
        value: "8089"
      - name: OTEL_COLLECTOR_HOST
        value: $(OTEL_COLLECTOR_NAME)
      - name: OTEL_COLLECTOR_PORT_GRPC
        value: "4317"
      - name: OTEL_COLLECTOR_PORT_HTTP
        value: "4318"
    resources:
      limits:
        memory: 65Mi
    securityContext:
      runAsUser: 101  # envoy
      runAsGroup: 101
      runAsNonRoot: true

  image-provider:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8081
    env:
      - name: IMAGE_PROVIDER_PORT
        value: "8081"
      - name: OTEL_COLLECTOR_PORT_GRPC
        value: "4317"
      - name: OTEL_COLLECTOR_HOST
        value: $(OTEL_COLLECTOR_NAME)
    resources:
      limits:
        memory: 50Mi

  load-generator:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8089
    env:
      - name: LOCUST_WEB_HOST
        value: "0.0.0.0"
      - name: LOCUST_WEB_PORT
        value: "8089"
      - name: LOCUST_USERS
        value: "10"
      - name: LOCUST_SPAWN_RATE
        value: "1"
      - name: LOCUST_HOST
        value: http://frontend-proxy:8080
      - name: LOCUST_HEADLESS
        value: "false"
      - name: LOCUST_AUTOSTART
        value: "true"
      - name: LOCUST_BROWSER_TRAFFIC_ENABLED
        value: "true"
      - name: PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION
        value: python
      - name: FLAGD_HOST
        value: flagd
      - name: FLAGD_PORT
        value: "8013"
      - name: FLAGD_OFREP_PORT
        value: "8016"
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4317
    resources:
      limits:
        memory: 1500Mi

  payment:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8080
    env:
      - name: PAYMENT_PORT
        value: "8080"
      - name: FLAGD_HOST
        value: flagd
      - name: FLAGD_PORT
        value: "8013"
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4317
    resources:
      limits:
        memory: 120Mi
    securityContext:
      runAsUser: 1000  # node
      runAsGroup: 1000
      runAsNonRoot: true

  product-catalog:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8080
    env:
      - name: PRODUCT_CATALOG_PORT
        value: "8080"
      - name: PRODUCT_CATALOG_RELOAD_INTERVAL
        value: "10"
      - name: FLAGD_HOST
        value: flagd
      - name: FLAGD_PORT
        value: "8013"
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4317
      - name: GOMEMLIMIT
        value: 16MiB
    mountedConfigMaps:
      - name: product-catalog-products
        mountPath: /usr/src/app/products
        existingConfigMap: product-catalog-products
    resources:
      limits:
        memory: 20Mi

  quote:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8080
    env:
      - name: QUOTE_PORT
        value: "8080"
      - name: OTEL_PHP_AUTOLOAD_ENABLED
        value: "true"
      - name: OTEL_PHP_INTERNAL_METRICS_ENABLED
        value: "true"
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4318
    resources:
      limits:
        memory: 40Mi
    securityContext:
      runAsUser: 33  # www-data
      runAsGroup: 33
      runAsNonRoot: true

  recommendation:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8080
    env:
      - name: RECOMMENDATION_PORT
        value: "8080"
      - name: PRODUCT_CATALOG_ADDR
        value: product-catalog:8080
      - name: OTEL_PYTHON_LOG_CORRELATION
        value: "true"
      - name: PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION
        value: python
      - name: FLAGD_HOST
        value: flagd
      - name: FLAGD_PORT
        value: "8013"
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4317
    resources:
      limits:
        memory: 500Mi            # This is high to enable supporting the recommendationCache feature flag use case

  shipping:
    enabled: true
    useDefault:
      env: true
    service:
      port: 8080
    env:
      - name: SHIPPING_PORT
        value: "8080"
      - name: QUOTE_ADDR
        value: http://quote:8080
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4317
    resources:
      limits:
        memory: 20Mi

  flagd:
    enabled: true
    imageOverride:
      repository: "ghcr.io/open-feature/flagd"
      tag: "v0.12.8"
    useDefault:
      env: true
    replicas: 1
    ports:
      - name: rpc
        value: 8013
      - name: ofrep
        value: 8016
    env:
      - name: FLAGD_METRICS_EXPORTER
        value: otel
      - name: FLAGD_OTEL_COLLECTOR_URI
        value: $(OTEL_COLLECTOR_NAME):4317
      - name: GOMEMLIMIT
        value: 60MiB
    resources:
      limits:
        memory: 75Mi
    command:
      - "/flagd-build"
      - "start"
      - "--port"
      - "8013"
      - "--ofrep-port"
      - "8016"
      - "--uri"
      - "file:./etc/flagd/demo.flagd.json"
    mountedEmptyDirs:
      - name: config-rw
        mountPath: /etc/flagd
    # flagd-ui as a sidecar container in the same pod so the flag json file can be shared
    sidecarContainers:
      - name: flagd-ui
        useDefault:
          env: true
        service:
          port: 4000
        env:
          - name: FLAGD_METRICS_EXPORTER
            value: otel
          - name: OTEL_EXPORTER_OTLP_ENDPOINT
            value: http://$(OTEL_COLLECTOR_NAME):4318
          - name: FLAGD_UI_PORT
            value: "4000"
          - name: SECRET_KEY_BASE
            value: yYrECL4qbNwleYInGJYvVnSkwJuSQJ4ijPTx5tirGUXrbznFIBFVJdPl5t6O9ASw
          - name: PHX_HOST
            value: localhost
        resources:
          limits:
            memory: 250Mi
        volumeMounts:
          - name: config-rw
            mountPath: /app/data
    initContainers:
      - name: init-config
        image: busybox
        command: ["sh", "-c", "cp /config-ro/demo.flagd.json /config-rw/demo.flagd.json && cat /config-rw/demo.flagd.json"]
        volumeMounts:
          - mountPath: /config-ro
            name: config-ro
          - mountPath: /config-rw
            name: config-rw
    additionalVolumes:
      - name: config-ro
        configMap:
          name: flagd-config

  kafka:
    enabled: true
    useDefault:
      env: true
    replicas: 1
    ports:
      - name: plaintext
        value: 9092
      - name: controller
        value: 9093
    env:
      - name: KAFKA_ADVERTISED_LISTENERS
        value: PLAINTEXT://kafka:9092
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: http://$(OTEL_COLLECTOR_NAME):4318
      - name: KAFKA_HEAP_OPTS
        value: "-Xmx400M -Xms400M"
      - name: KAFKA_LISTENERS
        value: PLAINTEXT://:9092,CONTROLLER://:9093
      - name: KAFKA_CONTROLLER_LISTENER_NAMES
        value: CONTROLLER
      - name: KAFKA_CONTROLLER_QUORUM_VOTERS
        value: 1@kafka:9093
    resources:
      limits:
        memory: 600Mi
    securityContext:
      runAsUser: 1000  # appuser
      runAsGroup: 1000
      runAsNonRoot: true

  postgresql:
    enabled: true
    useDefault:
      env: true
    replicas: 1
    service:
      port: 5432
    env:
      - name: POSTGRES_USER
        value: root
      - name: POSTGRES_PASSWORD
        value: otel
      - name: POSTGRES_DB
        value: otel
    resources:
      limits:
        memory: 100Mi

  valkey-cart:
    enabled: true
    useDefault:
      env: true
    imageOverride:
      repository: "valkey/valkey"
      tag: "8.1.3-alpine"
    replicas: 1
    ports:
      - name: valkey-cart
        value: 6379
    resources:
      limits:
        memory: 20Mi
    securityContext:
      runAsUser: 999  # valkey
      runAsGroup: 1000
      runAsNonRoot: true

opentelemetry-collector:
  enabled: true
  image:
    repository: "otel/opentelemetry-collector-contrib"
  fullnameOverride: otel-collector
  mode: deployment
  presets:
    kubernetesAttributes:
      enabled: true
  resources:
    limits:
      memory: 200Mi
  service:
    type: ClusterIP
  ports:
    metrics:
      enabled: true
  podAnnotations:
    prometheus.io/scrape: "true"
    opentelemetry_community_demo: "true"
  config:
    receivers:
      otlp:
        protocols:
          http:
            # Since this collector needs to receive data from the web, enable cors for all origins
            # `allowed_origins` can be refined for your deployment domain
            cors:
              allowed_origins:
                - "http://*"
                - "https://*"
      httpcheck/frontend-proxy:
        targets:
          - endpoint: http://frontend-proxy:8080
      nginx:
        endpoint: http://image-provider:8081/status
        collection_interval: 10s
      postgresql:
        endpoint: "postgresql:5432"
        username: "root"
        password: "otel"
        metrics:
          postgresql.blks_hit:
            enabled: true
          postgresql.blks_read:
            enabled: true
          postgresql.tup_fetched:
            enabled: true
          postgresql.tup_returned:
            enabled: true
          postgresql.tup_inserted:
            enabled: true
          postgresql.tup_updated:
            enabled: true
          postgresql.tup_deleted:
            enabled: true
          postgresql.deadlocks:
            enabled: true
        tls:
          insecure: true
      redis:
        endpoint: "valkey-cart:6379"
        username: "valkey"
        collection_interval: 10s

    exporters:
      ## Create an exporter to Jaeger using the standard `otlp` export format
      otlp:
        endpoint: jaeger-collector:4317
        tls:
          insecure: true
      # Create an exporter to Prometheus (metrics)
      otlphttp/prometheus:
        endpoint: http://prometheus:9090/api/v1/otlp
        tls:
          insecure: true
      opensearch:
        logs_index: otel-logs
        logs_index_time_format: "yyyy-MM-dd"
        http:
          endpoint: http://opensearch:9200
          tls:
            insecure: true

    processors:
      memory_limiter:
        check_interval: 5s
        limit_percentage: 80
        spike_limit_percentage: 25
      resourcedetection:
        detectors: [env, system]
      # This processor is used to help limit high cardinality on next.js span names
      # When this PR is merged (and released) we can remove this transform processor
      # https://github.com/vercel/next.js/pull/64852
      transform:
        error_mode: ignore
        trace_statements:
          - context: span
            statements:
              # could be removed when https://github.com/vercel/next.js/pull/64852 is fixed upstream
              - replace_pattern(name, "\\?.*", "")
              - replace_match(name, "GET /api/products/*", "GET /api/products/{productId}")
      resource:
        attributes:
        - key: service.instance.id
          from_attribute: k8s.pod.uid
          action: insert

    connectors:
      spanmetrics: {}

    service:
      pipelines:
        traces:
          processors: [memory_limiter, resourcedetection, resource, transform, batch]
          exporters: [otlp, debug, spanmetrics]
        metrics:
          receivers: [httpcheck/frontend-proxy, nginx, otlp, postgresql, redis, spanmetrics]
          processors: [memory_limiter, resourcedetection, resource, batch]
          exporters: [otlphttp/prometheus, debug]
        logs:
          processors: [memory_limiter, resourcedetection, resource, batch]
          exporters: [opensearch, debug]
      telemetry:
        metrics:
          level: detailed
          readers:
            - periodic:
                interval: 10000
                timeout: 5000
                exporter:
                  otlp:
                    protocol: http/protobuf
                    endpoint: otel-collector:4318

jaeger:
  enabled: true
  fullnameOverride: jaeger
  provisionDataStore:
    cassandra: false
  allInOne:
    enabled: true
    args:
      - "--memory.max-traces=5000"
      - "--query.base-path=/jaeger/ui"
      - "--prometheus.server-url=http://prometheus:9090"
      - "--prometheus.query.normalize-calls=true"
      - "--prometheus.query.normalize-duration=true"
    extraEnv:
      - name: METRICS_STORAGE_TYPE
        value: prometheus
      - name: COLLECTOR_OTLP_GRPC_HOST_PORT
        value: 0.0.0.0:4317
      - name: COLLECTOR_OTLP_HTTP_HOST_PORT
        value: 0.0.0.0:4318
    resources:
      limits:
        memory: 400Mi
  storage:
    type: memory
  agent:
    enabled: false
  collector:
    enabled: false
  query:
    enabled: false

prometheus:
  enabled: true
  alertmanager:
    enabled: false
  configmapReload:
    prometheus:
      enabled: false
  kube-state-metrics:
    enabled: false
  prometheus-node-exporter:
    enabled: false
  prometheus-pushgateway:
    enabled: false
  server:
    fullnameOverride: prometheus
    extraFlags:
      - "enable-feature=exemplar-storage"
      - "web.enable-otlp-receiver"
    tsdb:
      out_of_order_time_window: 30m
    otlp:
      keep_identifying_resource_attributes: true
      # Recommended attributes to be promoted to labels.
      promote_resource_attributes:
        - service.instance.id
        - service.name
        - service.namespace
        - service.version
        - cloud.availability_zone
        - cloud.region
        - deployment.environment.name
        # When deploying on Kubernetes, resource attributes used to identify the
        # kubernetes resources in dashboards and alerts.
        - k8s.cluster.name
        - k8s.container.name
        - k8s.cronjob.name
        - k8s.daemonset.name
        - k8s.deployment.name
        - k8s.job.name
        - k8s.namespace.name
        - k8s.node.name
        - k8s.pod.name
        - k8s.replicaset.name
        - k8s.statefulset.name
        - container.name
        # When deploying on VMs, resource attributes used to identify
        # the host in dashboards and alerts.
        - host.name
        # PostgreSQL resource attributes produced by the OTel Collector PostgreSQL receiver
        # and used in dashboards and alerts.
        # See https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/receiver/postgresqlreceiver/metadata.yaml
        - postgresql.database.name
        - postgresql.schema.name
        - postgresql.table.name
        - postgresql.index.name
    persistentVolume:
      enabled: false
    service:
      servicePort: 9090
    resources:
      limits:
        memory: 300Mi

grafana:
  enabled: true
  fullnameOverride: grafana
  testFramework:
    enabled: false
  grafana.ini:
    auth:
      disable_login_form: true
    auth.anonymous:
      enabled: true
      org_name: Main Org.
      org_role: Admin
    server:
      root_url: "%(protocol)s://%(domain)s:%(http_port)s/grafana"
      serve_from_sub_path: true
  adminPassword: admin
  plugins:
    - grafana-opensearch-datasource
  sidecar:
    alerts:
      enabled: true
    dashboards:
      enabled: true
    datasources:
      enabled: true
    resources:
      limits:
        cpu: 100m
        memory: 100Mi
  resources:
    limits:
      memory: 150Mi

opensearch:
  enabled: true
  fullnameOverride: opensearch
  clusterName: demo-cluster
  nodeGroup: otel-demo
  singleNode: true
  opensearchJavaOpts: "-Xms400m -Xmx400m"
  persistence:
    enabled: false
  extraEnvs:
    - name: "bootstrap.memory_lock"
      value: "true"
    - name: "DISABLE_INSTALL_DEMO_CONFIG"
      value: "true"
    - name: "DISABLE_SECURITY_PLUGIN"
      value: "true"
  resources:
    limits:
      memory: 1100Mi

---
# OpenTelemetry Demo Helm Chart

The helm chart installs [OpenTelemetry Demo](https://github.com/open-telemetry/opentelemetry-demo)
in kubernetes cluster.

> [!NOTE]
> The [Jaeger Service Performance Monitoring (SPM)](https://www.jaegertracing.io/docs/1.73/deployment/spm/)
> is currently **not working** in the OTel Demo.
>
> This happens because the OTel Demo Helm chart depends on the Jaeger Helm chart, and the latest
> published Jaeger Helm chart is incompatible with the new span metric names.
>
> The issue has already been fixed in newer Jaeger versions, but Helm charts for those versions
> are not yet available.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.14+

## Installing the Chart

Add OpenTelemetry Helm repository:

```console
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
```

To install the chart with the release name my-otel-demo, run the following command:

```console
helm install my-otel-demo open-telemetry/opentelemetry-demo
```

## Upgrading

See [UPGRADING.md](UPGRADING.md).

## OpenShift

Installing the chart on OpenShift requires the following additional steps:

1. Create a new project:

    ```console
    oc new-project opentelemetry-demo
    ```

2. Create a new service account:

    ```console
    oc create sa opentelemetry-demo
    ```

3. Add the service account to the `anyuid` SCC (may require cluster admin):

    ```console
    oc adm policy add-scc-to-user anyuid -z opentelemetry-demo
    ```

4. Add `view` role to the service account to allow Prometheus seeing the services pods:

    ```console
    oc adm policy add-role-to-user view -z opentelemetry-demo
    ```

5. Add `privileged` SCC to the service account to allow Grafana to run:

    ```console
    oc adm policy add-scc-to-user privileged -z opentelemetry-demo
    ```

6. Install the chart with the following command:

    ```console
    helm install my-otel-demo charts/opentelemetry-demo \
        --namespace opentelemetry-demo \
        --set serviceAccount.create=false \
        --set serviceAccount.name=opentelemetry-demo \
        --set prometheus.rbac.create=false \
        --set prometheus.serviceAccounts.server.create=false \
        --set prometheus.serviceAccounts.server.name=opentelemetry-demo \
        --set grafana.rbac.create=false \
        --set grafana.serviceAccount.create=false \
        --set grafana.serviceAccount.name=opentelemetry-demo
    ```

## Chart Parameters

Chart parameters are separated in 4 general sections:

- Default - Used to specify defaults applied to all demo components
- Components - Used to configure the individual components (microservices) for
the demo
- Observability - Used to enable/disable dependencies
- Sub-charts - Configuration for all sub-charts

### Default parameters (applied to all demo components)

| Property                               | Description                                                                               | Default                                              |
|----------------------------------------|-------------------------------------------------------------------------------------------|------------------------------------------------------|
| `default.env`                          | Environment variables added to all components                                             | Array of several OpenTelemetry environment variables |
| `default.envOverrides`                 | Used to override individual environment variables without re-specifying the entire array. | `[]`                                                 |
| `default.image.repository`             | Demo components image name                                                                | `otel/demo`                                          |
| `default.image.tag`                    | Demo components image tag (leave blank to use app version)                                | `nil`                                                |
| `default.image.pullPolicy`             | Demo components image pull policy                                                         | `IfNotPresent`                                       |
| `default.image.pullSecrets`            | Demo components image pull secrets                                                        | `[]`                                                 |
| `default.replicas`                     | Number of replicas for each component                                                     | `1`                                                  |
| `default.schedulingRules.nodeSelector` | Node labels for pod assignment                                                            | `{}`                                                 |
| `default.schedulingRules.affinity`     | Man of node/pod affinities                                                                | `{}`                                                 |
| `default.schedulingRules.tolerations`  | Tolerations for pod assignment                                                            | `[]`                                                 |
| `default.securityContext`              | Demo components container security context                                                | `{}`                                                 |
| `serviceAccount.annotations`           | Annotations for the serviceAccount                                                        | `{}`                                                 |
| `serviceAccount.create`                | Whether to create a serviceAccount or use an existing one                                 | `true`                                               |
| `serviceAccount.name`                  | The name of the ServiceAccount to use for demo components                                 | `""`                                                 |

### Component parameters

The OpenTelemetry demo contains several components (microservices). Each
component is configured with a common set of parameters. All components will
be defined within `components.[NAME]` where `[NAME]` is the name of the demo
component.

> **Note**
> The following parameters require a `components.[NAME].` prefix where `[NAME]`
> is the name of the demo component

| Parameter                              | Description                                                                                                | Default                                                       |
|----------------------------------------|------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| `enabled`                              | Is this component enabled                                                                                  | `true`                                                        |
| `useDefault.env`                       | Use the default environment variables in this component                                                    | `true`                                                        |
| `imageOverride.repository`             | Name of image for this component                                                                           | Defaults to the overall default image repository              |
| `imageOverride.tag`                    | Tag of the image for this component                                                                        | Defaults to the overall default image tag                     |
| `imageOverride.pullPolicy`             | Image pull policy for this component                                                                       | `IfNotPresent`                                                |
| `imageOverride.pullSecrets`            | Image pull secrets for this component                                                                      | `[]`                                                          |
| `service.type`                         | Service type used for this component                                                                       | `ClusterIP`                                                   |
| `service.port`                         | Service port used for this component                                                                       | `nil`                                                         |
| `service.nodePort`                     | Service node port used for this component                                                                  | `nil`                                                         |
| `service.annotations`                  | Annotations to add to the component's service                                                              | `{}`                                                          |
| `ports`                                | Array of ports to open for deployment and service of this component                                        | `[]`                                                          |
| `env`                                  | Array of environment variables added to this component                                                     | Each component will have its own set of environment variables |
| `envOverrides`                         | Used to override individual environment variables without re-specifying the entire array                   | `[]`                                                          |
| `replicas`                             | Number of replicas for this component                                                                      | `1` for kafka, and redis ; `nil` otherwise       |
| `resources`                            | CPU/Memory resource requests/limits                                                                        | Each component will have a default memory limit set           |
| `schedulingRules.nodeSelector`         | Node labels for pod assignment                                                                             | `{}`                                                          |
| `schedulingRules.affinity`             | Man of node/pod affinities                                                                                 | `{}`                                                          |
| `schedulingRules.tolerations`          | Tolerations for pod assignment                                                                             | `[]`                                                          |
| `securityContext`                      | Container security context to define user ID (UID), group ID (GID) and other security policies             | `{}`                                                          |
| `podSecurityContext`                   | Pod security context to define user ID (UID), group ID (GID) and other security policies                   | `{}`                                                          |
| `podAnnotations`                       | Pod annotations for this component                                                                         | `{}`                                                          |
| `ingress.enabled`                      | Enable the creation of Ingress rules                                                                       | `false`                                                       |
| `ingress.annotations`                  | Annotations to add to the ingress rule                                                                     | `{}`                                                          |
| `ingress.ingressClassName`             | Ingress class to use. If not specified default Ingress class will be used.                                 | `nil`                                                         |
| `ingress.hosts`                        | Array of Hosts to use for the ingress rule.                                                                | `[]`                                                          |
| `ingress.hosts[].paths`                | Array of paths / routes to use for the ingress rule host.                                                  | `[]`                                                          |
| `ingress.hosts[].paths[].path`         | Actual path route to use                                                                                   | `nil`                                                         |
| `ingress.hosts[].paths[].pathType`     | Path type to use for the given path. Typically this is `Prefix`.                                           | `nil`                                                         |
| `ingress.hosts[].paths[].port`         | Port to use for the given path                                                                             | `nil`                                                         |
| `ingress.additionalIngresses`          | Array of additional ingress rules to add. This is handy if you need to differently annotated ingress rules | `[]`                                                          |
| `ingress.additionalIngresses[].name`   | Each additional ingress rule needs to have a unique name                                                   | `nil`                                                         |
| `command`                              | Command & arguments to pass to the container being spun up for this service                                | `[]`                                                          |
| `additionalVolumeMounts`             | Array of Volumes that will be mounted                                                       | `[]`                                                         |
| `mountedConfigMaps[].name`             | Name of the Volume that will be used for the ConfigMap mount                                               | `nil`                                                         |
| `mountedConfigMaps[].mountPath`        | Path where the ConfigMap data will be mounted                                                              | `nil`                                                         |
| `mountedConfigMaps[].subPath`          | SubPath within the mountPath. Used to mount a single file into the path.                                   | `nil`                                                         |
| `mountedConfigMaps[].existingConfigMap` | Name of the existing ConfigMap to mount                                                                    | `nil`                                                         |
| `mountedConfigMaps[].data`             | Contents of a ConfigMap. Keys should be the names of the files to be mounted.                              | `{}`                                                          |
| `mountedEmptyDir[].name`             | Name of the EmptyDir volume that will be used for the volume mount                                                         | `nil`                                                         |
| `mountedEmptyDir[].mountPath`        | Path where the EmptyDir data will be mounted                                                              | `nil`                                                         |
| `mountedEmptyDir[].subPath`          | SubPath within the mountPath. Used to mount a single file into the path.                                   | `nil`                                                         |
| `initContainers`                       | Array of init containers to add to the pod                                                                 | `[]`                                                          |
| `initContainers[].name`                | Name of the init container                                                                                 | `nil`                                                         |
| `initContainers[].image`               | Image to use for the init container                                                                        | `nil`                                                         |
| `initContainers[].command`             | Command to run for the init container                                                                      | `nil`                                                         |
| `sidecarContainers`                    | Array of sidecar containers to add to the pod                                                              | `[]`                                                          |
| `additionalVolumes`                    | Array of additional volumes to add to the pod                                                              | `[]`                                                          |

### Sub-charts

The OpenTelemetry Demo Helm chart depends on 5 sub-charts:

- OpenTelemetry Collector
- Jaeger
- Prometheus
- Grafana
- OpenSearch

Parameters for each sub-chart can be specified within that sub-chart's
respective top level. This chart will override some of the dependent sub-chart
parameters by default. The overriden parameters are specified below.

#### OpenTelemetry Collector

> **Note**
> The following parameters have a `opentelemetry-collector.` prefix.

| Parameter        | Description                                        | Default                                                  |
|------------------|----------------------------------------------------|----------------------------------------------------------|
| `enabled`        | Install the OpenTelemetry collector                | `true`                                                   |
| `nameOverride`   | Name that will be used by the sub-chart release    | `otel-collector`                                                |
| `mode`           | The Deployment or Daemonset mode                   | `deployment`                                             |
| `resources`      | CPU/Memory resource requests/limits                | 100Mi memory limit                                       |
| `service.type`   | Service Type to use                                | `ClusterIP`                                              |
| `ports`          | Ports to enabled for the collector pod and service | `metrics` is enabled and `prometheus` is defined/enabled |
| `podAnnotations` | Pod annotations                                    | Annotations leveraged by Prometheus scrape               |
| `config`         | OpenTelemetry Collector configuration              | Configuration required for demo                          |

#### Jaeger

> **Note**
> The following parameters have a `jaeger.` prefix.

| Parameter                      | Description                                        | Default                                                               |
|--------------------------------|----------------------------------------------------|-----------------------------------------------------------------------|
| `enabled`                      | Install the Jaeger sub-chart                       | `true`                                                                |
| `provisionDataStore.cassandra` | Provision a cassandra data store                   | `false` (required for AllInOne mode)                                  |
| `allInOne.enabled`             | Enable All in One In-Memory Configuration          | `true`                                                                |
| `allInOne.args`                | Command arguments to pass to All in One deployment | `["--memory.max-traces", "10000", "--query.base-path", "/jaeger/ui"]` |
| `allInOne.resources`           | CPU/Memory resource requests/limits for All in One | 275Mi memory limit                                                    |
| `storage.type`                 | Storage type to use                                | `none` (required for AllInOne mode)                                   |
| `agent.enabled`                | Enable Jaeger agent                                | `false` (required for AllInOne mode)                                  |
| `collector.enabled`            | Enable Jaeger Collector                            | `false` (required for AllInOne mode)                                  |
| `query.enabled`                | Enable Jaeger Query                                | `false` (required for AllInOne mode)                                  |

#### Prometheus

> **Note**
> The following parameters have a `prometheus.` prefix.

| Parameter                            | Description                                    | Default                                                   |
|--------------------------------------|------------------------------------------------|-----------------------------------------------------------|
| `enabled`                            | Install the Prometheus sub-chart               | `true`                                                    |
| `alertmanager.enabled`               | Install the alertmanager                       | `false`                                                   |
| `configmapReload.prometheus.enabled` | Install the configmap-reload container         | `false`                                                   |
| `kube-state-metrics.enabled`         | Install the kube-state-metrics sub-chart       | `false`                                                   |
| `prometheus-node-exporter.enabled`   | Install the Prometheus Node Exporter sub-chart | `false`                                                   |
| `prometheus-pushgateway.enabled`     | Install the Prometheus Push Gateway sub-chart  | `false`                                                   |
| `server.extraFlags`                  | Additional flags to add to Prometheus server   | `["enable-feature=exemplar-storage"]`                     |
| `server.persistentVolume.enabled`    | Enable persistent storage for Prometheus data  | `false`                                                   |
| `server.global.scrape_interval`      | How frequently to scrape targets by default    | `5s`                                                      |
| `server.global.scrap_timeout`        | How long until a scrape request times out      | `3s`                                                      |
| `server.global.evaluation_interval`  | How frequently to evaluate rules               | `30s`                                                     |
| `service.servicePort`                | Service port used                              | `9090`                                                    |
| `serverFiles.prometheus.yml`         | Prometheus configuration file                  | Scrape config to get metrics from OpenTelemetry collector |

#### Grafana

> **Note**
> The following parameters have a `grafana.` prefix.

| Parameter             | Description                                        | Default                                                              |
|-----------------------|----------------------------------------------------|----------------------------------------------------------------------|
| `enabled`             | Install the Grafana sub-chart                      | `true`                                                               |
| `grafana.ini`         | Grafana's primary configuration                    | Enables anonymous login, and proxy through the frontend-proxy service |
| `adminPassword`       | Password used by `admin` user                      | `admin`                                                              |
| `rbac.pspEnabled`     | Enable PodSecurityPolicy resources                 | `false`                                                              |
| `datasources`         | Configure grafana datasources (passed through tpl) | Prometheus and Jaeger data sources                                   |
| `dashboardProviders`  | Configure grafana dashboard providers              | Defines a `default` provider based on a file path                    |
| `dashboardConfigMaps` | ConfigMaps reference that contains dashboards      | Dashboard config map deployed with this Helm chart                   |

#### OpenSearch

> **Note**
> The following parameters have a `opensearch.` prefix.

| Parameter             | Description                                       | Default                                  |
|-----------------------|---------------------------------------------------|------------------------------------------|
| `enabled`             | Install the OpenSearch sub-chart                  | `true`                                   |
| `fullnameOverride`    | Name that will be used by the sub-chart release   | `otel-demo-opensearch`                   |
| `clusterName`         | Name of the OpenSearch cluster                    | `demo-cluster`                           |
| `nodeGroup`           | OpenSearch Node group configuration               | `otel-demo`                              |
| `singleNode`          | Deploy a single node OpenSearch cluster           | `true`                                   |
| `opensearchJavaOpts`  | Java options for OpenSearch JVM                   | `-Xms300m -Xmx300m`                      |
| `persistence.enabled` | Enable persistent storage for OpenSearch data     | `false`                                  |
| `extraEnvs`           | Additional environment variables for OpenSearch   | Disables demo config and security plugin |

