# -*- coding: utf-8 -*-
"""Doc file .env va goi Adafruit IO."""

import json
import os
import sys
import urllib.error
import urllib.request
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

TEMP_MAX = env_float("TEMP_MAX", 32)
HUMID_MAX = env_float("HUMID_MAX", 80)
LIGHT_MIN = env_float("LIGHT_MIN", 20)

SENSOR_FEEDS = (FEED_TEMP, FEED_HUMID, FEED_LIGHT)
THRESHOLD_FEEDS = (FEED_TEMP_MAX, FEED_HUMID_MAX, FEED_LIGHT_MIN)
ALL_FEEDS = SENSOR_FEEDS + (FEED_ALERT,) + THRESHOLD_FEEDS


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


def ensure_feeds(names):
    """Tao feed con thieu. Tra ve tap feed key dang co, hoac None neu khong hoi duoc."""
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
