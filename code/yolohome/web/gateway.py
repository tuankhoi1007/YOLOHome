# -*- coding: utf-8 -*-
"""Web chay luon Module 1 + 2 + 3 va nut quet mat (WEB_DATA=gateway): mot chuong trinh cho buoi demo.

yolohome.web.server tao GatewayHome. GatewayHome chay yolohome.gateway.Gateway
(doc USB, gui feed, so nguong, gui LED:RED / LED:GREEN) trong mot luong rieng, va nhan
moi so doc duoc qua listener de day thang len web, khong phai doi Adafruit gui lai.

Moi xu ly so lieu, canh bao, nhat ky ke thua tu yolohome.web.live.LiveHome. O day chi doi
nguon du lieu: thay vi nghe MQTT, nghe luong gateway.

Khong chay cung luc voi python -m yolohome.gateway hay OhStem: ca ba deu can cung mot cong COM.
"""

import threading
import time

from yolohome import config
from yolohome.gateway import Gateway
from yolohome.module1 import MIN_COMMAND_GAP, NORMALIZERS
from yolohome.module2 import ThresholdPublisher
from yolohome.web.live import LiveHome
from yolohome.web.mock import DEVICE_NAMES, DOOR_RELOCK, LIGHT_COLORS, CommandError, parse_command

# Ten thiet bi tren web <-> feed/thiet bi cua gateway (docs/PROTOCOL.md v0.2.0)
WEB_TO_GATEWAY = {"light": "den", "fan": "quat", "door": "cua"}
GATEWAY_TO_WEB = {"den": "light", "quat": "fan", "cua": "door"}


class GatewayHome(LiveHome):
    MODE = "gateway"
    # Board gui khoang 2 giay, gateway lay mau 3 giay (READ_INTERVAL). 10 giay khong co so = mat board.
    STALE_SECONDS = 10

    def __init__(self, emit, clock=time.time, connect=True, gateway=None):
        # gateway: truyen vao khi kiem thu (khong mo cong COM that)
        self.gateway = gateway
        # Trang thai that cua thiet bi (do ack cua board). color/speed nho lan chon cuoi de bat lai dung.
        now = clock()
        self.devices = {
            "light": {"on": False, "color": LIGHT_COLORS[1][0], "at": now},
            "fan": {"on": False, "speed": 65, "at": now},
            "door": {"locked": True, "relock_at": None, "at": now},
        }
        self.last_sent = {}
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

    # ---------- thiet bi (Module 3) ----------

    def snapshot(self):
        view = LiveHome.snapshot(self)
        with self.lock:
            now = self.clock()
            view["features"]["devices"] = True
            view["features"]["door"] = True
            view["features"]["face"] = self.gateway is not None and getattr(self.gateway, "face", None) is not None
            view["devices"] = {name: self._device_view(name, now) for name in self.devices}
            view["colors"] = [{"hex": code, "name": name} for code, name in LIGHT_COLORS]
        return view

    def command(self, device, body, source="Giao diện web"):
        """Kiem tra lenh, doi ra gia tri feed roi dua vao gateway. Xac nhan den sau qua su kien 'device'."""
        with self.lock:
            changes = parse_command(device, body)
            if not self.online:
                raise CommandError(503, "Không thể gửi lệnh: mất kết nối Gateway")
            now = self.clock()
            last = self.last_sent.get(device)
            # Chong bam lien tuc: cung mot thiet bi cach nhau it nhat 2 giay (PROTOCOL v0.2.0)
            if last is not None and now - last < MIN_COMMAND_GAP:
                raise CommandError(429, "Vừa gửi lệnh. Đợi 2 giây rồi bấm lại.")
            target = self._target_value(device, changes)
            self.last_sent[device] = now
            key = WEB_TO_GATEWAY[device]
            if target == self.gateway.devices.confirmed[key] and key not in self.gateway.devices.pending:
                # Thiet bi da o trang thai nay (vd doi mau luc den tat): khong co gi de gui, nho lua chon va tra loi ngay
                self._remember(device, changes)
                self.emit("device", self._device_view(device, now))
            else:
                self.gateway.command(key, target, source)
            return {"device": device, "status": "sent", "requested": changes}

    def scan_face(self, source="Giao diện web"):
        """Bat dau mot lan quet. Ket qua den sau qua su kien 'face'; dung thi gateway tu mo cua."""
        if self.gateway is None or not hasattr(self.gateway, "scan_face"):
            raise CommandError(503, "Nhận diện khuôn mặt đang tắt.")
        status = self.gateway.scan_face(source)
        if status == "started":
            return {"status": "started"}
        if status == "busy":
            raise CommandError(409, "Webcam đang bận. Đợi lần quét hoặc đăng ký xong rồi bấm lại.")
        raise CommandError(503, "Nhận diện khuôn mặt đang tắt. Kiểm tra FACE_ENABLE, OpenCV và webcam.")

    def enroll_face(self, name):
        """Kiem tra ten roi mo webcam. Mat khau da duoc may chu kiem tra truoc do."""
        if self.gateway is None or not hasattr(self.gateway, "enroll_face"):
            raise CommandError(503, "Đăng ký khuôn mặt đang tắt.")
        from yolohome.face.enroll import check_name

        checked = check_name(name)
        if checked is None:
            raise CommandError(400, "Tên chỉ dùng chữ không dấu, số, _ hoặc -, tối đa 32 ký tự. Ví dụ: Minh.")
        status = self.gateway.enroll_face(checked)
        if status == "started":
            return {"status": "started", "name": checked}
        if status == "busy":
            raise CommandError(409, "Webcam đang bận. Đợi lần quét hoặc đăng ký xong rồi bấm lại.")
        raise CommandError(503, "Nhận diện khuôn mặt đang tắt. Kiểm tra FACE_ENABLE, OpenCV và webcam.")

    def on_enroll(self, result):
        self.incoming.put(("enroll", result))

    def face_frames(self):
        if self.gateway is None:
            return None
        return getattr(self.gateway, "frames", None)

    def face_action(self, action):
        if self.gateway is None or not hasattr(self.gateway, "face_action"):
            raise CommandError(503, "Điều khiển webcam đang tắt.")
        status = self.gateway.face_action(action)
        if status == "idle":
            raise CommandError(409, "Chưa có phiên đăng ký đang chạy.")
        if status != "ok":
            raise CommandError(400, "Không có lệnh này.")
        return {"ok": True}

    def on_face(self, result):
        # Goi tu luong gateway: chi bo vao hang doi
        self.incoming.put(("face", result))

    def _target_value(self, device, changes):
        """Gia tri feed (da chuan hoa) ung voi lenh tren web."""
        state = self.devices[device]
        if device == "door":
            return "CLOSE" if changes["locked"] else "OPEN"
        on = changes.get("on", state["on"])
        if device == "light":
            if not on:
                return "OFF"
            return NORMALIZERS["den"](changes.get("color", state["color"]))
        if not on:
            return "0"
        return NORMALIZERS["quat"](changes.get("speed", state["speed"]))

    def _remember(self, device, changes):
        state = self.devices[device]
        if "color" in changes:
            state["color"] = changes["color"]
        if "speed" in changes:
            state["speed"] = changes["speed"]

    def on_device(self, device, value, ok, source, reason):
        # Goi tu luong gateway: chi bo vao hang doi
        self.incoming.put(("device", (device, value, ok, source, reason)))

    def _take_device(self, now, device, value, ok, source, reason):
        name = GATEWAY_TO_WEB[device]
        label = DEVICE_NAMES[name]
        if not ok:
            self._add_log(now, "control", label, reason + " (" + source + ")", "Lỗi", "danger")
            return
        state = self.devices[name]
        state["at"] = now
        if name == "door":
            state["locked"] = value == "CLOSE"
            if state["locked"]:
                state["relock_at"] = None
                detail = "Tự khóa sau " + str(DOOR_RELOCK) + " giây" if source == "Board" else "Khóa cửa"
            else:
                state["relock_at"] = now + DOOR_RELOCK
                detail = "Mở khóa cửa, tự khóa sau " + str(DOOR_RELOCK) + " giây"
        elif name == "light":
            state["on"] = value != "OFF"
            if state["on"]:
                state["color"] = value
                detail = "Bật đèn — màu " + self._color_name(value)
            else:
                detail = "Tắt đèn"
        else:
            speed = int(value)
            state["on"] = speed > 0
            if state["on"]:
                state["speed"] = speed
                detail = "Bật quạt — tốc độ " + str(speed) + "%"
            else:
                detail = "Tắt quạt"
        self._add_log(now, "control", label, detail + " (" + source + ")", "Đã nhận", "ok")
        self.emit("device", self._device_view(name, now))

    def _color_name(self, hex_code):
        for code, name in LIGHT_COLORS:
            if code == hex_code:
                return name
        return hex_code

    def _device_view(self, name, now):
        state = self.devices[name]
        view = {"device": name, "at": state["at"]}
        if name == "door":
            view["locked"] = state["locked"]
            view["relock_in"] = None
            if state["relock_at"] is not None:
                view["relock_in"] = max(0, round(state["relock_at"] - now, 1))
        else:
            view["on"] = state["on"]
            if name == "light":
                view["color"] = state["color"]
            else:
                view["speed"] = state["speed"]
        return view
