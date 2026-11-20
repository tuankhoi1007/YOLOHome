# -*- coding: utf-8 -*-
"""YuNet (tim mat), LBPH (co dien) va SFace (embedding).

Chi chay tren laptop. Hai file ONNX tai tu OpenCV Zoo, khoa commit va SHA256
de may Windows cai lai ra cung mot model. Khong dung dlib.
"""

import hashlib
import json
import urllib.request
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
ZOO_DIR = ROOT / "models" / "face" / "zoo"
ZOO_COMMIT = "48b10fa505aeb51fbd127fc60a5c660040e823b7"

YUNET_NAME = "face_detection_yunet_2023mar.onnx"
SFACE_NAME = "face_recognition_sface_2021dec.onnx"
YUNET_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
SFACE_SHA256 = "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"
YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/"
    + ZOO_COMMIT
    + "/models/face_detection_yunet/"
    + YUNET_NAME
)
SFACE_URL = (
    "https://github.com/opencv/opencv_zoo/raw/"
    + ZOO_COMMIT
    + "/models/face_recognition_sface/"
    + SFACE_NAME
)

LBPH_SIZE = (100, 100)
SFACE_SIZE = (112, 112)
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp")


class ModelMissing(Exception):
    pass


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _download(url, path, expected):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and _sha256(path) == expected:
        return
    print("Dang tai", path.name, "...")
    tmp = path.with_suffix(path.suffix + ".part")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "YOLOHome-face"})
        with urllib.request.urlopen(request, timeout=120) as response:
            tmp.write_bytes(response.read())
    except Exception as exc:
        if tmp.is_file():
            tmp.unlink()
        raise ModelMissing("Khong tai duoc " + path.name + ": " + str(exc))
    digest = _sha256(tmp)
    if digest != expected:
        tmp.unlink()
        raise ModelMissing("Sai SHA256 cua " + path.name)
    tmp.replace(path)
    print("Da tai", path.name)


def ensure_models(zoo_dir=None):
    """Tai YuNet va SFace neu chua co. Tra ve (duong dan yunet, duong dan sface)."""
    folder = Path(zoo_dir) if zoo_dir else ZOO_DIR
    yunet = folder / YUNET_NAME
    sface = folder / SFACE_NAME
    _download(YUNET_URL, yunet, YUNET_SHA256)
    _download(SFACE_URL, sface, SFACE_SHA256)
    return yunet, sface


def read_image(path):
    """Doc anh ca khi duong dan co dau (Windows). Tra ve BGR hoac None."""
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
    except OSError:
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def write_image(path, image):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower() if path.suffix else ".jpg"
    if suffix not in (".jpg", ".jpeg", ".png", ".bmp"):
        suffix = ".jpg"
    ok, encoded = cv2.imencode(suffix, image)
    if not ok:
        raise OSError("Khong ghi duoc anh " + str(path))
    encoded.tofile(str(path))


def list_images(folder):
    folder = Path(folder)
    if not folder.is_dir():
        return []
    found = []
    for path in folder.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES and not path.name.startswith("."):
            found.append(path)
    found.sort(key=lambda item: item.name)
    return found


def load_people(dataset_dir, holdout=""):
    """Doc data/faces/<ten>/*.jpg. Thu muc 'unknown' va nguoi holdout la nguoi la, khong hoc.

    Tra ve (enrolled, unknown_paths). enrolled la dict ten -> list Path.
    """
    root = Path(dataset_dir)
    if not root.is_dir():
        raise ModelMissing("Chua co thu muc anh: " + str(root))
    holdout_name = holdout.strip()
    enrolled = {}
    unknown = []
    for person in sorted(root.iterdir(), key=lambda item: item.name):
        if not person.is_dir() or person.name.startswith("."):
            continue
        images = list_images(person)
        if not images:
            continue
        if person.name.lower() == "unknown" or person.name == holdout_name:
            unknown.extend(images)
            continue
        enrolled[person.name] = images
    if not enrolled:
        raise ModelMissing("Chua co anh thanh vien trong " + str(root))
    return enrolled, unknown


class YuNet:
    """Tim mat. input size doi theo khung hinh, nen goi setInputSize moi khi kich thuoc doi."""

    def __init__(self, model_path, score_threshold=0.8):
        # score_threshold loc mat mo. NMS 0.3 va top_k 5000 la mac dinh cua OpenCV Zoo.
        self.detector = cv2.FaceDetectorYN.create(
            str(model_path), "", (320, 320), score_threshold, 0.3, 5000
        )
        self.size = None

    def detect(self, image):
        height, width = image.shape[:2]
        if self.size != (width, height):
            self.detector.setInputSize((width, height))
            self.size = (width, height)
        _count, faces = self.detector.detect(image)
        if faces is None:
            return []
        return faces


def largest_face(faces, min_score):
    if faces is None or len(faces) == 0:
        return None
    best = None
    best_area = 0
    for row in faces:
        if float(row[-1]) < min_score:
            continue
        area = float(row[2]) * float(row[3])
        if area > best_area:
            best = row
            best_area = area
    return best


def crop_box(image, face_row, min_side=40):
    """Cat mat theo hop, them 15% vien de LBPH con thay tran va cam."""
    height, width = image.shape[:2]
    x, y, w, h = [int(round(float(value))) for value in face_row[:4]]
    if w < min_side or h < min_side:
        return None
    pad_x = int(w * 0.15)
    pad_y = int(h * 0.15)
    left = max(0, x - pad_x)
    top = max(0, y - pad_y)
    right = min(width, x + w + pad_x)
    bottom = min(height, y + h + pad_y)
    if right <= left or bottom <= top:
        return None
    return image[top:bottom, left:right]


def to_lbph_gray(image, detector=None):
    """Anh xam 100x100. Neu tim thay mat thi cat, khong thi dung ca anh (anh capture da la mat)."""
    working = image
    if detector is not None:
        row = largest_face(detector.detect(image), 0.5)
        if row is not None:
            cropped = crop_box(image, row, min_side=40)
            if cropped is not None:
                working = cropped
    if working.ndim == 3:
        gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
    else:
        gray = working
    return cv2.resize(gray, LBPH_SIZE)


class LbphModel:
    """LBPH: so sanh hoa van cuc bo. Diem predict() cua OpenCV la khoang cach, cang nho cang giong."""

    name = "lbph"
    metric = "lbph"
    higher_is_better = False

    def __init__(self):
        self.recognizer = None
        self.names = []

    def fit(self, grays, labels):
        if not grays:
            raise ValueError("Khong co anh de hoc LBPH")
        self.names = sorted(set(labels))
        ids = [self.names.index(label) for label in labels]
        self.recognizer = cv2.face.LBPHFaceRecognizer_create(radius=2, neighbors=8, grid_x=8, grid_y=8)
        self.recognizer.train(list(grays), np.array(ids, dtype=np.int32))

    def predict(self, gray):
        label_id, distance = self.recognizer.predict(gray)
        label_id = int(label_id)
        if label_id < 0 or label_id >= len(self.names):
            return None, float(distance)
        return self.names[label_id], float(distance)

    def save(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        # OpenCV FileStorage can duong dan ASCII. Thu muc models/face la ASCII.
        self.recognizer.write(str(folder / "lbph.yml"))
        (folder / "lbph_labels.json").write_text(
            json.dumps(self.names, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self, folder):
        folder = Path(folder)
        model_path = folder / "lbph.yml"
        label_path = folder / "lbph_labels.json"
        if not model_path.is_file() or not label_path.is_file():
            raise ModelMissing("Thieu lbph.yml hoac lbph_labels.json")
        self.names = json.loads(label_path.read_text(encoding="utf-8"))
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.read(str(model_path))


class SFaceModel:
    """SFace: vector 128 chieu. Diem la cosine, cang cao cang giong. Nguong OpenCV goi y 0.363."""

    name = "sface"
    metric = "cosine"
    higher_is_better = True

    def __init__(self, model_path):
        self.recognizer = cv2.FaceRecognizerSF.create(str(model_path), "")
        self.names = []
        self.embeddings = []
        self.label_ids = []

    def embed(self, image, detector=None):
        aligned = None
        if detector is not None:
            row = largest_face(detector.detect(image), 0.5)
            if row is not None:
                try:
                    aligned = self.recognizer.alignCrop(image, row)
                except cv2.error:
                    aligned = None
        if aligned is None or aligned.size == 0:
            aligned = cv2.resize(image, SFACE_SIZE)
        feature = self.recognizer.feature(aligned)
        return np.asarray(feature, dtype=np.float32).reshape(-1)

    def fit(self, embeddings, labels):
        if not embeddings:
            raise ValueError("Khong co embedding de hoc SFace")
        self.names = sorted(set(labels))
        self.embeddings = [np.asarray(item, dtype=np.float32).reshape(-1) for item in embeddings]
        self.label_ids = [self.names.index(label) for label in labels]

    def predict_embedding(self, embedding):
        query = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
        best_label = None
        best_score = -1.0
        # Lay cosine lon nhat trong cac anh cua tung nguoi, roi chon nguoi diem cao nhat.
        # Giua nhieu tu the tot hon la lay trung binh, vi trung binh lam mo cac huong nhin.
        per_person = {}
        for index, label_id in enumerate(self.label_ids):
            stored = self.embeddings[index].reshape(1, -1)
            score = float(self.recognizer.match(query, stored, cv2.FaceRecognizerSF_FR_COSINE))
            previous = per_person.get(label_id)
            if previous is None or score > previous:
                per_person[label_id] = score
        for label_id, score in per_person.items():
            if score > best_score:
                best_score = score
                best_label = self.names[label_id]
        return best_label, best_score

    def save(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        matrix = np.stack(self.embeddings).astype(np.float32)
        ids = np.array(self.label_ids, dtype=np.int32)
        np.savez(str(folder / "sface_gallery.npz"), embeddings=matrix, label_ids=ids)
        (folder / "sface_labels.json").write_text(
            json.dumps(self.names, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self, folder):
        folder = Path(folder)
        gallery = folder / "sface_gallery.npz"
        label_path = folder / "sface_labels.json"
        if not gallery.is_file() or not label_path.is_file():
            raise ModelMissing("Thieu sface_gallery.npz hoac sface_labels.json")
        self.names = json.loads(label_path.read_text(encoding="utf-8"))
        data = np.load(str(gallery))
        self.embeddings = [row for row in data["embeddings"]]
        self.label_ids = [int(item) for item in data["label_ids"]]


def confidence_percent(score, threshold, higher_is_better):
    """So 0-100 de giao dien mock cu van hieu. Log that nen nhin score va threshold."""
    if higher_is_better:
        value = float(score) * 100.0
    else:
        if threshold <= 0:
            return 0.0
        # 100 khi khoang cach 0, 50 dung nguong, 0 khi gap doi nguong.
        value = 100.0 * (1.0 - float(score) / (2.0 * float(threshold)))
    if value < 0:
        value = 0.0
    if value > 100:
        value = 100.0
    return round(value, 1)
