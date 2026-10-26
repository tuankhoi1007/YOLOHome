# -*- coding: utf-8 -*-
"""Web chay luon Module 1 + 2 (WEB_DATA=gateway): mot chuong trinh cho buoi demo.

web_server.py tao GatewayHome. GatewayHome chay gateway.Gateway (dung vong cua gateway.py:
doc USB, gui feed, so nguong, gui LED:RED / LED:GREEN) trong mot luong rieng, va nhan
moi so doc duoc qua listener de day thang len web, khong phai doi Adafruit gui lai.

Moi xu ly so lieu, canh bao, nhat ky ke thua tu web_live.LiveHome. O day chi doi
nguon du lieu: thay vi nghe MQTT, nghe luong gateway.

Khong chay cung luc voi gateway.py hay OhStem: ca ba deu can cung mot cong COM.
"""

import threading
import time

import config
from gateway import Gateway
from module2 import ThresholdPublisher
from web_live import LiveHome


class GatewayHome(LiveHome):
    MODE = "gateway"
    # Board gui khoang 2 giay, gateway lay mau 3 giay (READ_INTERVAL). 10 giay khong co so = mat board.
    STALE_SECONDS = 10

    def __init__(self, emit, clock=time.time, connect=True, gateway=None):
        # gateway: truyen vao khi kiem thu (khong mo cong COM that)
        self.gateway = gateway
        self.stop = threading.Event()
        self.thread = None
        LiveHome.__init__(self, emit, clock=clock, connect=connect)
        self.label = config.COM_PORT

    # ---------- nguon du lieu: luong gateway thay cho MQTT ----------

    def _seed(self):
        # Gateway.start() tu doc nguong tren Adafruit va bao qua on_thresholds
        pass

    def _connect(self):
        if self.gateway is None:
            self.gateway = Gateway(listener=self)
        self.gateway.start()
        # Dung chung ket noi MQTT cua gateway: web khong mo them ket noi thu hai
        self.publisher = ThresholdPublisher(self.gateway.client, self.gateway.feed_keys)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        try:
            self.gateway.run(self.stop)
        except Exception as exc:
            print("Gateway trong web dung vi loi:", exc)
            self.incoming.put(("mqtt", False))

    def close(self):
        self.stop.set()
        if self.thread is not None:
            self.thread.join(timeout=3)
        if self.gateway is not None:
            self.gateway.close()

    # ---------- listener: goi tu luong gateway, chi bo vao hang doi ----------

    def on_mqtt(self, ok):
        self.incoming.put(("mqtt", ok))

    def on_reading(self, reading):
        pairs = (
            (config.FEED_TEMP, reading.temp),
            (config.FEED_HUMID, reading.humid),
            (config.FEED_LIGHT, reading.light),
        )
        for feed, value in pairs:
            if value is not None:
                self.incoming.put(("feed", (feed, config.fmt_num(value))))

    def on_alert(self, alert):
        self.incoming.put(("feed", (config.FEED_ALERT, alert.text)))

    def on_thresholds(self, limits):
        pairs = (
            (config.FEED_TEMP_MAX, limits.temp_max),
            (config.FEED_HUMID_MAX, limits.humid_max),
            (config.FEED_LIGHT_MIN, limits.light_min),
        )
        for feed, value in pairs:
            self.incoming.put(("feed", (feed, config.fmt_num(value))))

    # ---------- nguong: ap dung ngay trong gateway (UC04) ----------

    def _apply_thresholds(self, changes, sent):
        """Moi nguong deu dua vao gateway de lan so sanh sau dung ngay, ke ca feed chua co tren tai khoan."""
        applied = set()
        for field, feed, value in changes:
            setattr(self.limits, field, value)
            self.gateway.set_threshold(feed, value)
            applied.add(field)
        return applied

    def _missing_note(self, missing):
        if not missing:
            return ""
        return (
            "Tài khoản chưa có feed " + ", ".join(missing)
            + " nên ngưỡng đó chỉ dùng đến khi tắt chương trình, chưa lưu lên Adafruit."
        )
