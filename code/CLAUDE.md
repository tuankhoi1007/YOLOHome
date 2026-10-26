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

## Style

- Comments, docstrings and `print` text: Vietnamese without accents (`Khong mo duoc COM`). Text sent to Adafruit feeds or shown in the UI: Vietnamese with accents (`Nhiệt độ cao`).
- Plain functions and small classes, no type-level tricks or dense one-liners. A 3rd-year student should follow it without help.
- Comment the why on thresholds, rate limits and timing.

## Checks

- `python3 -m py_compile code/*.py` — also run automatically by the hook after each edit.
- `python3 -m unittest discover -s code/tests -t code` — once `code/tests/` exists (ROADMAP 1.1). Tests set fake `AIO_USERNAME`/`AIO_KEY` before importing `config`, never use the real `.env`, and never open serial or network.
