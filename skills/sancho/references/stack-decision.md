# Stack decision and container decision tree

## 1. Decision matrix

Areas (include only those that apply): language(s), frontend framework, mobile approach, backend framework, database, authentication, hosting/deploy, CI/CD, key libraries (state management, ORM, testing).

Steps:
1. Agree the criteria weights with the user (1-5). Default weights:

| Criterion | Default weight | Question |
|---|---|---|
| Platform fit | 5 | Does it cover every target platform well? |
| Team skills | 4 | Can the team (or the user alone) maintain it? |
| Maturity / LTS | 4 | Stable, supported release line, long-term support? |
| Ecosystem | 3 | Libraries, docs, hiring, community? |
| Security record | 3 | Track record, update cadence, secure defaults? |
| Cost | 3 | Licenses, hosting, services at expected scale? |
| Performance | 2 | Enough for the non-functional requirements? |
| Time to market | 3 | How fast to an MVP? |
| License | gate | Compatible with the project license? (fail = excluded) |

2. For each area: a **recommendation** and **two alternatives**, scored 1-5 per criterion, weighted total, plus one paragraph of reasoning and the main risk of each. Present it as a table.
3. Verify time-sensitive facts (current LTS, deprecations, license changes, pricing) with a search, citing the source, or mark them HYPOTHESIS.
4. The user decides. Record each decision in `state.json` `stack` (via the orchestrator) and as an ADR.
5. If the user imposes a choice, do not re-argue it: list concrete risks and mitigations only.

Mobile approach options to always consider when Android and iOS are both targets: native (Kotlin + Swift), cross-platform (Flutter, React Native, Kotlin Multiplatform), PWA. State what each means for store presence, device APIs, offline, team size.

## 2. Container decision tree

```
Is there a backend, worker, or database the project runs itself?
├─ no  -> no containers. ADR: "static/serverless/mobile-only, no container".
└─ yes
   ├─ Is the deploy target a PaaS or serverless that builds from source (and the user prefers it)?
   │   └─ yes -> containers optional: use one for local dev parity only. ADR records it.
   └─ no / unsure
       ├─ More than one service (API + worker + DB + cache)? -> docker-compose for dev, one image per service.
       └─ Need dev/prod parity or reproducible builds? -> Dockerfile per service.
```

Always record the outcome as an ADR, including "no containers".

## 3. Container hardening checklist

- Multi-stage build: build tools stay in the builder stage.
- Minimal runtime base (distroless, slim or alpine as appropriate), **pinned by digest** (`image:tag@sha256:...`); document how to update it.
- Run as a non-root user (`USER`), read-only filesystem where possible, drop capabilities in compose/k8s.
- `HEALTHCHECK` (or orchestrator probes).
- `.dockerignore` excludes `.git`, `.env*`, `node_modules`, build output, secrets.
- No secrets in the image or build args; inject at runtime (env vars, secret store, compose secrets).
- One process per container; logs to stdout/stderr.
- Scan the image with Trivy in VERIFY.
- `docker-compose.yml` for development: named volumes for data, healthcheck-based `depends_on`, ports bound to `127.0.0.1` unless the user needs LAN access.
