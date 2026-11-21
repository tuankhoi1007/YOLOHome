# Protocol

Version **v0.2.1** — approved 2026-11-20 (v0.2.1: fan is PWM on P1, door servo on P4, stated by the owner the same day): Module 1–2 as running, plus the Module 3 contract (device control, section below). Module 3 code is written (ROADMAP Phase 3) but not yet run on the board (Gate 3). Code must match this file; a change here is approved before code depends on it. Bump the version on every approved change.

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
| `nguong-nhiet` | owner (Adafruit dashboard or web) | gateway, web | Alert when temperature **>** value. Fallback `TEMP_MAX` = 32. Accepted 0–80. |
| `nguong-am` | owner (Adafruit dashboard or web) | gateway, web | Alert when humidity **>** value. Fallback `HUMID_MAX` = 80. Accepted 0–100. |
| `nguong-sang` | owner (Adafruit dashboard or web) | gateway, web | Alert when light **<** value. Fallback `LIGHT_MIN` = 20. Accepted 0–100. |

In use: 7 of 10. Reserved for Module 3: `den`, `quat`, `cua` (would make 10/10 — Module 4 and face logging cannot add a feed without freeing one). Old feeds `temperature`, `humidity`, `light` are unused and should be deleted.

### Publish pacing (gateway)

A sensor feed is sent only when it changed by at least 0.3 °C / 1 % / 2 units, and at most once every 2 s per feed. A heartbeat is sent every ~15 s even without change. `canh-bao` is sent only when its text changes.

Budget: steady readings ≈ 3 feeds × 4/min = **12 points/min**. Worst case, if all three keep changing past their band at every 3 s sample: 3 × 20 = **60 points/min**, over the limit. The change bands are what keep normal use under 30; any new feed must be counted against this.

### Threshold writes from the web (v0.1.1)

The web (`/api/thresholds`, `module2.ThresholdPublisher`) publishes only the `nguong-*` feeds whose value changed: at most **3 points per save**, by hand, and at most one write per feed every 2 s. It never creates a missing feed. The gateway reads the new value from its subscription as before; with `WEB_DATA=gateway` the value is also handed to the running gateway directly so the next comparison uses it.

`WEB_DATA=gateway` runs the gateway loop inside `python -m yolohome` (`yolohome/web/server.py`): same publishes and pacing as `python -m yolohome.gateway`, one MQTT connection. `WEB_DATA=live` adds a second, subscribe-only connection next to that gateway. Sensor history for the web log is read over REST (`/feeds/<key>/data`) and costs no data points.

## v0.2.0 — Module 3 device control (approved 2026-11-20, Gate 2)

From ROADMAP 2.2. Plan: `plans/phase-2-module3-contract.md`. Owner approved this contract on 2026-11-20. Code for it was written in ROADMAP Phase 3 (3.1–3.4); the hardware check is Gate 3 (`code/KIEM_TRA_GATE_1_3.md`).

### Feeds (value = confirmed device state)

| Key | Value | Notes |
| --- | --- | --- |
| `den` | `OFF`, or `#rrggbb` of one of 4 presets: `#ffffff`, `#b8860b`, `#9333ea`, `#2563eb` | old test value `0` is read as `OFF` |
| `quat` | integer 0–100, `0` = off | PWM fan: the value is the speed in percent; `0` = off. Very low values may not spin the blades (static friction) |
| `cua` | `OPEN` or `CLOSE` | old test value `0` is read as `CLOSE` |

Feed count stays **10 of 10** (the three feeds already exist). Case and spacing are normalised before comparing.

### USB serial additions

| Direction | Line | Effect |
| --- | --- | --- |
| laptop → board | `LIGHT:OFF` / `LIGHT:RRGGBB` | Manual light on the 4 RGB LEDs (P14). |
| laptop → board | `FAN:<0-100>` | Fan speed by PWM on P1 (`0` = off, 100 = full). |
| laptop → board | `DOOR:OPEN` / `DOOR:CLOSE` | Door servo on P4 (the servo row of the expansion board). Board holds the angle, releases the pulse after about 1.5 s. |
| board → laptop | `ACK:LIGHT:<OFF\|RRGGBB>`, `ACK:FAN:<n>`, `ACK:DOOR:<OPEN\|CLOSE>` | Command done. After `DOOR:OPEN` the board closes the door by itself after 10 s and sends `ACK:DOOR:CLOSE` without a command. |

`LED:RED` / `LED:GREEN` and `RGB:*` stay as in v0.1.1. LED priority (D3): while an alert is active the 4 LEDs blink red; when it clears they show the manual light (default off). The 5x5 matrix always shows the alert state. The board starts with light `OFF`, fan `0`, door `CLOSE`. The fan and the servo never start within 0.5 s of each other.

### Gateway rules

1. Commands come from a control feed (Adafruit dashboard) or from the web. The web goes straight into the gateway queue, not through the feed.
2. The gateway keeps a `confirmed` state per device. A command equal to `confirmed` is ignored; this stops the loop feed → serial → ack → feed.
3. Otherwise it sends the serial line and waits up to 3 s for the ack. Ack: update `confirmed` and publish it to the feed if the feed differs.
4. No ack in 3 s: `confirmed` does not change, the failure is logged, and the gateway publishes `confirmed` back so the feed matches the real device (the feed is the source of truth).
5. At start the gateway publishes `OFF`, `0`, `CLOSE` once (3 points).
6. The door can always be opened from the web. Web commands to the same device closer than 2 s are refused (HTTP 429).

### Budget

Normal use under 6 clicks per minute: about 12 points for control, about 12 for sensors, about **24 points/min**, under 30. Worst case, spamming three devices every 2 s, goes over; the 2 s limit and sending the fan slider only on release keep normal use inside it.

## Changelog

- v0.2.0 — 2026-11-20 — Approved by the owner (Gate 2): feeds `den`, `quat`, `cua`; serial `LIGHT:`, `FAN:`, `DOOR:` and `ACK:` lines; gateway confirmed-state rules; fan on P1, door servo on P2. Feed count 10 of 10.
- v0.2.1 — 2026-11-20 — Owner: the fan is PWM (not a relay) on P1; the door servo is on P4, not P2. Commands, feeds and ack lines are unchanged.
- v0.1.1 — 2026-10-26 — Approved by the owner: the web may write `nguong-nhiet`, `nguong-am`, `nguong-sang` (same keys, ranges, meaning). Accepted ranges written for `nguong-am` and `nguong-sang`.
- v0.1.0 — 2026-10-26 — Written from the running Module 1–2 code and `README.md`.
