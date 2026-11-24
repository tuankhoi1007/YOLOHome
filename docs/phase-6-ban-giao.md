# Bàn giao Phase 6 — nhận diện khuôn mặt

Dành cho người làm tiếp. Hướng dẫn chạy cho cả nhóm nằm ở `README.md`, mục 4.5. File này ghi những gì phase này đã chốt, luật không được phá, và việc còn mở.

Ngày ghi: 2026-11-24.

## Phase này đã làm gì

Nhận diện khuôn mặt chạy trên laptop, dùng webcam của laptop. Board không chạy AI.

- **YuNet** tìm mặt và 5 điểm mốc (hai mắt, mũi, hai khóe miệng). Từ đó biết nhìn thẳng, quay trái, quay phải, hay đứng xa.
- **SFace** biến mặt đã căn thành vector 128 số. So cosine với mẫu đã lưu. Điểm cao hơn là giống hơn, không phải phần trăm.
- Hai file mô hình ONNX tải lần đầu vào `code/models/` (khoảng 37 MB). Ảnh và vector nằm ở `code/data/faces/`. Cả hai thư mục đã gitignore, không đẩy lên GitHub. Không tốn feed Adafruit.

Đăng ký một người gồm năm bước: nhìn thẳng, quay trái, quay phải, lùi xa, đổi kính. Bước kính không bắt buộc. Người không đeo kính bấm **Bỏ qua bước**. Nếu làm bước kính, kho lưu hai mẫu (có kính và không kính) và lúc quét lấy điểm cao hơn. Mẫu đăng ký trước khi có bước này vẫn chỉ một mẫu: muốn cả hai kiểu thì đăng ký lại cùng tên. Đăng ký lại thay mẫu cũ của tên đó.

Mở cửa khi trong 7 khung gần nhất có ít nhất 5 khung khớp cùng một người, điểm không thấp hơn ngưỡng. Ngưỡng lấy theo thứ tự:

1. `FACE_THRESHOLD` trong `.env` nếu có số
2. `code/data/faces/threshold.json` nếu đã chạy `python -m yolohome.face.evaluate`
3. mặc định **0,70**

Sàn của mô hình gốc là 0,363. Cửa nhà không dùng số đó: 0,50 từng nhận nhầm bạn cùng lớp ở điểm khoảng 0,59. Hạ ngưỡng để “dễ hơn” sẽ mở cửa cho người lạ. Lệch có kính / không kính khoảng 0,15 được xử lý bằng hai mẫu, không bằng cách hạ ngưỡng.

Trên web, chỉ khi `WEB_DATA=gateway`:

- Thẻ khuôn mặt có đúng hai nút: **Quét mặt mở cửa** và **Đăng ký mới**.
- **Đăng ký mới** mở cửa sổ nhập tên và mật khẩu chủ nhà. Webcam chỉ mở sau khi mật khẩu đúng.
- Hình webcam nằm trong cửa sổ riêng, đủ cả khung, có danh sách bước. Nút **Bỏ qua bước** và **Hủy** nằm trong cửa sổ đó.
- Chữ trên thẻ và trong nhật ký chỉ nói việc người nhà cần biết (nhận ra hay không, cửa có mở không, đã lưu khuôn mặt chưa). Không hiện điểm, ngưỡng, hay tên mô hình.
- Sai mật khẩu hiện lỗi ngay trong cửa sổ đăng ký, không đá về trang đăng nhập. Năm lần sai trong một phút thì đăng nhập và đăng ký cùng bị khóa.
- Tên chỉ gồm chữ không dấu, số, `_` hoặc `-`, tối đa 32 ký tự.
- Không có board thì web và phần mặt vẫn chạy. Lệnh cửa báo mạch chưa kết nối. Nút khóa cửa trên web vẫn là đường mở cửa khi mặt không khớp.

Dòng lệnh vẫn dùng được, và vẫn mở cửa sổ OpenCV riêng (phím S bỏ qua bước, Q hủy):

```powershell
.\.venv\Scripts\python.exe -m yolohome.face.enroll Minh
.\.venv\Scripts\python.exe -m yolohome.face.unlock
.\.venv\Scripts\python.exe -m yolohome.face.evaluate
```

## Luật không được phá

- AI chỉ trên laptop. Không nhét model lên Yolo:Bit.
- Cửa phải mở được từ nút trên web kể cả khi mặt tắt, webcam lỗi, hoặc không nhận ra. Không được khóa đường đó.
- Không thêm feed Adafruit cho mặt hoặc nhật ký. Tài khoản chỉ có 10 feed. Không vượt khoảng 30 điểm mỗi phút.
- Không làm bơm, ẩm đất, siêu âm.
- Giọng nói là Phase 7: lệnh tiếng Việt cố định, không dùng LLM. Chưa làm.
- Module 4 không bắt database. Rubric chỉ cần ghi nhận hoạt động và giao diện rõ. Hiện nhật ký nằm trong RAM, lịch sử cảm biến lấy từ Adafruit. Đừng thêm SQLite hay PostgreSQL trừ khi nhóm quyết rõ.
- Không chạy `code/board/yolobit.py` trên laptop. File đó là MicroPython, nạp bằng OhStem. Không sửa `code/board/board_main_backup.py`.
- Không đọc, không in, không commit `code/.env`. Tên biến xem ở `code/.env.example`.
- Chữ người nhà đọc trên web không kèm điểm cosine, ngưỡng, tỉ lệ khung, hay tên YuNet/SFace. Số đó ở trong code và file đánh giá, không trên thẻ.
- Web là HTML/CSS/JS trong `code/web`, không có npm. Sửa giao diện thì sửa `code/web/js/ai.js`, `code/web/index.html`, `code/web/css/dashboard.css`.
- Thiếu OpenCV, thiếu model, hoặc `FACE_ENABLE=0` thì chỉ tắt thẻ mặt. Phần còn lại của web vẫn chạy.
- `FACE_CAMERA=0` là webcam đầu tiên. Chỉ đổi sang 1 khi máy mở nhầm camera.
- `FACE_LIVENESS` mặc định tắt. Bật `1` thì phải quay đầu đủ `FACE_LIVE_SPREAD` (mặc định 0,30) mới mở cửa. Ảnh in sẽ khó qua hơn, người đứng yên cũng khó qua hơn.

## Đọc gì trước khi sửa

| Muốn sửa | Mở |
| --- | --- |
| Cách chạy, biến môi trường | `README.md` mục 4.5 và `code/.env.example` |
| Phát hiện, vector, kho mẫu, ngưỡng | `code/yolohome/face/engine.py` |
| Các bước đăng ký | `code/yolohome/face/enroll.py` |
| Luật mở cửa | `code/yolohome/face/unlock.py` |
| Chọn ngưỡng trên ảnh test | `code/yolohome/face/evaluate.py` |
| Luồng gateway, thiếu cổng COM, gửi `DOOR:OPEN` | `code/yolohome/gateway.py` |
| API web | `code/yolohome/web/server.py`: `POST /api/face/scan`, `POST /api/face/enroll`, `POST /api/face/control`, `GET /api/face/video` |
| Web từ chối mặt khi không phải gateway | `code/yolohome/web/mock.py`, `code/yolohome/web/live.py` |
| Nối gateway với trang | `code/yolohome/web/gateway.py` |
| Hai nút, cửa sổ mật khẩu, cửa sổ webcam | `code/web/js/ai.js`, `code/web/index.html` |
| Kiểm tra không cần webcam | `code/tests/test_face.py` |

`GET /api/face/video` là ảnh JPEG nối tiếp (`multipart/x-mixed-replace`). Chỉ gắn một thẻ `<img>` trong cửa sổ webcam. Đừng gắn thêm một hình nữa trên thẻ, sẽ thành hai luồng và hình bị cắt.

Mật khẩu đăng ký là `WEB_PASSWORD`, kiểm bằng `Sessions.verify`. Hàm này không tạo phiên mới. Sai mật khẩu trả 401 nhưng trình duyệt không được chuyển về `/login.html` vì người đó vẫn đang đăng nhập. Chỗ ngoại lệ nằm trong `code/web/js/api.js`.

## Cách chạy để xem tiếp

Trong thư mục `code`, `.env` cần `WEB_DATA=gateway`, `FACE_ENABLE=1`, `WEB_PASSWORD` đã đặt. Rồi:

```powershell
.\.venv\Scripts\python.exe -m yolohome
```

Mở `http://127.0.0.1:8000`. Sửa file Python thì tắt tiến trình (Ctrl+C) rồi chạy lại. Sửa HTML, CSS, JS thì tải lại trang là đủ: máy chủ gửi `Cache-Control: no-cache`.

Không có board vẫn xem được mặt. Cổng COM không tồn tại không được làm chết web.

Kiểm tra tự động, không cần board và không đọc `.env` thật:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t .
```

Phải in `OK`. Test mặt không được gọi đăng ký thật, vì lệnh đó mở webcam.

## Việc nên làm tiếp

1. Đăng ký lại từng thành viên trên web, có làm bước kính nếu người đó lúc đeo lúc không. Mẫu cũ không tự tách hai kiểu.
2. Buổi khác, ánh sáng phòng demo: chụp ảnh test thành viên và người lạ (`enroll <tên> --test`, tên lạ chưa có trong kho). Chạy `python -m yolohome.face.evaluate`. Nếu `.env` không ghi `FACE_THRESHOLD`, ngưỡng trong `threshold.json` sẽ được dùng thay cho 0,70. Đọc báo cáo trước khi khóa một số mới. Người lạ không được mở cửa. Thành viên vẫn nên qua được. Không qua thì nút cửa trên web là đường dự phòng, đừng hạ ngưỡng xuống dưới điểm của người lạ.
3. Khi có board: quét đúng người thì cửa mở và tự đóng sau 10 giây. Quét người lạ thì cửa không mở, nút khóa cửa vẫn mở được.
4. Phase 7, giọng nói: micro laptop, bộ lệnh tiếng Việt cố định cho đèn và quạt, không LLM, không chạy trên board. Thẻ giọng nói trên web hiện là chỗ chờ.
5. Nhật ký lâu dài chỉ làm nếu nhóm muốn. Đồ án không bắt database. Đừng tạo feed mới để chứa log.

## Git

Nhánh làm việc đang dựa trên `origin/feat/6-face-recognition`. Đẩy nhánh đó sẽ ghi đè phần của người đã mở nhánh. Hỏi nhóm trước khi push. Không force-push. Không commit `.env`, `code/data/`, `code/models/`.
