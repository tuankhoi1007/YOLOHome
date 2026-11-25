"""Thử nhận dạng tiếng Việt trên terminal, trước khi dùng nút micro trên web.

Chạy trong thư mục code:  python -X utf8 -m yolohome.voice.probe --offline
Xem docs/plans/phase-7-giong-noi.md (bước 2–4).
"""

import argparse
import sys
from pathlib import Path

from yolohome.voice import match_command
from yolohome.voice.listen import (
    HOTWORDS,
    QUIET_PEAK,
    ModelError,
    RecordingError,
    listen_once,
    load_model,
    missing_model_file,
    model_label,
    parse_mic,
    transcribe,
    wav_peak,
)


def show_status(status, detail):
    if status == "listening":
        print(f"Đang nghe qua {detail}.", flush=True)
    elif status == "transcribing":
        print("Đang nhận dạng.", flush=True)


def report(result):
    print(f"Âm thanh: {result.duration:.2f} s | Nhận dạng: {result.seconds:.2f} s")
    if result.peak is not None:
        note = " (quá nhỏ: tăng Input volume của mic hoặc nói gần, to hơn)" if result.peak < QUIET_PEAK else ""
        print(f"Mức âm lớn nhất: {result.peak * 100:.0f}%{note}")
    if result.after_vad is None:
        print("VAD đã tắt.")
    else:
        print(f"VAD giữ lại {result.after_vad:.2f} s.")
    print("Máy nghe được:", repr(result.text))
    command = match_command(result.text)
    print("Lệnh dự kiến:", command if command is not None else "Từ chối")


def main():
    parser = argparse.ArgumentParser(description="Thử nhận dạng tiếng Việt với Faster Whisper.")
    parser.add_argument("--device", help="Số thứ tự (hoặc một phần tên) mic từ python -m sounddevice")
    parser.add_argument("--seconds", type=int, default=3, help="Số giây thu mỗi lượt (mặc định 3)")
    parser.add_argument("--no-vad", action="store_true", help="Tắt bộ lọc tiếng nói để chẩn đoán")
    parser.add_argument("--hint-devices", action="store_true", help="Gợi ý hai từ đèn và quạt cho Whisper")
    files = parser.add_mutually_exclusive_group()
    files.add_argument("--wav", type=Path, help="Ghi đè file WAV với lượt thu mới nhất")
    files.add_argument("--input-wav", type=Path, help="Nhận dạng một bản thu có sẵn")
    models = parser.add_mutually_exclusive_group()
    models.add_argument("--model-dir", type=Path, help="Thư mục mô hình CTranslate2 đã chuyển đổi")
    models.add_argument("--model", help="Tên mô hình Whisper, ví dụ small (mặc định: VOICE_MODEL, giống web)")
    parser.add_argument("--offline", action="store_true", help="Nạp mô hình từ cache cục bộ")
    args = parser.parse_args()
    if args.seconds < 1:
        parser.error("--seconds phải là số nguyên dương")
    if args.input_wav is not None and not args.input_wav.is_file():
        parser.error(f"Không tìm thấy file WAV: {args.input_wav}")
    if args.model_dir is not None:
        missing = missing_model_file(args.model_dir)
        if missing is not None:
            parser.error(f"Thiếu {missing} trong {args.model_dir}. Kiểm tra thư mục mô hình CTranslate2.")

    from yolohome import config

    if args.model_dir is not None:
        source = str(args.model_dir)
    else:
        source = args.model or config.VOICE_MODEL
    print(f"Đang nạp {model_label(source)}.", flush=True)
    try:
        model = load_model(source, offline=args.offline)
    except ModelError as exc:
        parser.exit(1, str(exc) + "\n")

    vad_filter = not args.no_vad
    hotwords = HOTWORDS if args.hint_devices else None
    if args.input_wav is not None:
        result = transcribe(model, str(args.input_wav), vad_filter=vad_filter, hotwords=hotwords)
        report(result._replace(peak=wav_peak(args.input_wav)))
        return

    device = parse_mic(args.device)
    while input("Enter để nghe, q để thoát: ").strip().casefold() != "q":
        try:
            result = listen_once(
                model, device, args.seconds, args.wav,
                vad_filter=vad_filter, hotwords=hotwords, on_status=show_status,
            )
        except (RecordingError, ModelError) as exc:
            print(exc, file=sys.stderr)
        else:
            if args.wav is not None:
                print("Đã lưu âm thanh:", args.wav)
            report(result)


if __name__ == "__main__":
    main()
