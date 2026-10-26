# -*- coding: utf-8 -*-
"""Module 2 - Kiem tra nguong va canh bao.

So nhiet do, do am, anh sang voi nguong.
Vuot nguong: feed canh-bao doi noi dung, mau den la RED.
Trong nguong: feed canh-bao la "Bình thường", mau den la GREEN.

Nguong mac dinh nam trong .env.
Dashboard co the ghi de bang feed nguong-nhiet, nguong-am, nguong-sang.
"""

import time

import config
from module1 import Reading, normalize_light


class Alert:
    def __init__(self, ok, led, text):
        self.ok = ok
        self.led = led
        self.text = text


class Thresholds:
    def __init__(self):
        self.temp_max = config.TEMP_MAX
        self.humid_max = config.HUMID_MAX
        self.light_min = config.LIGHT_MIN

    def print_limits(self):
        print(
            "Nguong: nhiet do >",
            config.fmt_num(self.temp_max),
            "| do am >",
            config.fmt_num(self.humid_max),
            "| anh sang <",
            config.fmt_num(self.light_min),
        )

    def _ok(self, attr, value):
        if attr == "temp_max":
            return 0 <= value <= 80
        if attr == "humid_max":
            return 0 <= value <= 100
        if attr == "light_min":
            return 0 <= value <= 100
        return False

    def _set(self, attr, value, feed):
        if not self._ok(attr, value):
            print("Bo qua", feed, "=", value, "(nam ngoai khoang cho phep)")
            return False
        if getattr(self, attr) == value:
            return False
        setattr(self, attr, value)
        print("Doi nguong", feed, "=", config.fmt_num(value))
        self.print_limits()
        return True

    def load_cloud(self):
        pairs = (
            (config.FEED_TEMP_MAX, "temp_max"),
            (config.FEED_HUMID_MAX, "humid_max"),
            (config.FEED_LIGHT_MIN, "light_min"),
        )
        for feed, attr in pairs:
            value = config.fetch_last(feed)
            if value is None:
                continue
            if not self._ok(attr, value):
                print("Bo qua", feed, "=", value, "(nam ngoai khoang cho phep)")
                continue
            setattr(self, attr, value)
        self.print_limits()

    def apply_feed(self, feed, value):
        if feed == config.FEED_TEMP_MAX:
            return self._set("temp_max", value, feed)
        if feed == config.FEED_HUMID_MAX:
            return self._set("humid_max", value, feed)
        if feed == config.FEED_LIGHT_MIN:
            return self._set("light_min", value, feed)
        return False


def evaluate(reading, limits):
    """Tra ve Alert, hoac None neu chua co so lieu nao."""
    if not reading.has_value():
        return None
    problems = []
    if reading.temp is not None and reading.temp > limits.temp_max:
        problems.append(
            "Nhiệt độ cao: "
            + config.fmt_num(reading.temp)
            + "°C (ngưỡng "
            + config.fmt_num(limits.temp_max)
            + ")"
        )
    if reading.humid is not None and reading.humid > limits.humid_max:
        problems.append(
            "Độ ẩm cao: "
            + config.fmt_num(reading.humid)
            + "% (ngưỡng "
            + config.fmt_num(limits.humid_max)
            + ")"
        )
    if reading.light is not None and reading.light < limits.light_min:
        problems.append(
            "Ánh sáng thấp: "
            + config.fmt_num(reading.light)
            + " (ngưỡng "
            + config.fmt_num(limits.light_min)
            + ")"
        )
    if not problems:
        return Alert(True, "GREEN", "Bình thường")
    return Alert(False, "RED", " | ".join(problems))


class AlertPublisher:
    def __init__(self, client):
        self.client = client
        self.last_text = None

    def publish(self, alert):
        if alert is None or alert.text == self.last_text:
            return False
        self.client.publish(config.topic(config.FEED_ALERT), payload=alert.text)
        self.last_text = alert.text
        print("Canh bao:", alert.text)
        return True


# Ten truong nguong -> feed (PROTOCOL.md v0.1.1: web duoc ghi cac feed nay)
THRESHOLD_FIELD_FEEDS = (
    ("temp_max", config.FEED_TEMP_MAX),
    ("humid_max", config.FEED_HUMID_MAX),
    ("light_min", config.FEED_LIGHT_MIN),
)


class ThresholdPublisher:
    """Ghi nguong do nguoi dung doi tren web len feed nguong-*.

    Moi lan luu ton toi da 3 diem du lieu. Mot feed cach nhau it nhat 2 giay, de bam
    luu lien tuc khong lam vuot 30 diem/phut cua Adafruit.
    """

    MIN_GAP = 2

    def __init__(self, client, feed_keys=None, clock=time.time):
        self.client = client
        # Tap feed dang co tren tai khoan (ensure_feeds); None = khong biet, cu gui
        self.feed_keys = feed_keys
        self.clock = clock
        self.last_time = {}

    def changes(self, limits, values):
        """values: {"temp_max": 30, ...}. Tra ve list (truong, feed, so) khac voi nguong hien tai."""
        found = []
        for field, feed in THRESHOLD_FIELD_FEEDS:
            if field in values and values[field] != getattr(limits, field):
                found.append((field, feed, values[field]))
        return found

    def too_soon(self, changes):
        """True neu co feed vua gui chua du MIN_GAP giay."""
        now = self.clock()
        for field, feed, value in changes:
            if now - self.last_time.get(feed, 0.0) < self.MIN_GAP:
                return True
        return False

    def publish(self, changes):
        """Gui tung thay doi. Tra ve (da_gui, thieu_feed): hai list ten feed."""
        sent = []
        missing = []
        now = self.clock()
        for field, feed, value in changes:
            # Tai khoan khong co feed nay (gioi han 10 feed): khong gui, de Adafruit khong tu tao
            if self.feed_keys is not None and feed not in self.feed_keys:
                missing.append(feed)
                continue
            self.client.publish(config.topic(feed), payload=config.fmt_num(value))
            self.last_time[feed] = now
            sent.append(feed)
        if sent:
            print("Gui nguong tu web:", ", ".join(sent))
        return sent, missing


def take_cloud_value(feed, value, reading, limits):
    """Cap nhat nguong hoac so lieu. Tra ve True neu can so sanh lai."""
    if limits.apply_feed(feed, value):
        return True
    if feed == config.FEED_TEMP:
        reading.temp = round(value, 1)
    elif feed == config.FEED_HUMID:
        reading.humid = round(value, 1)
    elif feed == config.FEED_LIGHT:
        reading.light = normalize_light(value)
    else:
        return False
    print("Nhan", feed, "=", config.fmt_num(value))
    return True


def _seed(reading):
    pairs = (
        (config.FEED_TEMP, "temp"),
        (config.FEED_HUMID, "humid"),
        (config.FEED_LIGHT, "light"),
    )
    for feed, attr in pairs:
        value = config.fetch_last(feed)
        if value is None:
            continue
        if attr == "light":
            reading.light = normalize_light(value)
        else:
            setattr(reading, attr, round(value, 1))
        print("So cu", feed, "=", config.fmt_num(getattr(reading, attr)))


def main():
    """Nghe so lieu tren Adafruit roi cap nhat feed canh-bao. Khong can cam board."""
    print("Module 2 - kiem tra nguong")
    print("Feed canh bao:", config.FEED_ALERT)
    feed_keys = config.ensure_feeds(config.ALL_FEEDS)
    limits = Thresholds()
    limits.load_cloud()
    reading = Reading()
    _seed(reading)
    box = {}
    listen = list(config.SENSOR_FEEDS + config.THRESHOLD_FEEDS)
    if feed_keys is not None:
        listen = [feed for feed in listen if feed in feed_keys]

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print("Ket noi loi, ma", reason_code)
            return
        print("Da ket noi Adafruit")
        for feed in listen:
            client.subscribe(config.topic(feed))
        box["alerts"].publish(evaluate(reading, limits))

    def on_message(client, userdata, msg):
        feed = msg.topic.rsplit("/", 1)[-1]
        text = msg.payload.decode("utf-8", errors="ignore").strip()
        try:
            value = float(text)
        except ValueError:
            print("Bo qua", feed, text)
            return
        if take_cloud_value(feed, value, reading, limits):
            box["alerts"].publish(evaluate(reading, limits))

    client = config.connect_mqtt(on_connect, on_message)
    box["alerts"] = AlertPublisher(client)
    print("Dang nghe feed. Them so tren Adafruit hoac chay gateway.py de thu.")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Dung.")
        client.disconnect()


if __name__ == "__main__":
    main()
