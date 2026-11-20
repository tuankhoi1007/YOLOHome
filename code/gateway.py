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
from door import DoorController, format_pin_command, parse_door_ack, parse_servo_pin
from module1 import (
    Reading,
    SensorPublisher,
    open_serial,
    parse_line,
    send_led,
)
from module2 import AlertPublisher, Thresholds, evaluate
from runtime_store import append_jsonl, read_json, write_json


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
        self.clock = time.time
        self.last_seen = self.clock()
        self.told_json = False
        self.next_sample = 0.0
        self.pending_line = ""
        # Cua va nhan dien: luong khac chi bo vao hang, step() moi cham serial.
        self.door = DoorController(config.DOOR_OPEN_SECONDS, lambda: self.clock())
        self._door_queue = queue.Queue()
        self._face_queue = queue.Queue()
        self._pin_sent = False
        self.servo_pin = config.SERVO_PIN
        self.face_loop = None
        self.face_runtime = _face_off()
        self.last_face = None
        self._status_seq = 1
        self._door_cmd_id = 0
        self.status_path = config.FACE_STATUS_PATH
        self.log_path = config.FACE_LOG_PATH
        self.cmd_path = config.DOOR_CMD_PATH

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
        self._arm_cmd_cursor()
        self._ensure_pin()
        self._start_face()

    def set_threshold(self, feed, value):
        """Doi nguong tu luong khac (web). Di cung duong voi tin MQTT tu feed nguong-*."""
        payload = config.fmt_num(value).encode("utf-8")
        self.incoming.put((config.topic(feed), payload))

    def request_door(self, locked, source):
        """Xin mo hoac khoa cua tu luong khac. step() moi ghi serial."""
        self._door_queue.put((bool(locked), source))

    def submit_face(self, kind, payload):
        """Luong camera goi ham nay. kind la 'status' hoac 'attempt'."""
        self._face_queue.put((kind, payload))

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
        """Mot vong: nhan nguong, lenh cua, doc mot dong USB, so nguong, gui feed va lenh den.

        Lenh cua duoc gui ca khi dang cho mau cam bien ke tiep, de web khong bi qua 3 giay.
        Khong xoa buffer serial trong luc cho: ack DOOR: nam trong buffer do.
        """
        self.drain_thresholds()
        self.drain_face()
        self.drain_door()
        if self._waiting_sample():
            return
        line = self._readline()
        if not line:
            if self.clock() - self.last_seen > 5:
                print("5 giay roi, board khong gui gi qua USB")
                self.last_seen = self.clock()
            return
        self._handle_line(line)

    def _waiting_sample(self):
        if self.clock() >= self.next_sample:
            return False
        self._poll_ready_lines()
        time.sleep(0.05)
        return True

    def _poll_ready_lines(self):
        """Doc nhung dong da nam trong buffer. Giu lai dong cam bien moi nhat."""
        while getattr(self.ser, "in_waiting", 0):
            raw = self.ser.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            if self._take_control(line):
                continue
            self.pending_line = line

    def _readline(self):
        if self.pending_line:
            line = self.pending_line
            self.pending_line = ""
            return line
        raw = self.ser.readline()
        if not raw:
            return ""
        return raw.decode("utf-8", errors="ignore").strip()

    def _handle_line(self, line):
        self.last_seen = self.clock()
        print("Nhan:", line)
        if line.startswith("{") and not self.told_json:
            self.told_json = True
            print("Board in JSON. Lenh den van la LED:RED / LED:GREEN.")
        if self._take_control(line):
            return
        found = parse_line(line)
        if found is None:
            print("Bo qua dong nay. Can dang T:31.2,H:60,L:44")
            return
        self.reading.update(found)
        print("Doc:", self.reading.summary())
        self._tell("on_reading", self.reading)
        self.apply_alert()
        self.next_sample = self.clock() + config.READ_INTERVAL

    def _take_control(self, line):
        """RGB va DOOR la ack, khong phai so lieu. Tra ve True neu da xu ly."""
        if line.startswith("RGB:RED") or line.startswith("RGB:GREEN"):
            print("Board da doi den:", line.split(":", 1)[-1])
            return True
        ack = parse_door_ack(line)
        if ack is None:
            return False
        kind, value = ack
        if kind == "state":
            self.door.ack(value)
            print("Board xac nhan cua:", "dong" if value else "mo")
            self._tell("on_door", self.door.view())
            self._write_status()
        elif kind == "error":
            self.door.clear_pending()
            print("Board bao loi servo:", value)
            self._tell("on_door_error", value)
        elif kind == "pin":
            print("Board nhan chan servo:", value)
        return True

    def drain_face(self):
        while True:
            try:
                kind, payload = self._face_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "status":
                self.face_runtime = payload
                self._tell("on_face_status", payload)
                self._write_status()
            elif kind == "attempt":
                self._log_attempt(payload)
                self._tell("on_face", payload)
                if payload.get("ok"):
                    self.request_door(False, "FaceAI")
                self.last_face = payload
                self._write_status()

    def drain_door(self):
        self._take_file_cmd()
        while True:
            try:
                locked, source = self._door_queue.get_nowait()
            except queue.Empty:
                break
            self._apply_door(locked, source)
        action = self.door.tick()
        if action is not None:
            self._send_door_action(action)

    def _apply_door(self, locked, source):
        action = self.door.request(locked, source)
        self._send_door_action(action)

    def _send_door_action(self, action):
        if action is None:
            return
        if action == "REFRESH":
            self._tell("on_door", self.door.view())
            self._write_status()
            return
        if self.ser is None:
            print("Khong gui duoc lenh cua: chua mo cong COM")
            self.door.clear_pending()
            return
        self._ensure_pin()
        line = "DOOR:" + action + "\n"
        try:
            self.ser.write(line.encode("ascii"))
            self.ser.flush()
        except Exception as exc:
            print("Khong gui duoc lenh cua:", exc)
            self.door.clear_pending()
            return
        print("Lenh cua:", action)

    def _ensure_pin(self):
        if self._pin_sent or self.ser is None:
            return
        try:
            pin = parse_servo_pin(config.SERVO_PIN)
        except ValueError as exc:
            print("SERVO_PIN khong dung:", exc, "- dung P4")
            pin = "P4"
        try:
            self.ser.write((format_pin_command(pin) + "\n").encode("ascii"))
            self.ser.flush()
        except Exception as exc:
            print("Khong gui duoc chan servo:", exc)
            return
        self._pin_sent = True
        self.servo_pin = pin
        print("Lenh servo:", format_pin_command(pin))

    def _arm_cmd_cursor(self):
        """Bo qua lenh cua da nam trong file tu lan chay truoc, tranh mo cua luc khoi dong."""
        cmd = read_json(self.cmd_path)
        if not cmd:
            return
        try:
            self._door_cmd_id = int(cmd.get("id") or 0)
        except (TypeError, ValueError):
            self._door_cmd_id = 0

    def _take_file_cmd(self):
        cmd = read_json(self.cmd_path)
        if not cmd:
            return
        try:
            cmd_id = int(cmd.get("id") or 0)
        except (TypeError, ValueError):
            return
        if cmd_id <= self._door_cmd_id:
            return
        self._door_cmd_id = cmd_id
        source = cmd.get("source") or "Giao diện web"
        self._apply_door(bool(cmd.get("locked")), source)

    def _log_attempt(self, result):
        if result.get("ok"):
            print(
                "Nhan dien:",
                result.get("name"),
                "diem",
                result.get("score"),
                "nguong",
                result.get("threshold"),
                "chap nhan",
            )
        else:
            print(
                "Nhan dien: tu choi, gan nhat",
                result.get("name"),
                "diem",
                result.get("score"),
                "nguong",
                result.get("threshold"),
            )
        if self.log_path is None:
            return
        append_jsonl(self.log_path, {
            "at": result.get("at"),
            "name": result.get("name"),
            "ok": bool(result.get("ok")),
            "result": "accepted" if result.get("ok") else "rejected",
            "confidence": result.get("confidence"),
            "score": result.get("score"),
            "threshold": result.get("threshold"),
            "metric": result.get("metric"),
            "model": result.get("model"),
        })

    def _write_status(self):
        if self.status_path is None:
            return
        payload = {
            "seq": self._status_seq,
            "at": self.clock(),
            "face": self.last_face,
            "face_runtime": self.face_runtime,
            "door": self.door.view(),
            "servo_pin": self.servo_pin,
            "door_relock": config.DOOR_OPEN_SECONDS,
        }
        self._status_seq += 1
        write_json(self.status_path, payload)

    def _start_face(self):
        if not config.FACE_ENABLE:
            print("Nhan dien: tat (FACE_ENABLE=0). Cua van mo duoc bang nut tren web.")
            self.face_runtime = _face_off()
            self._tell("on_face_status", self.face_runtime)
            self._write_status()
            return
        try:
            import face_runtime

            recognizer = face_runtime.load_recognizer(config.FACE_MODEL_DIR, config.FACE_THRESHOLD)
        except Exception as exc:
            print("Nhan dien: khong bat duoc -", exc)
            self.face_runtime = _face_off()
            self.face_runtime["enabled"] = True
            self.face_runtime["message"] = "Chưa tải được model. Chụp ảnh rồi chạy face_train.py. Cửa vẫn mở bằng nút."
            self._tell("on_face_status", self.face_runtime)
            self._write_status()
            return
        self.face_runtime = recognizer.runtime_status()
        self.face_runtime["camera"] = "starting"
        self.face_runtime["message"] = "Đang mở webcam."
        self._tell("on_face_status", self.face_runtime)
        self.face_loop = face_runtime.FaceLoop(
            recognizer,
            self.submit_face,
            camera_index=config.FACE_CAMERA,
            interval=config.FACE_INTERVAL,
            stable_frames=config.FACE_STABLE_FRAMES,
            miss_reset=config.FACE_MISS_RESET,
        )
        self.face_loop.start()

    def run(self, stop=None):
        """Chay mai, hoac den khi stop (threading.Event) duoc bat."""
        while stop is None or not stop.is_set():
            self.step()

    def close(self):
        if self.face_loop is not None:
            self.face_loop.stop()
        if self.ser is not None:
            self.ser.close()
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()


def _face_off():
    return {
        "enabled": False,
        "ready": False,
        "model": None,
        "detector": "yunet",
        "camera": "off",
        "message": "Nhận diện đang tắt (FACE_ENABLE=0). Cửa vẫn mở được bằng nút Khóa cửa.",
        "threshold": None,
        "metric": None,
        "people": [],
    }


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
