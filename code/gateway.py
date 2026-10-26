# -*- coding: utf-8 -*-
"""Chay Module 1 va Module 2 cung luc.

Module 1 doc USB roi gui nhiet do, do am, anh sang len Adafruit.
Module 2 so nguong, gui feed canh-bao, va gui LED:RED / LED:GREEN xuong board.

Username va Active Key nam trong file .env, cung thu muc voi file nay.

Vong lap nam trong class Gateway de web_server.py (WEB_DATA=gateway) chay lai dung
vong nay trong mot luong rieng. Chay file nay truc tiep thi y nhu truoc.
"""

import queue
import time

import config
from module1 import (
    Reading,
    SensorPublisher,
    open_serial,
    parse_line,
    send_led,
    wait_interval,
)
from module2 import AlertPublisher, Thresholds, evaluate


class Gateway:
    """Vong Module 1 + 2.

    listener (tuy chon) duoc bao moi khi co so moi, de web hien thi:
    on_mqtt(ok), on_reading(reading), on_alert(alert), on_thresholds(limits).
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

    def start(self):
        print("Gateway: module 1 + module 2")
        print(
            "Feed:",
            config.FEED_TEMP,
            config.FEED_HUMID,
            config.FEED_LIGHT,
            "| canh bao:",
            config.FEED_ALERT,
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
            for feed in config.THRESHOLD_FEEDS:
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
        print("Moi lan doc cach nhau", config.fmt_num(config.READ_INTERVAL), "giay")

    def set_threshold(self, feed, value):
        """Doi nguong tu luong khac (web). Di cung duong voi tin MQTT tu feed nguong-*."""
        payload = config.fmt_num(value).encode("utf-8")
        self.incoming.put((config.topic(feed), payload))

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

    def drain_thresholds(self):
        changed = False
        while True:
            try:
                topic, payload = self.incoming.get_nowait()
            except queue.Empty:
                break
            feed = topic.rsplit("/", 1)[-1]
            text = payload.decode("utf-8", errors="ignore").strip()
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

    def step(self):
        """Mot vong: nhan nguong moi, doc mot dong USB, so nguong, gui feed va lenh den."""
        self.drain_thresholds()
        if wait_interval(self.ser, self.next_sample):
            return
        line = self.ser.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            if time.time() - self.last_seen > 5:
                print("5 giay roi, board khong gui gi qua USB")
                self.last_seen = time.time()
            return
        self.last_seen = time.time()
        print("Nhan:", line)
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
