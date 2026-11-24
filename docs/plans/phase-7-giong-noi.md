# Phase 7 · Từ micro laptop đến đèn và quạt Yolo:Bit

Sau khi hoàn thành hướng dẫn, bạn có thể bấm biểu tượng micro trên dashboard, đợi chữ **Đang nghe**, nói **“bật quạt”**, rồi nhìn thấy tốc độ quạt đã được board xác nhận. Ba lệnh còn lại là **“tắt quạt”, “bật đèn”, “tắt đèn”**. Mỗi lần bấm tương ứng với một lượt nói. Máy chuẩn để thử là Windows, Intel i5-1240P, RAM 16 GB và mic tích hợp.

**Bắt đầu ở bước 1 nếu chưa có kit.** Probe và bộ khớp lệnh ở bước 1–4 đã có trong repo. Bước 5–6 mô tả phần tích hợp vào dashboard. Bước 7–8 dùng kit để đánh giá tác động thật.

## Tài liệu và thiết bị cần chuẩn bị

- **Đọc trước khi code.** Trong giáo trình, đọc chương 19 (trang 159–165) để hiểu cách nhận lời nói trên máy tính, rồi đọc chương 29 (trang 233–238), đặc biệt hình 29.2 về đường đi của lệnh và hình 29.7 về câu ngoài phạm vi. Các kênh V10/V13 thuộc ví dụ OhStem. Dự án của nhóm đã có đường điều khiển riêng qua Gateway. File PDF nằm ngoài repo, ở thư mục DADN trên máy của nhóm. [Giáo trình YoloHome AIoT](../../../../YoloHome___AIoT_v2.pdf) · [Phạm vi đề tài](../../User_Requirements.md)
- **Mở khi tích hợp.** README mục 2 và 4 hướng dẫn cấu hình máy, COM, Adafruit và các chế độ web. Phần Module 3 trong giao thức mô tả giá trị đèn, tốc độ quạt, thời gian chờ và ACK (thông báo board đã xử lý lệnh). [README](../../README.md) · [Giao thức](../PROTOCOL.md) · [Checklist thử kit](../../code/KIEM_TRA_GATE_1_3.md) · [Roadmap, Phase 7](../ROADMAP.md)
- **Mở khi làm việc với âm thanh.** Faster Whisper dùng mô hình `small` đa ngôn ngữ, chỉ định tiếng Việt bằng `language="vi"` và chạy CPU với `int8`. Thư viện `sounddevice` đọc mic trên Windows. [Faster Whisper](https://github.com/SYSTRAN/faster-whisper) · [API RawInputStream](https://python-sounddevice.readthedocs.io/en/latest/api/raw-streams.html)
- **Chuẩn bị cho demo.** Laptop, mic, kit đã nạp chương trình của nhóm, cáp USB truyền dữ liệu, đèn RGB P14 và quạt P1. Tải thư viện và mô hình khi có Internet. Sau đó có thể kiểm tra nhận dạng offline, còn demo đầy đủ có đồng bộ Adafruit cần mạng.

## 1. Chuẩn bị Python và kiểm tra Windows thấy mic

Mở repo YOLOHome trong IDE. Mở **Terminal → PowerShell** ở thư mục chứa `README.md`, chạy các lệnh dưới đây. Từ đây đến hết hướng dẫn, làm việc trong thư mục `code`.

```powershell
Set-Location .\code
py -0p
if (!(Test-Path .\.venv\Scripts\python.exe)) { py -3 -m venv .venv }
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $python --version
& $python -m pip install -r requirements.txt
& $python -m pip install "faster-whisper==1.2.1" "av>=11,<19" sounddevice
& $python -c "import faster_whisper, sounddevice; print('Import OK')"
& $python -m sounddevice
```

**Kiểm tra:** cần thấy `Import OK` và một thiết bị như *Microphone Array* có ít nhất một kênh vào. Mở **Settings → System → Sound → Input**, chọn mic laptop, nói thử và nhìn thanh âm lượng. Trong **Privacy & security → Microphone**, cho phép ứng dụng desktop truy cập mic. Trong bài này Python là ứng dụng mở mic.

Giới hạn `av<19` giữ API đọc WAV tương thích với Faster Whisper 1.2.1. Nếu probe báo lỗi `metadata_errors`, chạy lại lệnh cài ở trên. [Lỗi tương thích đã ghi nhận ở Faster Whisper](https://github.com/SYSTRAN/faster-whisper/issues/1589)

Nếu pip báo thiếu wheel hoặc import DLL lỗi, ghi lại phiên bản Python và tên gói lỗi. Trên máy đang dùng Python 3.14, có thể thử CPython 3.11 x64 trong môi trường riêng: sau khi cài 3.11, chạy `py -3.11 -m venv .venv-voice`, đặt lại `$python = (Resolve-Path .\.venv-voice\Scripts\python.exe).Path` rồi lặp các lệnh cài và kiểm tra phía trên. Khi mở terminal mới, đặt lại `$python` tới môi trường đã chạy thành công. [Python cho Windows](https://www.python.org/downloads/windows/)

## 2. Tải mô hình tiếng Việt một lần

Chạy từ cùng cửa sổ PowerShell có Internet. Faster Whisper tải mô hình vào cache Hugging Face của tài khoản Windows. Sau khi thấy `Model OK`, dùng `--offline` để probe nạp từ cache.

```powershell
& $python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8'); print('Model OK')"
```

Nếu laptop khác sẽ dùng để demo, chạy lệnh trên máy đó trước buổi demo để tạo cache cho đúng tài khoản Windows.

### Dùng PhoWhisper-small của VinAI

Chạy probe với thư mục PhoWhisper-small đã chuyển sang CTranslate2. Bản chuyển đổi dùng INT8 trên CPU và nằm trong thư mục model cục bộ của YOLOHome. [Mô hình gốc của VinAI](https://huggingface.co/vinai/PhoWhisper-small) · [Cách chuyển mô hình cho Faster Whisper](https://github.com/SYSTRAN/faster-whisper#model-conversion)

```powershell
$pho = Join-Path $env:LOCALAPPDATA "YOLOHome\models\phowhisper-small-ct2"
& $python -X utf8 .\voice_probe.py --offline --model-dir $pho
```

Để so sánh trên một file WAV, dùng cùng đường dẫn trong cả hai lệnh.

```powershell
$wav = Join-Path $env:TEMP "yolohome-bat-den-test.wav"
& $python -X utf8 .\voice_probe.py --offline --input-wav $wav
& $python -X utf8 .\voice_probe.py --offline --model-dir $pho --input-wav $wav
```

Trên laptop khác, sao chép cả thư mục `phowhisper-small-ct2` rồi đặt `$pho` trỏ đến thư mục đó. Probe dùng trực tiếp bản CTranslate2 và các thư viện ở bước 1.

## 3. Nghe một câu thật trước khi viết API

Probe thu **3 giây** mỗi lượt, giữ âm thanh trong RAM và giải mã tiếng Việt sau khi thu. Faster Whisper lọc đoạn thiếu tiếng nói trước khi chép lời. Chạy lệnh từ thư mục `code`. [Mã probe](../../code/voice_probe.py)

```powershell
& $python .\voice_probe.py --offline
```

Nhấn Enter, đợi **“Đang nghe”** rồi nói **“bật đèn”**. Probe in tên mic, chuyển sang **“Đang nhận dạng”** khi thu xong, rồi in câu Whisper chép, thời gian xử lý và lệnh dự kiến. Nếu mic mất mẫu hoặc mở mic thất bại, probe báo lỗi và giữ mô hình trong bộ nhớ để bạn thử lượt tiếp theo. Nếu chạy offline mà thiếu mô hình, kết nối mạng và thực hiện lại bước 2.

### Khoanh vùng lỗi bằng cùng một file WAV

Chọn số mic bằng `& $python -m sounddevice`. Các lệnh dưới dùng mic số 2 làm ví dụ. Thu đúng một lượt, gõ `q` rồi nghe lại. Tùy chọn `--wav` ghi đè file sau mỗi lượt.

```powershell
$wav = Join-Path $env:TEMP "yolohome-voice-probe.wav"
& $python .\voice_probe.py --offline --device 2 --seconds 3 --wav $wav
Invoke-Item $wav
& $python .\voice_probe.py --offline --input-wav $wav
& $python .\voice_probe.py --offline --input-wav $wav --no-vad
```

- Nếu WAV thiếu tiếng đầu hoặc tiếng cuối, kiểm tra mic đã chọn và thử thu với `--seconds 4`.
- Nếu WAV rõ nhưng VAD giữ lại `0.00 s`, xem câu chép khi thêm `--no-vad`. Nếu tắt VAD giúp nghe đúng, thử thêm im lặng, tiếng quạt và câu phủ định trước khi chọn cấu hình.
- Nếu cả hai cấu hình đều chép sai dù WAV rõ, ghi câu sai và thời gian nhận dạng. Thử thêm giọng của một thành viên khác để xem lỗi có lặp lại.

Nếu Whisper nghe sai tên thiết bị, thử cùng file WAV với gợi ý từ vựng. Tùy chọn `--hint-devices` gợi ý hai từ **đèn** và **quạt** cho Whisper.

```powershell
& $python .\voice_probe.py --offline --input-wav $wav --hint-devices
& $python .\voice_probe.py --offline --hint-devices
```

Trên một bản WAV của nhóm, tùy chọn này đổi kết quả từ “Bật đen” thành “bật đèn”. Lặp lại bài thử ở bước 4 với cả hai cấu hình để xem gợi ý có giúp trên các câu khác hay khiến một câu phủ định bị chép thành lệnh hợp lệ.

## 4. Kiểm tra bốn lệnh trước khi nối Gateway

`match_command()` nhận đúng bốn câu sau khi chuẩn hóa chữ hoa/thường, dấu câu cuối câu và khoảng trắng. Dòng **“Lệnh dự kiến”** trong probe cho thấy thiết bị và giá trị mà Gateway sẽ nhận khi tích hợp. [Bộ khớp lệnh](../../code/yolohome/voice.py)

1. Chạy probe với cấu hình muốn dùng. Mỗi lượt nói một trong bốn câu **“bật đèn”**, **“tắt đèn”**, **“bật quạt”** hoặc **“tắt quạt”**. So sánh câu đã nói, câu Whisper chép và lệnh dự kiến. Ví dụ, “bật đèn” phải cho `('light', {'on': True})`.
2. Thử **im lặng**, **“đừng bật đèn”**, **“đừng tắt quạt”**, **“bật đèn rồi tắt quạt”** và **“mở cửa”**. Kỳ vọng mỗi lượt in `Lệnh dự kiến: Từ chối`. Nếu Whisper bỏ sót “đừng” và probe in lệnh bật/tắt, ghi nhận đây là lỗi kích hoạt và tiếp tục chẩn đoán ở bước 3.
3. Lặp lại với tiếng quạt và một giọng khác. Dùng kết quả bài thử nhỏ để quyết định cấu hình đem tích hợp. Bộ đánh giá cuối nằm ở bước 8.

## 5. Gắn việc nghe vào Gateway

1. Tách `listen_once` và `transcribe` sang module giọng nói trong `code/yolohome/`. Cho phép truyền hàm báo “đang nghe” vào nơi probe đang `print`. Chỉ import thư viện khi khởi tạo voice. Thêm `faster-whisper` và `sounddevice` vào danh sách phụ thuộc theo các phiên bản đã thử (`& $python -m pip show faster-whisper sounddevice`). Tải model trước buổi demo và cấu hình Gateway dùng `local_files_only=True` khi nạp.
2. Trong `GatewayHome`, thêm `start_voice()`. Dùng một khóa riêng cho lượt nghe, lấy khóa bằng `acquire(blocking=False)`. Nếu đang bận, trả `CommandError(409, "Micro đang bận")`. Nếu nhận lượt, khởi động worker rồi trả ngay. Worker nạp model lần đầu, giữ lại cho các lượt tiếp theo và giải phóng khóa trong `finally`. Nếu khởi động worker lỗi, giải phóng khóa ngay tại nơi tạo worker. Thu âm và suy luận ở ngoài khóa trạng thái của `GatewayHome`.
3. Khi stream mở thành công, phát sự kiện `voice` có `status="listening"`. Khi đóng mic và bắt đầu suy luận, phát `status="transcribing"`. Sau khi nhận dạng, gọi `match_command(text)`. Nếu là `None`, lưu `status="rejected"`, hiện “Hãy nói một trong bốn lệnh” rồi kết thúc. Nếu hợp lệ, tách `device, body` và gọi **một lần** `self.command(device, body, source="Giọng nói")`. Gọi hàm này bên ngoài `with self.lock` vì chính nó lấy khóa bên trong. Hàm hiện có phục hồi màu đèn hoặc tốc độ quạt khi bật. [GatewayHome.command](../../code/yolohome/web/gateway.py)
4. Ghi và phát trạng thái lượt nghe gồm `status`, `text`, `at` (giây Unix) và `message`. Dùng `sent` khi Gateway đã tiếp nhận, `error` khi mic/model lỗi hoặc `command()` từ chối. Cho `snapshot()` trả bản voice mới nhất, bốn câu hỗ trợ và cờ `features.voice` để tải lại trang vẫn đúng. Khi đóng Gateway, ngăn worker đang thu gửi lệnh muộn và đợi nó nhả mic. [Mẫu snapshot và sự kiện](../../code/yolohome/web/live.py)
5. Để luồng Module 3 cập nhật thẻ thiết bị khi board phản hồi. `status="sent"` chỉ diễn tả việc tiếp nhận yêu cầu. Nếu đích đã trùng trạng thái xác nhận, Gateway có thể phát lại trạng thái hiện tại ngay. Nếu lệnh mới hết hạn chờ ACK, xem lỗi trong log và giữ trạng thái thiết bị đã xác nhận trước đó. Không phát lệnh lần hai từ trình duyệt.

**Thử độc lập:** dùng Gateway giả theo mẫu test của repo, thay hàm nghe bằng hàm trả “bật quạt”. Kiểm tra đúng một yêu cầu đến `fan` với `{"on": True}`. Đổi sang “đừng bật quạt” và kiểm tra số yêu cầu bằng 0. Giả lập lỗi mic rồi thử lượt hợp lệ kế tiếp để kiểm tra khóa đã được nhả. [Các test web hiện có](../../code/tests/test_web.py)

## 6. Nối nút micro trên dashboard

1. Trong `Handler.do_POST`, thêm nhánh cho `/api/voice/listen` sau kiểm tra đăng nhập và đọc JSON. Với `WEB_DATA=gateway`, gọi `app.home.start_voice()` và trả HTTP 202 khi đã nhận lượt. Body gửi lên là `{}`. Với provider chưa hỗ trợ mic thật, trả lỗi có thông báo rõ qua cơ chế `CommandError`. [Router hiện tại](../../code/yolohome/web/server.py)
2. Trong object `api`, thêm `listenVoice: () => request("POST", "/api/voice/listen", {}),`. Sự kiện `voice` đã có trong danh sách SSE, và dashboard đã nối nó vào `ai.onVoice(voice)`. [API của frontend](../../code/web/js/api.js) · [Bộ nhận sự kiện](../../code/web/js/dashboard.js)
3. Trong `Ai.renderVoice()`, cho nút gọi `api.listenVoice()` ở chế độ gateway và `simulate("voice")` ở chế độ mock. Sửa cả điều kiện `disabled` hiện đang phụ thuộc vào `features.simulate`. Khóa nút từ lúc gửi yêu cầu tới khi nhận `sent`, `rejected` hoặc `error`. Hiện “Đang nghe” với `listening` và “Đang nhận dạng” với `transcribing`. Xử lý lỗi HTTP và đồng bộ lại qua `snapshot()` sau khi SSE kết nối lại. [Thẻ micro cần sửa](../../code/web/js/ai.js)

**Kiểm tra trong trình duyệt:** mở DevTools → Network. Một lần bấm tạo đúng một POST. Mở hai tab rồi bấm liên tiếp. Tab thứ hai phải thấy mic đang bận nếu lượt đầu còn chạy. Nói câu ngoài bộ lệnh, kiểm tra thẻ thiết bị giữ trạng thái trước đó. Chuyển sang mock và kiểm tra nút mô phỏng vẫn chạy trên máy thiếu mic.

## 7. Chạy với board thật

1. Trong `code`, chạy `& $python -m unittest discover -s tests -t .`. Kiểm tra cả test vừa bổ sung cho bộ lệnh và lượt nghe.
2. Nạp chương trình board và xác định COM theo README. Ngắt OhStem khỏi cổng COM. Trong `code/.env` đặt `WEB_DATA=gateway`, đúng `COM_PORT`, thông tin Adafruit và `WEB_PASSWORD`. Nạp thử mô hình offline theo bước 3. Khi cần tạo file lần đầu, dùng `if (!(Test-Path .env)) { Copy-Item .env.example .env }`. [Khởi động và kiểm tra phần cứng](../../README.md)
3. Chạy `& $python -m yolohome`. Mở địa chỉ mà terminal in (mặc định `http://127.0.0.1:8000`), đăng nhập. Dùng **nút tay** bật/tắt đèn và quạt một vòng. Nếu nút tay chưa điều khiển được, kiểm tra COM, nguồn và ACK theo checklist Gate 3 trước khi đánh giá giọng nói.
4. Tắt quạt bằng nút tay, đợi ít nhất 2 giây, bấm mic, nói “bật quạt”. Quan sát câu máy nghe, quạt có quay và thẻ quạt có cập nhật sau xác nhận. Lặp lại với “tắt quạt”, “bật đèn”, “tắt đèn”. Đèn RGB nhấp nháy đỏ khi có cảnh báo môi trường, nên thử màu bật/tắt khi cảnh báo đã hết. Nếu web báo 429, chờ ít nhất 2 giây trước lệnh tiếp theo cho cùng thiết bị.
5. Giữ nguyên màn hình, thử im lặng và “mở cửa”. Kiểm tra thiết bị không nhận lệnh. Thử trên tài khoản chưa tải mô hình để kiểm tra thông báo lỗi nạp offline. Giao diện cần báo lỗi voice và vẫn cho bật/tắt tay.

## 8. Thu số liệu cho báo cáo

Dùng vài lượt thử trước để chọn mic, thời gian thu và khoảng cách nói. Sau đó giữ nguyên cấu hình và đánh giá bằng lượt nói mới. Một bộ thử đề xuất gồm **3 người × 4 lệnh × 5 lần × 2 môi trường = 120 lượt**, trong phòng yên và khi có tiếng quạt. Thêm ít nhất 30 lượt gồm im lặng, hội thoại, câu phủ định, câu ghép và lệnh cửa. Để đo tác động vật lý, đặt thiết bị ở trạng thái ngược với lệnh thử trước mỗi lượt.

Mỗi lượt ghi một dòng theo mẫu sau. Điền trạng thái “hết hạn” nếu thiếu ACK, để trống thời gian ACK của lượt đó. Dùng đồng hồ đơn điệu cho các mốc trong cùng tiến trình. Nếu cần lấy mốc **nói xong** trên mic thật, quay video demo có âm thanh và thẻ trạng thái, sau đó đọc khoảng thời gian từ âm tiết cuối đến lúc UI xác nhận. Cách này đo cả thời gian cập nhật giao diện.

```text
Mã lượt | Người | Môi trường | Câu đã nói | Câu Whisper chép | Lệnh đã gửi | ACK | Tác động quan sát | Độ trễ | Ghi chú
```

- Với từng lệnh, đếm số lần khớp đúng chia số lần nói lệnh đó. Mốc đề xuất 90% tương ứng ít nhất **27/30** cho từng lệnh trong bộ thử trên.
- Với câu ngoài bộ lệnh, đếm số lần hệ thống thực sự gửi lệnh. Mục tiêu thử nghiệm đề xuất là **0/30**. Báo riêng số nhầm bật thành tắt, nhầm đèn thành quạt và số từ chối câu hợp lệ.
- Ghi tỷ lệ board xác nhận trên số lệnh cần đổi trạng thái và độ trễ trung vị. Ghi riêng thời gian thu, thời gian nhận dạng và thời gian chờ board. Nếu dùng cửa sổ 3 giây, người nói xong sớm vẫn phải chờ hết cửa sổ. Nếu độ trễ quá cao, thử kết thúc thu sau khoảng lặng rồi đánh giá lại cả câu ghép và câu phủ định trước khi dùng cho demo.
- Thử lại bốn câu trong buổi chạy 30 phút với cảm biến, Adafruit và FaceAI khi phần mặt đã sẵn sàng. Lưu phiên bản Python, Faster Whisper, sounddevice, tên model, laptop và số đo thực tế vào báo cáo nhóm. [Báo cáo dự án](../../Bao_cao_NhaThongMinh.md)
