# -*- coding: utf-8 -*-
"""Chup anh mat bang webcam laptop.

Moi nguoi mot thu muc trong data/faces/<ten>/. Thu muc unknown/ la nguoi la, de do FAR.
Anh nam trong data/ da gitignore, khong commit.

Vi du PowerShell:
  .\\.venv\\Scripts\\python.exe face_capture.py --name "An" --count 40
  .\\.venv\\Scripts\\python.exe face_capture.py --unknown --count 20
"""

import argparse
import sys
from pathlib import Path

import face_engine

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "data" / "faces"
# 40 anh: chia 30% test con khoang 12 anh moi nguoi, du de tinh recall. Quay mat cham trong luc chup.
DEFAULT_COUNT = 40
MIN_SIDE = 80


def safe_name(name):
    cleaned = " ".join(str(name).strip().split())
    if not cleaned or cleaned in (".", ".."):
        raise ValueError("Thieu ten")
    if "/" in cleaned or "\\" in cleaned or cleaned.startswith("."):
        raise ValueError("Ten khong duoc chua duong dan")
    if cleaned.lower() == "unknown":
        raise ValueError("Ten unknown danh cho nguoi la. Hay them --unknown")
    return cleaned


def save_crop(image, face_row, destination, sface=None):
    """Cat va canh mat (neu co SFace) roi ghi JPEG 112x112."""
    aligned = None
    if sface is not None:
        try:
            aligned = sface.alignCrop(image, face_row)
        except Exception:
            aligned = None
    if aligned is None or getattr(aligned, "size", 0) == 0:
        cropped = face_engine.crop_box(image, face_row, min_side=MIN_SIDE)
        if cropped is None:
            return False
        import cv2

        aligned = cv2.resize(cropped, face_engine.SFACE_SIZE)
    face_engine.write_image(destination, aligned)
    return True


def capture(name, count, camera_index, dataset_dir, unknown=False, window=True):
    import cv2

    dataset_dir = Path(dataset_dir)
    if unknown:
        folder_name = "unknown"
    else:
        folder_name = safe_name(name)
    folder = dataset_dir / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    existing = face_engine.list_images(folder)
    start_index = len(existing)
    yunet_path, sface_path = face_engine.ensure_models()
    detector = face_engine.YuNet(yunet_path, score_threshold=0.8)
    sface = face_engine.SFaceModel(sface_path)
    from face_runtime import open_camera

    capture_device = open_camera(camera_index)
    if not capture_device.isOpened():
        print("Khong mo duoc webcam", camera_index)
        return 0
    print("Chup", count, "anh vao", folder)
    print("Nhin vao webcam, quay mat cham trai/phai/len/xuong. Nhan q de dung.")
    saved = 0
    show = window
    last_save = 0.0
    import time

    while saved < count:
        ok, frame = capture_device.read()
        if not ok or frame is None:
            print("Khong doc duoc khung hinh")
            break
        row = face_engine.largest_face(detector.detect(frame), 0.8)
        display = frame.copy()
        if row is not None:
            x, y, w, h = [int(round(float(value))) for value in row[:4]]
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 220, 0), 2)
            now = time.time()
            # 0.4 giay moi anh de nguoi kip doi tu the, tranh 40 anh giong het nhau.
            if w >= MIN_SIDE and h >= MIN_SIDE and now - last_save >= 0.4:
                destination = folder / "{:04d}.jpg".format(start_index + saved)
                if save_crop(frame, row, destination, sface.recognizer):
                    saved += 1
                    last_save = now
                    print("Da luu", saved, "/", count, destination.name)
            elif w < MIN_SIDE or h < MIN_SIDE:
                cv2.putText(display, "Lai gan", (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 255), 2)
        if show:
            try:
                cv2.imshow("YOLOHome - chup mat", display)
                key = cv2.waitKey(1) & 0xFF
            except Exception as exc:
                print("Khong mo duoc cua so xem:", exc)
                show = False
                key = 255
            if key in (ord("q"), ord("Q"), 27):
                print("Dung som.")
                break
        else:
            time.sleep(0.05)
    capture_device.release()
    if show:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
    print("Xong", saved, "anh trong", folder)
    return saved


def main(argv=None):
    parser = argparse.ArgumentParser(description="Chup anh mat cho YOLOHome")
    parser.add_argument("--name", default="", help="Ten thanh vien, dung lam ten thu muc")
    parser.add_argument("--unknown", action="store_true", help="Chup nguoi la vao thu muc unknown/")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--data", default=str(DATASET))
    parser.add_argument("--no-window", action="store_true")
    args = parser.parse_args(argv)
    if args.count < 1 or args.count > 200:
        print("So anh phai tu 1 den 200")
        return 1
    if not args.unknown and not args.name.strip():
        print("Can --name \"Ten\" hoac --unknown")
        return 1
    try:
        saved = capture(
            args.name,
            args.count,
            args.camera,
            args.data,
            unknown=args.unknown,
            window=not args.no_window,
        )
    except face_engine.ModelMissing as exc:
        print(exc)
        return 1
    except ValueError as exc:
        print(exc)
        return 1
    if saved <= 0:
        return 1
    if saved < args.count:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
