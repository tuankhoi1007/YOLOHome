# -*- coding: utf-8 -*-
"""Quet mat de mo cua (UC07, UC08).

Moi lan quet toi da FACE_SCAN_SECONDS giay:
  - moi khung: phat hien mat -> can chinh -> vector SFace -> so voi mau trung binh tung nguoi
  - khung co 0 hoac tu 2 mat thi bo qua
  - mo cua khi trong FACE_WINDOW khung gan nhat co it nhat FACE_VOTES khung khop
    CUNG MOT nguoi voi diem >= nguong
  - FACE_LIVENESS=1: them thu thach quay dau (chong anh in / anh tren dien thoai)
Het gio ma chua du dieu kien thi tra ve that bai; cua khong duoc mo.

Gateway dung lop FaceUnlock (luong rieng). Thu rieng, khong can board:
  python -m yolohome.face.unlock
"""

import queue
import threading
import time
from collections import deque

from yolohome import config
from yolohome.face import engine
from yolohome.face.engine import Gallery, cv2, draw_face, load_threshold, yaw_ratio


class ScanResult:
    """Ket qua mot lan quet.

    detail: cau co dau de hien tren web / nhat ky. note: cau khong dau de print.
    name: nguoi duoc mo cua; khi that bai la nguoi giong nhat (chi de tham khao) hoac None.
    """

    def __init__(self, ok, name, score, detail, note, threshold=None):
        self.ok = ok
        self.name = name
        self.score = score
        self.detail = detail
        self.note = note
        self.threshold = threshold

    def as_dict(self):
        data = {"ok": self.ok, "name": self.name if self.ok else None,
                "score": round(float(self.score), 3), "detail": self.detail}
        if self.threshold is not None:
            data["threshold"] = round(float(self.threshold), 3)
        return data

    def __repr__(self):
        return "ScanResult(%s, %s, %.3f, %s)" % (self.ok, self.name, self.score, self.note)


class Decider:
    """Bo phieu qua nhieu khung. Khong dung webcam nen kiem thu duoc."""

    def __init__(self, threshold, window=None, votes=None, liveness=None, spread=None):
        self.threshold = threshold
        self.votes = config.FACE_VOTES if votes is None else votes
        self.liveness = config.FACE_LIVENESS if liveness is None else liveness
        self.spread = config.FACE_LIVE_SPREAD if spread is None else spread
        self.window = deque(maxlen=config.FACE_WINDOW if window is None else window)
        self.yaws = {}
        self.best_name = None
        self.best_score = 0.0
        self.frames_with_face = 0

    def add(self, name, score, yaw):
        """Them ket qua mot khung co dung mot mat. Tra ve ten neu du dieu kien mo cua."""
        self.frames_with_face += 1
        if score > self.best_score:
            self.best_name, self.best_score = name, score
        match = name if (name is not None and score >= self.threshold) else None
        self.window.append(match)
        if match is not None:
            self.yaws.setdefault(match, []).append(yaw)
        if match is None or self.window.count(match) < self.votes:
            return None
        if self.liveness and not self.alive(match):
            return None
        return match

    def alive(self, name):
        yaws = self.yaws.get(name, [])
        return len(yaws) >= 2 and (max(yaws) - min(yaws)) >= self.spread

    def success(self, name):
        return ScanResult(True, name, self.best_score, "Cửa đang mở.", "cua dang mo", self.threshold)

    def failure(self):
        if self.frames_with_face == 0:
            return ScanResult(False, None, 0.0, "Không thấy khuôn mặt. Đưa mặt vào giữa webcam.",
                              "khong thay khuon mat", self.threshold)
        names = [n for n in self.window if n is not None]
        top = max(names.count(n) for n in set(names)) if names else 0
        if self.best_score < self.threshold:
            return ScanResult(False, self.best_name, self.best_score,
                              "Không nhận ra. Nhìn thẳng rồi thử lại.",
                              "khong nhan ra", self.threshold)
        if self.liveness and top >= self.votes:
            return ScanResult(False, self.best_name, self.best_score,
                              "Hãy quay đầu nhẹ sang hai bên.", "hay quay dau nhe",
                              self.threshold)
        return ScanResult(False, self.best_name, self.best_score,
                          "Chưa nhận ra. Nhìn thẳng rồi thử lại.",
                          "chua nhan ra", self.threshold)


def _fail(detail, note):
    return ScanResult(False, None, 0.0, detail, note)


def scan(face_engine, seconds=None, preview=None, camera=None, viewer=None):
    """Mot lan quet. Tra ve ScanResult.

    viewer(frame) nhan anh da lat guong de dua len web. Co viewer thi khong mo cua so OpenCV.
    """
    seconds = config.FACE_SCAN_SECONDS if seconds is None else seconds
    preview = config.FACE_PREVIEW if preview is None else preview
    show_window = preview and viewer is None
    gallery = Gallery()  # doc lai moi lan: dang ky them luc gateway dang chay van an
    if not gallery.people:
        return _fail("Chưa ai đăng ký khuôn mặt", "chua ai dang ky khuon mat")
    decider = Decider(load_threshold())
    try:
        cap = camera or engine.open_camera()
    except Exception as exc:
        return _fail("Webcam lỗi", "webcam loi: " + str(exc))
    hint = "Nhin thang, quay dau nhe trai-phai" if decider.liveness else "Nhin thang vao webcam"
    end = time.time() + seconds
    result = None
    try:
        while time.time() < end and result is None:
            ok, frame = cap.read()
            if not ok:
                result = _fail("Webcam không trả ảnh", "webcam khong tra anh")
                break
            faces = face_engine.detect(frame)
            view = frame.copy() if (show_window or viewer is not None) else None
            if len(faces) == 1:
                face = faces[0]
                vec = face_engine.embed_aligned(face_engine.align(frame, face))
                name, score = gallery.best(vec)
                winner = decider.add(name, score, yaw_ratio(face))
                if view is not None:
                    good = score >= decider.threshold
                    label = name if good else "Chua khop"
                    draw_face(view, face, label, (0, 200, 0) if good else (0, 0, 255))
                if winner is not None:
                    result = decider.success(winner)
            elif view is not None and len(faces) > 1:
                cv2.putText(view, "Chi mot nguoi", (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            if view is not None:
                left = max(0.0, end - time.time())
                cv2.putText(view, "%s  %.0fs" % (hint, left), (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                if viewer is not None:
                    viewer(cv2.flip(view, 1))
                elif show_window:
                    cv2.imshow("Quet mat mo cua", view)
                    cv2.waitKey(1)
    finally:
        if camera is None:
            cap.release()
        if show_window:
            try:
                cv2.destroyWindow("Quet mat mo cua")
                cv2.waitKey(1)
            except Exception:
                pass
    return result if result is not None else decider.failure()


class FaceUnlock:
    """Luong quet mat cho gateway. request_scan() de bat dau, ket qua vao self.results.

    Lop nay khong mo cua: gateway doc self.results trong step() roi tu ra lenh cua.
    """

    def __init__(self, face_engine=None):
        # Loi thieu opencv / mo hinh bao ngay luc tao, de gateway tat phan nay va chay tiep
        self.engine = face_engine or engine.FaceEngine()
        self.results = queue.Queue()
        self._want = threading.Event()
        self._busy = threading.Event()
        self.viewer = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def is_busy(self):
        return self._busy.is_set() or self._want.is_set()

    def request_scan(self):
        """False neu dang quet do."""
        if self.is_busy():
            return False
        self._want.set()
        return True

    def _run(self):
        while True:
            self._want.wait()
            self._busy.set()
            self._want.clear()
            try:
                result = scan(self.engine, viewer=self.viewer)
            except Exception as exc:
                result = _fail("Lỗi khi quét", "loi khi quet: " + str(exc))
            self._busy.clear()
            self.results.put(result)


def main():
    print("Thu quet mat (khong mo cua that). Nguong: %.3f" % load_threshold())
    face_engine = engine.FaceEngine()
    while True:
        result = scan(face_engine)
        if result.ok:
            print("MO CUA:", result.name, "- diem %.2f," % result.score, result.note)
        else:
            print("GIU DONG:", result.note)
        try:
            again = input("Enter de quet lai, Q de thoat: ")
        except (EOFError, KeyboardInterrupt):
            break
        if again.strip().lower() == "q":
            break


if __name__ == "__main__":
    main()
