"""Chạy trên Yolo:bit bằng MicroPython của OhStem.

Thonny: chọn trình thông dịch MicroPython (ESP32) và cổng USB của bo.
Bo cần firmware MicroPython của OhStem có module yolobit.
Chép aiot_dht20.py và aiot_lcd1602.py vào thư mục gốc trên bo cùng main.py.
Nếu đã cài phần mở rộng AIoT, có thể dùng lib.aiot.aiot_dht20 sẵn có.
DHT20 và LCD1602 dùng chung I2C (SCL P19, SDA P20); ánh sáng nối P2.
Siêu âm OhStem Grove: TRIG P16, ECHO P12. Micro servo 180°: P4.
Servo bắt đầu 0°, khoảng cách <20 cm thì 90°, >=20 cm thì về 0°.
Hai lần đo liên tiếp xác nhận thay đổi; mất echo thì giữ góc đã ra lệnh.
Lưu chương trình vào thiết bị với tên main.py để chạy khi cấp nguồn.
LCD hiển thị nhiệt độ, độ ẩm và ánh sáng, đồng thời mỗi dòng USB là JSON:
temperature (°C), humidity (%RH),
light (analog thô), distance_cm, nearby, servo_angle (góc đã ra lệnh).
Đo siêu âm mỗi 200 ms; đọc môi trường, cập nhật LCD/JSON mỗi 2 giây.
"""

import sys
import time
import ujson

from machine import Pin, PWM, SoftI2C, time_pulse_us
from yolobit import pin2, pin4, pin12, pin14, pin16, pin19, pin20

try:
    import uselect

    _poll = uselect.poll()
    _poll.register(sys.stdin, uselect.POLLIN)
except Exception:
    _poll = None

try:
    from aiot_dht20 import DHT20
except ImportError:
    from lib.aiot.aiot_dht20 import DHT20

try:
    from aiot_lcd1602 import LCD1602
except ImportError:
    from lib.aiot.aiot_lcd1602 import LCD1602


SAMPLE_INTERVAL_MS = 2000
LIGHT_PIN = pin2
LCD_I2C_ADDRESS = None  # Tự dò; đặt 0x21, 0x27... nếu muốn chỉ định.
ULTRASONIC_INTERVAL_MS = 200
TRIGGER_PIN = pin16
ECHO_PIN = pin12
SERVO_PIN = pin4
NEAR_DISTANCE_CM = 20
CONFIRM_READINGS = 2
ECHO_TIMEOUT_US = 30000
# Dải xung thường dùng cho servo định vị 180°, có thể hiệu chỉnh theo servo.
SERVO_MIN_US = 500
SERVO_MAX_US = 2500

_rgb = None
_led_mode = "GREEN"
_led_on = True
_led_buf = ""
_blink_at = 0


def open_rgb():
    """4 LED RGB cam cong P14. Anh sang van o P2, khong dung chung chan."""
    global _rgb
    try:
        from aiot_rgbled import RGBLed

        _rgb = RGBLed(pin14.pin, 4)
    except Exception as exc:
        print("RGB loi:", exc)


def _fill_rgb(color):
    if _rgb is None:
        return
    try:
        _rgb.show(0, color)
    except Exception as exc:
        print("RGB loi:", exc)


def render_led():
    if _led_mode == "RED" and not _led_on:
        _fill_rgb((0, 0, 0))
        return
    if _led_mode == "RED":
        _fill_rgb((80, 0, 0))
        return
    _fill_rgb((0, 40, 0))


def set_led(color):
    global _led_mode, _led_on, _blink_at
    _led_mode = color
    _led_on = True
    _blink_at = time.ticks_add(time.ticks_ms(), 300)
    render_led()
    print("RGB:" + color)


def tick_blink():
    global _led_on, _blink_at
    if _led_mode != "RED":
        return
    now = time.ticks_ms()
    if time.ticks_diff(now, _blink_at) < 0:
        return
    _led_on = not _led_on
    _blink_at = time.ticks_add(now, 300)
    render_led()


def poll_led():
    global _led_buf
    if _poll is None:
        return
    while _poll.poll(0):
        chunk = sys.stdin.read(1)
        if not chunk:
            break
        if chunk in "\r\n":
            line = _led_buf.strip().upper()
            _led_buf = ""
            if line in ("LED:RED", "LED:GREEN"):
                set_led(line.split(":")[1])
        else:
            _led_buf += chunk
            if len(_led_buf) > 24:
                _led_buf = ""


class ProximityServo:
    def __init__(self):
        self.trigger = Pin(TRIGGER_PIN.pin, Pin.OUT, value=0)
        self.echo = Pin(ECHO_PIN.pin, Pin.IN)
        self.angle = None
        self.pending_angle = None
        self.confirmations = 0
        self.servo = PWM(Pin(SERVO_PIN.pin), freq=50, duty=0)
        try:
            self.move_to(0)
        except Exception:
            self.servo.deinit()
            raise

    def move_to(self, angle):
        pulse_us = SERVO_MIN_US + (SERVO_MAX_US - SERVO_MIN_US) * angle / 180
        self.servo.duty(round(pulse_us * 1023 / 20000))
        self.angle = angle  # Chỉ ghi nhận sau khi gửi lệnh thành công.

    def read_distance(self):
        self.trigger.value(0)
        time.sleep_us(2)
        self.trigger.value(1)
        time.sleep_us(10)
        self.trigger.value(0)
        pulse_us = time_pulse_us(self.echo, 1, ECHO_TIMEOUT_US)
        # MicroPython trả -1/-2 khi hết thời gian; không coi đó là 0 cm.
        if pulse_us <= 0:
            raise OSError("Ultrasonic echo timeout")
        distance = pulse_us / 58.0
        if distance > 400:
            raise OSError("Ultrasonic distance out of range")
        return distance

    def update(self):
        try:
            distance = self.read_distance()
        except (OSError, ValueError, RuntimeError):
            self.pending_angle = None
            self.confirmations = 0
            raise
        nearby = distance < NEAR_DISTANCE_CM
        target = 90 if nearby else 0
        if target != self.pending_angle:
            self.pending_angle = target
            self.confirmations = 1
        else:
            self.confirmations = min(self.confirmations + 1, CONFIRM_READINGS)
        if self.confirmations >= CONFIRM_READINGS and target != self.angle:
            self.move_to(target)
        return round(distance, 1), nearby

    def close(self):
        self.servo.deinit()


def init_lcd():
    bus = SoftI2C(scl=Pin(pin19.pin), sda=Pin(pin20.pin), freq=100000)
    devices = bus.scan()
    if LCD_I2C_ADDRESS is None:
        # PCF8574/PCF8574A; loại 0x38 vì đó là DHT20 trên cùng bus.
        candidates = [addr for addr in devices
                      if 0x20 <= addr <= 0x27 or 0x39 <= addr <= 0x3F]
        if len(candidates) != 1:
            found = ",".join(hex(addr) for addr in devices)
            raise OSError("LCD address ambiguous/missing; I2C=[" + found
                          + "]. Set LCD_I2C_ADDRESS")
        address = candidates[0]
    else:
        address = LCD_I2C_ADDRESS
        if address not in devices:
            raise OSError("LCD not found at " + hex(address))
    lcd = LCD1602(address)
    lcd.backlight_on()
    return lcd


def lcd_lines(data, show_distance=False):
    # ASCII để LCD1602 không hiển thị sai ký tự tiếng Việt.
    temperature = data["temperature"]
    humidity = data["humidity"]
    light = data["light"]
    temp_text = "ERR" if temperature is None else "%.1f" % temperature
    hum_text = "ERR" if humidity is None else "%.1f" % humidity
    light_text = "ERR" if light is None else str(light)
    # Mỗi đại lượng chiếm 8 cột, kể cả nhiệt độ âm / độ ẩm 100%.
    left = ("T:" + temp_text + "C")[:8]
    right = ("H:" + hum_text + "%")[:8]
    first = left + " " * (8 - len(left)) + right
    second = "Light:" + light_text + " ADC"
    if show_distance:
        distance = data.get("distance_cm")
        angle = data.get("servo_angle")
        distance_text = "ERR" if distance is None else "%.1f" % distance
        angle_text = "ERR" if angle is None else str(angle)
        second = "D:" + distance_text + "cm S:" + angle_text
    return tuple((line + " " * 16)[:16] for line in (first, second))


def update_lcd(lcd, data, show_distance=False):
    for row, line in enumerate(lcd_lines(data, show_distance)):
        lcd.move_to(0, row)
        lcd.putstr(line)  # Ghi đè đủ 16 cột, tránh ký tự cũ và nháy do clear().


def run(proximity):
    dht20 = None
    lcd = None
    show_distance = False
    now = time.ticks_ms()
    last_ultrasonic = time.ticks_add(now, -ULTRASONIC_INTERVAL_MS)
    last_environment = time.ticks_add(now, -SAMPLE_INTERVAL_MS)
    data = {"temperature": None, "humidity": None, "light": None,
            "distance_cm": None, "nearby": None, "servo_angle": proximity.angle}
    errors = {}

    while True:
        poll_led()
        tick_blink()
        now = time.ticks_ms()
        if time.ticks_diff(now, last_ultrasonic) >= ULTRASONIC_INTERVAL_MS:
            try:
                distance, nearby = proximity.update()
                data["distance_cm"] = distance
                data["nearby"] = nearby
                errors.pop("proximity", None)
            except (OSError, ValueError, RuntimeError) as exc:
                data["distance_cm"] = None
                data["nearby"] = None
                errors["proximity"] = str(exc)
            data["servo_angle"] = proximity.angle
            last_ultrasonic = time.ticks_ms()

        if time.ticks_diff(now, last_environment) < SAMPLE_INTERVAL_MS:
            time.sleep_ms(10)
            continue
        last_environment = now
        for key in ("temperature", "humidity", "light"):
            data[key] = None
        for key in ("dht20", "light", "lcd"):
            errors.pop(key, None)

        try:
            if dht20 is None:
                dht20 = DHT20()
            # Hai hàm của thư viện OhStem tự thực hiện phép đo.
            temperature = dht20.dht20_temperature()
            humidity = dht20.dht20_humidity()
            data["temperature"] = round(temperature, 1)
            data["humidity"] = round(humidity, 1)
        except (OSError, ValueError, RuntimeError) as exc:
            dht20 = None  # Thử khởi tạo lại ở vòng sau.
            errors["dht20"] = str(exc)

        try:
            data["light"] = LIGHT_PIN.read_analog()
        except (OSError, ValueError, RuntimeError) as exc:
            errors["light"] = str(exc)

        try:
            if lcd is None:
                lcd = init_lcd()
            update_lcd(lcd, data, show_distance)
            show_distance = not show_distance
        except Exception as exc:
            # Thư viện OhStem có thể ném Exception khi khởi tạo thất bại.
            # Vẫn gửi JSON và thử kết nối lại LCD ở vòng đo sau.
            lcd = None
            errors["lcd"] = str(exc)

        # Lỗi cũng nằm trong JSON; giá trị đo thất bại được gửi là null.
        if errors:
            data["errors"] = errors.copy()
        else:
            data.pop("errors", None)
        print(ujson.dumps(data))
        time.sleep_ms(10)


def main():
    time.sleep_ms(1000)  # Chờ nguồn và cảm biến ổn định.
    open_rgb()
    set_led("GREEN")
    proximity = ProximityServo()
    try:
        run(proximity)
    finally:
        proximity.close()  # Thả PWM khi dừng bằng Ctrl+C trong Thonny.


if __name__ == "__main__":
    main()
