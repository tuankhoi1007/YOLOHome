# -*- coding: utf-8 -*-
"""Dang ky khuon mat (UC02) va chup anh test cho face_eval.py.

Chay tu thu muc code/:
  python -m yolohome.face.enroll Minh           dang ky Minh (dang ky lai thi mau moi thay mau cu)
  python -m yolohome.face.enroll Minh --test    chup anh test cua Minh, KHONG dua vao kho mau
  python -m yolohome.face.enroll la1 --test     anh test nguoi la (ten khong co trong kho = nguoi la)
  python -m yolohome.face.enroll --list         xem ai da dang ky
  python -m yolohome.face.enroll --delete Minh  xoa Minh khoi kho mau

Chup theo tung buoc tu the. Chuong trinh do goc quay dau tu 5 diem moc cua YuNet:
  1. Nhin thang            |yaw| < 0.08
  2. Quay dau mot ben      0.15 <= |yaw| <= 0.45
  3. Quay dau ben kia      nhu tren, nguoc dau voi buoc 2
  4. Lui xa, nhin thang    mat nho lai >= 15% so voi buoc 1
Khong dung tu the thi KHONG chup va khong sang buoc. Moi buoc toi da FACE_STEP_TIMEOUT giay,
het gio thi bo buoc do va bao thieu goc. Buoc 1 bat buoc; tong it nhat 10 anh moi luu.
Phim: S bo qua buoc dang lam, Q huy.

Nen chup anh test vao buoi KHAC luc dang ky, anh sang phong demo, cach webcam 0,5-1 m.
Anh luu la mat da can chinh 112x112 trong data/faces/enroll/<ten> hoac data/faces/test/<ten>.
"""

import argparse
import re
import shutil
import sys
import time

from yolohome import config
from yolohome.face import engine
from yolohome.face.engine import FACE_DIR, FaceEngine, Gallery, cv2, sharpness, yaw_ratio

STRAIGHT = 0.08
SIDE_MIN = 0.15
SIDE_MAX = 0.45
FARTHER = 0.85
GAP = 0.3  # giay giua hai anh, tranh chup trung lap

# (ma, chu tren man hinh, ty le so anh). Chu khong dau vi OpenCV khong ve duoc dau tieng Viet.
STEPS = (
    ("straight", "Nhin thang vao webcam", 8),
    ("side1", "Quay dau sang TRAI mot chut", 6),
    ("side2", "Quay dau sang PHAI mot chut", 6),
    ("far", "Lui ra xa mot chut, nhin thang", 5),
)


def safe_name(name):
    name = name.strip()
    if not re.fullmatch(r"[A-Za-z0-9_\-]{1,32}", name):
        print("Ten chi dung chu khong dau, so, _ hoac -, toi da 32 ky tu. Vi du: Minh, Binh_2")
        sys.exit(1)
    return name


def plan(count):
    """Chia tong so anh cho 4 buoc theo ty le 8/6/6/5."""
    total = sum(weight for _, _, weight in STEPS)
    counts = [max(2, round(count * weight / total)) for _, _, weight in STEPS]
    return [(code, text, n) for (code, text, _), n in zip(STEPS, counts)]


class StepCheck:
    """Kiem tra tu the cua mot khung theo buoc hien tai. Tach rieng de kiem thu khong can webcam."""

    def __init__(self):
        self.side_sign = 0  # dau cua yaw o buoc quay dau dau tien
        self.widths = []  # be rong mat o buoc nhin thang

    def check(self, code, yaw, width):
        """Tra ve (dat, loi_nhac)."""
        if code == "straight":
            if abs(yaw) >= STRAIGHT:
                return False, "Nhin thang hon"
            return True, ""
        if code in ("side1", "side2"):
            if abs(yaw) < SIDE_MIN:
                return False, "Quay them chut nua"
            if abs(yaw) > SIDE_MAX:
                return False, "Quay it lai"
            sign = 1 if yaw > 0 else -1
            if code == "side2" and self.side_sign and sign == self.side_sign:
                return False, "Quay sang BEN KIA"
            return True, ""
        if code == "far":
            if abs(yaw) >= STRAIGHT + 0.02:
                return False, "Nhin thang hon"
            if self.widths:
                ref = sorted(self.widths)[len(self.widths) // 2]
                if width > ref * FARTHER:
                    return False, "Lui xa them"
            return True, ""
        return False, ""

    def accepted(self, code, yaw, width):
        if code == "straight":
            self.widths.append(width)
        if code == "side1" and not self.side_sign:
            self.side_sign = 1 if yaw > 0 else -1


def _yaw_bar(view, yaw, code):
    """Thanh ngang o day man hinh: vach trang = vi tri dau hien tai, vung xanh = vung can toi."""
    h, w = view.shape[:2]
    cx, y, half = w // 2, h - 30, 200
    scale = half / 0.6
    cv2.line(view, (cx - half, y), (cx + half, y), (120, 120, 120), 2)
    zones = []
    if code in ("straight", "far"):
        zones = [(-STRAIGHT, STRAIGHT)]
    elif code in ("side1", "side2"):
        zones = [(-SIDE_MAX, -SIDE_MIN), (SIDE_MIN, SIDE_MAX)]
    for lo, hi in zones:
        # Man hinh da lat guong nen yaw duong ve ben trai.
        cv2.line(view, (int(cx - hi * scale), y), (int(cx - lo * scale), y), (0, 200, 0), 6)
    if yaw is not None:
        x = int(cx - max(-0.6, min(0.6, yaw)) * scale)
        cv2.line(view, (x, y - 12), (x, y + 12), (255, 255, 255), 3)


def capture(name, count, folder):
    engine = FaceEngine()
    cap = engine.open_camera()
    folder.mkdir(parents=True, exist_ok=True)
    steps = plan(count)
    checker = StepCheck()
    saved = []
    missing = []
    print("Chup", sum(n for _, _, n in steps), "anh cho", name, "theo", len(steps), "buoc. S = bo qua buoc, Q = huy")
    try:
        for index, (code, text, need) in enumerate(steps, 1):
            got = 0
            start = time.time()
            last = 0.0
            while got < need:
                left = config.FACE_STEP_TIMEOUT - (time.time() - start)
                if left <= 0:
                    print("Het gio buoc", index, "-", text, "- chi duoc", got, "/", need, "anh")
                    missing.append(text)
                    break
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("Webcam khong tra anh")
                faces = engine.detect(frame)
                yaw = None
                status = ""
                box_color = (0, 0, 255)
                if len(faces) == 0:
                    status = "Khong thay mat"
                elif len(faces) > 1:
                    status = "Chi mot nguoi truoc webcam"
                else:
                    face = faces[0]
                    yaw = yaw_ratio(face)
                    width = float(face[2])
                    if min(face[2], face[3]) < config.FACE_MIN_SIZE:
                        status = "Lai gan hon"
                    else:
                        good, status = checker.check(code, yaw, width)
                        if good:
                            aligned = engine.align(frame, face)
                            if sharpness(aligned) < config.FACE_MIN_SHARP:
                                status = "Anh mo, dung yen"
                            else:
                                box_color = (0, 200, 0)
                                if time.time() - last >= GAP:
                                    path = folder / ("%s_%d%s_%02d.jpg" % (name, index, code, got))
                                    cv2.imwrite(str(path), aligned)
                                    saved.append(aligned)
                                    checker.accepted(code, yaw, width)
                                    got += 1
                                    last = time.time()
                    x, y, w, h = [int(v) for v in face[:4]]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
                # Lat guong cho giong soi guong, roi moi viet chu.
                view = cv2.flip(frame, 1)
                cv2.putText(view, "Buoc %d/%d: %s" % (index, len(steps), text), (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                cv2.putText(view, "%s  %d/%d   con %ds" % (name, got, need, int(left)), (10, 52),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                if status:
                    cv2.putText(view, status, (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                _yaw_bar(view, yaw, code)
                cv2.imshow("Dang ky khuon mat", view)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q")):
                    print("Da huy.")
                    return engine, saved, [t for _, t, _ in steps]
                if key in (ord("s"), ord("S")):
                    print("Bo qua buoc", index, "-", text)
                    missing.append(text)
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return engine, saved, missing


def main():
    parser = argparse.ArgumentParser(description="Dang ky khuon mat")
    parser.add_argument("name", nargs="?", help="ten thanh vien, khong dau")
    parser.add_argument("--test", action="store_true", help="chup anh test, khong dang ky")
    parser.add_argument("-n", "--count", type=int, help="tong so anh (mac dinh 25, --test 50)")
    parser.add_argument("--list", action="store_true", help="xem danh sach da dang ky")
    parser.add_argument("--delete", metavar="TEN", help="xoa mot nguoi khoi kho mau")
    args = parser.parse_args()

    gallery = Gallery()
    if args.list:
        if not gallery.people:
            print("Chua ai dang ky")
        for name, arr in gallery.people.items():
            print(name, "-", len(arr), "mau")
        return
    if args.delete:
        if gallery.remove(args.delete):
            gallery.save()
            print("Da xoa", args.delete)
        else:
            print("Khong co", args.delete, "trong kho mau")
        return
    if not args.name:
        parser.print_help()
        return

    name = safe_name(args.name)
    if args.test:
        folder = FACE_DIR / "test" / name
        _, saved, missing = capture(name, args.count or 50, folder)
        print("Da luu", len(saved), "anh test vao", folder)
        if missing:
            print("Thieu buoc:", "; ".join(missing))
        if name not in gallery.people:
            print("(", name, "khong co trong kho mau -> face_eval.py tinh la NGUOI LA )")
        return

    folder = FACE_DIR / "enroll" / name
    tmp = FACE_DIR / "enroll" / (name + ".moi")
    shutil.rmtree(tmp, ignore_errors=True)
    engine, saved, missing = capture(name, args.count or 25, tmp)
    straight_missing = STEPS[0][1] in missing
    if straight_missing or len(saved) < 10:
        shutil.rmtree(tmp, ignore_errors=True)
        why = "thieu buoc nhin thang" if straight_missing else "chi co %d anh, can it nhat 10" % len(saved)
        print("KHONG luu mau:", why + ". Giu nguyen mau cu (neu co).")
        sys.exit(1)
    # Dang ky lai: mau moi thay mau cu (UC02 - Alternative Flow).
    shutil.rmtree(folder, ignore_errors=True)
    tmp.rename(folder)
    gallery.set_person(name, [engine.embed_aligned(img) for img in saved])
    gallery.save()
    print("Da dang ky", name, "voi", len(saved), "mau. Kho mau:", ", ".join(gallery.people))
    if missing:
        print("CANH BAO: thieu goc", "; ".join(missing) + ".",
              "Quet luc nghieng dau co the bi tu choi. Nen dang ky lai cho du cac buoc.")


if __name__ == "__main__":
    main()
