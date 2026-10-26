# Protocol

Version **v0.1.0** — what is running today (Module 1–2). Code must match this file; a change here is approved before code depends on it. Bump the version on every approved change.

## USB serial (115200 baud, one message per line)

### Board → laptop

| Line | Meaning |
| --- | --- |
| `T:31.2,H:60,L:44` | Temperature °C, humidity %, light 0–100. Any part may be missing (`T:31.2,L:44`). |
| `{"temperature":31.2,"humidity":60,"light":44}` | Also accepted by the gateway. `yolobit.py` does not send it. |
| `RGB:RED` / `RGB:GREEN` | Acknowledges an LED command. Gateway prints it and ignores it as a reading. |

Board sends about every 2 s. Gateway samples every `READ_INTERVAL` (default 3 s).

### Laptop → board

| Line | Effect |
| --- | --- |
| `LED:RED` | Alert: 5x5 matrix fully lit, 4 RGB LEDs on P14 blink red. |
| `LED:GREEN` | Normal: one centre dot on the matrix, RGB LEDs green. |

## Adafruit IO feeds

Free tier: **max 10 feeds**, about **30 points/minute** total.

| Key | Written by | Read by | Value |
| --- | --- | --- | --- |
| `nhiet-do` | gateway | module2, dashboard | °C |
| `do-am` | gateway | module2, dashboard | % |
| `anh-sang` | gateway | module2, dashboard | 0–100 |
| `canh-bao` | gateway / module2 | dashboard | `Bình thường`, or alert texts joined by ` \| ` |
| `nguong-nhiet` | owner (dashboard) | gateway | Alert when temperature **>** value. Fallback `TEMP_MAX` = 32. Accepted 0–80. |
| `nguong-am` | owner | gateway | Alert when humidity **>** value. Fallback `HUMID_MAX` = 80. |
| `nguong-sang` | owner | gateway | Alert when light **<** value. Fallback `LIGHT_MIN` = 20. |

In use: 7 of 10. Reserved for Module 3: `den`, `quat`, `cua` (would make 10/10 — Module 4 and face logging cannot add a feed without freeing one). Old feeds `temperature`, `humidity`, `light` are unused and should be deleted.

### Publish pacing (gateway)

A sensor feed is sent only when it changed by at least 0.3 °C / 1 % / 2 units, and at most once every 2 s per feed. A heartbeat is sent every ~15 s even without change. `canh-bao` is sent only when its text changes.

Budget: steady readings ≈ 3 feeds × 4/min = **12 points/min**. Worst case, if all three keep changing past their band at every 3 s sample: 3 × 20 = **60 points/min**, over the limit. The change bands are what keep normal use under 30; any new feed must be counted against this.

## Changelog

- v0.1.0 — 2026-10-26 — Written from the running Module 1–2 code and `README.md`.
