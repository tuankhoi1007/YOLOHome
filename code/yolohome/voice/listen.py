"""Thu mic laptop và chép lời tiếng Việt bằng Faster Whisper (Phase 7).

Thư viện faster_whisper và sounddevice chỉ được import bên trong hàm: máy chưa cài
requirements-voice.txt vẫn chạy được web, chỉ có nút micro báo lỗi rõ ràng.

Dùng chung cho probe (python -m yolohome.voice.probe) và Gateway trên web (yolohome.web.gateway).
"""

import io
import threading
import wave
from collections import namedtuple
from pathlib import Path
from time import perf_counter

MODEL_FILES = ("model.bin", "config.json", "tokenizer.json")
# Gợi ý từ vựng cho Whisper khi bật VOICE_HINTS (probe: --hint-devices)
HOTWORDS = "đèn, quạt"
INSTALL_HINT = "Cài thư viện giọng nói: python -m pip install -r requirements-voice.txt"
CACHE_HINT = (
    "Chưa có mô hình {name} trong cache. Kết nối Internet và tải một lần theo bước 2 "
    "trong docs/plans/phase-7-giong-noi.md."
)

# text: câu Whisper chép; duration / after_vad: giây âm thanh trước và sau lọc VAD
# (after_vad là None khi tắt VAD); seconds: thời gian nhận dạng;
# peak: mức âm lớn nhất của bản thu (0..1), None khi không đo
Transcript = namedtuple("Transcript", "text duration after_vad seconds peak", defaults=(None,))
# Đỉnh dưới mức này (khoảng -16 dBFS) thì giọng quá nhỏ, Whisper dễ nghe sai
QUIET_PEAK = 0.15


class RecordingError(RuntimeError):
    """Mic không mở được hoặc mất mẫu. Lượt sau vẫn thử lại được."""


class ModelError(RuntimeError):
    """Thiếu thư viện hoặc mô hình. Nút tay trên web vẫn dùng được."""


def model_label(source):
    path = Path(str(source))
    if path.is_dir():
        return path.name
    return "Whisper " + str(source)


def missing_model_file(folder):
    """Tên file đầu tiên còn thiếu trong thư mục mô hình CTranslate2, hoặc None nếu đủ."""
    for name in MODEL_FILES:
        if not (Path(folder) / name).is_file():
            return name
    return None


def load_model(source, offline=True):
    """Nạp Whisper trên CPU (int8). source là tên mô hình (small) hoặc thư mục CTranslate2."""
    path = Path(str(source))
    is_dir = path.is_dir()
    if is_dir:
        missing = missing_model_file(path)
        if missing is not None:
            raise ModelError("Thiếu " + missing + " trong " + str(path) + ". Kiểm tra thư mục mô hình CTranslate2.")
    elif any(sep in str(source) for sep in ("/", "\\")):
        raise ModelError("Không tìm thấy thư mục mô hình " + str(source) + ". Kiểm tra VOICE_MODEL trong .env.")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ModelError(INSTALL_HINT) from exc
    try:
        return WhisperModel(
            str(path) if is_dir else str(source),
            device="cpu",
            compute_type="int8",
            local_files_only=offline or is_dir,
        )
    except Exception as exc:
        try:
            from huggingface_hub.errors import LocalEntryNotFoundError
        except ImportError:
            LocalEntryNotFoundError = ()
        if LocalEntryNotFoundError and isinstance(exc, LocalEntryNotFoundError):
            raise ModelError(CACHE_HINT.format(name=model_label(source))) from exc
        raise ModelError("Không nạp được mô hình " + model_label(source) + ": " + str(exc)) from exc


def parse_mic(raw):
    """VOICE_MIC / --device: trống = mic mặc định, số = thứ tự trong python -m sounddevice, chữ = một phần tên mic."""
    raw = (raw or "").strip() if isinstance(raw, str) else raw
    if raw in (None, ""):
        return None
    if isinstance(raw, int):
        return raw
    if raw.isdigit():
        return int(raw)
    return raw


def peak_level(pcm16):
    """Mức âm lớn nhất (0..1) của dữ liệu PCM 16 bit mono."""
    import numpy as np

    samples = np.frombuffer(bytes(pcm16), dtype=np.int16)
    if samples.size == 0:
        return 0.0
    return float(np.abs(samples.astype(np.int32)).max()) / 32768.0


def wav_peak(path):
    with wave.open(str(path), "rb") as recording:
        if recording.getsampwidth() != 2:
            return None
        frames = recording.readframes(recording.getnframes())
    return peak_level(frames)


def transcribe(model, audio, *, vad_filter=True, hotwords=None):
    started = perf_counter()
    segments, info = model.transcribe(
        audio,
        language="vi",
        vad_filter=vad_filter,
        condition_on_previous_text=False,
        hotwords=hotwords,
    )
    text = " ".join(segment.text.strip() for segment in segments).strip()
    after_vad = info.duration_after_vad if vad_filter else None
    return Transcript(text, info.duration, after_vad, perf_counter() - started)


def record(device=None, seconds=3, on_status=None):
    """Thu một lượt vào RAM, trả về (BytesIO chứa WAV mono 16 bit, mức âm lớn nhất 0..1)."""
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise ModelError(INSTALL_HINT) from exc

    try:
        info = sd.query_devices(device, "input")
        rate = int(info["default_samplerate"])
        with sd.RawInputStream(device=device, samplerate=rate, channels=1, dtype="int16") as mic:
            if on_status is not None:
                on_status("listening", info["name"])
            samples, overflow = mic.read(rate * seconds)
    except (sd.PortAudioError, ValueError) as exc:
        raise RecordingError("Không thu được từ mic. Kiểm tra thiết bị đầu vào: " + str(exc)) from exc
    if overflow:
        raise RecordingError("Mic mất mẫu. Bấm micro để thử lại.")

    audio = io.BytesIO()
    with wave.open(audio, "wb") as recording:
        recording.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        recording.writeframes(bytes(samples))
    audio.seek(0)
    return audio, peak_level(samples)


def listen_once(model, device=None, seconds=3, wav_path=None, *, vad_filter=True, hotwords=None, on_status=None):
    """Thu rồi chép lời một lượt. on_status(status, detail) nhận 'listening' và 'transcribing'."""
    audio, peak = record(device, seconds, on_status)
    if wav_path is not None:
        Path(wav_path).write_bytes(audio.getbuffer())
    if on_status is not None:
        on_status("transcribing", "")
    return transcribe(model, audio, vad_filter=vad_filter, hotwords=hotwords)._replace(peak=peak)


class VoiceEngine:
    """Giữ mô hình đã nạp và cấu hình mic cho các lượt nghe trên web.

    load() nạp mô hình một lần (an toàn khi gọi từ nhiều luồng); lỗi thì lần sau thử lại.
    listen(on_status) thu một lượt và trả về Transcript.
    """

    def __init__(self, source="small", device=None, seconds=3, vad_filter=True, hotwords=None, loader=load_model):
        self.source = source
        self.label = model_label(source)
        self.device = device
        self.seconds = seconds
        self.vad_filter = vad_filter
        self.hotwords = hotwords
        self.loader = loader
        self.model = None
        self.error = None
        self._load_lock = threading.Lock()

    @property
    def ready(self):
        return self.model is not None

    def load(self):
        with self._load_lock:
            if self.model is None:
                try:
                    import sounddevice  # noqa: F401  (báo thiếu thư viện ngay lúc nạp, không đợi lượt nghe)
                except ImportError as exc:
                    self.error = INSTALL_HINT
                    raise ModelError(INSTALL_HINT) from exc
                try:
                    self.model = self.loader(self.source)
                except ModelError as exc:
                    self.error = str(exc)
                    raise
                self.error = None
            return self.model

    def listen(self, on_status=None):
        model = self.load()
        return listen_once(
            model,
            self.device,
            self.seconds,
            vad_filter=self.vad_filter,
            hotwords=self.hotwords,
            on_status=on_status,
        )
