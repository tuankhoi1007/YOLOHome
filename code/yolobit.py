# -*- coding: utf-8 -*-
"""Code chay tren Yolo:Bit. Dan vao OhStem App, che do Python, roi bam Chay.

Khong chay file nay bang python tren laptop.
Laptop chay gateway.py sau khi da ngat ket noi OhStem.

Cam bien:
  DHT20 vao cong I2C
  Cam bien anh sang vao cong P0

Moi 2 giay in mot dong, vi du: T:31.2,H:60,L:44
Doc lenh LED:RED hoac LED:GREEN, va DOOR:OPEN / DOOR:CLOSE / DOOR:PIN:P4 tu laptop.

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

# Goc servo. Neu canh quay nguoc chieu cua, doi hai so nay roi nap lai board.
# 0 = cua dong, 90 = cua mo. Chan mac dinh P4 (tai lieu servo OhStem), laptop co the doi bang DOOR:PIN.
DOOR_CLOSED_ANGLE = 0
DOOR_OPEN_ANGLE = 90
_SERVO_BLOCKED = ("P0", "P14")
_servo = None
_servo_name = ""


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


def _pin_by_name(name):
    """P4 -> pin4. P0 va P14 khong gan servo."""
    if name in _SERVO_BLOCKED:
        print("Khong gan servo vao", name)
        return None
    if len(name) < 2 or name[0] != "P":
        print("Chan servo khong hop le:", name)
        return None
    obj = globals().get("pin" + name[1:])
    if obj is None:
        print("Khong co chan", name)
        return None
    return obj


def _move_servo(angle):
    if _servo is None:
        return False
    kind, dev = _servo
    try:
        if kind == "lib":
            if hasattr(dev, "angle"):
                dev.angle(angle)
            elif hasattr(dev, "set_angle"):
                dev.set_angle(angle)
            else:
                dev.write(angle)
            return True
        if kind == "pin":
            if hasattr(dev, "set_servo_angle"):
                dev.set_servo_angle(angle)
            else:
                dev.servo_write(angle)
            return True
        # PWM 50 Hz. Xung 1.0 ms o 0 do, 2.0 ms o 180 do, chu ky 20 ms.
        if angle < 0:
            angle = 0
        if angle > 180:
            angle = 180
        pulse_us = 1000 + int(angle * 1000 / 180)
        if hasattr(dev, "duty_ns"):
            dev.duty_ns(pulse_us * 1000)
        elif hasattr(dev, "duty_u16"):
            dev.duty_u16(int(pulse_us * 65535 / 20000))
        else:
            dev.duty(int(pulse_us * 1023 / 20000))
        return True
    except Exception as exc:
        print("Loi servo:", exc)
        return False


def set_servo_pin(name):
    """Gan servo vao chan laptop yeu cau. That bai thi in DOOR:ERR, khong doi P0/P14."""
    global _servo, _servo_name
    name = name.strip().upper()
    pin = _pin_by_name(name)
    if pin is None:
        print("DOOR:ERR")
        return
    try:
        from servo import Servo

        _servo = ("lib", Servo(pin))
        _servo_name = name
        print("Servo: thu vien servo, cong", name)
    except Exception as exc:
        print("Khong co thu vien servo:", exc)
        try:
            from machine import PWM

            sig = pin.pin if hasattr(pin, "pin") else pin
            _servo = ("pwm", PWM(sig, freq=50))
            _servo_name = name
            print("Servo: PWM 50Hz, cong", name)
        except Exception as pwm_exc:
            if hasattr(pin, "set_servo_angle") or hasattr(pin, "servo_write"):
                _servo = ("pin", pin)
                _servo_name = name
                print("Servo: ham san tren chan", name)
            else:
                print("Khong mo duoc servo:", pwm_exc)
                print("DOOR:ERR")
                return
    # Khoa ngay khi vua gan, de phan cung khop trang thai "dang khoa" tren web.
    if not _move_servo(DOOR_CLOSED_ANGLE):
        print("DOOR:ERR")
        return
    print("DOOR:PIN:" + name)
    print("DOOR:CLOSE")


def set_door(open_door):
    if _servo is None:
        set_servo_pin("P4")
    if _servo is None:
        return
    angle = DOOR_OPEN_ANGLE if open_door else DOOR_CLOSED_ANGLE
    if not _move_servo(angle):
        print("DOOR:ERR")
        return
    if open_door:
        print("DOOR:OPEN")
    else:
        print("DOOR:CLOSE")


def _handle_line(line):
    if line in ("LED:RED", "LED:GREEN"):
        set_led(line.split(":")[1])
        return
    if line == "DOOR:OPEN":
        set_door(True)
        return
    if line == "DOOR:CLOSE":
        set_door(False)
        return
    if line.startswith("DOOR:PIN:"):
        set_servo_pin(line.split(":", 2)[-1])


def poll_led():
    """Doc ca lenh den va lenh cua. Ten cu giu de vong lap khong doi."""
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
            if line:
                _handle_line(line)
        else:
            _buf += chunk
            # DOOR:PIN:P16 dai 12 ky tu. 40 cho du cho, qua do la rac thi bo.
            if len(_buf) > 40:
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
