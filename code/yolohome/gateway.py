# -*- coding: utf-8 -*-
"""Chay Module 1, 2 va 3 cung luc.

Module 1 doc USB roi gui nhiet do, do am, anh sang len Adafruit.
Module 2 so nguong, gui feed canh-bao, va gui LED:RED / LED:GREEN xuong board.
Module 3 nhan lenh den / quat / cua tu feed (hoac tu web), gui xuong board, cho ack.

Username va Active Key nam trong code/.env.

Vong lap nam trong class Gateway de yolohome.web.server (WEB_DATA=gateway) chay lai dung
vong nay trong mot luong rieng. Chay: python -m yolohome.gateway
"""

import queue
import time

from yolohome import config
from yolohome.module1 import (
    DEVICE_BY_FEED,
    DeviceControl,
    Reading,
    SensorPublisher,
    open_serial,
    parse_ack,
    parse_line,
    send_led,
    send_line,
)
from yolohome.module2 import AlertPublisher, Thresholds, evaluate


class Gateway:
    """Vong Module 1 + 2.

    listener (tuy chon) duoc bao moi khi co so moi, de web hien thi:
    on_mqtt(ok), on_reading(reading), on_alert(alert), on_thresholds(limits),
    on_device(device, value, ok, source, reason).
    Cac ham nay chay trong luong cua gateway; chung chi nen bo viec vao hang doi.
    """

    def __init__(self, listener=None):
        self.listener = listener
        self.ser = None
        self.client = None
        self.feed_keys = None
        self.limits = Thresholds()
        self.reading = Reading()
        # Tin MQTT va nguong tu web deu vao day; chi luong gateway doc ra
        self.incoming = queue.Queue()
        # Lenh dieu khien tu luong khac (web): (thiet bi, gia tri da chuan hoa, nguon)
        self.commands = queue.Queue()
        self.devices = DeviceControl(self._write_line, self._publish_feed, listener)
        self.sensors = None
        self.alerts = None
        self.last_led = None
        self.last_seen = time.time()
        self.told_json = False
        self.next_sample = 0.0

    def _tell(self, name, *args):
        if self.listener is None:
            return
        method = getattr(self.listener, name, None)
        if method is not None:
            method(*args)

    def _write_line(self, line):
        if self.ser is None:
            return False
        return send_line(self.ser, line)

    def _publish_feed(self, feed, value):
        if self.client is None:
            return
        self.client.publish(config.topic(feed), payload=value)
        print("Gui:", feed + "=" + value)

    def start(self):
        print("Gateway: module 1 + module 2 + module 3")
        print(
            "Feed:",
            config.FEED_TEMP,
            config.FEED_HUMID,
            config.FEED_LIGHT,
            "| canh bao:",
            config.FEED_ALERT,
            "| dieu khien:",
            ", ".join(config.CONTROL_FEEDS),
        )
        self.ser = open_serial()
        self.feed_keys = config.ensure_feeds(config.ALL_FEEDS)
        self.limits.load_cloud()
        self._tell("on_thresholds", self.limits)

        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code != 0:
                print("Ket noi loi, ma", reason_code)
                self._tell("on_mqtt", False)
                return
            print("Da ket noi Adafruit")
            for feed in config.THRESHOLD_FEEDS + config.CONTROL_FEEDS:
                if self.feed_keys is None or feed in self.feed_keys:
                    client.subscribe(config.topic(feed))
            self._tell("on_mqtt", True)

        def on_message(client, userdata, msg):
            self.incoming.put((msg.topic, msg.payload))

        self.client = config.connect_mqtt(on_connect, on_message)
        old_disconnect = self.client.on_disconnect

        def on_disconnect(client, userdata, flags, reason_code, properties):
            self._tell("on_mqtt", False)
            old_disconnect(client, userdata, flags, reason_code, properties)

        self.client.on_disconnect = on_disconnect
        self.client.loop_start()
        self.sensors = SensorPublisher(self.client)
        self.alerts = AlertPublisher(self.client)
        self.devices.start()
        print("Moi lan doc cach nhau", config.fmt_num(config.READ_INTERVAL), "giay")

    def set_threshold(self, feed, value):
        """Doi nguong tu luong khac (web). Di cung duong voi tin MQTT tu feed nguong-*."""
        payload = config.fmt_num(value).encode("utf-8")
        self.incoming.put((config.topic(feed), payload))

    def command(self, device, value, source):
        """Gui lenh tu luong khac (web). value da qua module1.NORMALIZERS."""
        self.commands.put((device, value, source))

    def apply_alert(self):
        alert = evaluate(self.reading, self.limits)
        changed = self.alerts.publish(alert)
        if alert is not None and alert.led != self.last_led:
            send_led(self.ser, alert.led)
            self.last_led = alert.led
        if self.reading.has_value():
            self.sensors.publish(self.reading, force=changed)
        if alert is not None:
            self._tell("on_alert", alert)

    def drain_incoming(self):
        """Tin tu feed (nguong, dieu khien) va lenh tu web. Chi luong gateway goi ham nay."""
        while True:
            try:
                device, value, source = self.commands.get_nowait()
            except queue.Empty:
                break
            self.devices.request(device, value, source)
        changed = False
        while True:
            try:
                topic, payload = self.incoming.get_nowait()
            except queue.Empty:
                break
            feed = topic.rsplit("/", 1)[-1]
            text = payload.decode("utf-8", errors="ignore").strip()
            if feed in DEVICE_BY_FEED:
                self.devices.from_feed(feed, text)
                continue
            try:
                value = float(text)
            except ValueError:
                print("Bo qua nguong khong phai so:", text)
                continue
            if self.limits.apply_feed(feed, value):
                changed = True
        if changed:
            self._tell("on_thresholds", self.limits)
            self.apply_alert()

    def handle_ack(self, line):
        """Dong ACK tu board. Tra ve True neu la ACK (ke ca ACK la), de khong xu ly nhu so do."""
        if not line.upper().startswith("ACK:"):
            return False
        found = parse_ack(line)
        if found is None:
            print("Bo qua ACK la:", line)
        else:
            self.devices.ack(found[0], found[1])
        return True

    def wait_for_sample(self):
        """Chua den luot lay mau: bo dong so do cu nhung van doc ACK, vi ACK khong lap lai."""
        if time.time() >= self.next_sample:
            return False
        while self.ser.in_waiting:
            line = self.ser.readline().decode("utf-8", errors="ignore").strip()
            self.handle_ack(line)
        time.sleep(0.05)
        return True

    def step(self):
        """Mot vong: nhan nguong va lenh moi, doc mot dong USB, so nguong, gui feed va lenh den."""
        self.drain_incoming()
        self.devices.expire()
        if self.wait_for_sample():
            return
        line = self.ser.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            if time.time() - self.last_seen > 5:
                print("5 giay roi, board khong gui gi qua USB")
                self.last_seen = time.time()
            return
        self.last_seen = time.time()
        print("Nhan:", line)
        if self.handle_ack(line):
            return
        if line.startswith("{") and not self.told_json:
            self.told_json = True
            print("Board in JSON. Lenh den van la LED:RED / LED:GREEN.")
        if line.startswith("RGB:RED") or line.startswith("RGB:GREEN"):
            print("Board da doi den:", line.split(":", 1)[-1])
            return
        found = parse_line(line)
        if found is None:
            print("Bo qua dong nay. Can dang T:31.2,H:60,L:44")
            return
        self.reading.update(found)
        print("Doc:", self.reading.summary())
        self._tell("on_reading", self.reading)
        self.apply_alert()
        self.next_sample = time.time() + config.READ_INTERVAL

    def run(self, stop=None):
        """Chay mai, hoac den khi stop (threading.Event) duoc bat."""
        while stop is None or not stop.is_set():
            self.step()

    def close(self):
        if self.ser is not None:
            self.ser.close()
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()


def main():
    gateway = Gateway()
    gateway.start()
    try:
        gateway.run()
    except KeyboardInterrupt:
        print("Dung.")
    finally:
        gateway.close()


if __name__ == "__main__":
    main()
