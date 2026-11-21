# Roadmap

One task per session. `[x]` only after the checks in `docs/AGENT_WORKFLOW.md` passed and the Outcome is written in `docs/plans/`. A phase starts only after the previous **Gate** is approved by the owner.

Effort in brackets is the suggested plan level; the agent re-proposes per subtask at task start.

## Phase 0 — Agent workflow

- [x] 0.1 Set up workflow files: `CLAUDE.md`, `code/CLAUDE.md`, `docs/`, `.claude/settings.json`, hook `[low]` → `plans/phase-0-agent-workflow.md`
- [ ] **Gate 0:** owner reads `docs/AGENT_WORKFLOW.md` and approves the structure.

## Phase 1 — Module 1–2 baseline (running, needs tests)

- [x] 1.1 Add `code/tests/` with stdlib `unittest` for `parse_line`, `normalize_light`, `Reading.update`, `evaluate`, `Thresholds.apply_feed`. No serial, no network, fake env. `[medium]` → `plans/phase-1-module12-tests.md`
- [ ] 1.2 Owner re-runs `code/HUONG_DAN.md` end to end on hardware; agent records the result in the Outcome. `[low]`
- [ ] **Gate 1:** tests green, hardware loop confirmed, `PROTOCOL.md` v0.1.1 matches the code.

## Phase 2 — Module 3 contract

- [x] 2.1 Settle D3, D4 (below) with the owner. `[high]` — answered 2026-11-20.
- [x] 2.2 Propose `PROTOCOL.md` v0.2.0: feeds `den`, `quat`, `cua`, serial commands for light/fan/servo, acknowledgements, feed budget and points/min. `[xhigh]` → `plans/phase-2-module3-contract.md` — proposal written 2026-11-20, approved at Gate 2 2026-11-20.
- [x] **Gate 2:** owner approves `PROTOCOL.md` v0.2.0. No Module 3 code before this. — approved 2026-11-20.

## Phase 3 — Module 3 device control

- [x] 3.1 `config.py` + `.env.example`: new feed constants. `[low]`
- [x] 3.2 `gateway.py`: subscribe to control feeds, forward commands to serial, avoid echo loops. `[high]` — done 2026-11-20 (gateway + web side; 116 tests green, not run on the board).
- [x] 3.3 `yolobit.py`: handle new commands, fan and servo, keep alert LED behaviour per D3. `[high]` — written 2026-11-20, compiles only; never run on the board (owner's run, Gate 3). Servo angles `ANGLE_OPEN`/`ANGLE_CLOSE` and `PWM_MAX` need checking on the kit.
- [x] 3.4 Tests for command parsing and routing. `[medium]` — `tests/test_module3.py`, written with 3.2.
- [ ] **Gate 3:** owner demo on hardware: dashboard click → device reacts in < 3 s.

## Phase 4 — Module 4 log

- [ ] 4.1 Settle D5 (log storage). `[xhigh]`
- [ ] 4.2 Log device on/off, alerts and face attempts per D5. `[medium]`
- [ ] **Gate 4:** owner sees each event type in the log after a demo run.

## Phase 5 — Module 5 interface

Owner waived the gate order on 2026-10-26 for the web **UI on mock data** only (5.2–5.5): no serial, feed or threshold change is allowed before its own gate. Plan: `plans/phase-5-web-ui.md`.

Owner instruction 2026-10-26 (later): finish all of Phase 5 in one run, no per-task plan approval; desktop browser only (D12).

- [ ] 5.1 Adafruit IO dashboard from the feeds in `PROTOCOL.md` (owner builds, agent writes the block list). `[low]` — block list done in `ADAFRUIT_DASHBOARD.md`; owner builds it.
- [x] 5.2 Tokens and components from Figma `180:20`; `web_server.py` with login cookie (D10) and SSE; `web_mock.py`; tests. `[high]`
- [x] 5.3 Login screen from Figma `5:4`. `[medium]`
- [x] 5.4a Dashboard shell, sensor cards, alert and offline states, threshold modal from `11:593`, `11:1014`, `11:1418`, `28:1829`. `[medium]`
- [x] 5.4b Device cards and state machines from `181:10`, door auto-lock (D11). `[high]`
- [x] 5.4c Face and voice panels on mock data, simulate buttons (D11). `[medium]`
- [x] 5.5 Activity log screen from `7:97` and dashboard section 04, on mock data. `[medium]`
- [ ] 5.6 `web_live.py`: sensors and thresholds after Gate 1, devices after Gate 3, log after D5, face after Gate 6, voice after Gate 7. `[high]` — sensors, alert, thresholds (read and write, `PROTOCOL.md` v0.1.1) and Adafruit sensor history done for `WEB_DATA=live`, not hardware-verified; devices, face, voice and stored log wait for their gates.
- [x] 5.7 Module 1–2 inside the web: `WEB_DATA=gateway` runs the `gateway.Gateway` loop in `web_server.py` (one program for the demo); web saves thresholds (v0.1.1). `[high]` — not hardware-verified.
- [ ] **Gate 5:** works in a desktop browser on the laptop (D12); sensor → screen < 5 s with the board (`WEB_DATA=gateway`).

## Phase 6 — Face recognition (main AI)

- [x] 6.1 Settle D7 (approach, library); plan dataset and internal test set. `[max]` → `plans/phase-6-face.md`
- [ ] 6.2 Enrol members, train, evaluate on the internal test set; record real accuracy. The pipeline is in the repo. This stays open until real photos replace `docs/face/smoke`. `[max]`
- [ ] 6.3 Correct face → servo opens door; wrong/failed → stays closed, UI button still works. Code sends `DOOR:OPEN` through Module 3. Not hardware-verified. `[high]`
- [ ] **Gate 6:** owner reviews the evaluation numbers and the fallback.

## Phase 7 — Vietnamese voice commands

- [ ] 7.1 Settle D8 (speech engine). `[high]`
- [ ] 7.2 Fixed commands for light and fan on/off, no LLM. `[medium]`
- [ ] **Gate 7:** owner demo of each command.

## Phase 8 — Demo hardening

- [ ] 8.1 30-minute stability run without losing Adafruit; fix what breaks. `[high]`
- [ ] 8.2 `/security-review` at `xhigh` (keys in browser, `.env`, door control). `[xhigh]`
- [ ] 8.3 Update `Bao_cao_NhaThongMinh.md` with real results. `[medium]`
- [ ] **Gate 8:** demo-ready.

## Decisions

Open rows are the owner's to answer. The agent does not decide them, and does not re-open closed ones.

| # | Question | Status | Answer | Blocks |
| --- | --- | --- | --- | --- |
| D1 | Which Figma file and account? | Closed 2026-10-26 | Account `pnghia`, file DADN `capP3RVGqyp3EogAk90l6a`, not the copy | — |
| D2 | Where does AI run? | Closed (spec) | Laptop gateway, webcam and mic of the laptop; never on the board | — |
| D3 | Share the 4 RGB LEDs on P14 between the alert (Module 2) and the manual light (Module 3), or move the alert to the 5x5 matrix only? | Closed 2026-11-20 | Share P14. Alert has priority: while an alert is active the 4 LEDs blink red; when it clears they return to the manual light colour. The 5x5 matrix always shows the alert state. | 2.2 |
| D4 | Which ports for the fan and the servo? (Not P0, not P14.) | Closed 2026-11-20 | Fan (PWM) on P1, door servo on P4 (servo row; changed from P2 by the owner 2026-11-20). | 2.2 |
| D5 | Where is the Module 4 log stored? Feeds are 10/10 after Module 3. | Open | | Phase 4 |
| D6 | Web stack, and how does the browser control Adafruit without exposing `AIO_KEY`? | Closed 2026-10-26 | Python stdlib server on the laptop (`code/web_server.py`, `http.server` + SSE) holds the key; plain HTML/CSS/JS in `code/web/`, no build step, no new dependency | — |
| D7 | Face recognition approach and library. | Closed 2026-11-20 | Laptop only. Compare OpenCV LBPH and YuNet + SFace. A match sends `DOOR:OPEN` on the Module 3 door command. Threshold comes from `face_train.py` on the team's photos, not from the synthetic smoke test. | — |
| D8 | Vietnamese speech engine (offline or online). | Open | | Phase 7 |
| D9 | Test framework: stdlib `unittest`, no new dependency. | Proposed | | 1.1 |
| D10 | Web login? (Not in the spec; the web can open the door.) | Closed 2026-10-26 | One shared `WEB_PASSWORD` in `.env`, HttpOnly session cookie; no email accounts, no "forgot password" | — |
| D11 | Keep Figma extras beyond the spec? | Closed 2026-10-26 | Keep: light colour (4 presets), fan speed 0–100 %, door auto-lock after 10 s, simulate/test buttons. Their feed/serial encoding is decided in 2.2 | 2.2 |
| D12 | Web on phones? | Closed 2026-10-26 | No: desktop browser on the laptop only. Server listens on `127.0.0.1`. `User_Requirements.md` §4 still says phone + computer; owner to update it | Gate 5 |
