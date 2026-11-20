# Việc cần làm — chạy thử Module 1 và Module 2

Checklist này chỉ phần đang làm: Yolo:Bit đọc cảm biến, laptop đẩy lên Adafruit, đèn báo khi vượt ngưỡng.

Phần chưa làm (đèn, quạt, nhật ký lâu dài, giọng nói) nằm ở cuối file. Nhận diện mặt và servo cửa có hướng dẫn riêng ở mục 6; làm sau khi vòng cảm biến đã chạy.

## Bối cảnh

Có hai chương trình, hai chỗ chạy:

| File | Chạy ở đâu | Việc của nó |
| --- | --- | --- |
| `yolobit.py` | Trên board, dán vào OhStem App | Đọc DHT20 + ánh sáng, in dòng `T:31.2,H:60,L:44`, nhận `LED:RED` / `LED:GREEN` và `DOOR:OPEN` / `DOOR:CLOSE` |
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

## 6. Nhận diện khuôn mặt và cửa servo

Làm sau khi bước 4 đã thấy số trên Adafruit. Phần này chạy trên laptop (Windows, Python 3.10, PowerShell 5.1, CPU). Không cần card đồ họa. Không cài dlib.

Ảnh mặt nằm trong `code\data\faces\` và bị gitignore. Không copy thư mục đó vào git, không gửi kèm báo cáo.

### Cài thêm thư viện

Nếu máy đã có `.venv` từ mục 1 (kể cả Python 3.13), không tạo lại. Chỉ cài lại requirements. Wheel `opencv-contrib-python` có sẵn cho Python 3.10 đến 3.13, không cần Visual Studio.

PowerShell 5.1 không có `&&`. Mỗi khối dưới đây chạy từng dòng.

```powershell
cd d:\HCMUT\261\DADN\code
.\.venv\Scripts\python.exe -m pip uninstall -y opencv-python
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Máy chưa có venv, hoặc muốn đúng Python 3.10:

```powershell
cd d:\HCMUT\261\DADN\code
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Lần train hoặc chụp đầu tiên tải hai file ONNX (YuNet, SFace) vào `code\models\face\zoo\`. Cần mạng một lần. Thư mục `models` cũng bị gitignore.

### Chụp ảnh

Đứng trước webcam laptop. Mỗi người 40 ảnh, mặt xoay nhẹ và đổi khoảng cách. Cửa sổ hiện hình; bấm `q` hoặc ESC để dừng sớm. Lặp lại, đổi tên, cho đủ 5 thành viên. Tên là tên thư mục, không dùng dấu `\` hoặc tên `unknown`.

```powershell
cd d:\HCMUT\261\DADN\code
.\.venv\Scripts\python.exe face_capture.py --name "Nguyen Van A" --count 40
```

Webcam không phải camera 0 thì thêm `--camera 1`.

Chụp thêm người không có trong nhóm, để đo tỷ lệ mở nhầm (FAR). Khoảng 20 ảnh là đủ cho bài nội bộ:

```powershell
.\.venv\Scripts\python.exe face_capture.py --unknown --count 20
```

### Train, đánh giá, chọn ngưỡng

```powershell
.\.venv\Scripts\python.exe face_train.py
```

Xong thì mở `docs\face\REPORT.md`. File đó ghi model được chọn, ngưỡng, accuracy, precision/recall từng người, FAR, FRR, và độ trễ CPU. Ảnh biểu đồ nằm cạnh file. Model để chạy cửa ghi vào `code\models\face\` (không commit).

Muốn thử pipeline khi chưa có ảnh người:

```powershell
.\.venv\Scripts\python.exe face_train.py --smoke
```

Kết quả vào `docs\face\smoke\` và được đánh dấu synthetic. Không chép các số đó vào báo cáo.

### Chạy thật cùng web

1. Nạp lại `yolobit.py` lên board (mục 3), **Lưu project vào thiết bị**, rồi ngắt OhStem. Bản cũ bỏ qua dòng `DOOR:` nên nút cửa trên web sẽ chờ quá 3 giây.
2. Cắm servo vào cổng **P4** trên mạch mở rộng. Không cắm vào P0 (ánh sáng) và không cắm vào P14 (LED RGB). Nhóm chưa chốt cổng (D4): muốn cổng khác thì sửa `SERVO_PIN` trong `.env`, ví dụ `SERVO_PIN=P5`, rồi chạy lại. Giá trị hợp lệ là P1–P13 và P15–P16.
3. Nếu sừng servo quay ngược, sửa hai dòng trong `yolobit.py` rồi nạp lại: `DOOR_CLOSED_ANGLE` và `DOOR_OPEN_ANGLE` (đang là 0 và 90). Laptop không gửi góc.
4. Trong `.env`:

```text
WEB_DATA=gateway
FACE_ENABLE=1
SERVO_PIN=P4
DOOR_OPEN_SECONDS=10
```

5. Không chạy thêm `gateway.py`. Một cửa sổ:

```powershell
.\.venv\Scripts\python.exe web_server.py
```

6. Mở `http://127.0.0.1:8000`. Thẻ khuôn mặt hiện model và trạng thái camera, không còn nút mô phỏng. Đưa mặt thành viên vào webcam: cửa mở, khoảng 10 giây sau gateway gửi lệnh đóng. Mặt lạ thì cửa giữ nguyên. Nút **Khóa cửa** vẫn mở được cửa khi nhận diện từ chối.
7. Mỗi lần nhận diện (ai, điểm, nhận hay từ chối, thời điểm) in trong PowerShell, vào nhật ký trên web, và thêm một dòng trong `code\data\runtime\face_log.jsonl`.

`FACE_ENABLE=0` là mặc định: web vẫn chạy cảm biến, không mở webcam. Nút cửa ở chế độ `gateway` vẫn dùng được.

### Kiểm tra không cần camera và không cần board

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t .
```

Phải in `OK`.

## Việc để sau

Làm tiếp chỉ khi bước 4 đã thấy số trên Adafruit và đèn đổi theo ngưỡng.

- [ ] Module 3: đọc feed `den`, `quat`, `cua` rồi điều khiển đèn RGB, quạt. Servo cửa của nhận diện mặt đi bằng USB (`DOOR:OPEN` / `DOOR:CLOSE`), không thêm feed.
- [ ] Module 4: lưu lịch sử cảm biến, lần bật/tắt, lần cảnh báo.
- [ ] Module 5: dựng dashboard Adafruit theo `docs/ADAFRUIT_DASHBOARD.md`.
- [ ] Web, dữ liệu giả lập: thêm `WEB_PASSWORD` vào `.env`, chạy `web_server.py`, mở `http://127.0.0.1:8000` trên laptop, đăng nhập được, số đổi mỗi 3 giây, bấm thử đèn, quạt, cửa và các nút mô phỏng. Chi tiết ở mục 6 của `README.md`.
- [ ] Web chạy luôn Module 1 + 2 (cách demo chính): làm xong bước 3, **không** chạy `gateway.py`, đặt `WEB_DATA=gateway` trong `.env`, chạy `web_server.py`. Cửa sổ in các dòng như bước 4; trên `http://127.0.0.1:8000` thẻ cảm biến đổi theo board trong vòng 5 giây. Hơ tay vào DHT20: dòng LED trên web chuyển đỏ, có thông báo, 4 LED RGB trên board nháy đỏ. Mở **Cấu hình ngưỡng**, lưu nhiệt độ cao hơn số đang đo: feed `nguong-nhiet` trên Adafruit đổi, web và board về xanh.
- [ ] Web chỉ đọc Adafruit: để `gateway.py` chạy (bước 4), đặt `WEB_DATA=live`, chạy `web_server.py` ở cửa sổ thứ hai. Thẻ cảm biến đổi theo số trên Adafruit.
- [x] Nhận diện khuôn mặt: làm theo mục 6. Phần mềm đã có. Nhóm còn phải tự chụp ảnh, train, nạp lại board và cắm servo.
- [ ] Lệnh giọng nói tiếng Việt cố định cho đèn và quạt, chạy trên mic laptop.
