# 0002. Containers for the API and database

- Status: accepted
- Date: 2026-10-06
- Deciders: Danilo (user); proposed by the architect role
- Phase: PLAN · Related: D-005, references/stack-decision.md (decision tree)

## Context and problem
There is a backend and a database we run ourselves (tree: yes). The deploy target is an EU VM, not a PaaS that builds from source. Two developers on Windows and Linux need identical environments.

## Options considered
1. Docker image for the API + docker compose (API + PostgreSQL) for development; same image in test and prod.
2. PaaS building from source; containers only for local development.
3. No containers: virtualenv locally, systemd service on the VM.

## Decision
Chosen: **option 1** - reproducible builds and dev/prod parity with little operational overhead.

## Consequences
- Good: same artifact in every environment; Trivy can scan the exact image.
- Bad: the team must keep the base image digest current (monthly task + Trivy in CI).
- Hardening applied: multi-stage build, non-root user, digest-pinned base, HEALTHCHECK, read-only filesystem and dropped capabilities in compose, secrets at runtime only, ports bound to 127.0.0.1 in development.
