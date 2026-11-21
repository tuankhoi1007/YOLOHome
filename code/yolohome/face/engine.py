# -*- coding: utf-8 -*-
"""Phan dung chung cua nhan dien khuon mat (Phase 6).

Hai mo hinh ONNX da huan luyen san cua OpenCV (opencv_zoo):
  YuNet  - phat hien mat va 5 diem moc (2 mat, mui, 2 khoe mieng)
  SFace  - bien mat da can chinh 112x112 thanh vector 128 so

Phan "huan luyen" cua nhom:
  yolohome.face.enroll    xay kho mau (vector cua tung thanh vien)
  yolohome.face.evaluate  hieu chinh nguong tren du lieu cua nhom, ghi threshold.json

AI chi chay tren laptop, khong chay tren Yolo:Bit.
"""

import json
import os
import urllib.request

from yolohome import config

try:
    import numpy as np
except ImportError:  # gateway van chay, chi tat phan khuon mat
    np = None
try:
    import cv2
except ImportError:
    cv2 = None

FACE_DIR = config.FACE_DIR
GALLERY = FACE_DIR / "gallery.npz"
THRESHOLD_FILE = FACE_DIR / "threshold.json"

# Nguong cosine OpenCV chon cho SFace tren LFW (so 1 anh voi 1 anh).
# evaluate khong chon nguong thap hon so nay.
SFACE_LFW_THRESHOLD = 0.363
# Nguong khi CHUA chay evaluate. Cao hon 0.363 vi day la cua: nhan nham nguoi la te hon
# tu choi nham thanh vien (thanh vien van mo cua bang nut tren web).
DEFAULT_THRESHOLD = 0.5

DETECT_MODEL = "face_detection_yunet_2023mar.onnx"
RECOG_MODEL = "face_recognition_sface_2021dec.onnx"
_URLS = {
    DETECT_MODEL: (
        "https://huggingface.co/opencv/face_detection_yunet/resolve/main/" + DETECT_MODEL,
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/" + DETECT_MODEL,
    ),
    RECOG_MODEL: (
        "https://huggingface.co/opencv/face_recognition_sface/resolve/main/" + RECOG_MODEL,
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/" + RECOG_MODEL,
    ),
}


def ensure_models():
    """Tai 2 file .onnx vao code/models neu chua co. Tra ve (duong dan YuNet, duong dan SFace)."""
    config.MODELS_DIR.mkdir(exist_ok=True)
    paths = []
    for name in (DETECT_MODEL, RECOG_MODEL):
        path = config.MODELS_DIR / name
        if not path.is_file() or path.stat().st_size < 100_000:
            last = None
            for url in _URLS[name]:
                try:
                    print("Dang tai", name, "...")
                    tmp = path.with_suffix(".part")
                    urllib.request.urlretrieve(url, tmp)
                    if tmp.stat().st_size < 100_000:
                        raise RuntimeError("file tai ve qua nho, co the la trang loi")
                    tmp.replace(path)
                    last = None
                    break
                except Exception as exc:
                    last = exc
            if last is not None:
                raise RuntimeError(
                    "Khong tai duoc " + name + ": " + str(last)
                    + ". Tai tay tu github.com/opencv/opencv_zoo roi dat vao " + str(config.MODELS_DIR)
                )
        paths.append(str(path))
    return paths


def unit(vec):
    vec = np.asarray(vec, dtype=np.float32).reshape(-1)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def yaw_ratio(face):
    """Do quay dau tu 5 diem moc YuNet. ~0 la nhin thang, am/duong la quay hai ben.

    Dau that quay thi mui lech khoi giua hai mat. Anh in nghieng di thi ti le nay gan nhu khong doi.
    """
    rx, lx, nx = face[4], face[6], face[8]
    dist = abs(lx - rx)
    if dist < 1:
        return 0.0
    return float((nx - (rx + lx) / 2.0) / dist)


def sharpness(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


class FaceEngine:
    def __init__(self):
        if cv2 is None or np is None:
            raise RuntimeError("Thieu opencv-python / numpy. Cai: python -m pip install -r requirements.txt")
        if not hasattr(cv2, "FaceDetectorYN"):
            raise RuntimeError("OpenCV qua cu, can >= 4.8: python -m pip install -U opencv-python")
        detect_path, recog_path = ensure_models()
        self.detector = cv2.FaceDetectorYN.create(detect_path, "", (320, 320), 0.9, 0.3, 5000)
        self.recognizer = cv2.FaceRecognizerSF.create(recog_path, "")
        self._size = None

    def detect(self, frame):
        """Mang (N, 15): x, y, w, h, 5 diem moc, diem tin cay. Khong co mat thi mang rong."""
        h, w = frame.shape[:2]
        if self._size != (w, h):
            self.detector.setInputSize((w, h))
            self._size = (w, h)
        _, faces = self.detector.detect(frame)
        if faces is None:
            return np.zeros((0, 15), dtype=np.float32)
        return faces

    def align(self, frame, face):
        return self.recognizer.alignCrop(frame, face)

    def embed_aligned(self, aligned):
        """Anh mat da can chinh 112x112 -> vector don vi 128 so."""
        return unit(self.recognizer.feature(aligned))

    def embed_image(self, path):
        """Doc file anh. Anh 112x112 coi nhu da can chinh; anh khac thi phat hien mat truoc.

        Tra ve vector, hoac None neu khong co dung mot mat.
        """
        img = cv2.imread(str(path))
        if img is None:
            return None
        if img.shape[:2] == (112, 112):
            return self.embed_aligned(img)
        faces = self.detect(img)
        if len(faces) != 1:
            return None
        return self.embed_aligned(self.align(img, faces[0]))


class Gallery:
    """Kho mau: moi thanh vien nhieu vector, luu o data/faces/gallery.npz.

    So khop dung MOT mau trung binh moi nguoi (cong cac vector roi chuan hoa). Mau trung binh
    it nhieu hon tung anh le, nen diem nguoi la thap hon so voi lay diem cao nhat trong nhieu anh.
    """

    def __init__(self, path=None):
        self.path = path or GALLERY
        self.people = {}
        self._centroids = None
        if self.path.is_file():
            data = np.load(self.path, allow_pickle=False)
            names = data["names"]
            vecs = data["vectors"]
            for name in sorted(set(names.tolist())):
                self.people[name] = vecs[names == name]

    def set_person(self, name, vectors):
        self.people[name] = np.stack([unit(v) for v in vectors])
        self._centroids = None

    def remove(self, name):
        self._centroids = None
        return self.people.pop(name, None) is not None

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        names, vecs = [], []
        for name, arr in self.people.items():
            names += [name] * len(arr)
            vecs.append(arr)
        if vecs:
            np.savez(self.path, names=np.array(names), vectors=np.concatenate(vecs))
        elif self.path.exists():
            self.path.unlink()

    def centroids(self):
        if self._centroids is None:
            self._centroids = {name: unit(arr.mean(axis=0)) for name, arr in self.people.items()}
        return self._centroids

    def scores(self, vec):
        """Diem cua tung nguoi = cosine giua vector moi va mau trung binh cua nguoi do."""
        return {name: float(center @ vec) for name, center in self.centroids().items()}

    def best(self, vec):
        """(ten, diem) cua nguoi giong nhat, hoac (None, 0) neu kho rong."""
        scores = self.scores(vec)
        if not scores:
            return None, 0.0
        name = max(scores, key=scores.get)
        return name, scores[name]


def load_threshold():
    """FACE_THRESHOLD trong .env, neu trong thi threshold.json, neu khong co thi DEFAULT_THRESHOLD."""
    if config.FACE_THRESHOLD:
        try:
            return float(config.FACE_THRESHOLD)
        except ValueError:
            print("FACE_THRESHOLD khong phai so, bo qua")
    if THRESHOLD_FILE.is_file():
        try:
            return float(json.loads(THRESHOLD_FILE.read_text(encoding="utf-8"))["threshold"])
        except Exception:
            pass
    return DEFAULT_THRESHOLD


def open_camera(index=None):
    index = config.FACE_CAMERA if index is None else index
    if os.name == "nt":
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)  # Windows mo nhanh hon
    else:
        cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError("Khong mo duoc webcam so " + str(index))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap


def draw_face(frame, face, text, color):
    x, y, w, h = [int(v) for v in face[:4]]
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
    cv2.putText(frame, text, (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
