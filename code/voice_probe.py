import argparse
import io
import sys
import wave
from pathlib import Path
from time import perf_counter

from yolohome.voice import match_command


class RecordingError(RuntimeError):
    pass


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
    print(f"Âm thanh: {info.duration:.2f} s | Nhận dạng: {perf_counter() - started:.2f} s")
    if vad_filter:
        print(f"VAD giữ lại {info.duration_after_vad:.2f} s.")
    else:
        print("VAD đã tắt.")
    return text


def listen_once(model, device=None, seconds=3, wav_path=None, *, vad_filter=True, hotwords=None):
    import sounddevice as sd

    try:
        info = sd.query_devices(device, "input")
        rate = int(info["default_samplerate"])
        with sd.RawInputStream(device=device, samplerate=rate, channels=1, dtype="int16") as mic:
            print(f"Đang nghe qua {info['name']} ({seconds} s).", flush=True)
            samples, overflow = mic.read(rate * seconds)
    except (sd.PortAudioError, ValueError) as exc:
        raise RecordingError(f"Không thu được từ mic. Kiểm tra thiết bị đầu vào: {exc}") from exc
    if overflow:
        raise RecordingError("Mic mất mẫu. Nhấn Enter để thử lại.")

    audio = io.BytesIO()
    with wave.open(audio, "wb") as recording:
        recording.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        recording.writeframes(bytes(samples))
    if wav_path is not None:
        wav_path.write_bytes(audio.getbuffer())
        print("Đã lưu âm thanh:", wav_path)
    audio.seek(0)
    print("Đang nhận dạng.", flush=True)
    return transcribe(model, audio, vad_filter=vad_filter, hotwords=hotwords)


def report_command(text):
    print("Máy nghe được:", repr(text))
    command = match_command(text)
    print("Lệnh dự kiến:", command if command is not None else "Từ chối")


def main():
    parser = argparse.ArgumentParser(description="Thử nhận dạng tiếng Việt với Faster Whisper.")
    parser.add_argument("--device", type=int, help="Số thứ tự mic từ python -m sounddevice")
    parser.add_argument("--seconds", type=int, default=3, help="Số giây thu mỗi lượt (mặc định 3)")
    parser.add_argument("--no-vad", action="store_true", help="Tắt bộ lọc tiếng nói để chẩn đoán")
    parser.add_argument("--hint-devices", action="store_true", help="Gợi ý hai từ đèn và quạt cho Whisper")
    files = parser.add_mutually_exclusive_group()
    files.add_argument("--wav", type=Path, help="Ghi đè file WAV với lượt thu mới nhất")
    files.add_argument("--input-wav", type=Path, help="Nhận dạng một bản thu có sẵn")
    parser.add_argument("--model-dir", type=Path, help="Thư mục mô hình CTranslate2 đã chuyển đổi")
    parser.add_argument("--offline", action="store_true", help="Nạp mô hình từ cache cục bộ")
    args = parser.parse_args()
    if args.seconds < 1:
        parser.error("--seconds phải là số nguyên dương")
    if args.input_wav is not None and not args.input_wav.is_file():
        parser.error(f"Không tìm thấy file WAV: {args.input_wav}")
    if args.model_dir is not None:
        for name in ("model.bin", "config.json", "tokenizer.json"):
            if not (args.model_dir / name).is_file():
                parser.error(f"Thiếu {name} trong {args.model_dir}. Kiểm tra thư mục mô hình CTranslate2.")

    from faster_whisper import WhisperModel
    from huggingface_hub.errors import LocalEntryNotFoundError

    model_source = str(args.model_dir) if args.model_dir is not None else "small"
    model_name = args.model_dir.name if args.model_dir is not None else "Whisper small"
    print(f"Đang nạp {model_name}.", flush=True)
    try:
        model = WhisperModel(
            model_source, device="cpu", compute_type="int8",
            local_files_only=args.offline or args.model_dir is not None,
        )
    except LocalEntryNotFoundError:
        parser.exit(1, "Chưa có mô hình trong cache. Hãy kết nối Internet và chạy lại probe "
                    "bỏ cờ --offline một lần.\n")

    vad_filter = not args.no_vad
    hotwords = "đèn, quạt" if args.hint_devices else None
    if args.input_wav is not None:
        text = transcribe(model, str(args.input_wav), vad_filter=vad_filter, hotwords=hotwords)
        report_command(text)
        return

    while input("Enter để nghe, q để thoát: ").strip().casefold() != "q":
        try:
            text = listen_once(
                model, args.device, args.seconds, args.wav,
                vad_filter=vad_filter, hotwords=hotwords,
            )
        except RecordingError as exc:
            print(exc, file=sys.stderr)
        else:
            report_command(text)


if __name__ == "__main__":
    main()
