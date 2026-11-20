# Checklist chạy phần cứng — Gate 1 và Gate 3

Chủ dự án chạy file này trên board thật. Agent không chạy được phần nào ở đây (cần board, cổng COM, `.env`).
Ghi kết quả từng dòng (đạt / không đạt + ghi chú) rồi gửi lại để agent ghi vào Outcome và tick `docs/ROADMAP.md`.

- **Gate 1** (Module 1–2): cảm biến → Adafruit → cảnh báo → đèn. Chi tiết từng bước ở `HUONG_DAN.md`.
- **Gate 3** (Module 3): bấm trên dashboard/web → thiết bị phản ứng **< 3 giây**; web mở được cửa khi không có nhận diện mặt.

Hợp đồng: `docs/PROTOCOL.md` v0.2.1. Ngày chạy: ____ · Người chạy: ____ · Cổng COM: ____

---

## 0. Chuẩn bị (một lần)

- [ ] `git pull`, đứng ở nhánh `feat/3-device-control`.
- [ ] Test xanh trên laptop: `.\.venv\Scripts\python.exe -m unittest discover -s tests -t .` → in `OK` (116 test).
- [ ] `.env` có `FEED_DEN=den`, `FEED_QUAT=quat`, `FEED_CUA=cua` (xem `.env.example`).
- [ ] Adafruit → Feeds: có đủ `nhiet-do`, `do-am`, `anh-sang`, `canh-bao`, `nguong-nhiet`, `nguong-am`, `nguong-sang`, `den`, `quat`, `cua` = **10/10**. Feed cũ `temperature`, `humidity`, `light` đã xóa.
- [ ] Cắm dây: DHT20 → I2C, cảm biến ánh sáng → **P0**, 4 LED RGB → **P14**, quạt (PWM) → **P1**, servo cửa → **P4**. Không cắm gì khác vào P0/P14.
- [ ] Nạp `yolobit.py` bản mới bằng OhStem (chế độ Python), bấm **Chạy**, thấy dòng `T:..,H:..,L:..` mỗi ~2 s, bấm **Lưu project vào thiết bị**, rồi **ngắt OhStem**.

## 1. Gate 1 — Module 1–2 (theo `HUONG_DAN.md` mục 4)

Chạy `.\.venv\Scripts\python.exe gateway.py`.

| # | Kiểm tra | Đạt? | Ghi chú |
| --- | --- | --- | --- |
| 1.1 | Cửa sổ in `Da ket noi Adafruit`, `Dang doc COMx`, rồi các dòng `Nhan:` / `Gui:` | | |
| 1.2 | `nhiet-do`, `do-am`, `anh-sang` trên Adafruit có số mới, Recorded vài giây trước | | |
| 1.3 | Bình thường: `canh-bao` = `Bình thường`, ma trận 1 điểm giữa, 4 LED **tắt** (đèn thủ công mặc định OFF, D3) | | |
| 1.4 | Hơ tay vào DHT20 vượt `nguong-nhiet` → `canh-bao` có `Nhiệt độ cao`, ma trận sáng 25 điểm, 4 LED nhấp nháy đỏ | | |
| 1.5 | Bỏ tay → về `Bình thường`, ma trận 1 điểm, LED về màu thủ công | | |
| 1.6 | Che cảm biến ánh sáng (< `nguong-sang`) → có `Ánh sáng thấp` | | |
| 1.7 | Đổi `nguong-nhiet` trên Adafruit (Add Data) → lần so sánh sau dùng số mới, không cần chạy lại | | |
| 1.8 | Thời gian cảm biến → Adafruit/màn hình < 5 s | | |
| 1.9 | Chạy 5 phút: Adafruit Monitor không báo throttle (≤ 30 điểm/phút) | | |

Dừng bằng `Ctrl+C`. Lưu ý: ở 1.3 nếu LED sáng **xanh lá** thì board đang chạy `yolobit.py` cũ — nạp lại.

## 2. Gate 3 — Module 3, từ dashboard Adafruit

Chạy `gateway.py` như trên. Khi khởi động, gateway gửi `den=OFF`, `quat=0`, `cua=CLOSE` (3 điểm). Dùng các block Module 3 trong `docs/ADAFRUIT_DASHBOARD.md` (hàng 4). Các màu preset khác `#ffffff` thì gửi bằng **Add Data** trực tiếp vào feed `den`.

Đo thời gian từ lúc bấm đến lúc thiết bị phản ứng (đồng hồ bấm giờ điện thoại là đủ).

| # | Thao tác | Mong đợi | Thời gian | Đạt? |
| --- | --- | --- | --- | --- |
| 3.1 | `den` = `#ffffff` | 4 LED sáng trắng; serial board in `ACK:LIGHT:ffffff` | | |
| 3.2 | `den` = `#b8860b`, `#9333ea`, `#2563eb` lần lượt | Đúng màu từng preset | | |
| 3.3 | `den` = `OFF` | 4 LED tắt | | |
| 3.4 | `quat` = `100` | Quạt quay hết tốc | | |
| 3.5 | `quat` = `50`, rồi `20` | Quay chậm dần; ghi lại số nhỏ nhất mà cánh còn quay: ____ | | |
| 3.6 | `quat` = `0` | Quạt dừng | | |
| 3.7 | `cua` = `OPEN` | Servo quay sang góc mở | | |
| 3.8 | Chờ, không làm gì | Sau ~10 s cửa tự đóng; feed `cua` tự về `CLOSE` | | |
| 3.9 | `cua` = `CLOSE` khi cửa đang đóng | Không có gì xảy ra (chống lặp), không gửi thêm lệnh | | |
| 3.10 | Đang cảnh báo (làm như 1.4) + `den` = `#2563eb` | LED vẫn nhấp nháy đỏ; hết cảnh báo thì về xanh dương (D3). Ma trận luôn theo cảnh báo | | |
| 3.11 | Bật quạt rồi mở cửa ngay (< 0,5 s) | Hai motor không khởi động cùng lúc; cửa chạy trễ ~0,5 s, vẫn có ACK | | |

## 3. Gate 3 — từ web (`WEB_DATA=gateway`)

Tắt `gateway.py` trước (chỉ một chương trình được giữ cổng COM). Đặt `WEB_DATA=gateway` trong `.env`, chạy `web_server.py`, mở `http://127.0.0.1:8000` bằng trình duyệt trên laptop, đăng nhập.

| # | Thao tác | Mong đợi | Đạt? |
| --- | --- | --- | --- |
| 4.1 | Bật/tắt đèn, đổi 4 màu | LED đổi < 3 s; thẻ thiết bị hiện trạng thái đã xác nhận; feed `den` khớp | |
| 4.2 | Kéo thanh tốc độ quạt, thả tay | Chỉ gửi một lệnh khi thả; quạt đổi tốc độ < 3 s; feed `quat` khớp | |
| 4.3 | Bấm mở cửa (không dùng nhận diện mặt) | Cửa mở < 3 s, tự đóng sau 10 s, thẻ cửa về "đóng" | |
| 4.4 | Bấm cùng một thiết bị hai lần trong < 2 s | Lần hai bị từ chối (thông báo, HTTP 429), không treo | |
| 4.5 | Đổi `den` trên dashboard Adafruit khi web đang mở | Web cập nhật theo | |
| 4.6 | Rút dây servo (hoặc quạt) rồi bấm lệnh | Sau 3 s web báo "Thiết bị không phản hồi sau 3 giây"; cửa sổ in `Board khong tra loi lenh ...`; feed quay về trạng thái thật | |
| 4.7 | Sensor trên web cập nhật < 5 s (Gate 5, ghi kèm) | | |

## 4. Hiệu chỉnh trên kit (ghi số thật lại)

Các hằng số ở đầu phần Module 3 trong `yolobit.py`. Sửa trên OhStem, chạy lại, rồi báo số để agent cập nhật file trong repo.

| Hằng số | Hiện tại | Kiểm tra | Số chốt |
| --- | --- | --- | --- |
| `ANGLE_CLOSE` | 0 | Cửa khép kín, servo không rè | |
| `ANGLE_OPEN` | 90 | Cửa mở đủ, không vấp khung | |
| `PWM_MAX` | 4095 | `quat=100` là tốc độ tối đa và `quat=25` chậm rõ. Nếu 25 % đã quay hết tốc thì thư viện dùng thang 0–1023 → đổi `PWM_MAX = 1023` | |
| `SERVO_RELEASE_MS` | 1500 | Servo kịp tới góc trước khi nhả xung | |

## 5. Kết quả

- Gate 1: ☐ đạt ☐ chưa — lỗi: ____
- Gate 3: ☐ đạt ☐ chưa — lỗi: ____
- Thời gian phản ứng chậm nhất đo được: ____ s

Gửi bảng này (hoặc ảnh chụp) cho agent ở phiên sau.
