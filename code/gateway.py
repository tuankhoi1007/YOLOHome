# -*- coding: utf-8 -*-
"""Chay Module 1 va Module 2 cung luc.

Module 1 doc USB roi gui nhiet do, do am, anh sang len Adafruit.
Module 2 so nguong, gui feed canh-bao, va gui LED:RED / LED:GREEN xuong board.

Username va Active Key nam trong file .env, cung thu muc voi file nay.
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


def main():
    print("Gateway: module 1 + module 2")
    print(
        "Feed:",
        config.FEED_TEMP,
        config.FEED_HUMID,
        config.FEED_LIGHT,
        "| canh bao:",
        config.FEED_ALERT,
    )
    ser = open_serial()
    feed_keys = config.ensure_feeds(config.ALL_FEEDS)
    limits = Thresholds()
    limits.load_cloud()
    reading = Reading()
    incoming = queue.Queue()

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print("Ket noi loi, ma", reason_code)
            return
        print("Da ket noi Adafruit")
        for feed in config.THRESHOLD_FEEDS:
            if feed_keys is None or feed in feed_keys:
                client.subscribe(config.topic(feed))

    def on_message(client, userdata, msg):
        incoming.put((msg.topic, msg.payload))

    client = config.connect_mqtt(on_connect, on_message)
    client.loop_start()
    sensors = SensorPublisher(client)
    alerts = AlertPublisher(client)
    last_led = None
    last_seen = time.time()
    told_json = False
    next_sample = 0.0
    print("Moi lan doc cach nhau", config.fmt_num(config.READ_INTERVAL), "giay")

    def apply_alert():
        nonlocal last_led
        alert = evaluate(reading, limits)
        changed = alerts.publish(alert)
        if alert is not None and alert.led != last_led:
            send_led(ser, alert.led)
            last_led = alert.led
        if reading.has_value():
            sensors.publish(reading, force=changed)

    def drain_thresholds():
        changed = False
        while True:
            try:
                topic, payload = incoming.get_nowait()
            except queue.Empty:
                break
            feed = topic.rsplit("/", 1)[-1]
            text = payload.decode("utf-8", errors="ignore").strip()
            try:
                value = float(text)
            except ValueError:
                print("Bo qua nguong khong phai so:", text)
                continue
            if limits.apply_feed(feed, value):
                changed = True
        if changed:
            apply_alert()

    try:
        while True:
            drain_thresholds()
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
            if line.startswith("{") and not told_json:
                told_json = True
                print("Board in JSON. Lenh den van la LED:RED / LED:GREEN.")
            if line.startswith("RGB:RED") or line.startswith("RGB:GREEN"):
                print("Board da doi den:", line.split(":", 1)[-1])
                continue
            found = parse_line(line)
            if found is None:
                print("Bo qua dong nay. Can dang T:31.2,H:60,L:44")
                continue
            reading.update(found)
            print("Doc:", reading.summary())
            apply_alert()
            next_sample = time.time() + config.READ_INTERVAL
    except KeyboardInterrupt:
        print("Dung.")
    finally:
        ser.close()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
