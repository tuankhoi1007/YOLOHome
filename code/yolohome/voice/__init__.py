"""Bộ lệnh giọng nói dùng chung cho probe, Gateway và dashboard (Phase 7).

File này không import thư viện âm thanh: chế độ mock và test chạy được trên máy chưa cài
requirements-voice.txt. Phần thu mic và Whisper nằm ở yolohome.voice.listen.
"""

import unicodedata


VOICE_COMMANDS = (
    ("bật đèn", "light", True),
    ("tắt đèn", "light", False),
    ("bật quạt", "fan", True),
    ("tắt quạt", "fan", False),
)


def match_command(text):
    normalized = unicodedata.normalize("NFC", text).casefold()
    phrase = " ".join(normalized.split()).rstrip(".!?").rstrip()
    for command, device, on in VOICE_COMMANDS:
        if phrase == command:
            return device, {"on": on}
    return None
