# Standard: architecture

_Source: ADR 0001, 0002 · Updated: 2026-10-07_

1. **MUST** keep three deployables: `android/`, `web/`, `api/` - _why:_ separate release cycles.
2. **MUST** treat the API as the only writer to the database; clients never talk to storage directly.
3. **MUST** generate job ids on the client (UUID v7) - _why:_ offline creation without collisions.
4. **SHOULD** keep API modules by domain (`jobs`, `auth`, `signature`), not by layer.
5. **MUST NOT** add a new service or queue without an ADR.
