# -*- coding: utf-8 -*-
"""Kiem tra Module 1 + 2 trong web (ROADMAP 5.7): vong gateway.Gateway, ThresholdPublisher,
web_gateway.GatewayHome va phan ghi nguong / lich su cua web_live.LiveHome.

Cong COM va MQTT la gia (FakeSerial, FakeClient): khong mo cong that, khong ra Internet.
"""

import os

FAKE_ENV = {
    "AIO_USERNAME": "test-user",
    "AIO_KEY": "test-key",
    "TEMP_MAX": "32",
    "HUMID_MAX": "80",
    "LIGHT_MIN": "20",
    "COM_PORT": "COM12",
    "WEB_PASSWORD": "test-password",
}
for _key, _value in FAKE_ENV.items():
    os.environ[_key] = _value

import unittest  # noqa: E402
from unittest import mock  # noqa: E402

import config  # noqa: E402
import gateway  # noqa: E402
import web_gateway  # noqa: E402
import web_live  # noqa: E402
from module1 import SensorPublisher  # noqa: E402
from module2 import AlertPublisher, ThresholdPublisher  # noqa: E402
from web_mock import CommandError  # noqa: E402


class FakeSerial:
    def __init__(self, lines):
        self.lines = [line.encode("utf-8") + b"\n" for line in lines]
        self.written = []
        self.in_waiting = 0

    def readline(self):
        return self.lines.pop(0) if self.lines else b""

    def write(self, data):
        self.written.append(data)

    def flush(self):
        pass

    def reset_input_buffer(self):
        pass

    def close(self):
        pass


class FakeClient:
    def __init__(self):
        self.sent = []

    def publish(self, topic, payload=None):
        self.sent.append((topic.rsplit("/", 1)[-1], payload))

    def feeds(self):
        return [feed for feed, payload in self.sent]

    def last(self, feed):
        for name, payload in reversed(self.sent):
            if name == feed:
                return payload
        return None


class FakeClock:
    def __init__(self, now=1_800_000_000.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class Listener:
    def __init__(self):
        self.calls = []

    def on_reading(self, reading):
        self.calls.append(("reading", reading.temp))

    def on_alert(self, alert):
        self.calls.append(("alert", alert.text))

    def on_thresholds(self, limits):
        self.calls.append(("thresholds", limits.temp_max))


def make_gateway(lines, listener=None):
    """Gateway da 'start' xong nhung voi cong COM va MQTT gia."""
    gw = gateway.Gateway(listener)
    gw.ser = FakeSerial(lines)
    gw.client = FakeClient()
    gw.sensors = SensorPublisher(gw.client)
    gw.alerts = AlertPublisher(gw.client)
    return gw


def step(gw):
    # Bo qua nhip cho READ_INTERVAL de moi lan step doc ngay mot dong
    gw.next_sample = 0
    gw.step()


class GatewayLoopTest(unittest.TestCase):
    def test_hot_reading_publishes_and_turns_led_red(self):
        listener = Listener()
        gw = make_gateway(["T:33,H:60,L:44"], listener)
        step(gw)
        for feed in ("nhiet-do", "do-am", "anh-sang", "canh-bao"):
            self.assertIn(feed, gw.client.feeds())
        self.assertTrue(gw.client.last("canh-bao").startswith("Nhiệt độ cao"))
        self.assertIn(b"LED:RED\n", gw.ser.written)
        self.assertIn(("reading", 33.0), listener.calls)
        self.assertEqual(listener.calls[-1][0], "alert")

    def test_threshold_from_web_changes_next_comparison(self):
        listener = Listener()
        gw = make_gateway(["T:33,H:60,L:44", "T:33,H:60,L:44"], listener)
        step(gw)
        gw.set_threshold(config.FEED_TEMP_MAX, 40)
        step(gw)
        self.assertEqual(gw.limits.temp_max, 40.0)
        self.assertIn(("thresholds", 40.0), listener.calls)
        self.assertEqual(gw.client.last("canh-bao"), "Bình thường")
        self.assertEqual(gw.ser.written[-1], b"LED:GREEN\n")

    def test_ack_and_bad_lines_are_ignored(self):
        gw = make_gateway(["RGB:RED", "hello", ""])
        for _ in range(3):
            step(gw)
        self.assertEqual(gw.client.sent, [])
        self.assertFalse(gw.reading.has_value())

    def test_works_without_listener(self):
        gw = make_gateway(["T:25,H:50,L:60"])
        step(gw)
        self.assertEqual(gw.client.last("canh-bao"), "Bình thường")


class ThresholdPublisherTest(unittest.TestCase):
    def setUp(self):
        self.limits = gateway.Thresholds()
        self.clock = FakeClock()
        self.client = FakeClient()

    def test_only_changed_feeds_are_sent(self):
        pub = ThresholdPublisher(self.client, None, clock=self.clock)
        changes = pub.changes(self.limits, {"temp_max": 30, "humid_max": 80, "light_min": 20})
        self.assertEqual(changes, [("temp_max", "nguong-nhiet", 30)])
        sent, missing = pub.publish(changes)
        self.assertEqual(sent, ["nguong-nhiet"])
        self.assertEqual(self.client.sent, [("nguong-nhiet", "30")])

    def test_two_second_gap(self):
        pub = ThresholdPublisher(self.client, None, clock=self.clock)
        changes = pub.changes(self.limits, {"temp_max": 30})
        pub.publish(changes)
        self.assertTrue(pub.too_soon(changes))
        self.clock.advance(ThresholdPublisher.MIN_GAP)
        self.assertFalse(pub.too_soon(changes))

    def test_missing_feed_is_not_published(self):
        pub = ThresholdPublisher(self.client, {"nguong-nhiet"}, clock=self.clock)
        changes = pub.changes(self.limits, {"temp_max": 30, "humid_max": 70})
        sent, missing = pub.publish(changes)
        self.assertEqual(sent, ["nguong-nhiet"])
        self.assertEqual(missing, ["nguong-am"])


class FakeGateway:
    def __init__(self):
        self.client = FakeClient()
        self.thresholds = []

    def set_threshold(self, feed, value):
        self.thresholds.append((feed, value))


class Recorder:
    def __init__(self):
        self.events = []

    def __call__(self, kind, data):
        self.events.append((kind, data))

    def last(self, kind):
        for event_kind, data in reversed(self.events):
            if event_kind == kind:
                return data
        return None


def make_gateway_home(feed_keys=None):
    clock = FakeClock()
    events = Recorder()
    fake = FakeGateway()
    home = web_gateway.GatewayHome(events, clock=clock, connect=False, gateway=fake)
    home.publisher = ThresholdPublisher(fake.client, feed_keys, clock=clock)
    return home, clock, events, fake


class GatewayHomeTest(unittest.TestCase):
    def test_readings_reach_the_web_and_bring_it_online(self):
        home, clock, events, _ = make_gateway_home()
        gw = make_gateway(["T:29.5,H:61,L:70"], listener=home)
        home.on_mqtt(True)
        step(gw)
        home.tick()
        self.assertEqual(events.last("sensors")["temp"], 29.5)
        self.assertTrue(events.last("gateway")["online"])
        self.assertEqual(events.last("gateway")["label"], config.COM_PORT)
        self.assertTrue(events.last("alert")["ok"])
        self.assertEqual(home.snapshot()["mode"], "gateway")

    def test_offline_after_ten_seconds_without_board(self):
        home, clock, events, _ = make_gateway_home()
        home.on_mqtt(True)
        home.on_reading(gateway.Reading())  # khong co so: khong dem
        gw = make_gateway(["T:29,H:61,L:70"], listener=home)
        step(gw)
        home.tick()
        clock.advance(web_gateway.GatewayHome.STALE_SECONDS + 1)
        home.tick()
        self.assertFalse(events.last("gateway")["online"])

    def test_save_thresholds_publishes_and_applies_in_gateway(self):
        home, clock, events, fake = make_gateway_home(feed_keys={"nguong-nhiet"})
        home.on_mqtt(True)
        home.tick()
        result = home.set_thresholds({"temp_max": 28, "humid_max": 70})
        self.assertEqual(fake.client.sent, [("nguong-nhiet", "28")])
        self.assertEqual(fake.thresholds, [("nguong-nhiet", 28.0), ("nguong-am", 70.0)])
        self.assertEqual(result["temp_max"], 28.0)
        self.assertEqual(result["humid_max"], 70.0)
        self.assertIn("nguong-am", result["note"])
        self.assertEqual(events.last("thresholds")["temp_max"], 28.0)

    def test_save_needs_mqtt(self):
        home, _, _, _ = make_gateway_home()
        with self.assertRaises(CommandError) as caught:
            home.set_thresholds({"temp_max": 28})
        self.assertEqual(caught.exception.status, 503)


class LiveWritesAndHistoryTest(unittest.TestCase):
    def make_live(self):
        clock = FakeClock()
        events = Recorder()
        home = web_live.LiveHome(events, clock=clock, connect=False)
        client = FakeClient()
        home.publisher = ThresholdPublisher(client, None, clock=clock)
        home.incoming.put(("mqtt", True))
        home.tick()
        return home, clock, events, client

    def test_live_save_publishes_then_waits_two_seconds(self):
        home, clock, events, client = self.make_live()
        home.set_thresholds({"temp_max": 30})
        self.assertEqual(client.sent, [("nguong-nhiet", "30")])
        self.assertEqual(home.limits.temp_max, 30.0)
        self.assertTrue(home.snapshot()["features"]["thresholds_write"])
        with self.assertRaises(CommandError) as caught:
            home.set_thresholds({"temp_max": 31})
        self.assertEqual(caught.exception.status, 429)

    def test_live_missing_feed_only_is_refused(self):
        home, _, _, _ = self.make_live()
        home.publisher.feed_keys = {"nguong-nhiet"}
        with self.assertRaises(CommandError) as caught:
            home.set_thresholds({"light_min": 30})
        self.assertEqual(caught.exception.status, 409)

    def test_history_is_loaded_in_time_order(self):
        home, _, _, _ = self.make_live()
        home.entries = []
        history = {
            "nhiet-do": [(1_700_000_200.0, 28.0), (1_700_000_100.0, 27.5)],
            "do-am": [(1_700_000_150.0, 60.0)],
            "anh-sang": [],
        }
        with mock.patch.object(config, "fetch_history", side_effect=lambda feed, limit: history[feed]):
            home._load_history()
        times = [entry["at"] for entry in home.entries]
        self.assertEqual(times, sorted(times))
        page = home.log(kind="sensor")
        self.assertEqual(page["total"], 3)
        self.assertIn("28", page["items"][0]["detail"])

    def test_epoch_parsing(self):
        self.assertEqual(config._epoch({"created_epoch": 1700000000}), 1700000000.0)
        self.assertEqual(config._epoch({"created_at": "2023-11-14T22:13:20Z"}), 1700000000.0)
        self.assertIsNone(config._epoch({}))


if __name__ == "__main__":
    unittest.main()
