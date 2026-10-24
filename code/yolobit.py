# -*- coding: utf-8 -*-
"""Code chay tren Yolo:Bit. Dan vao OhStem App, che do Python, roi bam Chay.

Khong chay file nay bang python tren laptop.
Laptop chay gateway.py sau khi da ngat ket noi OhStem.

Cam bien:
  DHT20 vao cong I2C
  Cam bien anh sang vao cong P0

Moi 2 giay in mot dong, vi du: T:31.2,H:60,L:44
Doc lenh LED:RED hoac LED:GREEN tu laptop.

Den 4 LED RGB cam cong P14 (khong cam chung P0 voi cam bien anh sang).
Vuot nguong: 4 den do nhap nhay. Trong nguong: 4 den xanh la.
Ma tran 5x5 chi co mau do, nen RED sang het, GREEN mot diem giua.
"""

from yolobit import *
import sys
import time

try:
    import uselect

    _poll = uselect.poll()
    _poll.register(sys.stdin, uselect.POLLIN)
except Exception:
    _poll = None

ADDR = 0x38
_dht = None
_buf = ""


def _call(obj, names):
    for name in names:
        if not hasattr(obj, name):
            continue
        attr = getattr(obj, name)
        return attr() if callable(attr) else attr
    return None


def _open_dht():
    global _dht
    try:
        from aiot_dht20 import DHT20

        _dht = DHT20()
        print("DHT20: thu vien AIOT KIT")
        return
    except Exception as exc:
        print("Khong co aiot_dht20:", exc)
    try:
        found = i2c.scan()
    except Exception as exc:
        print("Khong mo duoc I2C:", exc)
        return
    print("I2C thay:", found)
    if ADDR not in found:
        print("Cam DHT20 vao cong I2C")
        return
    _dht = "raw"
    print("DHT20: doc truc tiep I2C")


def _raw_dht():
    i2c.writeto(ADDR, b"\xac\x33\x00")
    time.sleep_ms(80)
    data = i2c.readfrom(ADDR, 7)
    humid = (data[1] << 12 | data[2] << 4 | (data[3] >> 4)) / 1048576.0 * 100.0
    temp = (((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]) / 1048576.0 * 200.0 - 50.0
    return temp, humid


def read_climate():
    if _dht is None:
        return None, None
    if _dht == "raw":
        try:
            return _raw_dht()
        except Exception as exc:
            print("Loi DHT20:", exc)
            return None, None
    try:
        if hasattr(_dht, "read_dht20"):
            _dht.read_dht20()
        temp = _call(_dht, ("temperature", "dht20_temp", "temp"))
        humid = _call(_dht, ("humidity", "dht20_humid", "humid"))
        return temp, humid
    except Exception as exc:
        print("Loi DHT20:", exc)
        return None, None


def read_light():
    """P0 la analog 0-4095. Quy ve thang 0-100 cho gateway."""
    try:
        raw = pin0.read_analog()
    except Exception as exc:
        print("Loi anh sang P0:", exc)
        return None
    if raw is None:
        return None
    if raw > 100:
        raw = raw * 100.0 / 4095.0
    if raw < 0:
        raw = 0
    if raw > 100:
        raw = 100
    return int(round(raw))


def fmt(value):
    value = round(float(value), 1)
    if value == int(value):
        return str(int(value))
    return str(value)


_rgb = None
_mode = "GREEN"
_lit = True
_tick = 0


def _open_rgb():
    """4 LED RGB cua kit nam o cong P14. P0 dang dung cho cam bien anh sang."""
    global _rgb
    try:
        sig = pin14.pin
    except Exception as exc:
        print("Khong co chan P14:", exc)
        return
    try:
        from aiot_rgbled import RGBLed

        _rgb = ("lib", RGBLed(sig, 4))
        print("RGB: thu vien AIOT, cong P14")
        return
    except Exception as exc:
        print("Khong co aiot_rgbled:", exc)
    try:
        import neopixel

        _rgb = ("np", neopixel.NeoPixel(sig, 4))
        print("RGB: NeoPixel, cong P14")
    except Exception as exc:
        print("Khong mo duoc den RGB:", exc)


def _fill(color):
    if _rgb is None:
        return
    kind, dev = _rgb
    try:
        if kind == "np":
            for index in range(4):
                dev[index] = color
            dev.write()
            return
        dev.show(0, color)
    except Exception as exc:
        print("Loi RGB:", exc)


def render():
    """RED nhap nhay. GREEN sang deu. Ma tran do sang theo cung trang thai."""
    on = _mode != "RED" or _lit
    if not on:
        _fill((0, 0, 0))
        display.clear()
        return
    if _mode == "RED":
        _fill((80, 0, 0))
        for x in range(5):
            for y in range(5):
                display.set_pixel(x, y, 9)
        return
    _fill((0, 40, 0))
    display.clear()
    display.set_pixel(2, 2, 4)


def set_led(color):
    global _mode, _lit, _tick
    _mode = color
    _lit = True
    _tick = 0
    render()
    print("RGB:" + color)


def tick_blink():
    global _tick, _lit
    if _mode != "RED":
        return
    _tick += 1
    if _tick < 3:
        return
    _tick = 0
    _lit = not _lit
    render()


def poll_led():
    global _buf
    if _poll is None:
        return
    while _poll.poll(0):
        chunk = sys.stdin.read(1)
        if not chunk:
            break
        if chunk in "\n\r":
            line = _buf.strip().upper()
            _buf = ""
            if line in ("LED:RED", "LED:GREEN"):
                set_led(line.split(":")[1])
        else:
            _buf += chunk
            if len(_buf) > 24:
                _buf = ""


_open_dht()
_open_rgb()
set_led("GREEN")
print("Yolo:Bit san sang")

while True:
    poll_led()
    temp, humid = read_climate()
    light = read_light()
    parts = []
    if temp is not None:
        parts.append("T:" + fmt(temp))
    if humid is not None:
        parts.append("H:" + fmt(humid))
    if light is not None:
        parts.append("L:" + fmt(light))
    if parts:
        print(",".join(parts))
    else:
        print("Khong doc duoc cam bien")
    for _ in range(20):
        poll_led()
        tick_blink()
        time.sleep(0.1)
