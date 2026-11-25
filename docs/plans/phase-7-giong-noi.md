# Phase 7 · Từ micro laptop đến đèn và quạt Yolo:Bit

Sau khi hoàn thành hướng dẫn, bạn có thể bấm biểu tượng micro trên dashboard, đợi chữ **Đang nghe**, nói **“bật quạt”**, rồi nhìn thấy tốc độ quạt đã được board xác nhận. Ba lệnh còn lại là **“tắt quạt”, “bật đèn”, “tắt đèn”**. Mỗi lần bấm tương ứng với một lượt nói. Máy chuẩn để thử là Windows, Intel i5-1240P, RAM 16 GB và mic tích hợp.

**Bắt đầu ở bước 1 nếu chưa có kit.** Probe và bộ khớp lệnh ở bước 1–4 đã có trong repo. Bước 5–6 (Gateway và nút micro trên dashboard) đã tích hợp, phần đó mô tả cách hoạt động và cấu hình. Bước 7–8 dùng kit để đánh giá tác động thật.

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
& $python -m pip install -r requirements-voice.txt
& $python -c "import faster_whisper, sounddevice; print('Import OK')"
& $python -m sounddevice
```

**Kiểm tra:** cần thấy `Import OK` và một thiết bị như *Microphone Array* có ít nhất một kênh vào. Mở **Settings → System → Sound → Input**, chọn mic laptop, nói thử và nhìn thanh âm lượng. Trong **Privacy & security → Microphone**, cho phép ứng dụng desktop truy cập mic. Trong bài này Python là ứng dụng mở mic.

Giới hạn `av<19` giữ API đọc WAV tương thích với Faster Whisper 1.2.1. Nếu probe báo lỗi `metadata_errors`, chạy lại lệnh cài ở trên. Các gói giọng nói nằm riêng trong `requirements-voice.txt` để máy chỉ dùng cảm biến và nút tay không phải cài chúng. [Lỗi tương thích đã ghi nhận ở Faster Whisper](https://github.com/SYSTRAN/faster-whisper/issues/1589)

Nếu pip báo thiếu wheel hoặc import DLL lỗi, ghi lại phiên bản Python và tên gói lỗi. Trên máy đang dùng Python 3.14, có thể thử CPython 3.11 x64 trong môi trường riêng: sau khi cài 3.11, chạy `py -3.11 -m venv .venv-voice`, đặt lại `$python = (Resolve-Path .\.venv-voice\Scripts\python.exe).Path` rồi lặp các lệnh cài và kiểm tra phía trên. Khi mở terminal mới, đặt lại `$python` tới môi trường đã chạy thành công. [Python cho Windows](https://www.python.org/downloads/windows/)

## 2. Tải mô hình tiếng Việt một lần

Chạy từ cùng cửa sổ PowerShell có Internet. Faster Whisper tải mô hình vào cache Hugging Face của tài khoản Windows. Sau khi thấy `Model OK`, dùng `--offline` để probe nạp từ cache.

```powershell
& $python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8'); print('Model OK')"
```

Nếu laptop khác sẽ dùng để demo, chạy lệnh trên máy đó trước buổi demo để tạo cache cho đúng tài khoản Windows.

### Dùng PhoWhisper-small của VinAI

PhoWhisper-small là Whisper được VinAI train thêm trên tiếng Việt, nghe lệnh tiếng Việt tốt hơn Whisper `small` gốc. **Web và probe tự dùng PhoWhisper** khi thư mục `%LOCALAPPDATA%\YOLOHome\models\phowhisper-small-ct2` có `model.bin` và `VOICE_MODEL` trong `.env` để trống. Chưa có thư mục này thì dùng Whisper `small`. [Mô hình gốc của VinAI](https://huggingface.co/vinai/PhoWhisper-small) · [Cách chuyển mô hình cho Faster Whisper](https://github.com/SYSTRAN/faster-whisper#model-conversion)

Chuyển đổi một lần, cần Internet. Torch và transformers chỉ dùng cho bước này, nên cài vào một venv tạm có đường dẫn ngắn: Windows chưa bật Long Path sẽ cài torch lỗi nếu đường dẫn dài. Xóa venv tạm sau khi xong.

```powershell
$cv = Join-Path $env:LOCALAPPDATA "YOLOHome\cv"
py -3.12 -m venv $cv
& "$cv\Scripts\python.exe" -m pip install torch --index-url https://download.pytorch.org/whl/cpu
& "$cv\Scripts\python.exe" -m pip install transformers "ctranslate2==4.9.1"
$pho = Join-Path $env:LOCALAPPDATA "YOLOHome\models\phowhisper-small-ct2"
& "$cv\Scripts\ct2-transformers-converter.exe" --model vinai/PhoWhisper-small --output_dir $pho --quantization int8 --copy_files tokenizer.json preprocessor_config.json
Remove-Item -Recurse -Force $cv
```

Thư mục kết quả khoảng 250 MB, gồm `model.bin`, `config.json`, `tokenizer.json`, `preprocessor_config.json` và `vocabulary.json`. Thử với probe:

```powershell
& $python -X utf8 -m yolohome.voice.probe --offline --model-dir $pho
```

Để so sánh trên một file WAV, dùng cùng đường dẫn trong cả hai lệnh. `--model small` ép dùng Whisper gốc.

```powershell
$wav = Join-Path $env:TEMP "yolohome-bat-den-test.wav"
& $python -X utf8 -m yolohome.voice.probe --offline --model small --input-wav $wav
& $python -X utf8 -m yolohome.voice.probe --offline --model-dir $pho --input-wav $wav
```

Trên laptop khác, sao chép cả thư mục `phowhisper-small-ct2` rồi đặt `$pho` trỏ đến thư mục đó. Probe dùng trực tiếp bản CTranslate2 và các thư viện ở bước 1.

## 3. Nghe một câu thật trước khi viết API

Probe thu **3 giây** mỗi lượt, giữ âm thanh trong RAM và giải mã tiếng Việt sau khi thu. Faster Whisper lọc đoạn thiếu tiếng nói trước khi chép lời. Chạy lệnh từ thư mục `code`. [Mã probe](../../code/yolohome/voice/probe.py) · [Thu mic và Whisper](../../code/yolohome/voice/listen.py)

```powershell
& $python -X utf8 -m yolohome.voice.probe --offline
```

Nhấn Enter, đợi **“Đang nghe”** rồi nói **“bật đèn”**. Probe in tên mic, chuyển sang **“Đang nhận dạng”** khi thu xong, rồi in câu Whisper chép, thời gian xử lý và lệnh dự kiến. Nếu mic mất mẫu hoặc mở mic thất bại, probe báo lỗi và giữ mô hình trong bộ nhớ để bạn thử lượt tiếp theo. Nếu chạy offline mà thiếu mô hình, kết nối mạng và thực hiện lại bước 2.

### Khoanh vùng lỗi bằng cùng một file WAV

Chọn số mic bằng `& $python -m sounddevice`. Các lệnh dưới dùng mic số 2 làm ví dụ. Thu đúng một lượt, gõ `q` rồi nghe lại. Tùy chọn `--wav` ghi đè file sau mỗi lượt.

```powershell
$wav = Join-Path $env:TEMP "yolohome-voice-probe.wav"
& $python -X utf8 -m yolohome.voice.probe --offline --device 2 --seconds 3 --wav $wav
Invoke-Item $wav
& $python -X utf8 -m yolohome.voice.probe --offline --input-wav $wav
& $python -X utf8 -m yolohome.voice.probe --offline --input-wav $wav --no-vad
```

- Nếu WAV thiếu tiếng đầu hoặc tiếng cuối, kiểm tra mic đã chọn và thử thu với `--seconds 4`.
- Nếu WAV rõ nhưng VAD giữ lại `0.00 s`, xem câu chép khi thêm `--no-vad`. Nếu tắt VAD giúp nghe đúng, thử thêm im lặng, tiếng quạt và câu phủ định trước khi chọn cấu hình.
- Nếu cả hai cấu hình đều chép sai dù WAV rõ, ghi câu sai và thời gian nhận dạng. Thử thêm giọng của một thành viên khác để xem lỗi có lặp lại.

Nếu Whisper nghe sai tên thiết bị, thử cùng file WAV với gợi ý từ vựng. Tùy chọn `--hint-devices` gợi ý hai từ **đèn** và **quạt** cho Whisper.

```powershell
& $python -X utf8 -m yolohome.voice.probe --offline --input-wav $wav --hint-devices
& $python -X utf8 -m yolohome.voice.probe --offline --hint-devices
```

Trên một bản WAV của nhóm, tùy chọn này đổi kết quả từ “Bật đen” thành “bật đèn”. Lặp lại bài thử ở bước 4 với cả hai cấu hình để xem gợi ý có giúp trên các câu khác hay khiến một câu phủ định bị chép thành lệnh hợp lệ.

## 4. Kiểm tra bốn lệnh trước khi nối Gateway

`match_command()` nhận đúng bốn câu sau khi chuẩn hóa chữ hoa/thường, dấu câu cuối câu và khoảng trắng. Dòng **“Lệnh dự kiến”** trong probe cho thấy thiết bị và giá trị mà Gateway sẽ nhận khi tích hợp. [Bộ khớp lệnh](../../code/yolohome/voice/__init__.py)

1. Chạy probe với cấu hình muốn dùng. Mỗi lượt nói một trong bốn câu **“bật đèn”**, **“tắt đèn”**, **“bật quạt”** hoặc **“tắt quạt”**. So sánh câu đã nói, câu Whisper chép và lệnh dự kiến. Ví dụ, “bật đèn” phải cho `('light', {'on': True})`.
2. Thử **im lặng**, **“đừng bật đèn”**, **“đừng tắt quạt”**, **“bật đèn rồi tắt quạt”** và **“mở cửa”**. Kỳ vọng mỗi lượt in `Lệnh dự kiến: Từ chối`. Nếu Whisper bỏ sót “đừng” và probe in lệnh bật/tắt, ghi nhận đây là lỗi kích hoạt và tiếp tục chẩn đoán ở bước 3.
3. Lặp lại với tiếng quạt và một giọng khác. Dùng kết quả bài thử nhỏ để quyết định cấu hình đem tích hợp. Bộ đánh giá cuối nằm ở bước 8.

## 5. Gateway nghe mic (đã tích hợp)

Khi chạy web với `WEB_DATA=gateway`, `GatewayHome` tạo `VoiceEngine` theo `.env` và nạp mô hình ở luồng nền ngay lúc mở web, nên lần bấm đầu không phải chờ. Terminal in `Giong noi: san sang (phowhisper-small-ct2)` (hoặc `Whisper small`) khi nạp xong, hoặc lý do chưa dùng được (thiếu thư viện, chưa có mô hình trong cache). Web luôn nạp với `local_files_only=True`, nên hãy tải mô hình trước theo bước 2. [GatewayHome](../../code/yolohome/web/gateway.py)

Các khóa trong `code/.env` (mẫu ở `.env.example`):

| Khóa | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `VOICE_ENABLE` | `1` | `0` để tắt mic; nút đèn/quạt vẫn dùng được |
| `VOICE_MODEL` | trống | Trống = PhoWhisper-small nếu đã chuyển đổi ở bước 2, chưa có thì Whisper `small`. Hoặc đặt `small` / đường dẫn thư mục CTranslate2 khác |
| `VOICE_MIC` | trống | Trống = mic mặc định; số = thứ tự trong `python -m sounddevice` |
| `VOICE_SECONDS` | `3` | Số giây thu mỗi lượt |
| `VOICE_VAD` | `1` | `0` tắt bộ lọc tiếng nói (chỉ để chẩn đoán) |
| `VOICE_HINTS` | `0` | `1` gợi ý hai từ “đèn”, “quạt” cho Whisper (như `--hint-devices`) |

Mỗi lần bấm là một lượt. `start_voice()` lấy khóa mic bằng `acquire(blocking=False)`: đang có lượt khác thì trả 409 “Micro đang bận”. Luồng nghe thu âm và chạy Whisper ngoài khóa trạng thái của web, rồi gọi `match_command(text)`:

- Câu khớp một trong bốn lệnh: gọi **một lần** `command(device, body, source="Giọng nói")`, giống nút trên web. Đèn bật lại màu đã chọn, quạt bật lại tốc độ đã chọn. Lượt kết thúc với `sent`.
- Câu ngoài bộ lệnh (im lặng, “đừng bật đèn”, câu ghép, “mở cửa”…): `rejected`, không gửi gì.
- Mic hoặc mô hình lỗi, hoặc `command()` từ chối (429 bấm quá nhanh, 503 mất board): `error` kèm lý do. Khóa mic luôn được nhả, lượt sau thử lại được.

Sự kiện `voice` gửi lên trình duyệt có `status` (`listening`, `transcribing`, `sent`, `rejected`, `error`), `text`, `message` và `at`. Nhật ký ghi một dòng loại **Giọng nói** cho mỗi lượt đã kết thúc. `sent` chỉ có nghĩa là Gateway đã nhận lệnh. Thẻ thiết bị đổi khi board gửi ACK, theo đúng luồng Module 3. Khi tắt web, lượt đang thu không gửi lệnh muộn.

**Test tự động:** `code/tests/test_voice.py` thay mic và Whisper bằng `FakeEngine`, nên chạy được trên máy chưa cài `requirements-voice.txt`. [Test giọng nói](../../code/tests/test_voice.py)

## 6. Nút micro trên dashboard (đã tích hợp)

Nút micro gọi `POST /api/voice/listen` (trả 202). Từ lúc bấm đến khi nhận `sent`, `rejected` hoặc `error`, nút bị khóa và thẻ hiện “Đang nghe…” rồi “Đang nhận dạng…”. Các tab khác đang mở cũng thấy micro bận. Câu máy nghe được và kết quả hiện dưới nút; `rejected`/`error` hiện thêm thông báo. Nếu mô hình chưa nạp được, thẻ ghi lý do và chấm trạng thái chuyển xám. [Thẻ micro](../../code/web/js/ai.js)

Với `WEB_DATA=mock`, nút micro đi qua đúng các bước như trên nhưng không mở mic: mỗi lượt lấy lần lượt một câu trong bộ lệnh. Dùng chế độ này để thử giao diện trên máy không có mic.

**Kiểm tra trong trình duyệt:** mở DevTools → Network. Một lần bấm tạo đúng một POST. Mở hai tab rồi bấm liên tiếp. Tab thứ hai phải thấy mic đang bận nếu lượt đầu còn chạy. Nói câu ngoài bộ lệnh, kiểm tra thẻ thiết bị giữ trạng thái trước đó.

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
