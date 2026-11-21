# Phase 5 — Web UI on mock data

Requested 2026-10-26 by the owner: "implement the web, read all the Figma design and plan the implementation". Plan approved 2026-10-26. Effort: plan `high`; per-task levels in the Session split table.

2026-11-21: `face_owner` and `face_stranger` were removed. The face card is a placeholder. Voice simulate stays. Phase 6 is a teammate's work.


## Context

The owner wants the YOLOHome web built from the Figma file DADN (`capP3RVGqyp3EogAk90l6a`). In `docs/ROADMAP.md` the web is Phase 5, behind Gates 0–4, with D6 (stack + key safety) open and the device, log, face and voice data not yet defined. Owner decisions on 2026-10-26:

- **Order:** build the **full UI now on a mock data layer**, and wire real data phase by phase later. This waives the gate order for UI work only. No serial, feed or threshold contract changes.
- **D6:** Python stdlib server on the laptop (`http.server`, SSE) holds `AIO_KEY`. Frontend is plain HTML/CSS/JS, no build step, no new dependency.
- **D10 (new):** login = one shared `WEB_PASSWORD` from `.env` + HttpOnly session cookie. No email accounts, no "forgot password".
- **D11 (new):** keep these Figma extras beyond the spec: light colour picker (4 presets), fan speed 0–100 %, door auto-lock after 10 s, simulate/test buttons. They become inputs to `PROTOCOL.md` v0.2.0 (task 2.2). Nothing is decided here about how `den`, `quat` and `cua` encode them.

All 8 frames were read on 2026-10-26: `180:20` foundations, `181:10` device states, `5:4` login, `11:593`/`11:1014`/`11:1418` dashboard normal/alert/offline, `28:1829` threshold modal, `7:97` activity log.

## Architecture

```
browser on the laptop (D12: 127.0.0.1 only, no phones)
   │  HTTP + cookie, JSON, SSE  (never sees AIO_KEY)
code/web_server.py  ── provider ──>  web_mock.py   (this phase)
                                      web_live.py   (later: MQTT via config.connect_mqtt)
```

- `code/web_server.py`: `ThreadingHTTPServer`, serves `code/web/` and `/api/*`. Settings come only from `config.py`: new `WEB_PORT` (8000), `WEB_PASSWORD`, `WEB_DATA` (`mock`). Key names go in `.env.example` only.
- `code/web_mock.py`: `MockHome`, a plain class holding sensors (slow drift), thresholds, alert text (it reuses `evaluate` from `module2.py` so alert wording matches the gateway), devices, gateway online flag, face/voice last result, and an in-memory event log. It simulates the device ack delay (`MOCK_ACK_MS`, default 900). An ack delay over the 3 s UI timeout shows the "Quá thời gian chờ" state.
- Swapping `mock` → `live` later must not change any frontend file. That is the point of the provider interface: `snapshot()`, `set_thresholds()`, `command(device, body)`, `log(filters)`, `simulate(kind)`, `subscribe()`.

### API (JSON, all except login need the session cookie → 401 redirects to login)

| Method & path | Purpose |
|---|---|
| `POST /api/login` `{password}` / `POST /api/logout` | `hmac.compare_digest`, random token, cookie `HttpOnly; SameSite=Strict` |
| `GET /api/state` | Full snapshot for first paint |
| `GET /api/events` | SSE: `sensors`, `alert`, `device`, `gateway`, `face`, `voice`, `log` |
| `POST /api/thresholds` | `temp_max` 0–80, `humid_max` 0–100, `light_min` 0–100 (ranges per PROTOCOL v0.1.0) |
| `POST /api/devices/light` `{on, color}` · `/fan` `{on, speed}` · `/door` `{action:"unlock"\|"lock"}` | Returns 202 "sent". The ack arrives later on SSE. While offline: 503 → "Gửi lệnh thất bại" |
| `GET /api/log?type=&date=&q=&page=` | 10 per page (frame `7:97`) |
| `POST /api/sim/{overheat,offline,face_owner,face_stranger,voice}` | Demo buttons (D11) |

Feed budget: **no change**. Mock publishes nothing: 7/10 feeds and about 12 points/min stay as in PROTOCOL v0.1.0.

## Frontend (`code/web/`)

- `login.html`, `index.html` (dashboard), `log.html`; `img/` holds the login photo (downloaded through `get_design_context`, no Figma URLs left).
- `css/tokens.css`: tokens from `180:20`: `--gold #b8860b`, `--ink #1a1a1a`, `--muted #6b6b6b`, `--line #e8e4df`, `--surface #f5f3f0`, `--bg #fafaf8`, ok `#166534`/`#f0fdf4`, warn `#92400e`/`#fffbeb`, danger `#b91c1c`/`#fef2f2`; spacing 4/8/16/24/48; radius 8/9999. The font is confirmed from design context (looks like Plus Jakarta Sans via Google Fonts, system fallback).
- `css/components.css`: button (primary/dark/ghost/outline), badge (ok/warn/danger/neutral), toggle, card, section divider title, modal, toast, pill filter, table, pagination.
- `js/api.js`: fetch wrapper, SSE with auto-reconnect, and an offline banner when SSE drops. `js/dashboard.js`, `js/devices.js`, `js/thresholds.js`, `js/log.js`, `js/login.js`.
- `js/devices.js` holds the state machine from `181:10`, one per device:
  - light/fan: `off → sending → awaiting_ack → on`, plus `send_failed` (Thử lại) and `timeout` after 3 s (Kiểm tra trạng thái). The card shows the requested state and the confirmed state separately.
  - door: `locked → unlocking → unlocked (countdown 10→0) → locked`, plus `unlock_failed`. **"Mở khóa bằng tay" stays enabled whatever the face result is**, and is disabled only while the gateway is offline.
- Responsive: Figma is desktop only (1440/1920). Below 900 px the cards and AI panels go to one column; below 600 px the header collapses (logo + status + menu) and the log table becomes stacked rows. No horizontal scroll at 360 px.

### Copy corrections (Figma text vs hardware: follow PROTOCOL/README)

LED RGB is **P14** (Figma says P0). The light sensor is **P0** (Figma says P2). Fan and servo ports show "chưa chốt" until D4. Footer: "Yolo:Bit • Adafruit IO" (not ESP32). The default light threshold comes from the API (code default 20, Figma shows 30). Camera and voice panels say they run on the laptop Gateway. The mic button triggers `/api/sim/voice` in mock mode (the real engine is D8). The camera box is a placeholder with the last result overlay (the real feed is D7).

## Session split (ROADMAP rewrite of Phase 5, one task per session, branch `feat/5-web-ui`)

| Task | Content | Figma | Effort |
|---|---|---|---|
| 5.2 | Record D6/D10/D11 + this plan in `docs/plans/phase-5-web-ui.md`; `tokens.css`, `components.css`; `web_server.py` skeleton + auth + `web_mock.py` + SSE; tests | `180:20` | `high` (auth, SSE threading); docs `low` |
| 5.3 | Login page | `5:4` | `medium` |
| 5.4a | Dashboard shell: header, sections 01 (sensor cards, LED status line), alert state + toast, offline banner + disabled cards, threshold modal | `11:593`, `11:1014`, `11:1418`, `28:1829` | `medium` |
| 5.4b | Device cards + state machines + door auto-lock | `181:10` | `high` |
| 5.4c | Section 03 face/voice panels (mock) + sim buttons | `11:593` child nodes | `medium` |
| 5.5 | Log page + dashboard section 04 (filters, search, date, pagination) | `7:97` | `medium` |
| later | `web_live.py`: sensors/thresholds live after Gate 1; devices after Gate 3; log after D5; face after Phase 6; voice after Phase 7 | — | per phase |

Figma rate limit: in each session, call `get_design_context` per frame, and for the 1920×2280 dashboards per section child node, never the page.

## Files

- New: `code/web_server.py`, `code/web_mock.py`, `code/web/**`, `code/tests/test_web.py` (stdlib `unittest`, D9).
- Edit: `code/config.py` (3 `WEB_*` settings), `code/.env.example` (key names only), `docs/ROADMAP.md` (Phase 5 rows, D6 closed, D10/D11 added, note on gate waiver for UI), `docs/FIGMA.md` (task column), `README.md` + `code/HUONG_DAN.md` (how to run the web), `code/CLAUDE.md` (web conventions: JS/HTML comments without accents like Python, UI text with accents, all data through `js/api.js`).
- Reuse: `config.env`/`env_float`, `module2.evaluate` for alert text, `config.connect_mqtt` later for live.
- Not touched: `yolobit.py`, `gateway.py`, `PROTOCOL.md`, `.env`.

## Verification

1. `python3 -m py_compile code/*.py` and `python3 -m unittest discover -s code/tests -t code`: auth (wrong/right password, missing cookie → 401), threshold validation, log filter/pagination, mock device transitions and the door countdown, alert text from `evaluate`.
2. The agent's smoke run sets fake `AIO_USERNAME`/`AIO_KEY`/`WEB_PASSWORD` in the shell environment. It runs `python3 code/web_server.py` and checks with `curl` (login → cookie → `/api/state`, `/api/events` stream, a light command → ack event). The real `.env` is never read or printed.
3. If a headless browser is available, screenshots at 360, 768 and 1440 px are compared with each frame. If not, the owner checks phone and desktop width (Gate 5).
4. Not verified by the agent: phone access over LAN, and anything live (Adafruit, board). Those are the owner's runs.

## Before starting

- Done 2026-10-26: owner committed Phase 0 on `main` (`1141500`) and created `feat/5-web-ui`.
- `/effort high` for the code part of 5.2.

## Outcome

Kept per task below as each session closes.

- 5.2 docs (2026-10-26): plan exported, ROADMAP Phase 5 rewritten, D6 closed, D10/D11 added. No code yet.

### 5.2 — server, mock, tokens (2026-10-26, effort `high`)

Changed:
- New `code/web_server.py`: `ThreadingHTTPServer` on `0.0.0.0:WEB_PORT`, `Sessions` (shared password, `hmac.compare_digest`, 12 h HttpOnly + SameSite=Strict cookie, 5 failures per 60 s → 429), `EventHub` (SSE, `retry: 3000`, 15 s ping, a slow client is dropped and re-syncs), static files with a fixed content-type table and a `..` guard, CSP and security headers, POST bodies only as `application/json` and ≤ 10 KB.
- New `code/web_mock.py`: `MockHome` with the provider interface from the plan. It reuses `module1.Reading`, `module2.Thresholds` ranges and `module2.evaluate`, so alert text matches the gateway. Simulated ack after `MOCK_ACK_MS`. While offline: commands get 503, sensors stop, pending acks are dropped (the UI shows a timeout). Door auto-lock after 10 s. Face owner opens the door; a stranger does not. Voice cycles the 4 fixed commands. In-memory log, newest first, 10 per page.
- `code/config.py`: `WEB_PORT`, `WEB_PASSWORD`, `WEB_DATA`, `MOCK_ACK_MS`; key names only in `.env.example`.
- `code/web/`:
  - `css/tokens.css` (all `180:20` variables) and `css/base.css`;
  - `css/components.css`: Button, Badge and Toggle from `180:20`; the toggle uses the three Figma SVGs in `img/`;
  - `js/api.js`: the only network layer, with SSE reconnect;
  - temporary `login.html`, `index.html` and `css/temp.css`, replaced in 5.3 and 5.4a;
  - `components.html`, a preview to compare with `180:20`.
- New `code/tests/test_web.py`: 35 `unittest` cases. Sessions, command/threshold/log validation, mock transitions (ack, offline, door relock, overheat alert text, face, voice), and the HTTP server on `127.0.0.1` (401, redirect, cookie flags, 415, traversal, SSE ack).
- `README.md` section 6, `code/HUONG_DAN.md` checklist line, and a Web section in `code/CLAUDE.md`.

Verified in this session:
- `py_compile` passes and the 35 tests pass.
- Smoke run from a scratchpad copy without `.env` and with fake env vars:
  - `/` redirects to login, a wrong password gets 401, login sets the cookie, `/api/state` returns 200;
  - a light command returns 202 and its `device` ack arrives on SSE after 0.97 s, sensor events every 3 s;
  - logout makes `/api/state` return 401.
- Headless Chrome screenshots of `components.html` (1440 px, 500 px) match `180:20`: the font loads and every state is shown. `login.html` has no overflow at 500 px.

Deviations:
- `components.css` covers only what `180:20` defines (button, badge, toggle). Card, modal, toast, table, pills and pagination are added in 5.4a and 5.5 from their own frames instead of being guessed now.
- Added `css/base.css` and the temporary `css/temp.css`. Inline `<style>` would be blocked by the CSP.
- Added the simulate kind `online` next to `offline`, for the Figma "Thử kết nối lại" link.
- `code/tests/` was created here, before ROADMAP 1.1, which will add the module 1/2 tests next to it. D9 stays "Proposed" for the owner.
- Badge padding is 2/8 px, as the badges are used in the dashboard and device frames. The `180:20` sample shows 8 px padding at a fixed 180 px width.

Not verified:
- 360 px width: headless Chrome won't go below 500 px.
- Phone access over LAN, and the Windows firewall prompt.
- Running on Windows with the team's `.venv`.
- Nothing touches the board or Adafruit.

Left open / risks for 8.2:
- The cookie has no `Secure` flag (http on LAN).
- Sessions live in RAM; a restart logs everyone out.
- `config.py` still exits without `AIO_USERNAME`/`AIO_KEY` even in mock mode.

### Owner instruction 2026-10-26 (later)

"Remove the working on phone idea, I just need it to work on web, also do everything in Phase 5 … just follow the existed roadmap and finish Phase 5." Recorded as D12 (desktop only, server on `127.0.0.1`) and as a note in ROADMAP Phase 5. No per-task plan approval; all remaining tasks were done in this session at effort `high`.

### 5.1 — Adafruit dashboard block list

- `docs/ADAFRUIT_DASHBOARD.md`: 8 blocks on the 7 existing feeds (3 gauges, alert text, history chart, 3 threshold sliders). No feed added; slider writes are by hand.
- Not ticked: the owner builds the dashboard on io.adafruit.com.

### 5.3 — Login (`5:4`)

- `login.html`, `css/login.css`, `js/login.js`. Hero photo and icons downloaded from Figma into `web/img/` (the photo is a JPEG, saved as `login-hero.jpg`).
- Deviation (D10): no email field, no "Quên mật khẩu?". Show/hide password reuses the Figma eye-off icon (no open-eye icon in the design).

### 5.4a / 5.4b / 5.4c / 5.5 — Dashboard, devices, AI panels, log

- `index.html`, `css/app.css` (header, offline banner, footer, modal, toast, tabs, table), `css/dashboard.css`, `log.html`, `css/log.css`.
- JS: `dashboard.js`, `devices.js` (state machines from `181:10`), `ai.js`, `logview.js`, `log.js`, `thresholds.js`, `toast.js`, `dom.js`, `format.js`.
- Device cards: confirmed state only comes from `device` events; phases sending → waiting → done, or failed (Thử lại) / timeout after 3 s (Kiểm tra trạng thái); measured ack time in the footer. Door: countdown from `relock_in`, "Khóa ngay", and "Mở khóa bằng tay" is never disabled by a face result, only while offline or busy.
- Alerts: red card and "VƯỢT NGƯỠNG!", blinking LED line, toast only when an alert starts or its kinds change (not every new number).
- Offline (`11:1418`): banner with last-seen time, red stale footers, faded device cards with "Không thể gửi lệnh" overlay; the web-server-lost case uses the same banner.
- Log page: type pills, date, search (debounced), 10 per page with `1 2 3 … N` pager; reloads page 1 on new events.
- Bugs found by screenshots and fixed: CSP blocked `style="…"` (swatches, slider fill) → styles set through `node.style`; alert log entry per new number → only on start or kind change (test added).

Figma: the MCP Starter-plan call limit was reached after `5:4`, `11:979`, `11:612`, `11:598`, `11:967`, `13:10`. The device cards, sections 03–04, the modal, the toast and the log page were built from the full-frame screenshots taken during planning, not from design context. Icons for sun, fan, lock, mic, calendar, search, chevrons and close are Lucide (ISC) stand-ins in `web/img/`, marked in each file. **Owner check when the limit resets:** compare `181:10`, `28:1829`, `7:97` and the toast in `11:1014` with the pages, and swap in the Figma icons.

Other deviations:
- Device toggle is the pill switch from the dashboard frame (`11:713`), not the round `Yolo/Toggle` of `180:20`/`181:10`; the round one stays in `components.css` and on `/components.html`.
- Copy follows the hardware: RGB LED P14, light sensor P0, fan/servo ports "chưa chốt (D4)", modal hint without "còi hú" (no buzzer), footer "MicroPython • Yolo:Bit • Adafruit IO", no team member names (profile shows "Chủ nhà"), camera watermark says simulated (D7 open), voice engine "chưa chốt (D8)".
- Log page has a sixth pill "Giọng nói" (voice events are logged; the Figma frame has five pills).
- Light card chip says "Đủ sáng" instead of Figma's "Ánh sáng tự nhiên".

### 5.6 — Live data (`web_live.py`), partial

- `WEB_DATA=live` → `LiveHome`: seeds from the last feed values over REST, subscribes to `nhiet-do`, `do-am`, `anh-sang`, `canh-bao`, `nguong-*` (MQTT callbacks only queue; `tick()` applies them with `module2.take_cloud_value`). Alert text comes from the gateway's `canh-bao` feed (local `evaluate` until the first message). Gateway counts as offline after 45 s without sensor data (3 missed 15 s heartbeats) or when MQTT drops.
- Feed budget: no change. The web only subscribes; it publishes nothing (7/10 feeds, ~12 points/min as in v0.1.0). It opens one more MQTT connection on the same account next to `gateway.py`.
- Refused with a clear message in live mode: device commands (Gate 2), threshold writes (see proposal below), simulate buttons. Face, voice and devices show "chưa có" cards. The live log is in RAM only (D5 open).
- Not verified: anything against the real Adafruit account or board. Owner run: `gateway.py` + `WEB_DATA=live web_server.py`, check sensor → screen < 5 s (Gate 5) and that the second MQTT connection is accepted.

**Proposed `PROTOCOL.md` change (needs owner approval, not applied):** v0.1.1 — in the feed table, `nguong-nhiet`, `nguong-am`, `nguong-sang` "Written by: owner (Adafruit dashboard or web `/api/thresholds`)". Same keys, ranges and meaning; at most 3 points per save, by hand. After approval: make `LiveHome.set_thresholds` publish through a small publisher class (one write per changed feed, ≥ 2 s apart) and set `features.thresholds_write` to true.

### Verified in this session (all of Phase 5)

- `py_compile` on all Python files; `unittest`: 43 tests pass (sessions, validation, mock transitions, alert logging, `LiveHome` with fake MQTT messages, HTTP server on 127.0.0.1 incl. SSE).
- Smoke run with real login from a scratchpad copy without `.env`: redirect, 401, cookie flags, 202 + `device` ack after 0.95 s, sensors every 3 s, logout.
- Headless Chrome at 1440 px: login, dashboard normal / active (light purple, fan 40 %, door countdown, face match, voice) / alert / offline, threshold modal, log page. Screenshots were taken from a scratchpad copy with login off and SSE stubbed (headless capture limits); the repo code was not patched for this.

### Not verified

- The real Adafruit account, the board, and `WEB_DATA=live` end to end.
- Windows with the team's `.venv`; browsers other than Chrome.
- The SSE-driven toast in a screenshot (the logic is covered by reading and the alert tests).
- Fidelity of the screenshot-built screens against design context (Figma limit).

### Left open

- Gate 5 (owner): desktop browser check and live sensor → screen < 5 s.
- `PROTOCOL.md` v0.1.1 proposal above; D3, D4, D5, D7, D8; `User_Requirements.md` §4 phone line vs D12.
- Phase 8.2 risks: cookie without `Secure` (http on localhost), sessions in RAM, `config.py` exits without AIO keys even in mock mode.

### 5.7 — Module 1–2 inside the web (2026-10-26, effort `high`)

Owner asked to integrate the running Module 1–2 into the web. Answers: one program (`WEB_DATA=gateway`), `PROTOCOL.md` v0.1.1 approved (web writes `nguong-*`, matches UC04), sensor history from Adafruit in the log (UC06). Plan approved in plan mode the same day.

Changed:
- `gateway.py`: the loop is now `class Gateway` (`start`, `step`, `run(stop)`, `set_threshold`, `close`) with an optional listener. Same prints, publishes and LED commands, in the same order. `main()` runs it as before.
- `module2.py`: `ThresholdPublisher` (`changes`, `too_soon` ≥ 2 s per feed, `publish`, skips feeds the account doesn't have).
- `config.py`: `list_feeds()` (split out of `ensure_feeds`, which is otherwise unchanged), `fetch_history()`, `_epoch()`.
- `web_live.py`: threshold writes, Adafruit sensor history (last 50 points per feed, inserted at the front of the log in time order), subclass hooks (`MODE`, `STALE_SECONDS`, `_seed`, `_connect`, `_apply_thresholds`).
- New `web_gateway.py`: `GatewayHome(LiveHome)` runs the gateway thread and shares its MQTT connection; online = MQTT up and a reading within 10 s; label = `COM_PORT`.
- `web_server.py`: `WEB_DATA=gateway`. The HTTP port is bound before the provider starts, so a busy port never touches the COM port. The provider order is serial/MQTT first, history last, so a missing board fails before any REST call.
- `dashboard.js`: shows the save note when a threshold feed is missing.
- `PROTOCOL.md` v0.1.1, ROADMAP 5.7 (ticked) and 5.6 note, README §6 (three modes; gateway is the demo command), HUONG_DAN checklist, `.env.example`, `code/CLAUDE.md`.

Verified in this session:
- `py_compile` passes; 58 tests pass. New `tests/test_gateway.py` uses a fake serial and a fake MQTT client:
  - the gateway loop publishes and sends `LED:RED`; a web threshold switches the next comparison back to green; `RGB:` and bad lines are ignored;
  - `ThresholdPublisher` sends only changes, waits 2 s and skips missing feeds;
  - `GatewayHome` events, 10 s offline, save publishes and applies;
  - `LiveHome` 429/409 cases and history order.
- Smoke run of `WEB_DATA=gateway` through the real `web_server.py`, with a pseudo-terminal as the board and stubbed network in a scratchpad copy:
  - board lines reached the browser as `sensors` events within the same second;
  - publishes matched `gateway.py`;
  - the board received `LED:GREEN` → `LED:RED` (35 °C) → `LED:GREEN` after saving 40 °C from the web, which published `nguong-nhiet` once;
  - a device command returns 503 as intended.
- No board, no fake network: `WEB_DATA=gateway` stops at "Khong mo duoc COM99" before any Adafruit call. Mock mode smoke unchanged.

Not verified (owner, hardware):
- The real board on Windows COM. The CH340 reset in `open_serial` (DTR/RTS) can't run on a pseudo-terminal and was stubbed in the smoke copy.
- The real Adafruit account: history read, threshold publish, `ensure_feeds`.
- Sensor → screen under 5 s with the board (Gate 5).

Left open: Gate 1 and Gate 5; D5 for a stored device/alert log; the `User_Requirements.md` §4 phone line vs D12.
