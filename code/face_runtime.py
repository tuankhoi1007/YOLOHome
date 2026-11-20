# -*- coding: utf-8 -*-
"""Vong nhan dien tren webcam laptop.

Khong mo cong COM. Gateway nhan ket qua qua submit(kind, payload) va tu gui lenh cua.
Mot lan nhan dien la mot quyet dinh sau vai khung on dinh, khong phai moi khung hinh,
de nhat ky va servo khong bi spam.
"""

import threading
import time

import face_metrics
from face_engine import ModelMissing, confidence_percent


class AttemptGate:
    """Gom nhieu khung thanh mot lan thu.

    Can `stable_frames` khung lien tiep cung mot ket luan moi ghi nhan.
    Het mat khoang `miss_reset` giay thi san sang cho lan sau.
    Tu choi khong phan biet ten gan nhat, vi ten gan nhat hay nhay khi diem thap.
    """

    def __init__(self, stable_frames, miss_reset):
        self.stable_frames = stable_frames
        self.miss_reset = miss_reset
        self.last_key = None
        self.run = 0
        self.latched = None
        self.last_face_at = None

    def push(self, observation, now):
        if observation is None:
            if self.last_face_at is not None and now - self.last_face_at >= self.miss_reset:
                self._reset()
            return None
        self.last_face_at = now
        if observation.get("ok"):
            key = ("yes", observation.get("name"))
        else:
            key = ("no",)
        if key == self.latched:
            self.last_key = key
            self.run = 0
            return None
        if key == self.last_key:
            self.run += 1
        else:
            self.last_key = key
            self.run = 1
        if self.run < self.stable_frames:
            return None
        self.latched = key
        self.run = 0
        return observation

    def _reset(self):
        self.last_key = None
        self.run = 0
        self.latched = None
        self.last_face_at = None


class Recognizer:
    """Tai model da chon trong chosen.json. Tu choi model synthetic."""

    def __init__(self, model_name, threshold, metric, higher_is_better, people, backend):
        self.model_name = model_name
        self.threshold = threshold
        self.metric = metric
        self.higher_is_better = higher_is_better
        self.people = people
        self.backend = backend
        self.detector = None
        self.min_score = 0.7

    def runtime_status(self):
        return {
            "enabled": True,
            "ready": False,
            "model": self.model_name,
            "detector": "yunet",
            "camera": "off",
            "message": "",
            "threshold": self.threshold,
            "metric": self.metric,
            "people": self.people,
        }

    def identify(self, frame):
        from face_engine import crop_box, largest_face, to_lbph_gray

        row = largest_face(self.detector.detect(frame), self.min_score)
        if row is None:
            return None
        if self.model_name == "lbph":
            cropped = crop_box(frame, row, min_side=60)
            if cropped is None:
                return None
            gray = to_lbph_gray(cropped, detector=None)
            name, score = self.backend.predict(gray)
        else:
            embedding = self.backend.embed(frame, self.detector)
            name, score = self.backend.predict_embedding(embedding)
        ok = bool(name) and face_metrics.accepts(score, self.threshold, self.higher_is_better)
        return {
            "ok": ok,
            "name": name,
            "score": round(float(score), 4),
            "threshold": self.threshold,
            "metric": self.metric,
            "model": self.model_name,
            "confidence": confidence_percent(score, self.threshold, self.higher_is_better),
            "detect_score": round(float(row[-1]), 4),
        }


def load_recognizer(model_dir, threshold=None):
    """Doc models/face/chosen.json. threshold khac None thi de len so da chon luc train."""
    import json
    from pathlib import Path

    from face_engine import LbphModel, SFaceModel, YuNet, ensure_models

    folder = Path(model_dir)
    chosen_path = folder / "chosen.json"
    if not chosen_path.is_file():
        raise ModelMissing("Chua co models/face/chosen.json. Hay chup anh roi chay face_train.py")
    chosen = json.loads(chosen_path.read_text(encoding="utf-8"))
    if chosen.get("synthetic"):
        raise ModelMissing("chosen.json danh dau synthetic, khong dung de mo cua")
    model_name = chosen.get("model")
    yunet_path, sface_path = ensure_models()
    # Nguong runtime thap hon luc chup de con nhin thay mat o 0.5-1 m, anh sang phong.
    detector = YuNet(yunet_path, score_threshold=0.7)
    if model_name == "lbph":
        backend = LbphModel()
        backend.load(folder)
    elif model_name == "sface":
        backend = SFaceModel(sface_path)
        backend.load(folder)
    else:
        raise ModelMissing("Model khong ho tro: " + str(model_name))
    limit = chosen.get("threshold")
    if threshold is not None:
        limit = threshold
    recognizer = Recognizer(
        model_name,
        float(limit),
        chosen.get("metric") or backend.metric,
        bool(chosen.get("higher_is_better", backend.higher_is_better)),
        chosen.get("people") or backend.names,
        backend,
    )
    recognizer.detector = detector
    return recognizer


def open_camera(index):
    import os

    import cv2

    # CAP_DSHOW on dinh hon tren Windows. May khac dung backend mac dinh.
    if os.name == "nt":
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    else:
        capture = cv2.VideoCapture(index)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return capture


class FaceLoop:
    """Doc webcam trong luong rieng. submit chi duoc goi de bo viec vao hang doi."""

    def __init__(self, recognizer, submit, camera_index=0, interval=0.3, stable_frames=3, miss_reset=1.0):
        self.recognizer = recognizer
        self.submit = submit
        self.camera_index = camera_index
        self.interval = interval
        self.gate = AttemptGate(stable_frames, miss_reset)
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run, name="face", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=2)

    def run(self):
        try:
            capture = open_camera(self.camera_index)
        except Exception as exc:
            print("Khong mo duoc webcam:", exc)
            self._status("off", "Không mở được webcam: " + str(exc))
            return
        if not capture.isOpened():
            print("Khong mo duoc webcam chi so", self.camera_index)
            self._status("off", "Không mở được webcam. Kiểm tra FACE_CAMERA và quyền camera.")
            return
        status = self.recognizer.runtime_status()
        status["ready"] = True
        status["camera"] = "on"
        status["message"] = ""
        self.submit("status", status)
        print("Nhan dien: camera", self.camera_index, "model", self.recognizer.model_name, "nguong", self.recognizer.threshold)
        while not self.stop_event.is_set():
            ok, frame = capture.read()
            now = time.time()
            observation = None
            if ok and frame is not None:
                try:
                    observation = self.recognizer.identify(frame)
                except Exception as exc:
                    print("Loi nhan dien:", exc)
            attempt = self.gate.push(observation, now)
            if attempt is not None:
                payload = dict(attempt)
                payload["at"] = now
                self.submit("attempt", payload)
            if self.stop_event.wait(self.interval):
                break
        capture.release()

    def _status(self, camera, message):
        status = self.recognizer.runtime_status()
        status["camera"] = camera
        status["ready"] = False
        status["message"] = message
        self.submit("status", status)
