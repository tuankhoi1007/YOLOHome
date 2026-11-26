# YOLOHome

YOLOHome là nhà thông minh trên board Yolo:Bit. Laptop làm gateway: đọc cảm biến, đồng bộ Adafruit IO, mở web điều khiển, mở cửa bằng nhận diện khuôn mặt và nghe lệnh giọng nói tiếng Việt chạy offline.

## Tính năng

- Xem nhiệt độ, độ ẩm và ánh sáng trên web và trên Adafruit IO.
- Nhận cảnh báo khi vượt ngưỡng, và sửa ngưỡng trên web.
- Bật đèn (chọn màu), chỉnh tốc độ quạt, mở hoặc đóng cửa.
- Quét khuôn mặt để mở cửa.
- Đăng ký khuôn mặt thành viên.
- Nói "bật đèn", "tắt đèn", "bật quạt" hoặc "tắt quạt". Lệnh chạy offline trên laptop.
- Xem nhật ký hoạt động.
- Thử giao diện khi không cắm board.

## Cài đặt

Cần Python 3, khuyên dùng 3.11 trở lên. Mọi lệnh bên dưới chạy trong thư mục `code` (nơi có `requirements.txt` và `.env.example`).

`requirements-voice.txt` phục vụ micro. Web cảm biến chạy với riêng `requirements.txt`.

Linux / macOS:

```bash
cd code
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pip install -r requirements-voice.txt
cp .env.example .env
```

Windows (PowerShell):

```powershell
cd code
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
copy .env.example .env
```

Khi virtualenv trong `code/.venv` đã được bật, hai lệnh cài là:

```bash
pip install -r requirements.txt
pip install -r requirements-voice.txt
```

### Biến cần điền trong `.env`

Mở `code/.env`. Dòng nào không có trong bảng thì giữ nguyên như `.env.example`.

| Biến | Điền |
| --- | --- |
| `AIO_USERNAME` | Username Adafruit IO. Thiếu dòng này thì chương trình thoát |
| `AIO_KEY` | Active Key trên [io.adafruit.com](https://io.adafruit.com) |
| `COM_PORT` | Cổng serial của board. Mẫu trong file là `COM11` |
| `WEB_PASSWORD` | Mật khẩu đăng nhập web. Để trống thì web thoát lúc khởi động |
| `WEB_DATA` | `mock` (giả lập), `gateway` (web chạy cùng board) hoặc `live` (web chỉ đọc Adafruit). Mặc định `mock` |
| `FACE_ENABLE` | `1` bật quét mặt, `0` tắt. Mặc định `1` |
| `VOICE_ENABLE` | `1` bật micro, `0` tắt. Mặc định `1` |

## Chạy

Đứng trong thư mục `code`. Dùng `./.venv/bin/python` (Linux / macOS) hoặc `.\.venv\Scripts\python.exe` (Windows) thay cho `python` ở các lệnh sau. Dừng bằng Ctrl+C.

Web (dashboard):

```bash
python -m yolohome
```

Mở `http://127.0.0.1:8000` trên chính laptop đó và đăng nhập bằng `WEB_PASSWORD`.

- `WEB_DATA=mock`: giao diện giả lập, không nối board và không nối Adafruit.
- `WEB_DATA=gateway`: một tiến trình gồm web và gateway, cần board đã nạp `code/board/yolobit.py`. Ngắt OhStem khỏi cổng serial trước. Lệnh này đã giữ cổng, nên không chạy thêm `python -m yolohome.gateway`.
- `WEB_DATA=live`: web đọc số trên Adafruit. Gateway chạy riêng bằng lệnh dưới.

Gateway, không mở web:

```bash
python -m yolohome.gateway
```

### Đăng ký khuôn mặt

Tên không dấu: chữ, số, `_` hoặc `-`, tối đa 32 ký tự. Đứng trong `code`:

```bash
python -m yolohome.face.enroll Minh
python -m yolohome.face.enroll --list
```

Khi `WEB_DATA=gateway` và `FACE_ENABLE=1`, nút **Đăng ký mới** trên web làm cùng việc và hỏi `WEB_PASSWORD`.

### Kiểm tra

Đứng trong `code`. Bộ test không mở cổng serial và không gọi mạng:

```bash
python -m unittest discover -s tests -t .
```

Kết quả in `OK`.

Chi tiết kỹ thuật: [docs/ky-thuat.md](docs/ky-thuat.md). Thư mục tài liệu: [docs](docs).
