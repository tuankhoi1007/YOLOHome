# -*- coding: utf-8 -*-
"""Kiem tra web (Module 5): dang nhap, du lieu gia lap, API.

Dat bien moi truong gia truoc khi import config, de khong phu thuoc .env that.
May chu thu chi mo tren 127.0.0.1, khong ra Internet, khong mo cong COM.
"""

import os

FAKE_ENV = {
    "AIO_USERNAME": "test-user",
    "AIO_KEY": "test-key",
    "TEMP_MAX": "32",
    "HUMID_MAX": "80",
    "LIGHT_MIN": "20",
    "WEB_PASSWORD": "test-password",
    "WEB_DATA": "mock",
    "MOCK_ACK_MS": "900",
}
for _key, _value in FAKE_ENV.items():
    os.environ[_key] = _value

import http.client  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import threading  # noqa: E402
import unittest  # noqa: E402

import module2  # noqa: E402
import web_mock  # noqa: E402
import web_server  # noqa: E402
from web_mock import CommandError, MockHome  # noqa: E402


class FakeClock:
    def __init__(self, now=1_800_000_000.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class Recorder:
    """Thay cho EventHub.publish: ghi lai moi su kien."""

    def __init__(self):
        self.events = []

    def __call__(self, kind, data):
        self.events.append((kind, data))

    def kinds(self):
        return [kind for kind, data in self.events]

    def last(self, kind):
        for event_kind, data in reversed(self.events):
            if event_kind == kind:
                return data
        return None


def make_home(ack_ms=900):
    clock = FakeClock()
    events = Recorder()
    home = MockHome(events, clock=clock, ack_ms=ack_ms, rng=random.Random(1))
    return home, clock, events


class SessionsTest(unittest.TestCase):
    def test_right_password_gives_token(self):
        sessions = web_server.Sessions("secret", clock=FakeClock())
        token, problem = sessions.login("secret")
        self.assertIsNone(problem)
        self.assertTrue(sessions.check(token))

    def test_wrong_password(self):
        sessions = web_server.Sessions("secret", clock=FakeClock())
        token, problem = sessions.login("Secret")
        self.assertIsNone(token)
        self.assertEqual(problem, "wrong")

    def test_empty_password_never_logs_in(self):
        sessions = web_server.Sessions("", clock=FakeClock())
        token, problem = sessions.login("")
        self.assertIsNone(token)
        self.assertEqual(problem, "wrong")

    def test_lock_after_five_failures_then_unlock(self):
        clock = FakeClock()
        sessions = web_server.Sessions("secret", clock=clock)
        for _ in range(web_server.MAX_FAILS):
            sessions.login("bad")
        self.assertEqual(sessions.login("secret"), (None, "locked"))
        clock.advance(web_server.FAIL_WINDOW + 1)
        token, problem = sessions.login("secret")
        self.assertIsNone(problem)
        self.assertTrue(sessions.check(token))

    def test_session_expires(self):
        clock = FakeClock()
        sessions = web_server.Sessions("secret", clock=clock)
        token, _ = sessions.login("secret")
        clock.advance(web_server.SESSION_SECONDS + 1)
        self.assertFalse(sessions.check(token))

    def test_logout(self):
        sessions = web_server.Sessions("secret", clock=FakeClock())
        token, _ = sessions.login("secret")
        sessions.logout(token)
        self.assertFalse(sessions.check(token))
        self.assertFalse(sessions.check(None))


class ParseTest(unittest.TestCase):
    def test_light_command(self):
        self.assertEqual(
            web_mock.parse_command("light", {"on": True, "color": "#9333ea"}),
            {"on": True, "color": "#9333ea"},
        )

    def test_rejects_bad_commands(self):
        bad = (
            ("light", {"on": "yes"}),
            ("light", {"color": "#000000"}),
            ("fan", {"speed": 101}),
            ("fan", {"speed": True}),
            ("fan", {}),
            ("door", {"action": "open"}),
        )
        for device, body in bad:
            with self.assertRaises(CommandError) as caught:
                web_mock.parse_command(device, body)
            self.assertEqual(caught.exception.status, 400, (device, body))

    def test_unknown_device(self):
        with self.assertRaises(CommandError) as caught:
            web_mock.parse_command("pump", {"on": True})
        self.assertEqual(caught.exception.status, 404)

    def test_fan_speed_rounded(self):
        self.assertEqual(web_mock.parse_command("fan", {"speed": 64.6}), {"speed": 65})

    def test_thresholds_use_module2_ranges(self):
        home, _, _ = make_home()
        self.assertEqual(
            web_mock.parse_thresholds({"temp_max": 31, "light_min": 30}, home.limits),
            {"temp_max": 31.0, "light_min": 30.0},
        )
        # Nhiet do 0-80 nhu PROTOCOL v0.1.0
        for body in ({"temp_max": 81}, {"humid_max": -1}, {"light_min": "30"}, {}):
            with self.assertRaises(CommandError):
                web_mock.parse_thresholds(body, home.limits)


class MockHomeTest(unittest.TestCase):
    def test_snapshot_shape(self):
        home, _, _ = make_home()
        state = home.snapshot()
        for key in ("gateway", "sensors", "thresholds", "alert", "devices", "colors", "voice_commands"):
            self.assertIn(key, state)
        self.assertTrue(state["gateway"]["online"])
        self.assertEqual(state["alert"]["text"], "Bình thường")
        self.assertEqual(len(state["colors"]), 4)

    def test_command_confirms_after_ack_delay(self):
        home, clock, events = make_home(ack_ms=900)
        result = home.command("light", {"on": True})
        self.assertEqual(result["status"], "sent")
        home.tick()
        self.assertIsNone(events.last("device"))
        clock.advance(1.0)
        home.tick()
        self.assertEqual(events.last("device")["on"], True)
        self.assertTrue(home.snapshot()["devices"]["light"]["on"])

    def test_offline_rejects_commands_and_drops_pending(self):
        home, clock, events = make_home()
        home.command("fan", {"on": True})
        home.simulate("offline")
        self.assertFalse(events.last("gateway")["online"])
        with self.assertRaises(CommandError) as caught:
            home.command("fan", {"on": False})
        self.assertEqual(caught.exception.status, 503)
        clock.advance(2)
        home.tick()
        # Lenh dang cho bi mat: web phai tu bao qua thoi gian cho
        self.assertIsNone(events.last("device"))
        self.assertFalse(home.snapshot()["devices"]["fan"]["on"])

    def test_offline_stops_sensor_updates(self):
        home, clock, events = make_home()
        home.simulate("offline")
        before = len([kind for kind in events.kinds() if kind == "sensors"])
        clock.advance(10)
        home.tick()
        after = len([kind for kind in events.kinds() if kind == "sensors"])
        self.assertEqual(before, after)
        self.assertGreater(home.snapshot()["sensors"]["age"], 9)

    def test_door_unlocks_then_relocks_after_10_seconds(self):
        home, clock, events = make_home()
        home.command("door", {"action": "unlock"})
        clock.advance(1)
        home.tick()
        door = events.last("device")
        self.assertFalse(door["locked"])
        self.assertAlmostEqual(door["relock_in"], web_mock.DOOR_RELOCK, delta=0.2)
        clock.advance(web_mock.DOOR_RELOCK - 1)
        home.tick()
        self.assertFalse(home.snapshot()["devices"]["door"]["locked"])
        clock.advance(1.5)
        home.tick()
        self.assertTrue(events.last("device")["locked"])
        self.assertIsNone(events.last("device")["relock_in"])

    def test_overheat_raises_alert_with_module2_text(self):
        home, clock, events = make_home()
        home.simulate("overheat")
        for _ in range(6):
            home.tick()
            clock.advance(web_mock.SENSOR_STEP)
        alert = events.last("alert")
        self.assertFalse(alert["ok"])
        self.assertEqual(alert["led"], "RED")
        self.assertTrue(alert["text"].startswith("Nhiệt độ cao: "))
        self.assertEqual(home.log(kind="alert")["items"][0]["tone"], "danger")

    def test_threshold_change_reevaluates_alert(self):
        home, _, events = make_home()
        home.set_thresholds({"temp_max": 20})
        self.assertEqual(events.last("thresholds")["temp_max"], 20.0)
        self.assertFalse(events.last("alert")["ok"])

    def test_thresholds_blocked_offline(self):
        home, _, _ = make_home()
        home.simulate("offline")
        with self.assertRaises(CommandError) as caught:
            home.set_thresholds({"temp_max": 30})
        self.assertEqual(caught.exception.status, 503)

    def test_face_owner_opens_door_stranger_does_not(self):
        home, clock, events = make_home()
        home.simulate("face_stranger")
        self.assertFalse(events.last("face")["ok"])
        clock.advance(2)
        home.tick()
        self.assertTrue(home.snapshot()["devices"]["door"]["locked"])
        home.simulate("face_owner")
        clock.advance(1)
        home.tick()
        self.assertFalse(home.snapshot()["devices"]["door"]["locked"])

    def test_manual_unlock_works_after_face_rejected(self):
        # Cua phai mo duoc tu giao dien khi nhan dien that bai (CLAUDE.md)
        home, clock, _ = make_home()
        home.simulate("face_stranger")
        home.command("door", {"action": "unlock"})
        clock.advance(1)
        home.tick()
        self.assertFalse(home.snapshot()["devices"]["door"]["locked"])

    def test_voice_cycles_fixed_commands(self):
        home, clock, events = make_home()
        home.simulate("voice")
        self.assertEqual(events.last("voice")["text"], "bật đèn")
        clock.advance(1)
        home.tick()
        self.assertTrue(home.snapshot()["devices"]["light"]["on"])
        home.simulate("voice")
        self.assertEqual(events.last("voice")["text"], "tắt đèn")

    def test_unknown_simulation(self):
        home, _, _ = make_home()
        with self.assertRaises(CommandError):
            home.simulate("explode")


class AlertLogTest(unittest.TestCase):
    def test_alert_kinds(self):
        home, _, _ = make_home()
        self.assertEqual(web_mock.alert_kinds(home.alert), set())
        alert = module2.Alert(False, "RED", "Nhiệt độ cao: 33°C (ngưỡng 30) | Ánh sáng thấp: 10 (ngưỡng 20)")
        self.assertEqual(web_mock.alert_kinds(alert), {"Nhiệt độ cao", "Ánh sáng thấp"})

    def test_rising_temperature_logs_one_alert(self):
        # So trong cau canh bao doi moi nhip; nhat ky chi ghi luc bat dau canh bao
        home, clock, events = make_home()
        home.simulate("overheat")
        for _ in range(8):
            home.tick()
            clock.advance(web_mock.SENSOR_STEP)
        self.assertEqual(home.log(kind="alert")["total"], 1)
        self.assertGreater(len([kind for kind in events.kinds() if kind == "alert"]), 1)


class LiveHomeTest(unittest.TestCase):
    """web_live.LiveHome voi connect=False: dua tin MQTT gia vao hang doi, khong mo mang."""

    def make_live(self):
        import web_live

        clock = FakeClock()
        events = Recorder()
        home = web_live.LiveHome(events, clock=clock, connect=False)
        return home, clock, events, web_live

    def test_snapshot_marks_missing_parts(self):
        home, _, _, _ = self.make_live()
        state = home.snapshot()
        self.assertEqual(state["mode"], "live")
        self.assertFalse(state["features"]["devices"])
        self.assertFalse(state["features"]["thresholds_write"])
        self.assertFalse(state["gateway"]["online"])
        self.assertIsNone(state["devices"])

    def test_sensor_message_brings_gateway_online(self):
        home, clock, events, _ = self.make_live()
        home.incoming.put(("mqtt", True))
        home.incoming.put(("feed", ("nhiet-do", "29.5")))
        home.tick()
        self.assertEqual(events.last("sensors")["temp"], 29.5)
        self.assertTrue(events.last("gateway")["online"])

    def test_gateway_goes_offline_when_stale(self):
        home, clock, events, web_live = self.make_live()
        home.incoming.put(("mqtt", True))
        home.incoming.put(("feed", ("do-am", "60")))
        home.tick()
        clock.advance(web_live.LiveHome.STALE_SECONDS + 1)
        home.tick()
        self.assertFalse(events.last("gateway")["online"])

    def test_alert_feed_text_is_used(self):
        home, _, events, _ = self.make_live()
        home.incoming.put(("feed", ("canh-bao", "Nhiệt độ cao: 33°C (ngưỡng 32)")))
        home.tick()
        alert = events.last("alert")
        self.assertFalse(alert["ok"])
        self.assertEqual(alert["led"], "RED")
        home.incoming.put(("feed", ("canh-bao", "Bình thường")))
        home.tick()
        self.assertTrue(events.last("alert")["ok"])

    def test_threshold_feed_updates_limits(self):
        home, _, events, _ = self.make_live()
        home.incoming.put(("feed", ("nguong-nhiet", "28")))
        home.tick()
        self.assertEqual(events.last("thresholds")["temp_max"], 28.0)

    def test_writes_are_refused_without_contract(self):
        home, _, _, _ = self.make_live()
        for call in (
            lambda: home.command("light", {"on": True}),
            lambda: home.set_thresholds({"temp_max": 30}),
            lambda: home.simulate("overheat"),
        ):
            with self.assertRaises(CommandError):
                call()


class LogTest(unittest.TestCase):
    def make_entries(self, count):
        entries = []
        for index in range(count):
            entries.append({
                "id": index + 1,
                "at": 1_800_000_000.0 + index * 60,
                "type": "control" if index % 2 else "sensor",
                "source": "Quạt mini" if index % 2 else "DHT20",
                "detail": "Bật quạt" if index % 2 else "Nhiệt độ 28",
                "status": "Đã nhận",
                "tone": "ok",
            })
        return entries

    def test_newest_first_and_pages(self):
        result = web_mock.filter_log(self.make_entries(25), page=1)
        self.assertEqual(result["total"], 25)
        self.assertEqual(result["pages"], 3)
        self.assertEqual(result["items"][0]["id"], 25)
        self.assertEqual(len(web_mock.filter_log(self.make_entries(25), page=3)["items"]), 5)
        # Trang qua lon thi ve trang cuoi
        self.assertEqual(web_mock.filter_log(self.make_entries(25), page=99)["page"], 3)

    def test_filter_type_and_query(self):
        entries = self.make_entries(10)
        self.assertEqual(web_mock.filter_log(entries, kind="control")["total"], 5)
        self.assertEqual(web_mock.filter_log(entries, query="QUẠT")["total"], 5)
        self.assertEqual(web_mock.filter_log(entries, query="khong-co")["total"], 0)

    def test_bad_filters(self):
        with self.assertRaises(CommandError):
            web_mock.filter_log([], kind="pump")
        with self.assertRaises(CommandError):
            web_mock.filter_log([], date="29/09/2026")


class ServerTest(unittest.TestCase):
    """Chay may chu that tren 127.0.0.1, cong ngau nhien."""

    @classmethod
    def setUpClass(cls):
        cls.clock = FakeClock()
        cls.hub = web_server.EventHub()
        cls.home = MockHome(cls.hub.publish, clock=cls.clock, ack_ms=0, rng=random.Random(1))
        app = web_server.App(cls.home, web_server.Sessions("secret"), cls.hub)
        cls.server = web_server.make_server(app, "127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, method, path, body=None, cookie=None, content_type="application/json"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {}
        raw = None
        if body is not None:
            raw = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = content_type
        if cookie:
            headers["Cookie"] = cookie
        conn.request(method, path, body=raw, headers=headers)
        response = conn.getresponse()
        data = response.read()
        result = (response.status, dict(response.getheaders()), data)
        conn.close()
        return result

    def login(self):
        status, headers, _ = self.call("POST", "/api/login", {"password": "secret"})
        self.assertEqual(status, 200)
        return headers["Set-Cookie"].split(";")[0]

    def test_api_needs_login(self):
        status, _, data = self.call("GET", "/api/state")
        self.assertEqual(status, 401)
        self.assertIn("error", json.loads(data))

    def test_private_page_redirects_to_login(self):
        status, headers, _ = self.call("GET", "/")
        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], "/login.html")

    def test_login_cookie_flags(self):
        status, headers, _ = self.call("POST", "/api/login", {"password": "secret"})
        self.assertEqual(status, 200)
        cookie = headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)

    def test_wrong_password_401(self):
        status, _, _ = self.call("POST", "/api/login", {"password": "nope"})
        self.assertEqual(status, 401)

    def test_state_and_command_with_cookie(self):
        cookie = self.login()
        status, _, data = self.call("GET", "/api/state", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["mode"], "mock")
        status, _, data = self.call("POST", "/api/devices/fan", {"on": True, "speed": 40}, cookie=cookie)
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(data)["requested"], {"on": True, "speed": 40})
        status, _, _ = self.call("POST", "/api/devices/fan", {"speed": 400}, cookie=cookie)
        self.assertEqual(status, 400)

    def test_post_needs_json_content_type(self):
        cookie = self.login()
        status, _, _ = self.call("POST", "/api/sim/voice", {}, cookie=cookie, content_type="text/plain")
        self.assertEqual(status, 415)

    def test_log_endpoint(self):
        cookie = self.login()
        status, _, data = self.call("GET", "/api/log?type=system&page=1", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(json.loads(data)["total"], 1)
        status, _, _ = self.call("GET", "/api/log?date=bad", cookie=cookie)
        self.assertEqual(status, 400)

    def test_static_files_and_traversal(self):
        status, headers, _ = self.call("GET", "/js/api.js")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/javascript"))
        self.assertIn("Content-Security-Policy", headers)
        for path in ("/../config.py", "/..%2Fconfig.py", "/../.env", "/css/../../web_server.py"):
            status, _, _ = self.call("GET", path)
            self.assertEqual(status, 404, path)

    def test_events_stream_delivers_device_ack(self):
        cookie = self.login()
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/api/events", headers={"Cookie": cookie})
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        self.assertTrue(response.getheader("Content-Type").startswith("text/event-stream"))
        self.assertEqual(response.fp.readline(), b"retry: 3000\n")
        response.fp.readline()
        self.call("POST", "/api/devices/light", {"on": True}, cookie=cookie)
        self.home.tick()
        lines = []
        while True:
            line = response.fp.readline().decode("utf-8")
            if line.startswith("event: device"):
                lines.append(line)
                lines.append(response.fp.readline().decode("utf-8"))
                break
        conn.close()
        self.assertTrue(lines[1].startswith("data: "))
        self.assertEqual(json.loads(lines[1][len("data: "):])["on"], True)


if __name__ == "__main__":
    unittest.main()
