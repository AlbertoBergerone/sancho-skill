# Standard: API

_Source: ADR 0001, threat model · Updated: 2026-10-07_

## Rules
1. **MUST** version under `/v1`; breaking changes need a new version and an ADR.
2. **MUST** return errors as `{"error": {"code": "...", "message": "..."}}`; messages never reveal whether an account exists (TM-01).
3. **MUST** check authorization on every request: a technician reads and writes only their own jobs (TM-03).
4. **MUST** validate input with Pydantic models; reject unknown fields.
5. **SHOULD** paginate lists with `?cursor=` and `limit` (max 100).

## Good
```python
raise HTTPException(401, detail={"code": "invalid_credentials", "message": "Email or password is not correct"})
```
## Bad
```python
raise HTTPException(404, detail="User not found")   # reveals account existence
```
