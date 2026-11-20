# Adafruit IO dashboard — block list

ROADMAP 5.1. The owner builds it on [io.adafruit.com](https://io.adafruit.com) → **Dashboards → New Dashboard** (name `YOLOHome`). Only feeds from `docs/PROTOCOL.md` v0.1.0 are used. Blocks read feeds; only the three threshold blocks write. Every value written by hand costs one data point (about 30/min free limit), so moving a slider does not flood the account.

## Layout (desktop, 3 columns)

| Row | Block | Feed | Settings | Why |
| --- | --- | --- | --- | --- |
| 1 | **Gauge** "Nhiệt độ (°C)" | `nhiet-do` | Min 0, Max 50, label `°C`, high warning = current `nguong-nhiet` (default 32) | Module 1 value at a glance |
| 1 | **Gauge** "Độ ẩm (%)" | `do-am` | Min 0, Max 100, label `%`, high warning 80 | Module 1 |
| 1 | **Gauge** "Ánh sáng (0–100)" | `anh-sang` | Min 0, Max 100, low warning 20 | Module 1, scale 0–100 as in the spec |
| 2 | **Text** "Cảnh báo" | `canh-bao` | Font size large | Module 2: shows `Bình thường` or the alert text |
| 2 | **Line Chart** "Lịch sử môi trường" | `nhiet-do`, `do-am`, `anh-sang` | History 24 hours, Y axis 0–100 | Sensor history (Adafruit keeps it per feed) |
| 3 | **Slider** "Ngưỡng nhiệt" | `nguong-nhiet` | Min 0, Max 80, step 0.5 | Gateway alerts when temperature **>** value (PROTOCOL range 0–80) |
| 3 | **Slider** "Ngưỡng độ ẩm" | `nguong-am` | Min 0, Max 100, step 1 | Alert when humidity **>** value |
| 3 | **Slider** "Ngưỡng ánh sáng" | `nguong-sang` | Min 0, Max 100, step 1 | Alert when light **<** value |

Total: 8 blocks, 7 feeds (7/10 used). No feed is added.

## After PROTOCOL v0.2.0 (Gate 2) — do not build yet

Module 3 will add toggle/slider blocks for `den`, `quat`, `cua` (10/10 feeds). Their values (colour, fan speed, door action, D11) are decided in ROADMAP 2.2. Add them only after `PROTOCOL.md` v0.2.0 is approved.

## Check

- Run `gateway.py` (owner, with board): the three gauges and the chart move; `canh-bao` shows `Bình thường`.
- Move the temperature slider below the room temperature: `canh-bao` switches to `Nhiệt độ cao: …` within a few seconds and the board LED turns red.
