# -*- coding: utf-8 -*-
"""Doc file .env va goi Adafruit IO."""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent


def load_env(path):
    if not path.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(path)
        return
    except ImportError:
        pass
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env(ROOT / ".env")


def env(name, default=None):
    value = os.getenv(name, "")
    if value is None:
        value = ""
    value = value.strip()
    if value:
        return value
    if default is not None:
        return default
    print("Thieu", name, "trong file .env")
    sys.exit(1)


def env_float(name, default):
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print(name, "khong phai so, dung", default)
        return default


def env_int(name, default):
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(name, "khong phai so nguyen, dung", default)
        return default


def env_bool(name, default=False):
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def env_optional_float(name):
    """None neu khong khai bao, de model tu dung nguong da chon luc train."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        print(name, "khong phai so, bo qua")
        return None


def fmt_num(value):
    value = round(float(value), 1)
    if value == int(value):
        return str(int(value))
    return str(value)


AIO_USERNAME = env("AIO_USERNAME")
AIO_KEY = env("AIO_KEY")
AIO_BROKER = env("AIO_BROKER", "io.adafruit.com")
AIO_PORT = int(env("AIO_PORT", "1883"))

COM_PORT = env("COM_PORT", "COM11")
BAUD = int(env("BAUD", "115200"))
READ_INTERVAL = env_float("READ_INTERVAL", 3)

FEED_TEMP = env("FEED_TEMP", "nhiet-do")
FEED_HUMID = env("FEED_HUMID", "do-am")
FEED_LIGHT = env("FEED_LIGHT", "anh-sang")
FEED_ALERT = env("FEED_ALERT", "canh-bao")
FEED_TEMP_MAX = env("FEED_TEMP_MAX", "nguong-nhiet")
FEED_HUMID_MAX = env("FEED_HUMID_MAX", "nguong-am")
FEED_LIGHT_MIN = env("FEED_LIGHT_MIN", "nguong-sang")
# Module 3: feed dieu khien, gia tri la trang thai thiet bi da duoc board xac nhan (docs/PROTOCOL.md v0.2.0)
FEED_DEN = env("FEED_DEN", "den")
FEED_QUAT = env("FEED_QUAT", "quat")
FEED_CUA = env("FEED_CUA", "cua")

TEMP_MAX = env_float("TEMP_MAX", 32)
HUMID_MAX = env_float("HUMID_MAX", 80)
LIGHT_MIN = env_float("LIGHT_MIN", 20)

# Web (Module 5). Mat khau rong thi web_server.py tu choi chay, gateway van chay binh thuong.
WEB_PORT = int(env("WEB_PORT", "8000"))
WEB_PASSWORD = env("WEB_PASSWORD", "")
WEB_DATA = env("WEB_DATA", "mock")
# Do tre gia lap tu luc gui lenh den luc thiet bi xac nhan. Lon hon 3000 thi web bao qua thoi gian cho.
MOCK_ACK_MS = env_float("MOCK_ACK_MS", 900)

# Cua servo. P4 la chan servo trong tai lieu OhStem, khong phai P0/P14.
# Fan o P1, servo o P4 (D4 da chot tren nhanh Module 3).
SERVO_PIN = env("SERVO_PIN", "P4")
# Mo 10 giay roi tu dong, trung voi web gia lap.
DOOR_OPEN_SECONDS = env_float("DOOR_OPEN_SECONDS", 10)

# Nhan dien khuon mat. Mac dinh tat de gateway cu van chay khi chua co model va webcam.
FACE_ENABLE = env_bool("FACE_ENABLE", False)
FACE_CAMERA = env_int("FACE_CAMERA", 0)
FACE_THRESHOLD = env_optional_float("FACE_THRESHOLD")
# 3 khung on dinh (~1 giay) moi tinh la mot lan nhan, tranh mo cua vi mot khung nhieu.
FACE_STABLE_FRAMES = env_int("FACE_STABLE_FRAMES", 3)
FACE_MISS_RESET = env_float("FACE_MISS_RESET", 1.0)
FACE_INTERVAL = env_float("FACE_INTERVAL", 0.3)
FACE_MODEL_DIR = ROOT / "models" / "face"
FACE_DATASET_DIR = ROOT / "data" / "faces"
# File local de web che do live thay trang thai khi gateway.py chay rieng. Khong phai feed Adafruit.
RUNTIME_DIR = ROOT / "data" / "runtime"
FACE_STATUS_PATH = RUNTIME_DIR / "status.json"
FACE_LOG_PATH = RUNTIME_DIR / "face_log.jsonl"
DOOR_CMD_PATH = RUNTIME_DIR / "door_cmd.json"
FACE_BRIDGE = env_bool("FACE_BRIDGE", True)

SENSOR_FEEDS = (FEED_TEMP, FEED_HUMID, FEED_LIGHT)
THRESHOLD_FEEDS = (FEED_TEMP_MAX, FEED_HUMID_MAX, FEED_LIGHT_MIN)
CONTROL_FEEDS = (FEED_DEN, FEED_QUAT, FEED_CUA)
ALL_FEEDS = SENSOR_FEEDS + (FEED_ALERT,) + THRESHOLD_FEEDS + CONTROL_FEEDS


def topic(feed):
    return AIO_USERNAME + "/feeds/" + feed


def _api(method, url, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"X-AIO-Key": AIO_KEY, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:180]
        raise RuntimeError("HTTP " + str(exc.code) + " " + detail) from exc
    if not raw:
        return None
    return json.loads(raw)


def _base():
    return "https://io.adafruit.com/api/v2/" + quote(AIO_USERNAME)


def list_feeds():
    """Tap feed key dang co tren tai khoan (khong tao gi), hoac None neu khong hoi duoc."""
    try:
        found = _api("GET", _base() + "/feeds?limit=100")
    except Exception as exc:
        print("Khong kiem tra duoc danh sach feed:", exc)
        return None
    if isinstance(found, dict):
        found = found.get("feeds", [])
    keys = set()
    for item in found or []:
        if isinstance(item, dict) and item.get("key"):
            keys.add(item["key"])
    return keys


def ensure_feeds(names):
    """Tao feed con thieu. Tra ve tap feed key dang co, hoac None neu khong hoi duoc."""
    keys = list_feeds()
    if keys is None:
        return None
    limited = False
    for name in names:
        if name in keys or limited:
            continue
        try:
            _api("POST", _base() + "/feeds", {"name": name})
            keys.add(name)
            print("Da tao feed", name)
        except Exception as exc:
            if "Feed limit reached" in str(exc):
                limited = True
                print("Tai khoan da du 10 feed. Nguong lay tu file .env.")
            else:
                print("Khong tao duoc feed", name, "-", exc)
    return keys


def fetch_last(feed):
    url = _base() + "/feeds/" + quote(feed) + "/data/last"
    try:
        data = _api("GET", url)
    except RuntimeError as exc:
        text = str(exc)
        if "HTTP 404" in text or "HTTP 400" in text:
            return None
        print("Khong doc duoc", feed, exc)
        return None
    except Exception as exc:
        print("Khong doc duoc", feed, exc)
        return None
    if not isinstance(data, dict):
        return None
    try:
        return float(str(data.get("value")).strip())
    except (TypeError, ValueError):
        return None


def _epoch(item):
    """Thoi diem cua mot diem du lieu Adafruit, giay tinh tu 1970."""
    if item.get("created_epoch") is not None:
        try:
            return float(item["created_epoch"])
        except (TypeError, ValueError):
            pass
    text = str(item.get("created_at") or "")
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def fetch_history(feed, limit=50):
    """Lich su feed (moi nhat truoc): list (epoch, so). Chi doc, khong ton diem du lieu."""
    url = _base() + "/feeds/" + quote(feed) + "/data?limit=" + str(int(limit))
    try:
        data = _api("GET", url)
    except Exception as exc:
        print("Khong doc duoc lich su", feed, exc)
        return []
    points = []
    for item in data or []:
        if not isinstance(item, dict):
            continue
        at = _epoch(item)
        try:
            value = float(str(item.get("value")).strip())
        except (TypeError, ValueError):
            continue
        if at is not None:
            points.append((at, value))
    return points


def connect_mqtt(on_connect, on_message=None):
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("Thieu thu vien paho-mqtt.")
        print("Cai bang lenh: python -m pip install paho-mqtt pyserial")
        sys.exit(1)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(AIO_USERNAME, AIO_KEY)
    client.on_connect = on_connect
    if on_message is not None:
        client.on_message = on_message

    def on_disconnect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print("Mat ket noi Adafruit, ma", reason_code, "- dang thu lai")

    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    try:
        client.connect(AIO_BROKER, AIO_PORT, 60)
    except Exception as exc:
        print("Khong ket noi duoc Adafruit:", exc)
        sys.exit(1)
    return client
