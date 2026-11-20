# Phase 2.2: hợp đồng Module 3 (PROTOCOL v0.2.0) và đường tới Module 4

- Approved: 2026-11-20 (owner, plan mode)
- Effort: xhigh (task 2.2); các task sau theo bảng bên dưới
- Branch: `feat/5-web-ui` (chưa tạo nhánh mới, xem Notes)

## Context

Module 1–2 và web đã chạy (92 test xanh). Chưa có Module 3 (đèn, quạt, cửa) và Module 4 (nhật ký). Tài khoản Adafruit đã đủ 10/10 feed, gồm `den`, `quat`, `cua` (giá trị cũ `0`, dữ liệu thử), nên không thêm feed. D3, D4, D11 đã chốt; D5 còn mở.

## Hợp đồng đề xuất (chờ Gate 2)

Bản đầy đủ nằm ở `docs/PROTOCOL.md`, mục "Proposed v0.2.0". Tóm tắt:

| Feed | Giá trị đã xác nhận |
| --- | --- |
| `den` | `OFF` hoặc `#rrggbb` (4 preset D11); `0` cũ = `OFF` |
| `quat` | số nguyên 0–100, `0` = tắt |
| `cua` | `OPEN` hoặc `CLOSE`; `0` cũ = `CLOSE` |

Serial laptop → board: `LIGHT:OFF`, `LIGHT:RRGGBB`, `FAN:<0-100>`, `DOOR:OPEN`, `DOOR:CLOSE`. Board → laptop: `ACK:LIGHT:<OFF|RRGGBB>`, `ACK:FAN:<n>`, `ACK:DOOR:<OPEN|CLOSE>`; cửa tự khóa sau 10 s thì board gửi `ACK:DOOR:CLOSE` không cần lệnh.

Luật gateway: `confirmed` cho từng thiết bị; lệnh bằng `confirmed` thì bỏ qua (chặn echo); chờ ack tối đa 3 s; có ack thì publish lên feed nếu feed khác; hết hạn thì publish lại `confirmed`. Web đi thẳng vào hàng đợi gateway (1 điểm mỗi lần bấm). Chống spam: cùng thiết bị cách nhau ≥ 2 s (429).

Ngân sách: feed 10/10 không đổi. Bấm bình thường dưới 6 lần/phút ≈ 12 điểm + cảm biến ≈ 12 = ~24 điểm/phút, dưới 30.

Hệ quả D3: bình thường 4 LED theo màu thủ công (mặc định tắt), không còn xanh lá; cảnh báo nháy đỏ; hết cảnh báo về màu thủ công. Ma trận 5x5 giữ nguyên.

## Các task sau

| Task | Effort | File chính | Nội dung |
| --- | --- | --- | --- |
| 3.1 | low | `config.py`, `.env.example` | `FEED_DEN/QUAT/CUA`, `CONTROL_FEEDS`, nối vào `ALL_FEEDS` |
| 3.2 | high | `gateway.py`, `module1.py`, `web_live.py`, `web_gateway.py` | Hàm chuẩn hóa + `DeviceControl`; subscribe feed điều khiển; `send_device`; đọc dòng `ACK:`; `GatewayHome.command` |
| 3.3 | high | `yolobit.py` | Quạt P1, servo P2, ưu tiên LED, tự khóa 10 s không `sleep`, quạt và servo cách nhau ≥ 0,5 s |
| 3.4 | medium | `tests/` | Chuẩn hóa, định tuyến, chống echo, hết hạn ack, 429 |
| Gate 3 | | | Owner trên board: bấm → thiết bị phản ứng < 3 s; web mở cửa khi không có mặt |
| 4.1 | xhigh | `ROADMAP.md` | Owner chốt D5 (đề xuất SQLite trên laptop) |
| 4.2 | medium | `logstore.py`, `web_live.py`, `.gitignore` | Bảng `events`, giờ UTC, nạp lại khi mở web |
| Gate 4 | | | Owner thấy từng loại sự kiện trong nhật ký |

## Verification (task 2.2)

- Chỉ tài liệu. Đối chiếu `PROTOCOL.md` với `gateway.py`, `module1.py`, `yolobit.py` hiện tại (phần v0.1.1 không đổi).
- Chưa kiểm tra được: mọi thứ cần board, cổng COM, `.env`, Adafruit thật.

## Open questions for the owner

1. Quạt là relay bật/tắt hay PWM? Relay thì tốc độ 0–100 chỉ có nghĩa bật/tắt (board: `> 0` là bật).
2. Góc servo mở/đóng đo trên mạch thật ở 3.3.
3. D5: duyệt SQLite trên laptop?
4. Duyệt hệ quả D3: đèn mặc định tắt khi bình thường.

## Outcome

2.2 soạn xong 2026-11-20 (xem Notes). Chờ owner duyệt để đóng Gate 2.

## Notes

- Nhánh `feat/5-web-ui` còn nhiều thay đổi chưa commit; agent chưa tạo nhánh mới và chưa commit.
- Khi code ở 3.2 cần tách `Gateway.step()` rõ ràng, giữ `python gateway.py` in và publish y như `HUONG_DAN.md`.

## Handoff prompt

"Owner approved PROTOCOL v0.2.0 (Gate 2): start ROADMAP 3.1 then 3.2 per docs/plans/phase-2-module3-contract.md."
