# Local-First Development

**The platform runs locally on Docker Compose. There is no cloud deployment, and none is planned until a readiness checkpoint says otherwise.** Every backing service runs as a container on a developer machine.

## Why Local First

Cloud infrastructure is a fixed cost paid before any of it is needed: a cluster to upgrade, IAM to debug, autoscalers to tune, a bill that accrues while the platform still does nothing useful. None of that teaches us anything about whether the architecture is right. Running locally means a full stack on one machine, a fast feedback loop, and no spend — and the architectural decisions in the spec are unaffected, because they describe the platform's *shape*, not its hosting.

The cloud design exists in the spec so we are not designing under pressure later. It is not built yet.

## The Portability Rule

**Application code must never know which environment it is running in.**

Every backing service is reached through an interface, and the concrete implementation is selected by configuration. Swapping MinIO for S3, or a local Postgres for a managed one, is a config change and never a code change. Concretely:

- Use the **S3 API** for object storage, not a MinIO-specific client.
- Use **standard Postgres plus pgvector**, not a managed-service-specific extension.
- Use **OpenTelemetry** for traces and metrics, not a vendor SDK. OTel is the seam that makes the observability backend swappable.
- Use the **Redis protocol**, not a managed-cache-specific feature.
- Keep provider-specific calls behind the model proxy so a model backend is a config entry.

Anything reachable only through a single vendor's API is a migration cliff. If one is genuinely required, it gets an ADR recording the lock-in as a deliberate accepted cost.

## Known Local/Cloud Gaps — Do Not Pretend These Are Equivalent

Some properties cannot be validated locally. Naming them is how we avoid being surprised later.

| Property | Local reality | Must be re-validated in cloud |
| --- | --- | --- |
| Object store latency | MinIO on a local disk has a completely different latency profile from a managed low-latency tier | Yes — any latency assumption in the session storage tiers is unverified until measured in cloud |
| Sandbox isolation | Docker with dropped capabilities is weaker than a gVisor- or Firecracker-class boundary | Yes — the isolation property for model-authored code is **not** proven locally |
| Autoscaling behaviour | Compose has no HPA, no PDB, no node pressure | Yes — every per-tier scaling signal is a design hypothesis until load-tested on a cluster |
| Network policy isolation | Compose networks are coarse compared to default-deny per-namespace policy | Yes — tenant and pool isolation is only partly testable locally |
| IAM and least privilege | Local containers have no equivalent | Yes — entirely untested locally |
| Secrets handling | A local `.env` is not a secrets manager | Yes, and see below |

**Local secret handling must never become the production pattern.** A `.env` file is acceptable for local development only. Code reads secrets through a resolver interface from day one, so the local file and a real secrets manager are two implementations of the same seam. Never read an environment variable for a credential directly in application code.

## Docker Compose Conventions

- **One service per container**, matching the architectural layer boundaries in the spec. Layer boundaries are the thing we are testing; collapsing them locally defeats the purpose.
- **Pin exact image tags.** Never `:latest`. Local reproducibility matters for the same reason it matters in production.
- **Named volumes** for anything with state, so a restart is not a data loss.
- **Health checks** on every service, and `depends_on` with condition `service_healthy` — the startup ordering in the spec (registry, then orchestrator, then pools, then gateway) is enforced locally too, so ordering bugs surface on a laptop rather than in a cluster.
- **A single `docker compose up` must bring the whole stack to a working state.** If onboarding needs a runbook, the Compose file is wrong.
- **Resource limits** on containers, so local behaviour under constraint is at least directionally informative.
- Keep a **`compose.override.yml`** for developer-specific tweaks, and keep it out of version control.

## Cloud Readiness Checkpoint

Reviewed **after every three features**. The default answer is *stay local* — the checkpoint exists to catch the moment that stops being true, not to build momentum toward a migration.

Move to cloud only when something concrete is blocked. Full criteria and the decision record live in the spec's phased delivery plan. The short version: a single machine no longer suffices, a property that only a cluster can validate is now on the critical path, data exists that must not be lost, someone outside the team needs access, or GPU capacity is required for self-hosted models.

"It feels like time" is not a criterion.
