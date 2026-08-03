# Kubernetes Operations Standards

> **STATUS: FUTURE STATE. NOT YET ACTIVE.**
>
> The platform currently runs **locally on Docker Compose** — see `local-development.md`. Kubernetes is the *eventual* deployment target, and this file is the checklist that becomes binding the day a cloud readiness checkpoint approves the move. Nothing here applies to local development.
>
> It exists now so the standard is settled before it is needed, not written under deployment pressure. Do not build toward it speculatively; do not treat a Compose file as failing these rules.

**When active:** Kubernetes is the deployment target. Every service ships as a container into a Kubernetes cluster. Architecture lives in the design document; this file is the checklist every workload must satisfy before it reaches production.

## Every Workload Must Have

No exceptions. A manifest missing any of these does not pass review.

- **Resource requests and limits** on every container. Requests reflect steady-state need; limits prevent one workload starving a node. A pod without requests is unschedulable in any meaningful sense — the scheduler is guessing.
- **A readiness probe that checks actual readiness.** Readiness means dependencies are loaded and the service can serve real traffic — the tool registry snapshot is in memory, the artifact pointer resolved. Returning 200 from a bare handler is not readiness.
- **A liveness probe that only checks liveness.** Liveness answers "is this process wedged." It must not check dependencies, or a downstream blip restarts healthy pods and turns a partial outage into a full one.
- **A startup probe** for anything with a slow initialization, so a cold start is not mistaken for a hang.
- **`terminationGracePeriodSeconds` long enough to drain in-flight work.** Agent tool calls are long-lived; 20–30 seconds minimum. Killing a pod mid-tool-call loses a session.
- **A `preStop` hook** that stops accepting new work before shutdown so the endpoint is deregistered before the process dies.
- **A PodDisruptionBudget.** Voluntary disruptions — node drains, cluster upgrades — must not take a service to zero.
- **An immutable image tag.** Never `:latest`. Deploys are reproducible or they are not deploys.
- **A non-root user, a read-only root filesystem, and dropped capabilities** unless a documented exception applies.
- **A default-deny NetworkPolicy** with an explicit egress allowlist.
- **Structured logs to stdout.** No log files inside containers.

## Namespaces and Isolation

- **One namespace per layer** — gateway, orchestrator, executors, tool pools. Namespaces are the failure and policy boundary, not just a naming convention.
- **Default-deny network policy per namespace**, with egress allowed only to what that layer genuinely needs. The database tool pool cannot reach the internet. The browser pool reaches only allowlisted domains.
- **One namespace per tool pool domain**, so a compromised or leaking tool cannot reach unrelated services.
- **Dedicated node groups** for workloads with distinct profiles: sandbox pods executing model-authored code get stronger isolation and no IAM path to tenant data beyond their own session prefix; storage-heavy scratch workloads get local NVMe nodes.
- **ServiceAccount per workload** with least-privilege IAM. No shared node-level credentials.

## Scaling

**Scale each tier independently. Coupling them wastes money and hides bottlenecks.**

- **Stateless tiers** (gateway, orchestrator, model proxy) scale horizontally on request rate and in-flight-turn count. They must be genuinely stateless — session state lives in the external store, never in process memory, or a scale-down drops sessions.
- **Tool pools scale per domain.** Browser pods are memory-hungry and slow; database pods are cheap and fast. One HPA covering both is one HPA sized wrong for both.
- **Scale on the metric that reflects saturation**, not CPU by default. For LLM-bound work CPU is nearly meaningless — use queue depth, in-flight requests, or concurrency. KEDA for queue- and event-driven scaling where HPA's metric model does not fit.
- **Set `minReplicas` above 1** for anything on the request path. A single replica has no availability story.
- **Configure scale-down stabilization** generously. Aggressive scale-down during bursty agent traffic causes thrash, and thrash costs more than the idle capacity it saves.
- **Cluster autoscaling** (or Karpenter) for node capacity, with provisioning limits so a runaway loop cannot scale the bill without bound.
- **Topology spread constraints** across availability zones and nodes so a single node or zone loss does not take a tier down.
- **Load test before trusting an autoscaling configuration.** An untested HPA is a guess with a YAML file.

## Service Management

- **Start order enforced by readiness gates, not by luck**: registry, then orchestrator, then tool pools, then gateway. The gateway must not accept traffic before at least one pool has registered.
- **Circuit breakers per pool, never globally.** One noisy tool must not throttle the rest.
- **Jittered exponential backoff everywhere.** Fixed-interval retries across replicas produce synchronized retry storms, and synchronized registration produces registration storms after a leader election.
- **Rolling updates with `maxUnavailable: 0`** for request-path services.
- **Health, not hope, gates promotion.** A canary watches error rate, escalation rate, cache hit rate, cost per task, and guardrail trips, with automatic rollback on degradation.
- **No manual `kubectl` changes to production.** All state is declarative and version-controlled. A hotfix applied by hand is a drift incident.
- **Terraform owns cluster and cloud resource lifecycle.** Application manifests never provision infrastructure.

## Observability Requirements

Every workload emits, without exception:

- **OpenTelemetry traces** with propagated context, so a request is one trace across gateway, orchestrator, and tool pool spans.
- **Token and cost accounting** per request, split by cached versus uncached input.
- **The platform's first-class metrics** as defined in the design document — KV-cache hit rate, prefix-hash cardinality, cost and tokens per task, tool calls per task, re-route rate, retry scope distribution, breaker state.
- **Alarms with defined thresholds.** A metric with no alarm is a dashboard decoration.

A service that cannot be traced cannot be debugged in production, and a service without token accounting cannot be priced.

## Secrets and Configuration

- Secrets come from a secrets manager, injected at runtime. Never baked into images, never in ConfigMaps, never in the manifest.
- Rotate on a fixed schedule.
- Configuration is environment-specific and version-controlled; artifacts are resolved by content-hashed pointer so a rollback is a pointer change rather than a rebuild.
