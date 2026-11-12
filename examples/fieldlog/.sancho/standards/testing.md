# Standard: testing

_Updated: 2026-10-07_

1. **MUST** write the failing test first (TDD) for every criterion and bug fix.
2. **MUST** name tests after behavior: `test_login_locks_after_five_failures`.
3. API: pytest, one test module per route module, factories for data, no real network.
4. Android: JUnit + Turbine for view models; Room in-memory DB for storage tests.
5. Web: Vitest for logic, Playwright + axe for accessibility of key pages.
6. **SHOULD** keep unit tests under 1 s each; mark slow tests.
