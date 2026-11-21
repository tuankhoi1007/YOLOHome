# -*- coding: utf-8 -*-
"""Kiem tra Module 3 (ROADMAP 3.2 / 3.4): chuan hoa gia tri, DeviceControl, dinh tuyen trong
gateway.Gateway va lenh tu web (GatewayHome.command). Khong mo cong COM, khong ra Internet."""

from tests.test_gateway import FakeClock, Recorder, make_gateway  # dat bien moi truong gia truoc khi import config

import unittest  # noqa: E402

from yolohome import config  # noqa: E402
from yolohome.module1 import (  # noqa: E402
    DeviceControl,
    device_line,
    normalize_cua,
    normalize_den,
    normalize_quat,
    parse_ack,
)
from yolohome.web import gateway as web_gateway  # noqa: E402
from yolohome.web.mock import CommandError  # noqa: E402


class NormalizeTest(unittest.TestCase):
    def test_den(self):
        self.assertEqual(normalize_den(" OFF "), "OFF")
        self.assertEqual(normalize_den("0"), "OFF")
        self.assertEqual(normalize_den("#B8860B"), "#b8860b")
        self.assertEqual(normalize_den("2563eb"), "#2563eb")
        self.assertIsNone(normalize_den("#123456"))
        self.assertIsNone(normalize_den(""))

    def test_quat(self):
        self.assertEqual(normalize_quat("0"), "0")
        self.assertEqual(normalize_quat(" 65.4 "), "65")
        self.assertEqual(normalize_quat("100"), "100")
        for bad in ("101", "-1", "abc", "nan", ""):
            self.assertIsNone(normalize_quat(bad))

    def test_cua(self):
        self.assertEqual(normalize_cua("open"), "OPEN")
        self.assertEqual(normalize_cua("0"), "CLOSE")
        self.assertIsNone(normalize_cua("1"))

    def test_lines(self):
        self.assertEqual(device_line("den", "OFF"), "LIGHT:OFF")
        self.assertEqual(device_line("den", "#9333ea"), "LIGHT:9333ea")
        self.assertEqual(device_line("quat", "50"), "FAN:50")
        self.assertEqual(device_line("cua", "OPEN"), "DOOR:OPEN")

    def test_parse_ack(self):
        self.assertEqual(parse_ack("ACK:LIGHT:9333EA"), ("den", "#9333ea"))
        self.assertEqual(parse_ack("ACK:LIGHT:OFF"), ("den", "OFF"))
        self.assertEqual(parse_ack("ACK:FAN:50"), ("quat", "50"))
        self.assertEqual(parse_ack("ACK:DOOR:CLOSE"), ("cua", "CLOSE"))
        for bad in ("ACK:FAN", "ACK:FAN:200", "ACK:LAMP:1", "RGB:RED", "T:30"):
            self.assertIsNone(parse_ack(bad))


class Listener:
    def __init__(self):
        self.calls = []

    def on_device(self, device, value, ok, source, reason):
        self.calls.append((device, value, ok, source))


def make_control():
    clock = FakeClock()
    sent = []
    published = []
    listener = Listener()
    control = DeviceControl(lambda line: sent.append(line) or True, lambda feed, value: published.append((feed, value)), listener, clock)
    return control, clock, sent, published, listener


class DeviceControlTest(unittest.TestCase):
    def test_start_publishes_initial_state_once(self):
        control, _, _, published, _ = make_control()
        control.start()
        self.assertEqual(published, [("den", "OFF"), ("quat", "0"), ("cua", "CLOSE")])

    def test_command_equal_to_confirmed_is_ignored(self):
        control, _, sent, _, _ = make_control()
        control.from_feed("den", "OFF")
        control.from_feed("den", "0")
        control.from_feed("cua", "CLOSE")
        self.assertEqual(sent, [])

    def test_feed_command_is_sent_and_ack_does_not_publish_again(self):
        control, _, sent, published, listener = make_control()
        control.from_feed("quat", "50")
        self.assertEqual(sent, ["FAN:50"])
        control.ack("quat", "50")
        self.assertEqual(control.confirmed["quat"], "50")
        self.assertEqual(published, [])  # feed da la 50, khong co diem du lieu thua
        self.assertEqual(listener.calls, [("quat", "50", True, "Adafruit IO")])
        # Vong lap: feed bao lai 50 -> bo qua
        control.from_feed("quat", "50")
        self.assertEqual(sent, ["FAN:50"])

    def test_web_command_publishes_on_ack_because_feed_differs(self):
        control, _, sent, published, listener = make_control()
        self.assertEqual(control.request("cua", "OPEN", "Giao diện web"), "sent")
        control.ack("cua", "OPEN")
        self.assertEqual(published, [("cua", "OPEN")])
        self.assertEqual(listener.calls[-1], ("cua", "OPEN", True, "Giao diện web"))

    def test_no_ack_keeps_state_and_restores_feed(self):
        control, clock, sent, published, listener = make_control()
        control.from_feed("cua", "OPEN")
        clock.advance(2.9)
        control.expire()
        self.assertEqual(published, [])
        clock.advance(0.2)
        control.expire()
        self.assertEqual(control.confirmed["cua"], "CLOSE")
        self.assertEqual(published, [("cua", "CLOSE")])
        self.assertFalse(listener.calls[-1][2])
        self.assertEqual(control.pending, {})

    def test_door_auto_close_ack_without_command(self):
        control, _, _, published, listener = make_control()
        control.request("cua", "OPEN", "Giao diện web")
        control.ack("cua", "OPEN")
        control.ack("cua", "CLOSE")
        self.assertEqual(control.confirmed["cua"], "CLOSE")
        self.assertEqual(published[-1], ("cua", "CLOSE"))
        self.assertEqual(listener.calls[-1], ("cua", "CLOSE", True, "Board"))

    def test_invalid_feed_value_is_not_sent_and_feed_is_restored(self):
        control, _, sent, published, _ = make_control()
        control.from_feed("quat", "abc")
        self.assertEqual(sent, [])
        self.assertEqual(published, [("quat", "0")])

    def test_serial_failure_is_reported(self):
        listener = Listener()
        control = DeviceControl(lambda line: False, lambda feed, value: None, listener, FakeClock())
        self.assertEqual(control.request("quat", "10", "Adafruit IO"), "failed")
        self.assertFalse(listener.calls[-1][2])
        self.assertEqual(control.pending, {})


class GatewayRoutingTest(unittest.TestCase):
    def test_control_feed_message_goes_to_serial_and_ack_is_read(self):
        gw = make_gateway(["ACK:FAN:80"])
        gw.incoming.put((config.topic(config.FEED_QUAT), b"80"))
        gw.next_sample = 0
        gw.step()  # nhan lenh, gui FAN:80, doc ACK
        self.assertIn(b"FAN:80\n", gw.ser.written)
        self.assertEqual(gw.devices.confirmed["quat"], "80")
        self.assertEqual(gw.client.sent, [])  # feed da la 80

    def test_ack_is_kept_while_waiting_for_next_sample(self):
        gw = make_gateway([])
        gw.ser.in_waiting = 1
        gw.ser.lines = [b"ACK:DOOR:OPEN\n"]
        gw.devices.request("cua", "OPEN", "Giao diện web")

        class OneShot(type(gw.ser)):
            @property
            def in_waiting(self):
                return len(self.lines)

            @in_waiting.setter
            def in_waiting(self, value):
                pass

        gw.ser.__class__ = OneShot
        gw.next_sample = 10 ** 12  # chua den luot lay mau
        gw.step()
        self.assertEqual(gw.devices.confirmed["cua"], "OPEN")

    def test_threshold_messages_still_work(self):
        gw = make_gateway([])
        gw.set_threshold(config.FEED_TEMP_MAX, 40)
        gw.next_sample = 0
        gw.step()
        self.assertEqual(gw.limits.temp_max, 40.0)

    def test_unknown_ack_is_ignored(self):
        gw = make_gateway(["ACK:LAMP:1"])
        gw.next_sample = 0
        gw.step()
        self.assertEqual(gw.devices.confirmed, {"den": "OFF", "quat": "0", "cua": "CLOSE"})


def make_web():
    clock = FakeClock()
    events = Recorder()
    home = web_gateway.GatewayHome(events, clock=clock, connect=False, gateway=object())
    gw = make_gateway(["T:29,H:61,L:70"], listener=home)
    gw.devices.clock = clock
    home.gateway = gw
    home.on_mqtt(True)
    gw.next_sample = 0
    gw.step()
    home.tick()
    return home, gw, clock, events


class WebCommandTest(unittest.TestCase):
    def test_door_open_goes_to_board_and_ack_reaches_web(self):
        home, gw, clock, events = make_web()
        result = home.command("door", {"action": "unlock"})
        self.assertEqual(result["status"], "sent")
        gw.next_sample = 0
        gw.ser.lines = [b"ACK:DOOR:OPEN\n"]
        gw.step()
        self.assertIn(b"DOOR:OPEN\n", gw.ser.written)
        home.tick()
        self.assertFalse(events.last("device")["locked"])
        self.assertEqual(gw.client.last("cua"), "OPEN")

    def test_light_and_fan_values(self):
        home, gw, clock, events = make_web()
        home.command("light", {"on": True, "color": "#9333ea"})
        home.command("fan", {"on": True, "speed": 40})
        gw.ser.lines = []
        gw.next_sample = 0
        gw.step()
        self.assertIn(b"LIGHT:9333ea\n", gw.ser.written)
        self.assertIn(b"FAN:40\n", gw.ser.written)

    def test_second_command_within_two_seconds_is_refused(self):
        home, gw, clock, events = make_web()
        home.command("fan", {"on": True, "speed": 40})
        with self.assertRaises(CommandError) as caught:
            home.command("fan", {"on": False})
        self.assertEqual(caught.exception.status, 429)
        clock.advance(2.1)
        home.command("fan", {"on": False})

    def test_color_change_while_off_sends_nothing(self):
        home, gw, clock, events = make_web()
        home.command("light", {"color": "#2563eb"})
        gw.next_sample = 0
        gw.step()
        self.assertFalse(any(line.startswith(b"LIGHT") for line in gw.ser.written))
        self.assertEqual(events.last("device")["color"], "#2563eb")

    def test_offline_gateway_refuses(self):
        home, gw, clock, events = make_web()
        clock.advance(web_gateway.GatewayHome.STALE_SECONDS + 1)
        home.tick()
        with self.assertRaises(CommandError) as caught:
            home.command("door", {"action": "unlock"})
        self.assertEqual(caught.exception.status, 503)

    def test_no_ack_is_logged_as_error(self):
        home, gw, clock, events = make_web()
        home.command("door", {"action": "unlock"})
        gw.ser.lines = []
        gw.next_sample = 0
        gw.step()  # gui DOOR:OPEN, bat dau cho ack
        clock.advance(3.5)
        gw.devices.expire()
        home.tick()
        errors = [data for kind, data in events.events if kind == "log" and data["status"] == "Lỗi"]
        self.assertEqual(len(errors), 1)
        self.assertIn("3 giây", errors[0]["detail"])
        self.assertEqual(gw.devices.confirmed["cua"], "CLOSE")

    def test_snapshot_has_devices(self):
        home, gw, clock, events = make_web()
        snap = home.snapshot()
        self.assertTrue(snap["features"]["devices"])
        self.assertTrue(snap["devices"]["door"]["locked"])
        self.assertEqual(len(snap["colors"]), 4)


if __name__ == "__main__":
    unittest.main()
