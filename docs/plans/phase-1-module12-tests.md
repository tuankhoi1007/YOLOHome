# Phase 1.1: unit tests for the pure Module 1-2 functions

- Approved: 2026-11-20 (owner, plan mode)
- Effort: medium
- Branch: `feat/5-web-ui` (see Notes)

## Plan

Cover `parse_line`, `normalize_light`, `Reading.update`, `evaluate` and `Thresholds.apply_feed` with stdlib `unittest`, in one new file `code/tests/test_module12.py`. Fake env set before `import config`; no serial, no network, no real `.env`. No change to `module1.py` or `module2.py`.

Before this task the suite had 58 passing tests (gateway loop, web providers, `ThresholdPublisher`). None of the five functions was tested directly.

Also in this task (docs only): fix `code/HUONG_DAN.md` (threshold feeds `nguong-am` and `nguong-sang` exist; stale `d:\HCMUT\...` path), tick 1.1 in `docs/ROADMAP.md`.

## Outcome

Done 2026-11-20.

- Added `code/tests/test_module12.py`: 34 tests in 5 classes (`ParseLineTest`, `NormalizeLightTest`, `ReadingUpdateTest`, `EvaluateTest`, `ThresholdsApplyFeedTest`).
- `python3 -m py_compile code/*.py code/tests/test_module12.py`: OK.
- `python3 -m unittest discover -s code/tests -t code`: 92 tests, OK (58 old + 34 new). No code bug found.
- `HUONG_DAN.md`: threshold paragraph and two paths updated.

Not verified:

- The mutation check from the plan (flip `>` to `>=` in a scratchpad copy of `evaluate`) was not run: the command was denied. The boundary test `test_exactly_at_limit_is_still_ok` is therefore not proven to catch that change.
- Everything that needs the board, the COM port, `.env` or Adafruit. That is 1.2 and Gate 1, the owner's.

## Notes

- The branch `feat/5-web-ui` still holds uncommitted Phase 5 documents. The agent did not create a new branch or commit anything. Owner decides how to commit these changes.
- ROADMAP rule: Gate 1 needs 1.2 (owner re-runs `HUONG_DAN.md` on hardware) and a check that `PROTOCOL.md` v0.1.1 matches the code.

## Open decisions for the owner (Phase 2)

These are proposals only. The owner answers; the agent does not decide them.

**D3: the 4 RGB LEDs on P14, shared or not?**

- Option A (recommended): share P14. Alert has priority: while an alert is active the LEDs blink red; otherwise they show the manual light colour. The 5x5 matrix keeps showing the alert state in both cases. Pros: matches the spec (one set of LEDs, one light), no extra hardware. Cons: the manual light is overridden during an alert, so the board code needs a priority rule.
- Option B: alert on the 5x5 matrix only, P14 is the manual light only. Pros: simple, no priority rule. Cons: the 4 red blinking LEDs shown in the current demo checklist disappear, and the alert is easier to miss.

**D4: ports for the fan relay and the servo (not P0, not P14)?**

- The agent cannot see which expansion-board ports are free on the owner's kit. Needed from the owner: the port names printed on the board for the fan relay and the servo (candidates: P1, P2, P3, P4 or the D-ports on the extension board).
- Proposal: servo on one PWM-capable port, fan relay on a digital port next to it, so wiring stays tidy. Owner confirms after checking the kit.

## Handoff prompt

"Start ROADMAP 2.1: read docs/ROADMAP.md D3 and D4 and the options in docs/plans/phase-1-module12-tests.md, take the owner's answers, then plan PROTOCOL.md v0.2.0 (2.2) at xhigh."
