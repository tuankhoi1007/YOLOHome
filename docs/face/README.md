# Kết quả nhận diện khuôn mặt

Thư mục này là phần đưa vào báo cáo. Ảnh mặt người không nằm ở đây và không được commit (`code/data/faces/` bị gitignore).

## Bài chạy thử đã commit (`smoke/`)

`smoke/` là **synthetic smoke test**: bốn họa tiết vẽ (`mau_a` … `mau_d`), không phải mặt người. `metrics.json` có `"synthetic": true`. File này chứng minh pipeline chạy (chia tập, hai mô hình, FAR/FRR, ma trận, sweep, độ trễ CPU) và **không được chép vào báo cáo như độ chính xác của hệ thống**.

Đọc `smoke/REPORT.md`. Tóm tắt của lần chạy đã commit (OpenCV 4.10, CPU, seed 42, 32 train / 16 test / 10 ảnh lạ):

| | LBPH | YuNet + SFace |
| --- | --- | --- |
| Accuracy tập kín (bắt buộc chọn người gần nhất) | 1.0, precision/recall 1.0 mỗi lớp | 1.0, precision/recall 1.0 mỗi lớp |
| Ngưỡng đã chọn | khoảng cách 17.6418 | cosine 0.9976 |
| FAR / FRR / nhận nhầm | 0 / 0.9375 / 0 | 0 / 1 / 0 |
| Thời gian CPU | khớp LBPH ~1.8 ms | feature ONNX ~7.7 ms, rồi cosine ~0.04 ms |

YuNet trên khung trống 640×480 thêm khoảng 7.4 ms. Quy tắc chọn: FAR thấp nhất, rồi nhận nhầm người trong nhà, rồi FRR, rồi accuracy tập kín, rồi tốc độ. Cả hai cùng FAR = 0 nên LBPH thắng vì FRR thấp hơn. FRR rất cao vì họa tiết giả và ảnh lạ (bản xoay của `mau_a`) chồng điểm; FAR leave-one-person-out = 0 trong bài này chủ yếu vì ngưỡng từ chối gần hết, không phải vì mô hình tách người lạ tốt. SFace học từ mặt người thật nên trên họa tiết nó thường kém LBPH. Điều đó không dự đoán kết quả khi có ảnh thật.

Độ trễ là đo thời gian, sẽ lệch vài phần mười mili giây giữa các máy. FAR, FRR và accuracy của bài này cố định với seed 42.

## Sau khi nhóm chụp ảnh thật

Chạy `face_train.py` (lệnh trong `code/HUONG_DAN.md`). Script ghi đè các file sau ngay trong `docs/face/` (không đụng `smoke/`):

| File | Nội dung |
| --- | --- |
| `REPORT.md` | Đoạn văn đưa vào báo cáo, có lý do chọn model và ngưỡng |
| `metrics.json` | Đủ số: accuracy, precision/recall từng người, ma trận, sweep, FAR, FRR, độ trễ |
| `per_class.csv` | Precision, recall, support từng người, từng model |
| `threshold_sweep.csv` | FAR, FRR, nhận nhầm theo từng ngưỡng |
| `confusion_lbph.png`, `confusion_sface.png` | Ma trận nhầm (cột `reject` là từ chối) |
| `threshold_lbph.png`, `threshold_sface.png` | Đường FAR/FRR và ngưỡng đã chọn |
| `split.json` | Đúng file nào vào train, test, unknown. Seed 42 |

`metrics.json` của lần chạy thật phải có `"synthetic": false`. Model để mở cửa nằm ở `code/models/face/chosen.json` (gitignore, không commit vì là đặc trưng sinh trắc).

Nếu chưa có thư mục `unknown/`, FAR để trống và ngưỡng lấy điểm chặt nhất còn FRR ≤ 10%. Nên chụp thêm người lạ để FAR là số đo được, không chỉ ước lượng leave-one-person-out.
