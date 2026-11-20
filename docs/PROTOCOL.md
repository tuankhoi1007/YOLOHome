# Protocol

Version **v0.1.2** — Module 1–2 plus the door servo used by face recognition. Code must match this file. Bump the version on every approved change.

This version does **not** add an Adafruit feed and does **not** change publish timing. Still **7 of 10 feeds**. Points/min are unchanged from v0.1.0 (steady ≈ 12, worst case ≈ 60 if all three sensors keep moving). Face attempts and door state stay on the laptop. `den`, `quat` and `cua` stay reserved for Module 3.

## USB serial (115200 baud, one message per line)

### Board → laptop

| Line | Meaning |
| --- | --- |
| `T:31.2,H:60,L:44` | Temperature °C, humidity %, light 0–100. Any part may be missing (`T:31.2,L:44`). |
| `{"temperature":31.2,"humidity":60,"light":44}` | Also accepted by the gateway. `yolobit.py` does not send it. |
| `RGB:RED` / `RGB:GREEN` | Acknowledges an LED command. Gateway prints it and ignores it as a reading. |
| `DOOR:OPEN` | Servo moved to the open angle. Gateway treats the door as unlocked. |
| `DOOR:CLOSE` | Servo moved to the closed angle. Gateway treats the door as locked. |
| `DOOR:PIN:P4` | Board accepted the servo pin (the `P4` part is whatever pin was sent). |
| `DOOR:ERR` | Servo could not be attached or moved. Gateway clears the pending command. The door stays as it was. |

Board sends a sensor line about every 2 s. Gateway samples every `READ_INTERVAL` (default 3 s). Door lines are not sensor readings: they do not reset the sample timer, and the gateway must not wipe the serial buffer while it is waiting for the next sample (an ack would be lost).

Old firmware that only understands `LED:` ignores `DOOR:` lines. The command is then safe but the web button times out until `yolobit.py` is flashed again.

### Laptop → board

| Line | Effect |
| --- | --- |
| `LED:RED` | Alert: 5x5 matrix fully lit, 4 RGB LEDs on P14 blink red. |
| `LED:GREEN` | Normal: one centre dot on the matrix, RGB LEDs green. |
| `DOOR:PIN:P4` | Attach the servo on that pin, then move it to the closed angle. Sent once per gateway start, before the first open or close. `P0` and `P14` are rejected. Default pin is `SERVO_PIN` (`P4`) until D4 is closed. |
| `DOOR:OPEN` | Move the servo to the open angle and reply `DOOR:OPEN`. |
| `DOOR:CLOSE` | Move the servo to the closed angle and reply `DOOR:CLOSE`. |

Angles live only on the board: `DOOR_CLOSED_ANGLE = 0`, `DOOR_OPEN_ANGLE = 90` in `yolobit.py`. Swap those two constants and flash again if the horn turns the wrong way. The laptop never sends an angle.

The gateway, not the board, times the auto-close (`DOOR_OPEN_SECONDS`, default 10). When the timer fires it sends `DOOR:CLOSE`. A second `DOOR:OPEN` while the door is already unlocked only refreshes that timer; it does not send another line. The web **Khóa cửa** button sends the same `DOOR:OPEN` / `DOOR:CLOSE` pair and must keep working when recognition rejects a face.

`WEB_DATA=gateway` queues the button on the in-process gateway. `WEB_DATA=live` cannot open the COM port (a separate `gateway.py` owns it), so the web writes `code/data/runtime/door_cmd.json` and `gateway.py` applies each new `id` once. A command already in that file at startup is skipped, so a reboot does not open the door.

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

## Face recognition (laptop only, no feed)

Recognition runs on the laptop webcam. The board never sees an image. A decision is one attempt after `FACE_STABLE_FRAMES` (default 3) agreeing frames, not every frame. Each attempt is printed and appended to `code/data/runtime/face_log.jsonl` (gitignored) and to the web log in RAM:

| Field | Meaning |
| --- | --- |
| `at` | Unix time of the attempt |
| `name` | Nearest enrolled person, even when rejected |
| `ok` / `result` | `true` / `accepted` or `false` / `rejected` |
| `confidence` | 0–100 display score |
| `score` | Raw cosine (higher is better) or LBPH distance (lower is better) |
| `threshold` | Operating threshold from `models/face/chosen.json`, unless `FACE_THRESHOLD` overrides it |
| `metric` | `cosine` or `lbph` |
| `model` | `sface` or `lbph` |

`ok: true` asks the gateway to open the door. `ok: false` does not send `DOOR:OPEN`. Empty frames are not logged.

`FACE_ENABLE` defaults to `0`, so the sensor demo does not open a camera. The door button still works in gateway mode without a model.

The gateway writes `code/data/runtime/status.json` (last face attempt, runtime, door) whenever that state changes. `WEB_DATA=live` reads the file, because that process does not own the serial port. `WEB_DATA=gateway` does not poll it; the web thread gets the same events in process. None of these files is an Adafruit feed. `code/data/` is gitignored.

## Changelog

- v0.1.2 — 2026-11-20 — Door servo over USB for face recognition. No new feed, same points/min. Pin default `P4`, still open as D4. Face log is local, not a feed.
- v0.1.0 — 2026-10-26 — Written from the running Module 1–2 code and `README.md`.
