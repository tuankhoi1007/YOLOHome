# Việc cần làm — chạy thử Module 1 và Module 2

Checklist này chỉ phần đang làm: Yolo:Bit đọc cảm biến, laptop đẩy lên Adafruit, đèn báo khi vượt ngưỡng.

Phần chưa làm (đèn, quạt, cửa, nhật ký, nhận diện mặt, giọng nói) nằm ở cuối file. Chưa đụng tới cho đến khi vòng chạy này ổn.

## Bối cảnh

Có hai chương trình, hai chỗ chạy:

| File | Chạy ở đâu | Việc của nó |
| --- | --- | --- |
| `yolobit.py` | Trên board, dán vào OhStem App | Đọc DHT20 + ánh sáng, in dòng `T:31.2,H:60,L:44`, nhận `LED:RED` / `LED:GREEN` |
| `gateway.py` | Trên laptop | Đọc dòng đó qua USB, gửi feed, so ngưỡng, gửi lệnh đèn xuống board |
| `module1.py` | Laptop, chỉ khi muốn thử cảm biến riêng | Giống nửa thu thập của gateway, không so ngưỡng |
| `module2.py` | Laptop, chỉ khi không cắm board | Nghe số có sẵn trên Adafruit rồi ghi feed cảnh báo |
| `config.py` | Không chạy trực tiếp | Đọc `.env`, nối Adafruit |
| `.env` | Không chạy | Username, Active Key, cổng COM, tên feed, ngưỡng mặc định |

OhStem và `gateway.py` không được giữ cùng một cổng COM. OhStem để nạp code. Sau khi lưu xong thì ngắt OhStem, rồi mới chạy gateway.

Feed đang dùng (cột **Key** trên Adafruit, không phải tên hiển thị):

| Key | Ý nghĩa |
| --- | --- |
| `nhiet-do` | Nhiệt độ (°C) |
| `do-am` | Độ ẩm (%) |
| `anh-sang` | Ánh sáng, thang 0–100 |
| `canh-bao` | Dòng chữ cảnh báo |
| `nguong-nhiet` | Ngưỡng nhiệt. Cao hơn số này thì cảnh báo |

`temperature`, `humidity`, `light` là bộ feed cũ, chương trình không ghi vào đó. `cua`, `den`, `quat` để dành cho điều khiển thiết bị.

Ngưỡng độ ẩm và ánh sáng chưa có feed. Chương trình lấy số trong `.env`: độ ẩm > 80, ánh sáng < 20. Ngưỡng nhiệt lấy từ feed `nguong-nhiet` nếu feed đó có số; không có thì dùng `32` trong `.env`.

## 1. Máy tính

- [ ] Cắm laptop vào mạng. Adafruit cần Internet.
- [ ] Mở PowerShell, vào thư mục code:

```powershell
cd d:\HCMUT\261\DADN\code
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Lệnh `python` trên máy này là Python của MSYS2, không có pip. Mọi lệnh bên dưới dùng Python trong `.venv`.

- [ ] Mở `.env`. Kiểm tra bốn dòng sau còn đúng:

```text
COM_PORT=COM11
FEED_TEMP=nhiet-do
FEED_HUMID=do-am
FEED_LIGHT=anh-sang
FEED_ALERT=canh-bao
FEED_TEMP_MAX=nguong-nhiet
```

Chưa sửa `COM_PORT` vội. Cổng thật lấy ở bước 3.

## 2. Feed ngưỡng nhiệt

Tài khoản Adafruit miễn phí chỉ có 10 feed. Muốn thêm feed thì phải xóa một feed thừa trước.

- [ ] Vào [io.adafruit.com](https://io.adafruit.com) → **Feeds**.
- [ ] Nếu đã có key `nguong-nhiet`, bỏ qua bước xóa và tạo.
- [ ] Nếu chưa có: mở feed **temperature** → **⋯** → **Delete**.
- [ ] Bấm **+**, tên gõ đúng `nguong-nhiet`, tạo. Cột Key phải là `nguong-nhiet`.
- [ ] Mở feed đó → **Add Data** → giá trị `32`.

`32` nghĩa là nhiệt độ cao hơn 32°C thì cảnh báo. Muốn đổi sau này thì thêm một điểm dữ liệu mới, không sửa code.

## 3. Cắm thiết bị và nạp code lên board

- [ ] Cắm Yolo:Bit vào mạch mở rộng.
- [ ] Cắm DHT20 vào một cổng **I2C**.
- [ ] Cắm cảm biến ánh sáng vào cổng **P0**.
- [ ] Cắm 4 đèn LED RGB vào cổng **P14**. Không cắm chung với cảm biến ánh sáng ở P0.
- [ ] Cắm cáp USB từ Yolo:Bit vào laptop.
- [ ] Mở [app.ohstem.vn](https://app.ohstem.vn) bằng Chrome hoặc Edge.
- [ ] Chọn thiết bị **Yolo:Bit**.
- [ ] Bấm kết nối **USB**, chọn cổng COM hiện ra. Ghi lại tên cổng (ví dụ `COM11`). Nếu không thấy cổng, cài driver tại [ohstem.vn/driver](https://ohstem.vn/driver) rồi cắm lại.
- [ ] Nếu cổng khác `COM11`, sửa dòng `COM_PORT` trong `.env` cho trùng, rồi lưu file.
- [ ] Trên OhStem, bấm nút chuyển sang chế độ **Python**.
- [ ] Xóa code mẫu. Mở `code/yolobit.py`, chọn hết, dán vào ô soạn thảo.
- [ ] Bấm **Chạy** (nút chạy góc dưới).
- [ ] Mở cửa sổ thông tin / serial trong OhStem.

Đúng khi mỗi khoảng 2 giây có một dòng như:

```text
T:31.2,H:60,L:44
```

Thiếu độ ẩm vẫn được, ví dụ `T:31.2,L:44`. Đèn ma trận lúc này sáng một điểm ở giữa. Bốn LED RGB sáng xanh lá.

- [ ] Nếu báo thiếu `aiot_dht20`: vào thư viện, tải **AIOT KIT**, bấm **Chạy** lại. File vẫn đọc DHT20 trực tiếp qua I2C khi thư viện không có.
- [ ] Nếu dòng là `Khong doc duoc cam bien`: kiểm tra DHT20 đang ở cổng I2C và ánh sáng đang ở P0, rồi bấm **Chạy** lại.
- [ ] Khi đã thấy dòng `T:...`, bấm **Lưu project vào thiết bị**.
- [ ] Bấm **ngắt kết nối** trong OhStem. Giữ nguyên dây USB. Đóng hẳn tab OhStem nếu cổng COM vẫn bị chiếm.

Không chạy `python yolobit.py` trên laptop. File đó chỉ chạy trên board.

## 4. Chạy gateway trên laptop

- [ ] OhStem đã ngắt kết nối.
- [ ] PowerShell đang đứng trong `d:\HCMUT\261\DADN\code`.
- [ ] Chạy:

```powershell
.\.venv\Scripts\python.exe gateway.py
```

Đúng khi cửa sổ in lần lượt các dòng kiểu:

```text
Gateway: module 1 + module 2
Da ket noi Adafruit
Dang doc COM11 toc do 115200
Nhan: T:31.2,H:60,L:44
Doc: T=31.2 H=60 L=44
Gui: nhiet-do=31.2, do-am=60, anh-sang=44
Canh bao: Bình thường
Lenh den: GREEN
```

Số thật sẽ khác. `Canh bao` chỉ in lại khi nội dung đổi.

- [ ] Mở lại trang Feeds. `nhiet-do`, `do-am`, `anh-sang` có số mới, cột Recorded là vài giây trước.
- [ ] `canh-bao` là `Bình thường` khi cả ba thông số nằm trong ngưỡng.
- [ ] Hơ tay vào DHT20 cho nhiệt độ vượt số trên `nguong-nhiet`. `canh-bao` đổi thành câu có `Nhiệt độ cao`, ma trận đèn sáng hết 25 điểm, bốn LED RGB nhấp nháy đỏ.
- [ ] Bỏ tay ra, đợi nhiệt độ xuống. Feed về `Bình thường`, ma trận còn một điểm giữa, RGB sáng xanh lá.
- [ ] Che cảm biến ánh sáng. Nếu giá trị xuống dưới 20, cảnh báo có thêm `Ánh sáng thấp`.
- [ ] Dừng gateway bằng `Ctrl+C` trong PowerShell.

## 5. Khi cửa sổ báo lỗi

| Dòng in ra | Việc làm |
| --- | --- |
| `Khong mo duoc COM11` | OhStem còn kết nối, hoặc `COM_PORT` sai. Ngắt OhStem, xem lại cổng ở bước 3, sửa `.env`, chạy lại. |
| `5 giay roi, board khong gui gi qua USB` | Board chưa chạy `yolobit.py`. Nạp và lưu lại ở OhStem, ngắt OhStem, chạy lại gateway. |
| `Bo qua dong nay. Can dang T:31.2,H:60,L:44` | Board đang in câu khác. Nhìn serial OhStem, chạy lại đúng file `yolobit.py`. |
| `Khong ket noi duoc Adafruit` | Kiểm tra mạng, username và Active Key trong `.env`. Key lấy ở biểu tượng chìa khóa vàng trên Adafruit, không phải mật khẩu đăng nhập. |
| `Tai khoan da du 10 feed` | Bình thường nếu chưa xóa feed thừa. Ngưỡng ẩm và sáng vẫn lấy từ `.env`. |
| Feed không đổi số | Đợi khoảng 15 giây. Chương trình không gửi lại khi số gần như không đổi, để khỏi vượt 30 điểm/phút của Adafruit. |

## Việc để sau

Làm tiếp chỉ khi bước 4 đã thấy số trên Adafruit và đèn đổi theo ngưỡng.

- [ ] Module 3: đọc feed `den`, `quat`, `cua` rồi điều khiển đèn RGB, quạt, servo.
- [ ] Module 4: lưu lịch sử cảm biến, lần bật/tắt, lần cảnh báo.
- [ ] Module 5: dựng dashboard Adafruit theo `docs/ADAFRUIT_DASHBOARD.md`.
- [ ] Web, dữ liệu giả lập: thêm `WEB_PASSWORD` vào `.env`, chạy `web_server.py`, mở `http://127.0.0.1:8000` trên laptop, đăng nhập được, số đổi mỗi 3 giây, bấm thử đèn, quạt, cửa và các nút mô phỏng. Chi tiết ở mục 6 của `README.md`.
- [ ] Web chạy luôn Module 1 + 2 (cách demo chính): làm xong bước 3, **không** chạy `gateway.py`, đặt `WEB_DATA=gateway` trong `.env`, chạy `web_server.py`. Cửa sổ in các dòng như bước 4; trên `http://127.0.0.1:8000` thẻ cảm biến đổi theo board trong vòng 5 giây. Hơ tay vào DHT20: dòng LED trên web chuyển đỏ, có thông báo, 4 LED RGB trên board nháy đỏ. Mở **Cấu hình ngưỡng**, lưu nhiệt độ cao hơn số đang đo: feed `nguong-nhiet` trên Adafruit đổi, web và board về xanh.
- [ ] Web chỉ đọc Adafruit: để `gateway.py` chạy (bước 4), đặt `WEB_DATA=live`, chạy `web_server.py` ở cửa sổ thứ hai. Thẻ cảm biến đổi theo số trên Adafruit.
- [ ] Nhận diện khuôn mặt trên webcam laptop, đúng người thì mở servo.
- [ ] Lệnh giọng nói tiếng Việt cố định cho đèn và quạt, chạy trên mic laptop.
