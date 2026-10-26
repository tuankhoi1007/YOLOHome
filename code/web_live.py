# -*- coding: utf-8 -*-
"""Du lieu that cho web (WEB_DATA=live): doc feed Adafruit IO theo PROTOCOL.md v0.1.1.

Cung giao dien voi web_mock.MockHome: snapshot, set_thresholds, command, simulate, log, tick.
web_gateway.GatewayHome ke thua class nay, chi doi nguon du lieu (chay gateway ngay trong web).

Co du lieu that:
- cam bien nhiet-do, do-am, anh-sang va cau canh-bao (gateway.py ghi)
- nguong nguong-nhiet, nguong-am, nguong-sang: doc va ghi (PROTOCOL.md v0.1.1)
- lich su cam bien: doc tu lich su feed tren Adafruit luc mo web (UC06)

Chua co, tra loi ro rang thay vi doan hop dong:
- den, quat, cua: can PROTOCOL.md v0.2.0 (Gate 2)
- nhat ky dieu khien/canh bao luu lau: D5 chua chot; o day chi giu trong RAM
- khuon mat (Phase 6), giong noi (Phase 7)
"""

import queue
import threading
import time

import config
from module1 import Reading
from module2 import Alert, Thresholds, ThresholdPublisher, evaluate, take_cloud_value
from web_mock import (
    DOOR_RELOCK,
    MAX_ENTRIES,
    SENSOR_LOG_EVERY,
    CommandError,
    alert_kinds,
    filter_log,
    parse_thresholds,
)

NORMAL_TEXT = "Bình thường"
# So diem lich su lay cho moi feed cam bien khi mo web. Chi la luot doc REST, khong ton diem du lieu.
HISTORY_POINTS = 50

SENSOR_NAMES = {
    config.FEED_TEMP: ("Nhiệt độ", "°C"),
    config.FEED_HUMID: ("Độ ẩm", "%"),
    config.FEED_LIGHT: ("Ánh sáng", ""),
}


class LiveHome:
    MODE = "live"
    # Gateway gui nhip 15 giay moi feed (PROTOCOL.md). Qua 3 nhip khong co so moi thi coi nhu mat Gateway.
    STALE_SECONDS = 45

    def __init__(self, emit, clock=time.time, connect=True):
        self.emit = emit
        self.clock = clock
        self.lock = threading.Lock()
        # Callback MQTT (hoac luong gateway) chi bo viec vao hang doi; tick() lam viec
        self.incoming = queue.Queue()
        now = clock()
        self.label = "Adafruit"
        self.reading = Reading()
        self.limits = Thresholds()
        self.alert = None
        self.alert_from_feed = False
        self.mqtt_ok = False
        self.online = False
        self.online_since = now
        self.sensor_at = None
        self.next_sensor_log = now
        self.entries = []
        self.next_id = 1
        self.client = None
        self.publisher = None
        self._add_log(now, "system", "Web", "Mở web, dữ liệu thật (" + self.MODE + ")", "Khởi tạo", "neutral")
        if connect:
            # Noi truoc (che do gateway mo cong COM o day), loi thi dung ngay; lich su doc sau cung
            self._seed()
            self._connect()
            self._load_history()

    # ---------- nguon du lieu (GatewayHome thay hai ham _seed, _connect) ----------

    def _load_history(self):
        """Lich su cam bien tu Adafruit, chen vao dau nhat ky theo dung thoi diem (cu truoc)."""
        points = []
        for feed in config.SENSOR_FEEDS:
            for at, value in config.fetch_history(feed, HISTORY_POINTS):
                points.append((at, feed, value))
        points.sort()
        history = []
        for at, feed, value in points:
            name, unit = SENSOR_NAMES[feed]
            detail = name + " " + config.fmt_num(value) + unit + " (lịch sử Adafruit)"
            history.append(self._entry(at, "sensor", "Feed " + feed, detail, "Hợp lệ", "neutral"))
        with self.lock:
            # filter_log can danh sach theo thu tu thoi gian: lich su cu dung truoc su kien moi
            self.entries = (history + self.entries)[-MAX_ENTRIES:]
        if points:
            print("Web: da doc", len(points), "diem lich su cam bien tu Adafruit")

    def _seed(self):
        """Lay so cuoi cua moi feed qua REST de trang co so ngay khi mo."""
        self.limits.load_cloud()
        for feed in config.SENSOR_FEEDS:
            value = config.fetch_last(feed)
            if value is not None:
                take_cloud_value(feed, value, self.reading, self.limits)
        self.alert = evaluate(self.reading, self.limits)

    def _connect(self):
        listen = list(config.SENSOR_FEEDS + (config.FEED_ALERT,) + config.THRESHOLD_FEEDS)

        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code != 0:
                print("Web: ket noi Adafruit loi, ma", reason_code)
                return
            for feed in listen:
                client.subscribe(config.topic(feed))
            self.incoming.put(("mqtt", True))

        def on_message(client, userdata, msg):
            feed = msg.topic.rsplit("/", 1)[-1]
            text = msg.payload.decode("utf-8", errors="ignore").strip()
            self.incoming.put(("feed", (feed, text)))

        self.client = config.connect_mqtt(on_connect, on_message)
        old_disconnect = self.client.on_disconnect

        def on_disconnect(client, userdata, flags, reason_code, properties):
            self.incoming.put(("mqtt", False))
            old_disconnect(client, userdata, flags, reason_code, properties)

        self.client.on_disconnect = on_disconnect
        # Chi doc danh sach feed, khong tao feed moi (gateway.py moi la noi tao)
        self.publisher = ThresholdPublisher(self.client, config.list_feeds())
        # paho tu chay luong rieng va tu noi lai
        self.client.loop_start()

    def close(self):
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()

    # ---------- doc trang thai ----------

    def snapshot(self):
        with self.lock:
            now = self.clock()
            return {
                "mode": self.MODE,
                "features": {
                    "devices": False,
                    "face": False,
                    "voice": False,
                    "simulate": False,
                    "log": True,
                    "thresholds_write": self.publisher is not None,
                },
                "gateway": self._gateway_view(),
                "sensors": self._sensors_view(now),
                "thresholds": self._thresholds_view(),
                "alert": self._alert_view(),
                "devices": None,
                "face": None,
                "voice": None,
                "colors": [],
                "voice_commands": [],
                "door_relock": DOOR_RELOCK,
            }

    def log(self, kind="all", date="", query="", page=1):
        with self.lock:
            return filter_log(self.entries, kind, date, query, page)

    # ---------- nguong (PROTOCOL.md v0.1.1, UC04) ----------

    def set_thresholds(self, body):
        with self.lock:
            if self.publisher is None or not self.mqtt_ok:
                raise CommandError(503, "Chưa kết nối Adafruit, chưa lưu được ngưỡng.")
            values = parse_thresholds(body, self.limits)
            changes = self.publisher.changes(self.limits, values)
            if not changes:
                return self._thresholds_view()
            if self.publisher.too_soon(changes):
                raise CommandError(429, "Vừa lưu ngưỡng. Đợi 2 giây rồi lưu lại.")
            sent, missing = self.publisher.publish(changes)
            applied = self._apply_thresholds(changes, sent)
            now = self.clock()
            if applied:
                parts = [feed + " = " + config.fmt_num(value) for field, feed, value in changes if field in applied]
                self._add_log(now, "control", "Giao diện web", "Đổi ngưỡng: " + ", ".join(parts), "Đã lưu", "ok")
                self.emit("thresholds", self._thresholds_view())
                if not self.alert_from_feed:
                    self._set_alert(now, evaluate(self.reading, self.limits))
            result = self._thresholds_view()
            result["note"] = self._missing_note(missing)
            if missing and not applied:
                raise CommandError(409, result["note"])
            return result

    def _apply_thresholds(self, changes, sent):
        """Ban live: chi ap dung nhung feed da gui (gateway.py doc lai tu Adafruit). Tra ve tap truong."""
        applied = set()
        for field, feed, value in changes:
            if feed in sent:
                setattr(self.limits, field, value)
                applied.add(field)
        return applied

    def _missing_note(self, missing):
        if not missing:
            return ""
        return "Tài khoản chưa có feed " + ", ".join(missing) + " (giới hạn 10 feed) nên ngưỡng đó chưa lưu lên Adafruit."

    # ---------- lenh: chua co hop dong ----------

    def command(self, device, body, source="Giao diện web"):
        raise CommandError(503, "Chưa có điều khiển thật: cần PROTOCOL.md v0.2.0 (Gate 2).")

    def simulate(self, kind):
        raise CommandError(404, "Nút mô phỏng chỉ có khi WEB_DATA=mock.")

    # ---------- nhip ----------

    def tick(self):
        with self.lock:
            now = self.clock()
            while True:
                try:
                    kind, data = self.incoming.get_nowait()
                except queue.Empty:
                    break
                if kind == "mqtt":
                    self.mqtt_ok = data
                elif kind == "feed":
                    self._take(now, data[0], data[1])
            self._check_online(now)

    def _take(self, now, feed, text):
        if feed == config.FEED_ALERT:
            ok = text == NORMAL_TEXT
            self._set_alert(now, Alert(ok, "GREEN" if ok else "RED", text))
            self.alert_from_feed = True
            return
        try:
            value = float(text)
        except ValueError:
            return
        before = self._thresholds_view()
        if not take_cloud_value(feed, value, self.reading, self.limits):
            return
        if feed in config.SENSOR_FEEDS:
            self.sensor_at = now
            self.emit("sensors", self._sensors_view(now))
            if now >= self.next_sensor_log:
                self._log_sensors(now)
                self.next_sensor_log = now + SENSOR_LOG_EVERY
        elif self._thresholds_view() != before:
            self._add_log(now, "control", "Adafruit IO", "Ngưỡng đổi: " + feed + " = " + config.fmt_num(value), "Đã nhận", "ok")
            self.emit("thresholds", self._thresholds_view())
        # Chua co cau canh-bao tu gateway thi tu so nguong de hien tam
        if not self.alert_from_feed:
            self._set_alert(now, evaluate(self.reading, self.limits))

    def _set_alert(self, now, alert):
        if alert is None or (self.alert is not None and alert.text == self.alert.text):
            return
        was_ok = self.alert is None or self.alert.ok
        old_kinds = alert_kinds(self.alert)
        self.alert = alert
        if not alert.ok and (was_ok or alert_kinds(alert) != old_kinds):
            self._add_log(now, "alert", "Gateway (canh-bao)", alert.text + " — LED đỏ", "Cảnh báo", "danger")
        elif alert.ok and not was_ok:
            self._add_log(now, "alert", "Gateway (canh-bao)", "Trở về bình thường — LED xanh", "Bình thường", "ok")
        self.emit("alert", self._alert_view())

    def _check_online(self, now):
        fresh = self.sensor_at is not None and now - self.sensor_at < self.STALE_SECONDS
        online = self.mqtt_ok and fresh
        if online == self.online:
            return
        self.online = online
        self.online_since = now
        if online:
            self._add_log(now, "system", "IoT Gateway", "Nhận lại dữ liệu từ Gateway", "Đã kết nối", "ok")
        else:
            why = "mất MQTT" if not self.mqtt_ok else "quá " + str(self.STALE_SECONDS) + " giây không có số mới"
            self._add_log(now, "system", "IoT Gateway", "Mất kết nối Gateway (" + why + ")", "Mất kết nối", "danger")
        self.emit("gateway", self._gateway_view())

    # ---------- nhat ky trong RAM (D5 chua chot) ----------

    def _log_sensors(self, now):
        detail = (
            "Nhiệt độ " + config.fmt_num(self.reading.temp or 0) + "°C, độ ẩm "
            + config.fmt_num(self.reading.humid or 0) + "%, ánh sáng " + config.fmt_num(self.reading.light or 0)
        )
        self._add_log(now, "sensor", "DHT20 (I2C) + ánh sáng (P0)", detail, "Hợp lệ", "neutral")

    def _entry(self, now, kind, source, detail, status, tone):
        entry = {
            "id": self.next_id,
            "at": now,
            "type": kind,
            "source": source,
            "detail": detail,
            "status": status,
            "tone": tone,
        }
        self.next_id += 1
        return entry

    def _add_log(self, now, kind, source, detail, status, tone):
        entry = self._entry(now, kind, source, detail, status, tone)
        self.entries.append(entry)
        if len(self.entries) > MAX_ENTRIES:
            self.entries = self.entries[-MAX_ENTRIES:]
        self.emit("log", entry)

    # ---------- dang du lieu gui trinh duyet (giong web_mock) ----------

    def _gateway_view(self):
        return {"online": self.online, "since": self.online_since, "label": self.label}

    def _sensors_view(self, now):
        at = self.sensor_at if self.sensor_at is not None else now
        return {
            "temp": self.reading.temp,
            "humid": self.reading.humid,
            "light": self.reading.light,
            "at": at,
            "age": round(now - at, 1) if self.sensor_at is not None else 0,
        }

    def _thresholds_view(self):
        return {
            "temp_max": self.limits.temp_max,
            "humid_max": self.limits.humid_max,
            "light_min": self.limits.light_min,
        }

    def _alert_view(self):
        if self.alert is None:
            return {"ok": True, "led": "GREEN", "text": "Chưa có số liệu"}
        return {"ok": self.alert.ok, "led": self.alert.led, "text": self.alert.text}
