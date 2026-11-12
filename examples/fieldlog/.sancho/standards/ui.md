# Standard: UI

_Source: design/tokens.json, PLAN · Updated: 2026-10-07_

1. **MUST** use semantic tokens only (`color.text.default`, `color.action.primary`), never raw hex values.
2. **MUST** keep focus visible (2 px outline, `color.action.primary`) and a logical tab order.
3. **MUST** give touch targets at least 48x48 dp on Android (Material) and 24x24 CSS px on web.
4. **MUST NOT** convey status by color alone: sync state uses icon + text ("Waiting to sync").
5. **SHOULD** write UI copy in Italian with the glossary terms; sentence case for buttons.
