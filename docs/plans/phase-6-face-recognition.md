# Phase 6: nhận diện khuôn mặt mở cửa (AI chính)

- Người làm: thành viên phụ trách Phase 6 (Minh)
- Trạng thái: code đã viết và có test tự động; **chờ owner chốt D7 và duyệt Gate 6**
- Branch: `feat/6-face-recognition`

## Đề xuất cho D7 (chờ owner chốt)

| Câu hỏi | Đề xuất | Lý do |
| --- | --- | --- |
| Phát hiện mặt | YuNet (OpenCV DNN, ONNX ~0,3 MB) | Có sẵn trong `opencv-python` ≥ 4.8, chạy CPU nhanh, trả 5 điểm mốc để căn chỉnh và đo tư thế |
| Nhận diện | SFace (OpenCV DNN, ONNX ~37 MB), vector 128 số, so cosine | Không cần train mạng; cài chỉ bằng pip trên Windows (dlib/face_recognition hay lỗi biên dịch) |
| "Huấn luyện" | Đăng ký mẫu từng thành viên + hiệu chỉnh ngưỡng trên dữ liệu của nhóm | Đúng yêu cầu "có huấn luyện và đánh giá trên tập kiểm thử nội bộ" mà không cần GPU hay tập dữ liệu lớn |
| Thư viện mới | `opencv-python`, `numpy` (thêm vào `requirements.txt`); `matplotlib` tùy chọn cho biểu đồ | Chỉ `yolohome.face` import; thiếu thì gateway tắt phần mặt và chạy tiếp |

Không so sánh baseline LBPH (người làm Phase 6 quyết định 2026-11-21).

## Thiết kế

- **Đăng ký (UC02)** — `python -m yolohome.face.enroll <ten>`: 4 bước tư thế (nhìn thẳng 8 ảnh, quay một bên 6, quay bên kia 6, lùi xa 5). Đo góc quay đầu từ 5 điểm mốc YuNet: |yaw| < 0,08 là thẳng, 0,15–0,45 là quay. Sai tư thế thì không chụp, không sang bước; mỗi bước tối đa 30 s. Thiếu bước thẳng hoặc < 10 ảnh thì không lưu, giữ mẫu cũ. Ảnh mặt đã căn chỉnh 112x112 lưu trong `code/data/faces/enroll/<ten>/`, vector trong `gallery.npz`.
- **So khớp (UC08)** — mỗi người một mẫu trung bình (trung bình các vector rồi chuẩn hóa); điểm = cosine với mẫu đó.
- **Mở cửa (UC07)** — quét tối đa 6 s; mở khi 5/7 khung liên tiếp khớp cùng một người với điểm ≥ ngưỡng; khung 0 hoặc ≥ 2 mặt bị bỏ. `FACE_LIVENESS=1`: thêm thử thách quay đầu (độ lệch yaw ≥ 0,30 trong lúc quét) chống ảnh in; mặc định tắt cho đến khi thử trên webcam thật.
- **Ngưỡng** — `python -m yolohome.face.evaluate` chia ảnh test mỗi người theo thứ tự chụp: nửa đầu chọn ngưỡng (nhỏ nhất để FAR = 0 trên người lạ, cộng biên 0,03, không thấp hơn 0,363 của SFace/LFW), nửa sau để báo cáo. Chưa chạy thì dùng 0,5.
- **Đánh giá** — Accuracy, FAR, FRR, nhầm giữa thành viên, EER, ma trận nhầm lẫn, mô phỏng luật 5/7 theo lượt quét; ghi `data/faces/eval_report.md` và `eval_plot.png`.

## Nối với Module 3, 4, 5

- Không đổi `docs/PROTOCOL.md`: không feed mới (vẫn 10/10), không lệnh serial mới. Cửa mở bằng `DeviceControl.request("cua", "OPEN", "Khuôn mặt")` giống lệnh từ web; board tự đóng sau 10 s (v0.2.0), nên phần mặt không tự đóng.
- `Gateway.scan_face(source)` bắt đầu quét từ luồng khác; `Gateway.drain_face()` chạy trong `step()`; kết quả báo qua listener `on_face({"ok", "name", "score", "detail"})`.
- **Còn mở cho Module 4/5:** nút quét và hiển thị kết quả trên web (thay placeholder trong `web/js/ai.js`, gọi `scan_face`, nhận `on_face`); ghi lần nhận diện vào nhật ký khi D5 chốt. Hiện tại chạy `python -m yolohome.gateway` thì gõ `f` + Enter để quét.

## Kiểm tra

- `python -m compileall yolohome` và `python -m unittest discover -s tests -t .`: 133 test, OK (115 cũ + 18 trong `tests/test_face.py`). Không có numpy/OpenCV: vẫn OK, 4 test kho mẫu tự bỏ qua.
- **Chưa kiểm tra:** chạy với webcam và mô hình thật trên laptop của nhóm; ngưỡng yaw khi đăng ký và `FACE_LIVE_SPREAD`; cửa mở trên board thật (cần Gate 3). Đây là phần owner / người làm Phase 6 chạy.

## Outcome

Chưa có số đánh giá thật. Điền sau khi chạy `evaluate` trên dữ liệu của nhóm (Gate 6): số ảnh, ngưỡng, Accuracy, FAR, FRR, lượt quét.

Handoff: "Phase 6: chạy enroll/evaluate trên webcam thật, ghi số vào Outcome; Module 5 nối nút quét web vào `Gateway.scan_face` và `on_face`."
