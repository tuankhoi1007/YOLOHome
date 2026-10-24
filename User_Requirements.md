# Đề xuất User Requirements — Nhà thông minh

Nhóm 1 — CO3107 Đồ án đa ngành hướng TTNT — HK261

Tài liệu này xin GVHD góp ý: đề xuất dưới đây với kit **Yolo:Bit** (không dùng YoloUno) có **khả thi** và **làm được** trong phạm vi môn hay không.

---

## 1. Giới thiệu

Nhóm đề xuất mô hình **một phòng nhà thông minh**. Người dùng xem nhiệt độ, độ ẩm, ánh sáng; được cảnh báo khi vượt ngưỡng; bật/tắt đèn, quạt và cửa từ giao diện; cửa mở bằng nhận diện khuôn mặt; đèn/quạt điều khiển thêm bằng giọng nói tiếng Việt (bộ lệnh cố định).

Khi nhận diện khuôn mặt hoặc giọng nói lỗi, người dùng vẫn điều khiển tay trên giao diện được.

AI **không chạy trên Yolo:Bit**. Board chỉ thu cảm biến và điều khiển thiết bị. Suy luận Face/giọng nói chạy trên **laptop (Gateway)**, dùng **webcam và mic có sẵn của laptop**.

---

## 2. Actors

- **Chủ nhà:** xem môi trường, điều khiển đèn–quạt–cửa, dùng Face để mở cửa, dùng giọng nói để bật/tắt đèn và quạt.
- **Bạn cùng phòng:** được đăng ký khuôn mặt; dùng hệ thống như chủ nhà.
- **Hệ thống:** đọc cảm biến, so ngưỡng, ghi nhật ký, chạy FaceAI và nhận lệnh giọng nói tại Gateway.

---

## 3. Yêu cầu chức năng

### Module 1 — Thu thập và hiển thị môi trường

- Đọc nhiệt độ, độ ẩm (DHT20) và ánh sáng
- Gửi lên Adafruit IO, hiện trên dashboard (và LCD nếu kịp)
- Ánh sáng thang **0–100** (0 = tối, 100 = sáng; không dùng lux)
- Input: DHT20, cảm biến ánh sáng

### Module 2 — Kiểm tra ngưỡng và cảnh báo

- So sánh dữ liệu module 1 với ngưỡng (chỉnh được)
- Khi vượt ngưỡng: LED RGB đổi màu, dashboard hiện cảnh báo
- Input: dữ liệu module 1 + ngưỡng
- Output: LED RGB, cảnh báo trên dashboard

### Module 3 — Điều khiển thiết bị

- Bật/tắt đèn LED RGB, quạt mini và cửa (servo) từ dashboard/web
- Cả ba thiết bị đều có trong kit
- Lệnh tay không phụ thuộc AI
- Output: LED RGB, quạt mini, servo

### Module 4 — Nhật ký

- Ghi lịch sử cảm biến
- Ghi lần bật/tắt đèn, quạt, cửa
- Ghi lần cảnh báo
- Ghi lần nhận diện khuôn mặt (đúng/sai)

### Module 5 — Giao diện

- Dashboard Adafruit để giám sát và điều khiển
- Về sau bổ sung web trên máy tính và điện thoại
- Không làm ứng dụng native

### Tính năng AI

- **Nhận diện khuôn mặt (AI chính):** webcam laptop; đúng thành viên thì servo mở cửa, sai thì cửa đóng; có huấn luyện và đánh giá trên tập test nội bộ
- **Giọng nói (phụ):** mic laptop, tiếng Việt, lệnh cố định (bật/tắt đèn, bật/tắt quạt); không dùng LLM

---

## 4. Yêu cầu phi chức năng

- Cảm biến lên dashboard dưới 5 giây.
- Bấm điều khiển đến thiết bị phản ứng dưới 3 giây.
- Demo ổn định khoảng 30 phút, không rớt kết nối Adafruit.
- Giao diện xem được trên điện thoại và máy tính.
- Độ chính xác Face: đo trên tập test nội bộ (ánh sáng phòng demo, khoảng 0,5–1 m) và ghi số thật, không cam kết trước một mốc cố định.

---

## 5. Thiết bị đề xuất

| Vai trò | Thiết bị | Trong kit? |
| --- | --- | --- |
| Input | DHT20 (nhiệt, ẩm) | Có |
| Input | Cảm biến ánh sáng | Có |
| Input AI | Webcam laptop | Không — dùng máy Gateway |
| Input AI | Mic laptop | Không — dùng máy Gateway |
| Output | Đèn 4 LED RGB | Có |
| Output | Quạt mini | Có |
| Output | Servo (cửa) | Có |
| Phụ | LCD 16x2 | Có, nếu kịp |
| Không dùng | Bơm, ẩm đất, siêu âm, remote | Có trong kit, chủ động bỏ |

Yolo:Bit nối laptop bằng USB. Laptop cần mạng Internet (Adafruit IO).

---

## 6. Ràng buộc

- Không TinyML trên chip Yolo:Bit (khác đồ án dùng YoloUno).
- Không camera/mic rời, không cửa hay đèn 220V thật, không bàn phím mật mã. Face lỗi thì mở cửa bằng nút trên giao diện.
- Không dùng LLM cho giọng nói.

---

## 7. Nội dung xin GVHD góp ý

1. Ba output cùng lúc (đèn + quạt + servo) với Yolo:Bit có ổn không, hay chỉ nên làm hai?
2. Face và giọng nói trên webcam/mic laptop, AI tại Gateway — có được tính đúng hướng TTNT của môn không?
3. Giọng nói chỉ khớp lệnh cố định, không LLM, có chấp nhận là tính năng phụ không?
4. Thang ánh sáng 0–100 (quy đổi từ cảm biến analog) có được không?
