# Contributing

Thanks for helping Sancho ride straighter.

1. Open an issue first for anything larger than a fix.
2. Edit roles only in `skills/sancho/roles/`; run `python tools/build.py --agents` to regenerate `agents/`.
3. Gate checklist items live only in `skills/sancho/scripts/gates.json`.
4. Scripts must stay standard-library only and Python 3.9 compatible.
5. Run `python -I tests/validate.py` before opening a pull request; add fixtures for new rules (one valid, two invalid per schema change).
6. Add behavioral scenarios to `tests/evals.json` when you change how the skill behaves.
7. Use Conventional Commits; update `CHANGELOG.md` under Unreleased.

Documentation is maintained in English, Italian and Spanish; please update all three READMEs and guides, or say in the PR which translations are pending.
