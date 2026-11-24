"""Bộ lệnh giọng nói dùng chung cho probe và dashboard."""

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
