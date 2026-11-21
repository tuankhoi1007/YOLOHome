# -*- coding: utf-8 -*-
"""Module 1 - Thu thap va hien thi moi truong.

Doc dong cam bien tu Yolo:Bit qua cong COM, gui len Adafruit IO:
nhiet-do, do-am, anh-sang. Anh sang theo thang 0-100.

Dong board co the la T:31.2,H:60,L:44
hoac JSON: {"temperature":31.2,"humidity":60,"light":44}
"""

import json
import math
import sys
import time

from yolohome import config

# Khong gui lai neu so gan nhu khong doi, de tranh vuot 30 diem/phut cua Adafruit.
MIN_GAP = 2
HEARTBEAT = 15


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _parse_json(line):
    """Board dang in JSON: temperature, humidity, light."""
    try:
        data = json.loads(line)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    found = {}
    temp = _number(data.get("temperature"))
    humid = _number(data.get("humidity"))
    light = _number(data.get("light"))
    if temp is not None:
        found["T"] = temp
    if humid is not None:
        found["H"] = humid
    # Firmware nay gui anh sang 0-100. So lon hon 100 la xung nhieu, bo qua mau do.
    if light is not None and 0 <= light <= 100:
        found["L"] = light
    if not found:
        return None
    return found


def parse_line(line):
    """Tach T, H, L tu mot dong. Tra ve None neu khong co so lieu."""
    line = line.strip()
    if not line or ":" not in line:
        return None
    if line.startswith("{") and line.endswith("}"):
        return _parse_json(line)
    found = {}
    for part in line.split(","):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        key = key.strip().upper()
        if key not in ("T", "H", "L"):
            continue
        try:
            number = float(value.strip())
        except ValueError:
            continue
        if not math.isfinite(number):
            continue
        found[key] = number
    if not found:
        return None
    return found


_light_scaled = False


def normalize_light(value):
    """OhStem khoi do sang tra 0-100. So lon hon 100 duoc coi la analog 0-4095."""
    global _light_scaled
    if value > 100:
        if not _light_scaled:
            print("Anh sang > 100, quy doi 0-4095 ve thang 0-100")
            _light_scaled = True
        value = value * 100.0 / 4095.0
    if value < 0:
        value = 0
    if value > 100:
        value = 100
    return round(value, 1)


class Reading:
    def __init__(self):
        self.temp = None
        self.humid = None
        self.light = None

    def update(self, found):
        if not found:
            return
        if "T" in found:
            self.temp = round(found["T"], 1)
        if "H" in found:
            self.humid = round(found["H"], 1)
        if "L" in found:
            self.light = normalize_light(found["L"])

    def has_value(self):
        return self.temp is not None or self.humid is not None or self.light is not None

    def summary(self):
        parts = []
        if self.temp is not None:
            parts.append("T=" + config.fmt_num(self.temp))
        if self.humid is not None:
            parts.append("H=" + config.fmt_num(self.humid))
        if self.light is not None:
            parts.append("L=" + config.fmt_num(self.light))
        return " ".join(parts)


class SensorPublisher:
    def __init__(self, client):
        self.client = client
        self.last_value = {}
        self.last_time = {}

    def publish(self, reading, force=False):
        now = time.time()
        items = (
            (config.FEED_TEMP, reading.temp, 0.3),
            (config.FEED_HUMID, reading.humid, 1.0),
            (config.FEED_LIGHT, reading.light, 2.0),
        )
        sent = []
        for feed, value, band in items:
            if value is None:
                continue
            prev = self.last_value.get(feed)
            age = now - self.last_time.get(feed, 0.0)
            changed = prev is None or abs(value - prev) >= band
            if force:
                should = True
            elif age < MIN_GAP:
                should = False
            else:
                should = changed or age >= HEARTBEAT
            if not should:
                continue
            self.client.publish(config.topic(feed), payload=config.fmt_num(value))
            self.last_value[feed] = value
            self.last_time[feed] = now
            sent.append(feed + "=" + config.fmt_num(value))
        if sent:
            print("Gui:", ", ".join(sent))
        return bool(sent)


def wait_interval(ser, next_sample):
    """Chua den luot doc thi xoa dong cu va cho mot chut. Tra ve True neu con doi."""
    if time.time() >= next_sample:
        return False
    if ser.in_waiting:
        ser.reset_input_buffer()
    time.sleep(0.05)
    return True


def _run_board(ser):
    """Mo cong CH340 de GPIO0 o muc thap thi ESP32 vao che do nap va im lang.

    Keo GPIO0 len cao, nhip chan reset, de board chay chuong trinh da luu.
    """
    ser.dtr = False
    ser.rts = True
    time.sleep(0.1)
    ser.rts = False
    time.sleep(0.8)
    boot = ser.read(4096).decode("utf-8", errors="ignore")
    if "waiting for download" in boot or "DOWNLOAD_BOOT" in boot:
        return False
    ser.reset_input_buffer()
    return True


def open_serial():
    try:
        import serial
    except ImportError:
        print("Thieu thu vien pyserial.")
        print("Cai bang lenh: python -m pip install pyserial paho-mqtt")
        sys.exit(1)
    try:
        ser = serial.Serial(config.COM_PORT, config.BAUD, timeout=1)
    except Exception as exc:
        print("Khong mo duoc", config.COM_PORT)
        print("Ngat ket noi OhStem, kiem tra dung cong COM, roi chay lai.")
        print(exc)
        sys.exit(1)
    print("Dang doc", config.COM_PORT, "toc do", config.BAUD)
    if not _run_board(ser):
        print("Board dang o che do nap, thu khoi dong lai")
        if not _run_board(ser):
            print("Rut cap USB, cam lai, ngat OhStem, roi chay lai gateway.")
    print("Cho dong dang T:31.2,H:60,L:44")
    return ser


def send_line(ser, line):
    """Ghi mot dong lenh xuong board. Tra ve True neu ghi duoc."""
    try:
        ser.write((line + "\n").encode("ascii"))
        ser.flush()
    except Exception as exc:
        print("Khong gui duoc lenh", line + ":", exc)
        return False
    print("Lenh:", line)
    return True


def send_led(ser, color):
    """Gui lenh mau den xuong board. Board can doc dong LED:RED hoac LED:GREEN."""
    if color not in ("RED", "GREEN"):
        return
    try:
        ser.write(("LED:" + color + "\n").encode("ascii"))
        ser.flush()
    except Exception as exc:
        print("Khong gui duoc lenh den:", exc)
        return
    print("Lenh den:", color)


# ---------- Module 3: dieu khien den, quat, cua (docs/PROTOCOL.md v0.2.0) ----------

# 4 mau den co dinh (D11). Dung chung voi web_mock.LIGHT_COLORS.
LIGHT_PRESETS = ("#ffffff", "#b8860b", "#9333ea", "#2563eb")
# Board bao ack trong vai tram ms. Qua 3 giay thi coi nhu lenh mat.
ACK_WAIT = 3.0
# Web: cung mot thiet bi khong nhan lenh thu hai trong 2 giay (HTTP 429).
MIN_COMMAND_GAP = 2.0

DEVICE_FEEDS = {
    "den": config.FEED_DEN,
    "quat": config.FEED_QUAT,
    "cua": config.FEED_CUA,
}
DEVICE_BY_FEED = {feed: device for device, feed in DEVICE_FEEDS.items()}
DEVICE_ACK = {"LIGHT": "den", "FAN": "quat", "DOOR": "cua"}
# Trang thai luc bat dau: board khoi dong voi den tat, quat 0, cua dong.
START_STATE = {"den": "OFF", "quat": "0", "cua": "CLOSE"}


def normalize_den(text):
    """Gia tri feed den -> 'OFF' hoac '#rrggbb' (1 trong 4 mau). Sai thi None. '0' cu = OFF."""
    value = str(text).strip().lower()
    if value in ("off", "0"):
        return "OFF"
    if not value.startswith("#"):
        value = "#" + value
    if value in LIGHT_PRESETS:
        return value
    return None


def normalize_quat(text):
    """Gia tri feed quat -> so nguyen 0-100 dang chuoi. Sai thi None."""
    number = _number(str(text).strip())
    if number is None or number < 0 or number > 100:
        return None
    return str(int(round(number)))


def normalize_cua(text):
    """Gia tri feed cua -> 'OPEN' hoac 'CLOSE'. '0' cu = CLOSE. Sai thi None."""
    value = str(text).strip().upper()
    if value == "0":
        return "CLOSE"
    if value in ("OPEN", "CLOSE"):
        return value
    return None


NORMALIZERS = {"den": normalize_den, "quat": normalize_quat, "cua": normalize_cua}


def device_line(device, value):
    """Dong gui xuong board cho gia tri da chuan hoa, vi du LIGHT:b8860b."""
    if device == "den":
        return "LIGHT:" + ("OFF" if value == "OFF" else value.lstrip("#"))
    if device == "quat":
        return "FAN:" + value
    return "DOOR:" + value


def parse_ack(line):
    """ACK:LIGHT:OFF / ACK:FAN:50 / ACK:DOOR:OPEN -> (thiet bi, gia tri chuan hoa), hoac None."""
    parts = line.strip().split(":")
    if len(parts) != 3 or parts[0].upper() != "ACK":
        return None
    device = DEVICE_ACK.get(parts[1].strip().upper())
    if device is None:
        return None
    value = NORMALIZERS[device](parts[2])
    if value is None:
        return None
    return device, value


class DeviceControl:
    """Giu trang thai da xac nhan cua den, quat, cua va luat gui lenh.

    send(line) ghi mot dong xuong board (tra ve True neu ghi duoc).
    publish(feed, value) gui len Adafruit. Ca hai duoc truyen vao de kiem thu khong can cong COM.
    listener.on_device(device, value, ok, source, reason) bao ket qua cho web.

    Luat (PROTOCOL v0.2.0): lenh bang trang thai da xac nhan thi bo qua, de feed -> USB -> ack -> feed
    khong quay vong. Co ack thi cap nhat va dua len feed neu feed khac. Het 3 giay khong ack thi
    giu nguyen, ghi loi, dua trang thai that len lai feed.
    """

    def __init__(self, send, publish, listener=None, clock=time.time):
        self.send = send
        self.publish = publish
        self.listener = listener
        self.clock = clock
        self.confirmed = dict(START_STATE)
        # Gia tri feed theo hieu biet cua gateway: de biet khi nao can dua len de feed khop thiet bi
        self.feed_value = dict(START_STATE)
        self.pending = {}
        self.last_command = {}

    def _tell(self, device, value, ok, source, reason=""):
        method = getattr(self.listener, "on_device", None)
        if method is not None:
            method(device, value, ok, source, reason)

    def _sync_feed(self, device):
        if self.feed_value[device] == self.confirmed[device]:
            return
        self.publish(DEVICE_FEEDS[device], self.confirmed[device])
        self.feed_value[device] = self.confirmed[device]

    def start(self):
        """Luc moi chay: dua trang thai ban dau len feed mot lan (3 diem)."""
        for device in DEVICE_FEEDS:
            self.publish(DEVICE_FEEDS[device], self.confirmed[device])

    def too_soon(self, device):
        last = self.last_command.get(device)
        return last is not None and self.clock() - last < MIN_COMMAND_GAP

    def from_feed(self, feed, text):
        """Gia tri vua doc tu feed dieu khien (Adafruit dashboard hoac vong lap lai cua chinh minh)."""
        device = DEVICE_BY_FEED.get(feed)
        if device is None:
            return
        value = NORMALIZERS[device](text)
        if value is None:
            print("Bo qua gia tri khong hop le cua", feed + ":", text)
            self.feed_value[device] = str(text).strip()
            self._sync_feed(device)
            return
        # Giu nguyen dang feed dang co (vd '0' cu) de lan sau so sanh dung
        self.feed_value[device] = str(text).strip()
        self.request(device, value, "Adafruit IO")

    def request(self, device, value, source):
        """Yeu cau doi trang thai. value da chuan hoa. Tra ve 'ignored', 'sent' hoac 'failed'."""
        if value == self.confirmed[device] and device not in self.pending:
            return "ignored"
        line = device_line(device, value)
        if not self.send(line):
            self._tell(device, self.confirmed[device], False, source, "Không gửi được lệnh xuống board")
            return "failed"
        now = self.clock()
        self.last_command[device] = now
        self.pending[device] = (now + ACK_WAIT, value, source)
        return "sent"

    def ack(self, device, value):
        """Board bao xong. Cua tu khoa sau 10 giay cung den day ma khong co lenh."""
        waiting = self.pending.pop(device, None)
        source = waiting[2] if waiting else "Board"
        changed = value != self.confirmed[device]
        self.confirmed[device] = value
        self._sync_feed(device)
        if changed or waiting:
            self._tell(device, value, True, source)

    def expire(self):
        """Goi moi vong: lenh qua 3 giay khong ack thi bo, dua trang thai that len feed."""
        now = self.clock()
        for device in list(self.pending):
            deadline, value, source = self.pending[device]
            if now < deadline:
                continue
            del self.pending[device]
            print("Board khong tra loi lenh", device_line(device, value), "sau", int(ACK_WAIT), "giay")
            self._sync_feed(device)
            self._tell(device, self.confirmed[device], False, source, "Thiết bị không phản hồi sau 3 giây")


def main():
    print("Module 1 - thu thap moi truong")
    print("Feed:", ", ".join(config.SENSOR_FEEDS))
    ser = open_serial()
    config.ensure_feeds(config.SENSOR_FEEDS)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Da ket noi Adafruit")
        else:
            print("Ket noi loi, ma", reason_code)

    client = config.connect_mqtt(on_connect)
    client.loop_start()
    publisher = SensorPublisher(client)
    reading = Reading()
    last_seen = time.time()
    next_sample = 0.0
    print("Moi lan doc cach nhau", config.fmt_num(config.READ_INTERVAL), "giay")
    try:
        while True:
            if wait_interval(ser, next_sample):
                continue
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                if time.time() - last_seen > 5:
                    print("5 giay roi, board khong gui gi qua USB")
                    last_seen = time.time()
                continue
            last_seen = time.time()
            print("Nhan:", line)
            found = parse_line(line)
            if found is None:
                print("Bo qua dong nay. Can dang T:31.2,H:60,L:44")
                continue
            reading.update(found)
            print("Doc:", reading.summary())
            publisher.publish(reading)
            next_sample = time.time() + config.READ_INTERVAL
    except KeyboardInterrupt:
        print("Dung.")
    finally:
        ser.close()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
