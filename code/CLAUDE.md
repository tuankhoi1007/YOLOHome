# code/CLAUDE.md

How gateway and board code is written. Copy the patterns already here; add a rule when a new one lands.

## Two runtimes

- `yolobit.py` is MicroPython on the board. Only use what the board has: no f-strings with `=`, no `dataclasses`, no `typing`, no `pathlib`. Keep the main loop non-blocking (`poll_led`, `tick_blink` pattern) so serial input is never missed.
- Everything else is CPython 3 on the laptop. Dependencies are only `code/requirements.txt`; adding one needs a reason in the plan.

## Patterns to follow

- Settings come from `config.py` (`env`, `env_float`), which reads `.env`. Never read `os.environ` elsewhere, never hard-code a key, username or COM port.
- Feed keys are `config.FEED_*` constants. A new feed gets a constant, an `.env.example` line and a row in `docs/PROTOCOL.md` in the same change.
- Parsing and decisions are plain functions (`parse_line`, `normalize_light`, `evaluate`) that don't touch serial or MQTT, so they can be tested. Keep new logic the same way.
- Publishing goes through a publisher class (`SensorPublisher`, `AlertPublisher`) that owns rate limiting. Don't call `client.publish` from new places.
- MQTT callbacks only put work on a `queue.Queue`; the main loop does the work (see `gateway.py`).
- `gateway.py` composes modules; `module1.py` / `module2.py` stay runnable on their own.

## Web (Module 5)

- `web_server.py` serves `web/` and `/api/*` on `127.0.0.1` only (D12: laptop browser, no phones). Data comes from a provider with `snapshot`, `set_thresholds`, `command`, `simulate`, `log`, `tick`: `web_mock.MockHome` (`WEB_DATA=mock`) or `web_live.LiveHome` (`WEB_DATA=live`). A new data source is a new provider; the frontend does not change.
- `snapshot()["features"]` says which parts have data. The frontend shows a "chưa có" card for a missing part instead of guessing. `LiveHome` refuses writes that `docs/PROTOCOL.md` does not allow yet (devices, threshold writes) with `CommandError`.
- `LiveHome` follows the gateway pattern: MQTT callbacks only put messages on `self.incoming`; `tick()` does the work. It reuses `module2.take_cloud_value` and `evaluate`.
- `WEB_DATA=gateway`: `web_gateway.GatewayHome(LiveHome)` runs `gateway.Gateway` in a thread. The gateway reports through listener methods (`on_mqtt`, `on_reading`, `on_alert`, `on_thresholds`) that only put feed-shaped items on `self.incoming`, so `LiveHome._take` does all the work. Other threads change the gateway only through `Gateway.set_threshold` (its `incoming` queue), never by touching `limits` directly.
- Change the gateway loop in `gateway.Gateway.step()` only; `gateway.py`, `GatewayHome` and the tests all use it. Running `python gateway.py` must keep printing and publishing exactly as `code/HUONG_DAN.md` step 4 says.
- Threshold writes go through `module2.ThresholdPublisher` (`changes` → `too_soon` → `publish`); it never creates a missing feed.
- The provider reports every change through `emit(kind, data)`; `EventHub` sends it to browsers over SSE. Validation is plain functions (`parse_command`, `parse_thresholds`, `filter_log`) that raise `CommandError(status, message)`.
- The browser never gets `AIO_KEY`. Every read and write goes through `/api` with the session cookie (D6, D10).
- Frontend is plain HTML/CSS/JS, ES modules, no build step, no npm, no framework. Every network call goes through `web/js/api.js`.
- No inline `<script>`, `<style>` or `style="..."`: the Content-Security-Policy blocks them. Build DOM with `h()` from `web/js/dom.js` (text via `textContent`, styles as an object set through `node.style`). Colours, spacing and radius only through the variables in `web/css/tokens.css`.
- Pages fetch `api.state()` at start and again on every SSE `open`, so a reconnect never leaves stale data.
- Figma frames are a visual reference. Hardware text follows `README.md` and `docs/PROTOCOL.md` (RGB LED on P14, light sensor on P0), not the Figma copy.

## Style

- Comments, docstrings and `print` text: Vietnamese without accents (`Khong mo duoc COM`), in Python, JS, CSS and HTML alike. Text sent to Adafruit feeds or shown in the UI (including API error messages): Vietnamese with accents (`Nhiệt độ cao`).
- Plain functions and small classes, no type-level tricks or dense one-liners. A 3rd-year student should follow it without help.
- Comment the why on thresholds, rate limits and timing.

## Checks

- `python3 -m py_compile code/*.py` — also run automatically by the hook after each edit.
- `python3 -m unittest discover -s code/tests -t code`. Tests set fake `AIO_USERNAME`/`AIO_KEY` (and every setting they depend on) before importing `config`, never use the real `.env`, and never open serial or the Internet. Web server tests bind `127.0.0.1` on a random port only.
- Agent smoke runs of `web_server.py` use a copy of `code/` in the scratchpad with fake env vars, so the real `.env` is never loaded.
- Web screenshots: headless Chrome on the Windows side (`/mnt/c/Program Files/Google/Chrome/Application/chrome.exe --headless=new --screenshot`), a fresh `--user-data-dir` per run. SSE never finishes, so `--virtual-time-budget` hangs and `--timeout` captures before data arrives: screenshot a scratchpad copy whose `listen()` is stubbed and whose login check is off. Never patch the repo for this.
