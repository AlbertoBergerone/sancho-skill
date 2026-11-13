# User Acceptance Testing (UAT)

UAT is the user (or their testers) confirming, on real devices, that the product does what the stories promised. Automated tests check the code; UAT checks the product.

## Where cases come from

Every acceptance criterion with `verification.method = "uat"` needs at least one UAT case. QA writes them in TASKS, so the user knows early what they will be asked to check. Cases live in `.sancho/uat.json` (`schemas/uat.schema.json`).

Testers read these cases, so their text (title, preconditions, test data notes, steps, expected results) is written in the project language (`settings.language`), even when the user chats in another language. Ids, keys and enum values stay in English. Write a new case in the project language even when the existing cases are in another language: never match the old cases instead; offer once to translate them, and translate only if the user agrees. When guiding a case in chat, talk in the user's language and quote the case text as written.

## Writing a good case

| Field | Rule |
|---|---|
| title | What is checked, in the user's words ("Wrong password shows a generic error") |
| story, criteria | The story and the criterion ids it verifies |
| platform | One platform/device per case: "web (Chrome, desktop)", "android (Pixel 7, Android 15)" |
| preconditions | What must be true before step 1, and how to make it true |
| test_data | Exact accounts, values, files - copyable |
| steps | Numbered, one action each, imperative, no jargon ("Tap Save", not "Submit the form") |
| steps[].expected | What the tester should see after that step, when it matters |
| expected_result | The final observable outcome that decides pass/fail |

For must-have stories also write negative and edge cases: wrong input, empty state, no network, permission denied, interrupted flow, very long text, another language.

## Outputs

`scripts/uat_export.py .sancho/uat.json --md docs/uat/UAT.md --csv docs/uat/uat.csv` (labels in the project language by default; pass `--lang it|en|es` only if the user asks for another; add `--delimiter ";"` for spreadsheet apps set to Italian/Spanish locales). The Markdown is printable with checkboxes; the CSV opens in a spreadsheet for testers.

## Running UAT (VERIFY)

Two ways, the user chooses:
1. **Guided in chat.** One case at a time: show preconditions, data and steps; wait for "pass", "fail" or "blocked" plus notes. On fail ask what they saw (screenshot welcome), then create the defect. Record each case with `scripts/state.py uat UAT-004 --result pass|fail|blocked [--note TEXT] [--new-defect major:WHAT THEY SAW | --defect DEF-002] [--tester NAME]` (it validates the file); defect status with `scripts/state.py defect DEF-002 --status fixed|verified|wont_fix [--task T-012]`.
2. **Spreadsheet.** The user fills the CSV (Result, Executed by, Notes) and sends it back; import with `scripts/uat_export.py .sancho/uat.json --import-csv <file>`. Failed cases without a defect get one automatically (severity major) for QA to triage. In team mode the import writes `uat.json` directly: use it only when one person runs the whole UAT round; otherwise each tester records results with `state.py uat` (`references/team.md`).

Defects: `DEF-nnn` with severity (single scale), steps to reproduce, status; linked to a fix task. A fixed defect is `verified` only after the case is re-run and passes.

Gate: VERIFY cannot be approved with open blocker or major defects, unless the user explicitly accepts the risk (recorded with `approve --override`).

## For the tester (text for help uat)

```
You will receive a list of checks. For each one:
1. Prepare what "Preconditions" says, using the "Test data".
2. Follow the steps in order, exactly as written.
3. Compare what you see with the "Expected result".
4. Mark: pass (it matches), fail (it does not - describe what you saw), blocked (you could not run it - say why).
Write notes for anything odd, even when the check passes.
Two ways to run them: guided here in chat, one check at a time, or in a spreadsheet (uat.csv) that you fill in and send back.
```
