# 0001. Application stack

- Status: accepted
- Date: 2026-10-06
- Deciders: Danilo (user); proposed by the architect role
- Phase: PLAN · Related: R-002, R-004, R-007, D-004

## Context and problem
Two platforms (Android for technicians, web for the office) and an API. Offline-first logging on Android is the hardest requirement (R-004). The team knows Python and Kotlin, some React.

## Options considered
1. Kotlin (Compose, Room) + FastAPI + PostgreSQL + React
2. Flutter + Django REST + PostgreSQL (Flutter also for web)
3. React Native + NestJS + PostgreSQL + React

## Decision
Chosen: **option 1**, because it scores highest on team skills and on the maturity of offline storage (Room + WorkManager), and keeps each layer on mainstream, long-supported tools.

## Consequences
- Good: native performance and Android APIs; Python API is quick for the team; PostgreSQL covers reporting needs.
- Bad: no code sharing between Android and web; an iOS app later means a second native app or a rewrite in a cross-platform toolkit.
- Follow-up: revisit Kotlin Multiplatform if iOS enters scope.

## Pros and cons of the options
### Flutter + Django
- Good: one codebase for Android and (later) iOS.
- Bad: team has no Dart experience; web support for a data-heavy dashboard is weaker.
### React Native + NestJS
- Good: TypeScript everywhere.
- Bad: offline storage choices less mature for the conflict model; team prefers Python on the server.
