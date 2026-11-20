# -*- coding: utf-8 -*-
"""Code chay tren Yolo:Bit. Dan vao OhStem App, che do Python, roi bam Chay.

Khong chay file nay bang python tren laptop.
Laptop chay gateway.py sau khi da ngat ket noi OhStem.

Cam bien:
  DHT20 vao cong I2C
  Cam bien anh sang vao cong P0

Moi 2 giay in mot dong, vi du: T:31.2,H:60,L:44
Doc lenh tu laptop (docs/PROTOCOL.md v0.2.1):
  LED:RED / LED:GREEN      canh bao / binh thuong (Module 2)
  LIGHT:OFF / LIGHT:rrggbb den thu cong (Module 3)
  FAN:0-100                quat, dieu xung (PWM) o P1
  DOOR:OPEN / DOOR:CLOSE   servo cua o P4
Xong viec thi tra ACK:LIGHT:..., ACK:FAN:n, ACK:DOOR:... Cua tu dong sau 10 giay va tra ACK:DOOR:CLOSE.

Den 4 LED RGB cam cong P14 (khong cam chung P0 voi cam bien anh sang).
Canh bao: 4 den do nhap nhay (uu tien hon den thu cong). Het canh bao: 4 den ve mau thu cong,
mac dinh tat. Ma tran 5x5 chi co mau do, nen RED sang het, GREEN mot diem giua.
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

# ---------- Module 3: den thu cong, quat, cua ----------
FAN_PIN = pin1
DOOR_PIN = pin4
# Dieu xung 12 bit theo sach OhStem (chuong 7): 0 la tat, 4095 la het cong suat. Can thu tren board.
PWM_MAX = 4095
# Goc servo. Do tren mach that roi sua hai so nay.
ANGLE_CLOSE = 0
ANGLE_OPEN = 90
# Cua tu dong sau 10 giay. Nha xung servo sau 1.5 giay cho do nong va do dien (sach chuong 12).
DOOR_AUTO_CLOSE_MS = 10000
SERVO_RELEASE_MS = 1500
# Quat va servo khong khoi dong trong vong 0.5 giay cua nhau, tranh sut ap cung luc.
MOTOR_GAP_MS = 500
# Den thu cong chi sang 40% de 4 LED trang khong qua choi va do hao nguon.
LIGHT_SCALE = 0.4

_light = "OFF"
_fan = 0
_door_open = False
_door_close_at = None
_servo_release_at = None
_last_motor = None
_waiting = {}


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


def _manual_color():
    """Mau den thu cong (Module 3). Mac dinh tat."""
    if _light == "OFF":
        return (0, 0, 0)
    red = int(int(_light[0:2], 16) * LIGHT_SCALE)
    green = int(int(_light[2:4], 16) * LIGHT_SCALE)
    blue = int(int(_light[4:6], 16) * LIGHT_SCALE)
    return (red, green, blue)


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
    _fill(_manual_color())
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


def _is_hex(text):
    if len(text) != 6:
        return False
    for ch in text:
        if ch not in "0123456789abcdef":
            return False
    return True


def set_light(value):
    """value: 'OFF' hoac 'rrggbb' (chu thuong)."""
    global _light
    _light = value
    render()
    print("ACK:LIGHT:" + value)


def set_fan(percent):
    global _fan
    _fan = percent
    try:
        FAN_PIN.write_analog(int(percent * PWM_MAX / 100))
    except Exception as exc:
        print("Loi quat P1:", exc)
    print("ACK:FAN:" + str(percent))


def move_door(open_it):
    """Quay servo roi hen gio nha xung. Mo cua thi hen luon gio tu dong."""
    global _door_open, _door_close_at, _servo_release_at
    _door_open = open_it
    now = time.ticks_ms()
    try:
        DOOR_PIN.servo_write(ANGLE_OPEN if open_it else ANGLE_CLOSE)
    except Exception as exc:
        print("Loi servo P4:", exc)
    _servo_release_at = time.ticks_add(now, SERVO_RELEASE_MS)
    _door_close_at = time.ticks_add(now, DOOR_AUTO_CLOSE_MS) if open_it else None
    print("ACK:DOOR:" + ("OPEN" if open_it else "CLOSE"))


def _run_motor(name, value):
    """Chay quat hoac cua. Neu motor kia vua chay chua du 0.5 giay thi cho (xem run_waiting)."""
    global _last_motor
    now = time.ticks_ms()
    if _last_motor is not None and _last_motor[0] != name:
        if time.ticks_diff(now, _last_motor[1]) < MOTOR_GAP_MS:
            _waiting[name] = value
            return
    _last_motor = (name, now)
    if name == "FAN":
        set_fan(value)
    else:
        move_door(value)


def run_waiting():
    """Goi moi nhip 0.1 giay: chay lenh dang cho, tu dong cua, nha xung servo. Khong sleep."""
    global _door_close_at, _servo_release_at
    for name in list(_waiting):
        value = _waiting.pop(name)
        _run_motor(name, value)
    now = time.ticks_ms()
    if _door_close_at is not None and time.ticks_diff(now, _door_close_at) >= 0:
        _run_motor("DOOR", False)
    if _servo_release_at is not None and time.ticks_diff(now, _servo_release_at) >= 0:
        _servo_release_at = None
        try:
            DOOR_PIN.servo_release()
        except Exception as exc:
            print("Loi nha servo:", exc)


def handle_line(line):
    """Mot dong lenh tu laptop. Dong sai thi bo qua."""
    upper = line.strip().upper()
    if upper in ("LED:RED", "LED:GREEN"):
        set_led(upper.split(":")[1])
        return
    if ":" not in upper:
        return
    name, value = upper.split(":", 1)
    if name == "LIGHT":
        if value == "OFF":
            set_light("OFF")
        elif _is_hex(value.lower()):
            set_light(value.lower())
    elif name == "FAN":
        try:
            percent = int(value)
        except ValueError:
            return
        if 0 <= percent <= 100:
            _run_motor("FAN", percent)
    elif name == "DOOR":
        if value == "OPEN":
            _run_motor("DOOR", True)
        elif value == "CLOSE":
            _run_motor("DOOR", False)


def poll_led():
    global _buf
    if _poll is None:
        return
    while _poll.poll(0):
        chunk = sys.stdin.read(1)
        if not chunk:
            break
        if chunk in "\n\r":
            line = _buf
            _buf = ""
            if line.strip():
                handle_line(line)
        else:
            _buf += chunk
            if len(_buf) > 24:
                _buf = ""


_open_dht()
_open_rgb()
set_led("GREEN")
# Trang thai ban dau (PROTOCOL): den tat, quat 0, cua dong
set_fan(0)
move_door(False)
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
        run_waiting()
        time.sleep(0.1)
