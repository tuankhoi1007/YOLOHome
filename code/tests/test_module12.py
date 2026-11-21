# -*- coding: utf-8 -*-
"""Kiem tra cac ham thuan cua Module 1 + 2 (ROADMAP 1.1).

parse_line, normalize_light, Reading.update, evaluate, Thresholds.apply_feed.
Khong mo cong COM, khong ra Internet, khong doc .env that: moi cai dat la gia.
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

import contextlib  # noqa: E402
import io  # noqa: E402
import unittest  # noqa: E402

from yolohome import config, module1  # noqa: E402
from yolohome.module1 import Reading, normalize_light, parse_line  # noqa: E402
from yolohome.module2 import Thresholds, evaluate  # noqa: E402


def quiet(func, *args):
    """Chay func va bo qua dong print cua no, de ket qua test de doc."""
    with contextlib.redirect_stdout(io.StringIO()):
        return func(*args)


def make_reading(temp=None, humid=None, light=None):
    reading = Reading()
    reading.temp = temp
    reading.humid = humid
    reading.light = light
    return reading


class ParseLineTest(unittest.TestCase):
    def test_full_line(self):
        self.assertEqual(parse_line("T:31.2,H:60,L:44"), {"T": 31.2, "H": 60.0, "L": 44.0})

    def test_partial_lines_are_valid(self):
        self.assertEqual(parse_line("T:31.2,L:44"), {"T": 31.2, "L": 44.0})
        self.assertEqual(parse_line("H:60"), {"H": 60.0})

    def test_case_and_spaces_are_tolerated(self):
        self.assertEqual(parse_line("  t: 31.2 , h : 60 \n"), {"T": 31.2, "H": 60.0})

    def test_json_line(self):
        line = '{"temperature": 31.2, "humidity": 60, "light": 44}'
        self.assertEqual(parse_line(line), {"T": 31.2, "H": 60.0, "L": 44.0})

    def test_json_light_above_100_is_dropped(self):
        # Firmware gui anh sang 0-100, so lon hon la xung nhieu.
        line = '{"temperature": 31.2, "light": 900}'
        self.assertEqual(parse_line(line), {"T": 31.2})

    def test_json_without_known_keys_or_broken(self):
        self.assertIsNone(parse_line('{"x": 1}'))
        self.assertIsNone(parse_line("{1,2}"))
        self.assertIsNone(parse_line('{"temperature": "abc"}'))

    def test_garbage_gives_none(self):
        for line in (
            "",
            "   ",
            "hello",
            "Khong doc duoc cam bien",
            "T:abc",
            "X:1",
            "T:nan",
            "T:inf",
            "RGB:RED",
        ):
            self.assertIsNone(parse_line(line), line)

    def test_bad_part_does_not_drop_good_parts(self):
        self.assertEqual(parse_line("T:31,H:abc"), {"T": 31.0})
        self.assertEqual(parse_line("T:31,junk,L:5"), {"T": 31.0, "L": 5.0})


class NormalizeLightTest(unittest.TestCase):
    def setUp(self):
        # Co nay chi de in dong thong bao mot lan, dat lai de test khong anh huong nhau.
        module1._light_scaled = False

    def test_percent_scale_passes_through(self):
        self.assertEqual(normalize_light(0), 0)
        self.assertEqual(normalize_light(44), 44)
        self.assertEqual(normalize_light(100), 100)
        self.assertEqual(normalize_light(44.26), 44.3)

    def test_analog_range_is_scaled_to_percent(self):
        self.assertEqual(quiet(normalize_light, 4095), 100.0)
        self.assertEqual(quiet(normalize_light, 2048), 50.0)

    def test_value_just_above_100_is_scaled(self):
        self.assertEqual(quiet(normalize_light, 101), 2.5)

    def test_negative_is_clamped_to_zero(self):
        self.assertEqual(normalize_light(-5), 0)

    def test_very_large_is_clamped_to_100(self):
        self.assertEqual(quiet(normalize_light, 99999), 100)


class ReadingUpdateTest(unittest.TestCase):
    def test_empty_reading_has_no_value(self):
        reading = Reading()
        self.assertFalse(reading.has_value())
        self.assertEqual(reading.summary(), "")

    def test_each_key_sets_only_its_field(self):
        reading = Reading()
        reading.update({"T": 31.24})
        self.assertEqual((reading.temp, reading.humid, reading.light), (31.2, None, None))
        reading.update({"H": 60.06})
        self.assertEqual((reading.temp, reading.humid, reading.light), (31.2, 60.1, None))
        reading.update({"L": 44})
        self.assertEqual((reading.temp, reading.humid, reading.light), (31.2, 60.1, 44))
        self.assertTrue(reading.has_value())

    def test_empty_update_changes_nothing(self):
        reading = make_reading(temp=30.0)
        reading.update(None)
        reading.update({})
        self.assertEqual(reading.temp, 30.0)
        self.assertIsNone(reading.humid)

    def test_partial_update_keeps_older_fields(self):
        reading = Reading()
        reading.update({"T": 31.2, "H": 60, "L": 44})
        reading.update({"T": 33.0})
        self.assertEqual((reading.temp, reading.humid, reading.light), (33.0, 60.0, 44))

    def test_light_goes_through_normalize(self):
        module1._light_scaled = False
        reading = Reading()
        quiet(reading.update, {"L": 4095})
        self.assertEqual(reading.light, 100.0)

    def test_summary(self):
        reading = Reading()
        reading.update({"T": 31.2, "H": 60, "L": 44})
        self.assertEqual(reading.summary(), "T=31.2 H=60 L=44")
        self.assertEqual(make_reading(humid=55.5).summary(), "H=55.5")


class EvaluateTest(unittest.TestCase):
    def setUp(self):
        self.limits = Thresholds()  # 32 / 80 / 20 theo FAKE_ENV

    def test_no_data_gives_none(self):
        self.assertIsNone(evaluate(Reading(), self.limits))

    def test_all_in_range_is_green(self):
        alert = evaluate(make_reading(25, 50, 60), self.limits)
        self.assertTrue(alert.ok)
        self.assertEqual(alert.led, "GREEN")
        self.assertEqual(alert.text, "Bình thường")

    def test_hot_is_red(self):
        alert = evaluate(make_reading(33, 50, 60), self.limits)
        self.assertFalse(alert.ok)
        self.assertEqual(alert.led, "RED")
        self.assertIn("Nhiệt độ cao", alert.text)
        self.assertIn("ngưỡng 32", alert.text)

    def test_humid_is_red(self):
        alert = evaluate(make_reading(25, 85, 60), self.limits)
        self.assertEqual(alert.led, "RED")
        self.assertIn("Độ ẩm cao", alert.text)

    def test_dark_is_red(self):
        alert = evaluate(make_reading(25, 50, 10), self.limits)
        self.assertEqual(alert.led, "RED")
        self.assertIn("Ánh sáng thấp", alert.text)

    def test_exactly_at_limit_is_still_ok(self):
        # Nhiet va am so voi ">", anh sang so voi "<": bang ngưỡng chua canh bao.
        alert = evaluate(make_reading(32, 80, 20), self.limits)
        self.assertTrue(alert.ok)

    def test_several_problems_are_joined(self):
        alert = evaluate(make_reading(40, 90, 5), self.limits)
        self.assertEqual(alert.text.count(" | "), 2)
        for part in ("Nhiệt độ cao", "Độ ẩm cao", "Ánh sáng thấp"):
            self.assertIn(part, alert.text)

    def test_missing_field_is_skipped(self):
        self.assertTrue(evaluate(make_reading(temp=25), self.limits).ok)
        self.assertFalse(evaluate(make_reading(temp=40), self.limits).ok)
        self.assertTrue(evaluate(make_reading(light=50), self.limits).ok)


class ThresholdsApplyFeedTest(unittest.TestCase):
    def setUp(self):
        self.limits = Thresholds()

    def apply(self, feed, value):
        return quiet(self.limits.apply_feed, feed, value)

    def test_defaults_come_from_env(self):
        self.assertEqual((self.limits.temp_max, self.limits.humid_max, self.limits.light_min), (32, 80, 20))

    def test_each_feed_updates_its_own_limit(self):
        self.assertTrue(self.apply(config.FEED_TEMP_MAX, 28))
        self.assertTrue(self.apply(config.FEED_HUMID_MAX, 70))
        self.assertTrue(self.apply(config.FEED_LIGHT_MIN, 30))
        self.assertEqual((self.limits.temp_max, self.limits.humid_max, self.limits.light_min), (28, 70, 30))

    def test_same_value_returns_false(self):
        self.assertFalse(self.apply(config.FEED_TEMP_MAX, 32))

    def test_out_of_range_is_refused_and_old_value_kept(self):
        cases = (
            (config.FEED_TEMP_MAX, 81, "temp_max", 32),
            (config.FEED_TEMP_MAX, -1, "temp_max", 32),
            (config.FEED_HUMID_MAX, 101, "humid_max", 80),
            (config.FEED_HUMID_MAX, -1, "humid_max", 80),
            (config.FEED_LIGHT_MIN, 101, "light_min", 20),
            (config.FEED_LIGHT_MIN, -1, "light_min", 20),
        )
        for feed, value, attr, old in cases:
            self.assertFalse(self.apply(feed, value), (feed, value))
            self.assertEqual(getattr(self.limits, attr), old, (feed, value))

    def test_range_boundaries_are_accepted(self):
        self.assertTrue(self.apply(config.FEED_TEMP_MAX, 80))
        self.assertTrue(self.apply(config.FEED_TEMP_MAX, 0))
        self.assertTrue(self.apply(config.FEED_HUMID_MAX, 100))
        self.assertTrue(self.apply(config.FEED_LIGHT_MIN, 0))
        self.assertTrue(self.apply(config.FEED_LIGHT_MIN, 100))

    def test_unknown_feed_is_ignored(self):
        self.assertFalse(self.apply("khong-co-feed", 10))
        self.assertEqual(self.limits.temp_max, 32)

    def test_new_limit_changes_the_next_evaluation(self):
        reading = make_reading(temp=30)
        self.assertTrue(evaluate(reading, self.limits).ok)
        self.apply(config.FEED_TEMP_MAX, 28)
        self.assertFalse(evaluate(reading, self.limits).ok)


if __name__ == "__main__":
    unittest.main()
