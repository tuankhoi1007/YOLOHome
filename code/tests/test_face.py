# -*- coding: utf-8 -*-
"""Nhan dien va cua: khong mo webcam, khong mo cong COM.

Bai LBPH dung anh hoa tiet ve trong thu muc tam. Khong phai do chinh xac that.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

FAKE_ENV = {
    "AIO_USERNAME": "test-user",
    "AIO_KEY": "test-key",
}
for _key, _value in FAKE_ENV.items():
    os.environ[_key] = _value

import face_metrics  # noqa: E402
from door import DoorController, parse_door_ack, parse_servo_pin  # noqa: E402
from face_capture import safe_name  # noqa: E402
from face_runtime import AttemptGate  # noqa: E402

try:
    import face_engine
    import face_study
except ImportError:
    face_engine = None
    face_study = None


class SplitAndThresholdTest(unittest.TestCase):
    def test_split_is_stable_and_stratified(self):
        groups = {
            "b": ["b/3.jpg", "b/1.jpg", "b/2.jpg", "b/4.jpg"],
            "a": ["a/1.jpg", "a/2.jpg", "a/3.jpg", "a/4.jpg"],
        }
        first = face_metrics.stratified_split(groups, seed=42, test_ratio=0.3)
        second = face_metrics.stratified_split(groups, seed=42, test_ratio=0.3)
        self.assertEqual(first, second)
        train, test = first
        for label in ("a", "b"):
            self.assertEqual(len(test[label]), 1)
            self.assertEqual(len(train[label]), 3)
            self.assertFalse(set(train[label]) & set(test[label]))

    def test_split_needs_two_images(self):
        with self.assertRaises(ValueError):
            face_metrics.stratified_split({"a": ["only.jpg"]}, seed=1)

    def test_choose_threshold_prefers_zero_far(self):
        rows = [
            {"threshold": 0.30, "far": 0.5, "misid": 0.0, "frr": 0.0},
            {"threshold": 0.50, "far": 0.0, "misid": 0.0, "frr": 0.2},
            {"threshold": 0.70, "far": 0.0, "misid": 0.0, "frr": 0.4},
        ]
        chosen, rule = face_metrics.choose_threshold(rows, higher_is_better=True)
        self.assertEqual(rule, "min_far_then_misid_then_frr")
        self.assertEqual(chosen["threshold"], 0.50)

    def test_without_impostors_stays_strict(self):
        rows = [
            {"threshold": 0.30, "far": None, "misid": 0.0, "frr": 0.0},
            {"threshold": 0.80, "far": None, "misid": 0.0, "frr": 0.05},
        ]
        chosen, rule = face_metrics.choose_threshold(rows, higher_is_better=True)
        self.assertEqual(rule, "no_impostor_strict_under_frr_0.10")
        self.assertEqual(chosen["threshold"], 0.80)

    def test_closed_set_precision_recall(self):
        trials = [
            {"kind": "known", "label": "An", "predicted": "An", "score": 1},
            {"kind": "known", "label": "An", "predicted": "Binh", "score": 1},
            {"kind": "known", "label": "Binh", "predicted": "Binh", "score": 1},
            {"kind": "unknown", "label": "unknown", "predicted": "An", "score": 1},
        ]
        closed = face_metrics.closed_set(trials)
        self.assertAlmostEqual(closed["accuracy"], 2 / 3)
        by_name = {row["label"]: row for row in closed["per_class"]}
        self.assertAlmostEqual(by_name["An"]["recall"], 0.5)
        self.assertAlmostEqual(by_name["Binh"]["precision"], 0.5)

    def test_far_and_frr(self):
        trials = [
            {"kind": "known", "label": "An", "predicted": "An", "score": 0.8},
            {"kind": "known", "label": "An", "predicted": "An", "score": 0.2},
            {"kind": "unknown", "label": "unknown", "predicted": "An", "score": 0.9},
            {"kind": "unknown", "label": "unknown", "predicted": "An", "score": 0.1},
        ]
        row = face_metrics.summarize(trials, 0.5, higher_is_better=True)
        self.assertAlmostEqual(row["frr"], 0.5)
        self.assertAlmostEqual(row["far"], 0.5)
        self.assertAlmostEqual(row["misid"], 0.0)


class DoorLogicTest(unittest.TestCase):
    def test_pins(self):
        self.assertEqual(parse_servo_pin("p4"), "P4")
        self.assertEqual(parse_servo_pin("16"), "P16")
        for bad in ("P0", "P14", "P20", "led", ""):
            with self.assertRaises(ValueError):
                parse_servo_pin(bad)

    def test_ack_lines(self):
        self.assertEqual(parse_door_ack("DOOR:OPEN"), ("state", False))
        self.assertEqual(parse_door_ack("door:close"), ("state", True))
        self.assertEqual(parse_door_ack("DOOR:PIN:P4")[0], "pin")
        self.assertIsNone(parse_door_ack("T:31,H:60,L:44"))
        self.assertEqual(parse_door_ack("DOOR:ERR")[0], "error")

    def test_open_then_relock(self):
        now = {"t": 100.0}

        def clock():
            return now["t"]

        door = DoorController(10, clock)
        self.assertEqual(door.request(False, "FaceAI"), "OPEN")
        self.assertIsNone(door.request(False, "again"))
        door.ack(False)
        self.assertFalse(door.locked)
        self.assertEqual(door.view()["relock_in"], 10)
        self.assertEqual(door.request(False, "FaceAI"), "REFRESH")
        now["t"] = 120
        self.assertEqual(door.tick(), "CLOSE")
        door.ack(True)
        self.assertTrue(door.locked)
        self.assertIsNone(door.view()["relock_in"])

    def test_names(self):
        self.assertEqual(safe_name("  An   Nguyen "), "An Nguyen")
        with self.assertRaises(ValueError):
            safe_name("unknown")
        with self.assertRaises(ValueError):
            safe_name("../An")


class AttemptGateTest(unittest.TestCase):
    def test_three_frames_then_latch_until_face_leaves(self):
        gate = AttemptGate(3, 1.0)
        seen = {"ok": True, "name": "An"}
        self.assertIsNone(gate.push(seen, 0.0))
        self.assertIsNone(gate.push(seen, 0.2))
        self.assertTrue(gate.push(seen, 0.4)["ok"])
        self.assertIsNone(gate.push(seen, 0.6))
        self.assertIsNone(gate.push(None, 1.0))
        self.assertIsNone(gate.push(None, 1.7))
        self.assertIsNone(gate.push(seen, 1.8))
        self.assertIsNone(gate.push(seen, 1.9))
        self.assertEqual(gate.push(seen, 2.0)["name"], "An")

    def test_reject_ignores_nearest_name_flicker(self):
        gate = AttemptGate(2, 1.0)
        self.assertIsNone(gate.push({"ok": False, "name": "An"}, 0.0))
        got = gate.push({"ok": False, "name": "Binh"}, 0.2)
        self.assertFalse(got["ok"])


@unittest.skipIf(face_engine is None, "Chua cai opencv-contrib-python")
class EngineSmokeTest(unittest.TestCase):
    def test_lbph_study_on_patterns_is_marked_synthetic(self):
        root = Path(tempfile.mkdtemp(prefix="yolohome-faces-"))
        out = Path(tempfile.mkdtemp(prefix="yolohome-out-"))
        try:
            face_study.write_pattern_dataset(root, people=2, shots=6, unknown_shots=4)
            summary = face_study.run_evaluation(
                root,
                out,
                model_dir=None,
                synthetic=True,
                models=("lbph",),
                download=False,
                plots=False,
            )
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(out, ignore_errors=True)
        self.assertTrue(summary["synthetic"])
        self.assertFalse(summary["deploy"])
        self.assertEqual(summary["winner"], "lbph")
        self.assertIsNotNone(summary["models"]["lbph"]["operating"]["far"])
        self.assertGreater(summary["models"]["lbph"]["closed"]["accuracy"], 0.5)
        self.assertIn("SYNTHETIC", summary["warning"])

    def test_roundtrip_unicode_path(self):
        folder = Path(tempfile.mkdtemp(prefix="yolohome-vn-"))
        try:
            path = folder / "Nguyễn" / "ảnh.jpg"
            image = face_study.paint_pattern(1, 2)
            face_engine.write_image(path, image)
            loaded = face_engine.read_image(path)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.shape[0], image.shape[0])
        finally:
            shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
