# -*- coding: utf-8 -*-
"""Kiem tra nhan dien khuon mat (Phase 6) khong can webcam, mo hinh hay Internet.

Vector khuon mat la vector gia: moi nguoi mot tam ngau nhien cong nhieu, giong cach SFace tach nguoi.
Phan can numpy tu bo qua neu may chua cai numpy.
"""

from tests.test_gateway import make_gateway, step  # dat bien moi truong gia truoc khi import config

import queue  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
from pathlib import Path  # noqa: E402

from yolohome import config  # noqa: E402
from yolohome.face import engine  # noqa: E402
from yolohome.face.unlock import Decider, ScanResult  # noqa: E402

np = engine.np


class FakeFace:
    """Thay FaceUnlock: khong mo webcam, ket qua do test dat san."""

    def __init__(self):
        self.results = queue.Queue()
        self.busy = False

    def request_scan(self):
        if self.busy:
            return False
        self.busy = True
        return True

    def finish(self, result):
        self.busy = False
        self.results.put(result)


class FaceListener:
    def __init__(self):
        self.faces = []

    def on_face(self, result):
        self.faces.append(result)


def ok_result(name="Minh"):
    return ScanResult(True, name, 0.72, "Khớp 5/7 khung", "khop 5/7 khung")


def bad_result():
    return ScanResult(False, "Minh", 0.31, "Không nhận ra (điểm 0.31, ngưỡng 0.50)", "khong nhan ra")


class DeciderTest(unittest.TestCase):
    def test_needs_five_of_seven_frames_of_the_same_person(self):
        d = Decider(0.5, window=7, votes=5, liveness=False)
        results = [d.add("Minh", s, 0.0) for s in (0.7, 0.2, 0.7, 0.7, 0.7)]
        self.assertEqual(results, [None] * 5)  # moi 4 khung khop
        self.assertEqual(d.add("Minh", 0.7, 0.0), "Minh")

    def test_two_people_never_add_up(self):
        d = Decider(0.5, window=7, votes=5, liveness=False)
        for name in ("Minh", "An", "Minh", "An", "Minh", "An", "Minh"):
            self.assertIsNone(d.add(name, 0.8, 0.0))

    def test_stranger_below_threshold_is_rejected(self):
        d = Decider(0.5, window=7, votes=5, liveness=False)
        for _ in range(10):
            self.assertIsNone(d.add("Minh", 0.4, 0.0))
        result = d.failure()
        self.assertFalse(result.ok)
        self.assertTrue(result.detail.startswith("Không nhận ra"))

    def test_no_face_at_all(self):
        result = Decider(0.5, liveness=False).failure()
        self.assertEqual(result.note, "khong thay dung mot khuon mat")

    def test_liveness_needs_a_head_turn(self):
        d = Decider(0.5, window=7, votes=5, liveness=True, spread=0.3)
        for _ in range(6):
            self.assertIsNone(d.add("Minh", 0.8, 0.0))  # anh in: khong quay
        self.assertEqual(d.failure().note, "khong qua kiem tra quay dau")
        self.assertEqual(d.add("Minh", 0.8, 0.35), "Minh")

    def test_result_dict_hides_name_on_failure(self):
        self.assertIsNone(bad_result().as_dict()["name"])
        self.assertEqual(ok_result().as_dict()["name"], "Minh")


class GatewayFaceTest(unittest.TestCase):
    def test_correct_face_opens_door_through_module3(self):
        listener = FaceListener()
        gw = make_gateway([], listener)
        face = FakeFace()
        gw.enable_face(face)
        self.assertEqual(gw.scan_face("test"), "started")
        self.assertEqual(gw.scan_face("test"), "busy")
        face.finish(ok_result())
        step(gw)
        self.assertIn(b"DOOR:OPEN\n", gw.ser.written)
        self.assertEqual(listener.faces[-1]["name"], "Minh")
        self.assertTrue(listener.faces[-1]["ok"])

    def test_wrong_face_keeps_door_closed(self):
        listener = FaceListener()
        gw = make_gateway([], listener)
        face = FakeFace()
        gw.enable_face(face)
        gw.scan_face("test")
        face.finish(bad_result())
        step(gw)
        self.assertNotIn(b"DOOR:OPEN\n", gw.ser.written)
        self.assertFalse(listener.faces[-1]["ok"])

    def test_without_face_the_gateway_still_runs(self):
        gw = make_gateway(["T:30,H:60,L:50"])
        self.assertEqual(gw.scan_face("test"), "off")
        step(gw)
        self.assertIn("nhiet-do", gw.client.feeds())

    def test_disabled_by_setting(self):
        gw = make_gateway([])
        old = config.FACE_ENABLE
        config.FACE_ENABLE = False
        try:
            self.assertFalse(gw.enable_face())
        finally:
            config.FACE_ENABLE = old
        self.assertIsNone(gw.face)


@unittest.skipIf(np is None, "chua cai numpy")
class GalleryAndEvaluateTest(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(0)
        self.centers = {n: engine.unit(self.rng.normal(size=128)) for n in ("Minh", "An", "la1", "la2")}

    def sample(self, name, noise=0.09):
        return engine.unit(self.centers[name] + self.rng.normal(scale=noise, size=128))

    def test_gallery_saves_and_matches_the_centroid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gallery.npz"
            gallery = engine.Gallery(path)
            gallery.set_person("Minh", [self.sample("Minh") for _ in range(20)])
            gallery.set_person("An", [self.sample("An") for _ in range(20)])
            gallery.save()
            loaded = engine.Gallery(path)
            self.assertEqual(sorted(loaded.people), ["An", "Minh"])
            name, score = loaded.best(self.sample("Minh"))
            self.assertEqual(name, "Minh")
            self.assertGreater(score, 0.5)
            _, stranger = loaded.best(self.sample("la1"))
            self.assertLess(stranger, 0.3)
            self.assertTrue(loaded.remove("An"))
            loaded.save()
            self.assertEqual(list(engine.Gallery(path).people), ["Minh"])

    def test_threshold_sits_above_every_stranger(self):
        from yolohome.face import evaluate

        calib = [evaluate.Sample("Minh", "Minh", Path("m%02d.jpg" % i), "Minh", 0.7) for i in range(10)]
        calib += [evaluate.Sample("la1", evaluate.UNKNOWN, Path("s%02d.jpg" % i), "Minh", s)
                  for i, s in enumerate((0.1, 0.2, 0.42))]
        threshold, _ = evaluate.pick_threshold(calib, 0.0, 0.03)
        self.assertAlmostEqual(threshold, 0.45, places=3)
        rates = evaluate.rates(calib, threshold)
        self.assertEqual(rates["FAR"], 0.0)
        self.assertEqual(rates["FRR"], 0.0)

    def test_threshold_never_below_sface_value(self):
        from yolohome.face import evaluate

        calib = [evaluate.Sample("la1", evaluate.UNKNOWN, Path("s.jpg"), "Minh", 0.05)]
        threshold, _ = evaluate.pick_threshold(calib, 0.0, 0.03)
        self.assertEqual(threshold, engine.SFACE_LFW_THRESHOLD)

    def test_scan_simulation_counts_windows(self):
        from yolohome.face import evaluate

        member = [evaluate.Sample("Minh", "Minh", Path("m%02d.jpg" % i), "Minh", 0.7) for i in range(9)]
        stranger = [evaluate.Sample("la1", evaluate.UNKNOWN, Path("s%02d.jpg" % i), "Minh", 0.2) for i in range(9)]
        opened, total, s_opened, s_total = evaluate.simulate_scans(member + stranger, 0.5, 7, 5)
        self.assertEqual((opened, total, s_opened, s_total), (3, 3, 0, 3))


class EnrollStepTest(unittest.TestCase):
    def setUp(self):
        from yolohome.face import enroll

        self.enroll = enroll

    def test_plan_splits_25_photos(self):
        counts = [n for _, _, n in self.enroll.plan(25)]
        self.assertEqual(counts, [8, 6, 6, 5])

    def test_not_turning_is_never_accepted_as_a_side_pose(self):
        check = self.enroll.StepCheck()
        self.assertEqual(check.check("side1", 0.02, 150), (False, "Quay them chut nua"))
        self.assertEqual(check.check("side1", 0.6, 150), (False, "Quay it lai"))
        self.assertTrue(check.check("side1", 0.25, 150)[0])

    def test_second_side_must_be_the_other_side(self):
        check = self.enroll.StepCheck()
        check.accepted("side1", 0.25, 150)
        self.assertEqual(check.check("side2", 0.25, 150), (False, "Quay sang BEN KIA"))
        self.assertTrue(check.check("side2", -0.25, 150)[0])

    def test_far_step_needs_a_smaller_face(self):
        check = self.enroll.StepCheck()
        for _ in range(3):
            check.accepted("straight", 0.0, 150)
        self.assertEqual(check.check("far", 0.0, 145), (False, "Lui xa them"))
        self.assertTrue(check.check("far", 0.0, 120)[0])


if __name__ == "__main__":
    unittest.main()
