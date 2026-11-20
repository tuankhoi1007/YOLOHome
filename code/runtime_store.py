# -*- coding: utf-8 -*-
"""File nho de gateway.py va web (WEB_DATA=live) trao doi trang thai cua va khuon mat.

Khong phai feed Adafruit: tai khoan mien phi chi co 10 feed, va nhat ky mat o lai tren laptop
cho den khi D5 chot cho luu lau. Thu muc data/ bi gitignore vi co the kem anh mat.
"""

import json
import os
import threading
import time

_LOCK = threading.Lock()


def write_json(path, payload):
    """Ghi tron ven: doc file tam roi doi ten, de tien trinh kia khong doc do dang."""
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    tmp = path.with_suffix(path.suffix + ".tmp")
    with _LOCK:
        tmp.write_bytes(raw)
        os.replace(tmp, path)


def read_json(path):
    if path is None or not path.is_file():
        return None
    try:
        with _LOCK:
            raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def append_jsonl(path, payload):
    """Moi lan nhan dien mot dong JSON. Day la nhat ky local, khong gui Adafruit."""
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    with _LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)


def write_door_command(path, locked, source):
    """Web che do live nho gateway.py gui lenh cua. id tang de khong gui lai lenh cu."""
    current = read_json(path) or {}
    try:
        last = int(current.get("id") or 0)
    except (TypeError, ValueError):
        last = 0
    payload = {
        "id": last + 1,
        "locked": bool(locked),
        "source": source,
        "at": time.time(),
    }
    write_json(path, payload)
    return payload
