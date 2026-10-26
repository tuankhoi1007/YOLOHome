# -*- coding: utf-8 -*-
"""Du lieu gia lap cho web (Module 5) khi chua noi board va Adafruit.

web_server.py chi goi cac ham cong khai cua MockHome: snapshot, set_thresholds,
command, simulate, log, tick. Ban that (web_live.py, ROADMAP 5.6) phai co dung cac
ham nay de trang web khong phai sua.

Moi thay doi bao ra ngoai qua emit(kind, data); web_server.py day xuong trinh duyet bang SSE.
Chuoi trong du lieu tra ve la chu hien tren giao dien nen co dau.
"""

import random
import threading
import time
from datetime import datetime

import config
from module1 import Reading
from module2 import Thresholds, evaluate

# Board gui khoang 2 giay, gateway lay mau 3 giay (READ_INTERVAL). Gia lap cung nhip 3 giay.
SENSOR_STEP = 3
# Ghi mot dong cam bien vao nhat ky moi phut, de nhat ky khong ngap so do.
SENSOR_LOG_EVERY = 60
# D11: cua tu khoa lai 10 giay sau khi mo.
DOOR_RELOCK = 10
# Nut "Mo phong vuot nguong" giu nhiet do cao trong 30 giay roi tha ve.
OVERHEAT_SECONDS = 30
# Nhiet do bi day len cao hon nguong bao nhieu do khi mo phong.
OVERHEAT_MARGIN = 2.5
PAGE_SIZE = 10
MAX_ENTRIES = 500

# Gia tri giong khung Figma 11:593 de giao dien gia lap nhin quen.
BASE_TEMP = 28.4
BASE_HUMID = 62
BASE_LIGHT = 78

# D11: 4 mau co san cua den (Figma 181:10).
LIGHT_COLORS = (
    ("#ffffff", "Trắng"),
    ("#b8860b", "Vàng cổ điển"),
    ("#9333ea", "Tím"),
    ("#2563eb", "Xanh dương"),
)

# Bo lenh giong noi co dinh (User_Requirements, khong dung LLM).
VOICE_COMMANDS = (
    ("bật đèn", "light", True),
    ("tắt đèn", "light", False),
    ("bật quạt", "fan", True),
    ("tắt quạt", "fan", False),
)

LOG_TYPES = ("sensor", "control", "alert", "face", "voice", "system")
DEVICES = ("light", "fan", "door")
DEVICE_NAMES = {"light": "Đèn LED RGB (P14)", "fan": "Quạt mini", "door": "Khóa cửa (servo)"}
THRESHOLD_FIELDS = ("temp_max", "humid_max", "light_min")


class CommandError(Exception):
    """Loi tra ve cho trinh duyet: status la ma HTTP, message hien tren giao dien."""

    def __init__(self, status, message):
        Exception.__init__(self, message)
        self.status = status
        self.message = message


def _is_number(value):
    # bool la con cua int trong Python, khong chap nhan true/false thay cho so
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def parse_command(device, body):
    """Kiem tra lenh tu web. Tra ve dict thay doi, sai thi nem CommandError(400)."""
    if device not in DEVICES:
        raise CommandError(404, "Không có thiết bị này")
    changes = {}
    if device == "door":
        action = body.get("action")
        if action == "unlock":
            changes["locked"] = False
        elif action == "lock":
            changes["locked"] = True
        else:
            raise CommandError(400, "Lệnh cửa phải là mở hoặc khóa")
        return changes
    if "on" in body:
        if not isinstance(body["on"], bool):
            raise CommandError(400, "Trạng thái bật/tắt không hợp lệ")
        changes["on"] = body["on"]
    if device == "light" and "color" in body:
        allowed = [hex_code for hex_code, name in LIGHT_COLORS]
        if body["color"] not in allowed:
            raise CommandError(400, "Màu không có trong bộ màu")
        changes["color"] = body["color"]
    if device == "fan" and "speed" in body:
        speed = body["speed"]
        if not _is_number(speed) or speed < 0 or speed > 100:
            raise CommandError(400, "Tốc độ quạt phải từ 0 đến 100")
        changes["speed"] = int(round(speed))
    if not changes:
        raise CommandError(400, "Lệnh trống")
    return changes


def parse_thresholds(body, limits):
    """Kiem tra nguong tu web theo khoang cua module2.Thresholds. Sai thi CommandError(400)."""
    values = {}
    for field in THRESHOLD_FIELDS:
        if field not in body:
            continue
        value = body[field]
        if not _is_number(value) or not limits._ok(field, float(value)):
            raise CommandError(400, "Ngưỡng không hợp lệ: " + field)
        values[field] = round(float(value), 1)
    if not values:
        raise CommandError(400, "Chưa có ngưỡng nào để lưu")
    return values


def alert_kinds(alert):
    """Tap loai van de trong cau canh bao, vi du {"Nhiệt độ cao"}. Rong neu binh thuong."""
    if alert is None or alert.ok:
        return set()
    return set(part.split(":")[0].strip() for part in alert.text.split(" | "))


def filter_log(entries, kind="all", date="", query="", page=1):
    """Loc nhat ky, moi nhat truoc, PAGE_SIZE dong mot trang (Figma 7:97)."""
    if kind not in ("all", "") and kind not in LOG_TYPES:
        raise CommandError(400, "Loại nhật ký không hợp lệ")
    day = None
    if date:
        try:
            day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise CommandError(400, "Ngày phải có dạng YYYY-MM-DD")
    text = query.strip().lower()
    found = []
    for entry in reversed(entries):
        if kind not in ("all", "") and entry["type"] != kind:
            continue
        if day is not None and datetime.fromtimestamp(entry["at"]).date() != day:
            continue
        if text and text not in (entry["source"] + " " + entry["detail"]).lower():
            continue
        found.append(entry)
    total = len(found)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(1, page), pages)
    start = (page - 1) * PAGE_SIZE
    return {
        "items": found[start:start + PAGE_SIZE],
        "page": page,
        "pages": pages,
        "total": total,
        "page_size": PAGE_SIZE,
    }


class MockHome:
    """Mot phong gia lap: cam bien troi nhe, thiet bi xac nhan sau MOCK_ACK_MS, cua tu khoa."""

    def __init__(self, emit, clock=time.time, ack_ms=None, rng=None):
        self.emit = emit
        self.clock = clock
        if ack_ms is None:
            ack_ms = config.MOCK_ACK_MS
        self.ack_delay = ack_ms / 1000.0
        self.rng = rng or random.Random()
        # web_server goi tu nhieu luong (moi request mot luong + luong tick)
        self.lock = threading.Lock()
        now = clock()
        self.reading = Reading()
        self.reading.temp = BASE_TEMP
        self.reading.humid = BASE_HUMID
        self.reading.light = BASE_LIGHT
        self.limits = Thresholds()
        self.alert = evaluate(self.reading, self.limits)
        self.online = True
        self.online_since = now
        self.sensor_at = now
        self.next_sensor = now + SENSOR_STEP
        self.next_sensor_log = now + SENSOR_LOG_EVERY
        self.overheat_until = 0
        self.devices = {
            "light": {"on": False, "color": LIGHT_COLORS[1][0], "at": now},
            "fan": {"on": False, "speed": 65, "at": now},
            "door": {"locked": True, "relock_at": None, "at": now},
        }
        self.pending = []
        self.face = None
        self.voice = None
        self.voice_index = 0
        self.entries = []
        self.next_id = 1
        self._add_log(now, "system", "IoT Gateway", "Khởi động web với dữ liệu giả lập", "Khởi tạo", "neutral")
        self._log_sensors(now)

    # ---------- doc trang thai ----------

    def snapshot(self):
        with self.lock:
            now = self.clock()
            return {
                "mode": "mock",
                # Phan nao co du lieu. Ban that (5.6) tat nhung phan chua co hop dong trong PROTOCOL.md.
                "features": {
                    "devices": True,
                    "face": True,
                    "voice": True,
                    "simulate": True,
                    "log": True,
                    "thresholds_write": True,
                },
                "gateway": self._gateway_view(),
                "sensors": self._sensors_view(now),
                "thresholds": self._thresholds_view(),
                "alert": self._alert_view(),
                "devices": {
                    "light": self._device_view("light", now),
                    "fan": self._device_view("fan", now),
                    "door": self._device_view("door", now),
                },
                "face": self.face,
                "voice": self.voice,
                "colors": [{"hex": hex_code, "name": name} for hex_code, name in LIGHT_COLORS],
                "voice_commands": [text for text, device, on in VOICE_COMMANDS],
                "door_relock": DOOR_RELOCK,
            }

    def log(self, kind="all", date="", query="", page=1):
        with self.lock:
            return filter_log(self.entries, kind, date, query, page)

    # ---------- lenh tu web ----------

    def set_thresholds(self, body):
        with self.lock:
            if not self.online:
                raise CommandError(503, "Mất kết nối Gateway, chưa lưu được ngưỡng")
            values = parse_thresholds(body, self.limits)
            now = self.clock()
            for field in values:
                setattr(self.limits, field, values[field])
            parts = []
            if "temp_max" in values:
                parts.append("nhiệt > " + config.fmt_num(values["temp_max"]) + "°C")
            if "humid_max" in values:
                parts.append("ẩm > " + config.fmt_num(values["humid_max"]) + "%")
            if "light_min" in values:
                parts.append("sáng < " + config.fmt_num(values["light_min"]))
            self._add_log(now, "control", "Giao diện web", "Đổi ngưỡng: " + ", ".join(parts), "Đã lưu", "ok")
            self.emit("thresholds", self._thresholds_view())
            self._check_alert(now)
            return self._thresholds_view()

    def command(self, device, body, source="Giao diện web"):
        """Gui lenh. Tra ve ngay (202); xac nhan cua thiet bi den sau qua emit('device')."""
        with self.lock:
            changes = parse_command(device, body)
            if not self.online:
                raise CommandError(503, "Không thể gửi lệnh: mất kết nối Gateway")
            self._queue(device, changes, source)
            return {"device": device, "status": "sent", "requested": changes}

    def simulate(self, kind):
        """Nut gia lap tren dashboard (D11). Chi co o ban mock."""
        with self.lock:
            now = self.clock()
            if kind == "overheat":
                self.overheat_until = now + OVERHEAT_SECONDS
                self.next_sensor = now
                self._add_log(now, "system", "Giao diện web", "Mô phỏng vượt ngưỡng nhiệt độ trong 30 giây", "Mô phỏng", "neutral")
            elif kind == "offline":
                self._set_online(False, now)
            elif kind == "online":
                self._set_online(True, now)
            elif kind == "face_owner":
                self._face(now, True)
            elif kind == "face_stranger":
                self._face(now, False)
            elif kind == "voice":
                self._voice(now)
            else:
                raise CommandError(404, "Không có kiểu mô phỏng này")
            return {"ok": True}

    # ---------- nhip dong ho, web_server goi khoang 0.5 giay ----------

    def tick(self):
        with self.lock:
            now = self.clock()
            self._apply_due(now)
            self._relock(now)
            if self.online and now >= self.next_sensor:
                self._step_sensors(now)

    # ---------- phan ben trong ----------

    def _queue(self, device, changes, source):
        self.pending.append((self.clock() + self.ack_delay, device, changes, source))

    def _apply_due(self, now):
        waiting = []
        for item in self.pending:
            due, device, changes, source = item
            if due > now:
                waiting.append(item)
                continue
            # Mat ket noi luc thiet bi le ra xac nhan: lenh mat, web tu bao qua thoi gian cho.
            if not self.online:
                continue
            self._confirm(now, device, changes, source)
        self.pending = waiting

    def _confirm(self, now, device, changes, source):
        state = self.devices[device]
        for key in changes:
            state[key] = changes[key]
        state["at"] = now
        if device == "door":
            if state["locked"]:
                state["relock_at"] = None
                detail = "Khóa cửa"
            else:
                state["relock_at"] = now + DOOR_RELOCK
                detail = "Mở khóa cửa, tự khóa sau " + str(DOOR_RELOCK) + " giây"
        elif device == "light":
            detail = "Bật đèn" if state["on"] else "Tắt đèn"
            if state["on"]:
                detail += " — màu " + self._color_name(state["color"])
        else:
            detail = "Bật quạt" if state["on"] else "Tắt quạt"
            if state["on"]:
                detail += " — tốc độ " + str(state["speed"]) + "%"
        self._add_log(now, "control", DEVICE_NAMES[device], detail + " (" + source + ")", "Đã nhận", "ok")
        self.emit("device", self._device_view(device, now))

    def _relock(self, now):
        door = self.devices["door"]
        if door["locked"] or door["relock_at"] is None or now < door["relock_at"]:
            return
        door["locked"] = True
        door["relock_at"] = None
        door["at"] = now
        self._add_log(now, "control", DEVICE_NAMES["door"], "Tự khóa sau " + str(DOOR_RELOCK) + " giây", "Đã khóa", "ok")
        self.emit("device", self._device_view("door", now))

    def _step_sensors(self, now):
        target = BASE_TEMP
        if now < self.overheat_until:
            target = self.limits.temp_max + OVERHEAT_MARGIN
        # Di nua quang duong ve muc tieu moi nhip, cong nhieu nho cho giong cam bien that.
        temp = self.reading.temp + (target - self.reading.temp) * 0.5 + self.rng.uniform(-0.1, 0.1)
        humid = self.reading.humid + (BASE_HUMID - self.reading.humid) * 0.3 + self.rng.uniform(-0.5, 0.5)
        light = self.reading.light + (BASE_LIGHT - self.reading.light) * 0.3 + self.rng.uniform(-1, 1)
        self.reading.temp = round(temp, 1)
        self.reading.humid = round(min(100, max(0, humid)), 1)
        self.reading.light = round(min(100, max(0, light)), 1)
        self.sensor_at = now
        self.next_sensor = now + SENSOR_STEP
        self.emit("sensors", self._sensors_view(now))
        self._check_alert(now)
        if now >= self.next_sensor_log:
            self._log_sensors(now)
            self.next_sensor_log = now + SENSOR_LOG_EVERY

    def _check_alert(self, now):
        alert = evaluate(self.reading, self.limits)
        if alert is None or alert.text == self.alert.text:
            return
        was_ok = self.alert.ok
        old_kinds = alert_kinds(self.alert)
        self.alert = alert
        # So trong cau canh bao doi moi nhip (31.5 -> 31.9); chi ghi nhat ky khi bat dau
        # canh bao hoac khi loai van de doi (them/bot nhiet, am, sang).
        if not alert.ok and (was_ok or alert_kinds(alert) != old_kinds):
            self._add_log(now, "alert", "DHT20 + ánh sáng", alert.text + " — LED đỏ", "Cảnh báo", "danger")
        elif alert.ok and not was_ok:
            self._add_log(now, "alert", "DHT20 + ánh sáng", "Trở về bình thường — LED xanh", "Bình thường", "ok")
        self.emit("alert", self._alert_view())

    def _set_online(self, online, now):
        if self.online == online:
            return
        self.online = online
        self.online_since = now
        if online:
            self._add_log(now, "system", "IoT Gateway", "Kết nối lại Adafruit IO / Gateway", "Đã kết nối", "ok")
            # Lay mau ngay de the cam bien het "khong co du lieu moi"
            self.next_sensor = now
        else:
            self._add_log(now, "system", "IoT Gateway", "Mất kết nối Adafruit IO / Gateway (mô phỏng)", "Mất kết nối", "danger")
        self.emit("gateway", self._gateway_view())

    def _face(self, now, ok):
        if ok:
            self.face = {"ok": True, "name": "Chủ nhà", "confidence": 98.4, "at": now}
            if self.online:
                self._add_log(now, "face", "Camera laptop (Gateway)", "Nhận diện Chủ nhà (98.4%) — mở khóa cửa", "Thành công", "ok")
                self._queue("door", {"locked": False}, "FaceAI")
            else:
                self._add_log(now, "face", "Camera laptop (Gateway)", "Nhận diện Chủ nhà nhưng không gửi được lệnh mở cửa", "Lỗi", "danger")
        else:
            self.face = {"ok": False, "name": None, "confidence": 41.2, "at": now}
            self._add_log(now, "face", "Camera laptop (Gateway)", "Khuôn mặt không xác định — từ chối mở khóa", "Từ chối", "danger")
        self.emit("face", self.face)

    def _voice(self, now):
        text, device, on = VOICE_COMMANDS[self.voice_index % len(VOICE_COMMANDS)]
        self.voice_index += 1
        self.voice = {"text": text, "at": now}
        self.emit("voice", self.voice)
        if self.online:
            self._add_log(now, "voice", "Micro laptop (Gateway)", "Lệnh \"" + text + "\"", "Đã gửi", "ok")
            self._queue(device, {"on": on}, "giọng nói")
        else:
            self._add_log(now, "voice", "Micro laptop (Gateway)", "Lệnh \"" + text + "\" không gửi được", "Lỗi", "danger")

    def _log_sensors(self, now):
        detail = (
            "Nhiệt độ " + config.fmt_num(self.reading.temp) + "°C, độ ẩm "
            + config.fmt_num(self.reading.humid) + "%, ánh sáng " + config.fmt_num(self.reading.light)
        )
        self._add_log(now, "sensor", "DHT20 (I2C) + ánh sáng (P0)", detail, "Hợp lệ", "neutral")

    def _add_log(self, now, kind, source, detail, status, tone):
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
        self.entries.append(entry)
        if len(self.entries) > MAX_ENTRIES:
            self.entries = self.entries[-MAX_ENTRIES:]
        self.emit("log", entry)

    def _color_name(self, hex_code):
        for code, name in LIGHT_COLORS:
            if code == hex_code:
                return name
        return hex_code

    def _gateway_view(self):
        return {"online": self.online, "since": self.online_since, "label": "Giả lập"}

    def _sensors_view(self, now):
        # "age" tinh tren laptop de dien thoai lech dong ho van hien dung "x giay truoc"
        return {
            "temp": self.reading.temp,
            "humid": self.reading.humid,
            "light": self.reading.light,
            "at": self.sensor_at,
            "age": round(now - self.sensor_at, 1),
        }

    def _thresholds_view(self):
        return {
            "temp_max": self.limits.temp_max,
            "humid_max": self.limits.humid_max,
            "light_min": self.limits.light_min,
        }

    def _alert_view(self):
        return {"ok": self.alert.ok, "led": self.alert.led, "text": self.alert.text}

    def _device_view(self, device, now):
        state = self.devices[device]
        view = {"device": device, "at": state["at"]}
        if device == "door":
            view["locked"] = state["locked"]
            view["relock_in"] = None
            if state["relock_at"] is not None:
                view["relock_in"] = max(0, round(state["relock_at"] - now, 1))
        else:
            view["on"] = state["on"]
            if device == "light":
                view["color"] = state["color"]
            else:
                view["speed"] = state["speed"]
        return view
