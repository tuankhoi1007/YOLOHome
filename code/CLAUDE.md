# code/CLAUDE.md

How gateway and board code is written. Copy the patterns already here; add a rule when a new one lands.

## Layout

- `board/yolobit.py` is MicroPython, flashed by pasting into OhStem. Never run it on the laptop. `board/board_main_backup.py` is the old prototype; do not edit it.
- `yolohome/` is the laptop package. Run from `code/`: `python -m yolohome` (web), `python -m yolohome.gateway`, `python -m yolohome.module1`, `python -m yolohome.module2`.
- `web/` is the static site (HTML, CSS, JS). The server reads it; the browser never imports Python.
- `.env` stays in `code/`. `yolohome.config` loads that file. Do not move it next to the package.

## Two runtimes

- `board/yolobit.py` only uses what the board has: no f-strings with `=`, no `dataclasses`, no `typing`, no `pathlib`. Keep the main loop non-blocking (`poll_led`, `tick_blink` pattern) so serial input is never missed.
- Everything else is CPython 3 on the laptop. Dependencies are only `code/requirements.txt`; adding one needs a reason in the plan. Imports inside the package are `from yolohome...`, not bare `import config`.

## Patterns to follow

- Settings come from `yolohome.config` (`env`, `env_float`), which reads `code/.env`. Never read `os.environ` elsewhere, never hard-code a key, username or COM port.
- Feed keys are `config.FEED_*` constants. A new feed gets a constant, an `.env.example` line and a row in `docs/PROTOCOL.md` in the same change.
- Parsing and decisions are plain functions (`parse_line`, `normalize_light`, `evaluate`) that don't touch serial or MQTT, so they can be tested. Keep new logic the same way.
- Publishing goes through a publisher class (`SensorPublisher`, `AlertPublisher`) that owns rate limiting. Don't call `client.publish` from new places.
- MQTT callbacks only put work on a `queue.Queue`; the main loop does the work (see `yolohome/gateway.py`).
- Module 3 devices: `module1.DeviceControl` holds the `confirmed` state, the 3 s ack wait and the echo-loop rule (see `docs/PROTOCOL.md` v0.2.0). Serial writes and feed publishes are injected as functions so it is tested without a port. Commands from other threads (web) go in through `Gateway.command`; the gateway reads `ACK:` lines in `Gateway.step()` and `wait_for_sample()` (an ACK is never repeated, so it must not be flushed with old sensor lines).
- `yolohome/gateway.py` composes modules; `module1.py` / `module2.py` stay runnable on their own (`python -m yolohome.module1`).

## Web (Module 5)

- `yolohome/web/server.py` serves `code/web/` and `/api/*` on `127.0.0.1` only (D12: laptop browser, no phones). Data comes from a provider with `snapshot`, `set_thresholds`, `command`, `simulate`, `log`, `tick`: `web.mock.MockHome` (`WEB_DATA=mock`) or `web.live.LiveHome` (`WEB_DATA=live`). A new data source is a new provider; the frontend does not change.
- `snapshot()["features"]` says which parts have data. The frontend shows a "chưa có" card for a missing part instead of guessing. `LiveHome` refuses writes that `docs/PROTOCOL.md` does not allow yet (devices, threshold writes) with `CommandError`.
- `LiveHome` follows the gateway pattern: MQTT callbacks only put messages on `self.incoming`; `tick()` does the work. It reuses `module2.take_cloud_value` and `evaluate`.
- `WEB_DATA=gateway`: `web.gateway.GatewayHome(LiveHome)` runs `yolohome.gateway.Gateway` in a thread. The gateway reports through listener methods (`on_mqtt`, `on_reading`, `on_alert`, `on_thresholds`) that only put feed-shaped items on `self.incoming`, so `LiveHome._take` does all the work. Other threads change the gateway only through `Gateway.set_threshold` (its `incoming` queue), never by touching `limits` directly.
- Change the gateway loop in `Gateway.step()` only; `python -m yolohome.gateway`, `GatewayHome` and the tests all use it. Running it must keep printing and publishing exactly as `code/HUONG_DAN.md` step 4 says.
- Threshold writes go through `module2.ThresholdPublisher` (`changes` → `too_soon` → `publish`); it never creates a missing feed.
- The provider reports every change through `emit(kind, data)`; `EventHub` sends it to browsers over SSE. Validation is plain functions (`parse_command`, `parse_thresholds`, `filter_log`) that raise `CommandError(status, message)`.
- The browser never gets `AIO_KEY`. Every read and write goes through `/api` with the session cookie (D6, D10).
- Frontend is plain HTML/CSS/JS, ES modules, no build step, no npm, no framework. Every network call goes through `web/js/api.js`.
- No inline `<script>`, `<style>` or `style="..."`: the Content-Security-Policy blocks them. Build DOM with `h()` from `web/js/dom.js` (text via `textContent`, styles as an object set through `node.style`). Colours, spacing and radius only through the variables in `web/css/tokens.css`.
- Pages fetch `api.state()` at start and again on every SSE `open`, so a reconnect never leaves stale data.
- Figma frames are a visual reference. Hardware text follows `README.md` and `docs/PROTOCOL.md` (RGB LED on P14, light sensor on P0), not the Figma copy.

## Door (Module 3)

- The board only sees `LIGHT:`, `FAN:` and `DOOR:OPEN` / `DOOR:CLOSE`, then answers `ACK:`. Fan is P1 and the servo is P4. Angles stay in `yolobit.py`. The board closes the door itself after 10 s and sends `ACK:DOOR:CLOSE`.
- The manual door button on the web uses `Gateway.command("cua", ...)`. It must stay usable when face recognition is missing or fails.
- The dashboard face card is still a placeholder. Wiring it (scan button, result) is Module 5 work; see "Face (Phase 6)".

## Face (Phase 6)

- Code is `yolohome/face/`: `engine.py` (models, `FaceEngine`, `Gallery`, threshold), `enroll.py`, `unlock.py` (`Decider`, `scan`, `FaceUnlock`), `evaluate.py`. Settings are `config.FACE_*`; data in `code/data/faces/`, models in `code/models/` (both git-ignored). Plan: `docs/plans/phase-6-face-recognition.md`.
- `opencv-python` and `numpy` are imported inside `yolohome.face` only, and a missing library or model only turns face off (`Gateway.face is None`). Never import them from `gateway.py`, `module*.py` or `web/` at module level.
- The recognizer never touches serial. `FaceUnlock` runs the camera in its own thread and puts `ScanResult` on a queue; `Gateway.drain_face()` (called in `step()`) opens the door with `self.devices.request("cua", "OPEN", "Khuôn mặt")` and reports `on_face(result.as_dict())`. The board closes the door after 10 s, so the face code has no auto-close.
- Other threads start a scan with `Gateway.scan_face(source)` (`off` / `busy` / `started`). `ScanResult.detail` is UI text with accents; `note` is the accent-free text for `print`.
- Tests: `tests/test_face.py` uses fake vectors and a `FakeFace`; no camera, no model download. Tests that need numpy skip when it is missing.

## Style

- Comments, docstrings and `print` text: Vietnamese without accents (`Khong mo duoc COM`), in Python, JS, CSS and HTML alike. Text sent to Adafruit feeds or shown in the UI (including API error messages): Vietnamese with accents (`Nhiệt độ cao`).
- Plain functions and small classes, no type-level tricks or dense one-liners. A 3rd-year student should follow it without help.
- Comment the why on thresholds, rate limits and timing.

## Checks

- From `code/`: `python -m compileall yolohome` and `python -m unittest discover -s tests -t .`. Tests set fake `AIO_USERNAME`/`AIO_KEY` (and every setting they depend on) before importing `yolohome.config`, never use the real `.env`, and never open serial or the Internet. Web server tests bind `127.0.0.1` on a random port only.
- Agent smoke runs of `python -m yolohome` use a copy of `code/` in the scratchpad with fake env vars, so the real `.env` is never loaded.
- Web screenshots: headless Chrome on the Windows side (`/mnt/c/Program Files/Google/Chrome/Application/chrome.exe --headless=new --screenshot`), a fresh `--user-data-dir` per run. SSE never finishes, so `--virtual-time-budget` hangs and `--timeout` captures before data arrives: screenshot a scratchpad copy whose `listen()` is stubbed and whose login check is off. Never patch the repo for this.
