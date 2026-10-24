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

import config

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
