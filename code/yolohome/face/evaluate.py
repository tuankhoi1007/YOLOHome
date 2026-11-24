# -*- coding: utf-8 -*-
"""Danh gia nhan dien khuon mat tren tap test noi bo va chon nguong.

Chay tu thu muc code/: python -m yolohome.face.evaluate

Du lieu (trong code/data/faces):
  gallery.npz        kho mau (python -m yolohome.face.enroll <ten>)
  test/<ten>/*.jpg   anh test (python -m yolohome.face.enroll <ten> --test)
    <ten> co trong kho mau -> thanh vien; khong co -> nguoi la
  --extra THU_MUC         them anh nguoi la bat ky (vi du mot phan LFW), quet ca thu muc con

Cach chia: anh test moi nguoi xep theo thu tu chup, NUA DAU de chon nguong (hieu chinh),
NUA SAU de bao cao. Nhu vay so bao cao khong dung lai anh da dung de chon nguong.

Chon nguong: nho nhat sao cho FAR tren nua hieu chinh <= --far (mac dinh 0),
cong them bien --margin (0.03), va khong thap hon 0.363 (nguong OpenCV chon cho SFace).

Ket qua: in ra man hinh, data/faces/eval_report.md (dan vao bao cao), data/faces/eval_plot.png
(can matplotlib, khong co thi bo qua), va ghi nguong vao data/faces/threshold.json
(yolohome.face.unlock tu dung). --no-save de chi xem.
"""

import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from yolohome import config
from yolohome.face import engine
from yolohome.face.engine import FACE_DIR, FaceEngine, Gallery, np

UNKNOWN = "unknown"


class Sample:
    def __init__(self, person, true, path, pred, score):
        self.person = person  # ten thu muc
        self.true = true  # ten thanh vien, hoac UNKNOWN
        self.path = path
        self.pred = pred
        self.score = score


def decide(sample, threshold):
    return sample.pred if sample.score >= threshold else UNKNOWN


def rates(samples, threshold):
    genuine = [s for s in samples if s.true != UNKNOWN]
    strangers = [s for s in samples if s.true == UNKNOWN]
    rejected = sum(1 for s in genuine if decide(s, threshold) == UNKNOWN)
    swapped = sum(1 for s in genuine if decide(s, threshold) not in (UNKNOWN, s.true))
    accepted = sum(1 for s in strangers if decide(s, threshold) != UNKNOWN)
    correct = sum(1 for s in samples if decide(s, threshold) == s.true)
    return {
        "n_genuine": len(genuine),
        "n_stranger": len(strangers),
        "FRR": rejected / len(genuine) if genuine else float("nan"),
        "swap": swapped / len(genuine) if genuine else float("nan"),
        "FAR": accepted / len(strangers) if strangers else float("nan"),
        "accuracy": correct / len(samples) if samples else float("nan"),
    }


def pick_threshold(calib, far_target, margin):
    strangers = sorted(s.score for s in calib if s.true == UNKNOWN)
    if not strangers:
        return None, "khong co anh nguoi la de hieu chinh"
    # FAR(t) = ti le nguoi la co diem >= t. Tim t nho nhat co FAR <= muc tieu.
    allowed = int(np.floor(far_target * len(strangers)))
    if allowed >= len(strangers):
        base = 0.0
    else:
        base = strangers[len(strangers) - 1 - allowed] + 1e-6
    t = max(base + margin, engine.SFACE_LFW_THRESHOLD)
    return round(float(t), 3), "diem nguoi la cao nhat (sau khi bo %d) = %.3f" % (allowed, base)


def simulate_scans(samples, threshold, window, votes):
    """Truot cua so qua anh theo thu tu chup cua tung nguoi. Moi cua so = mot luot quet."""
    by_person = {}
    for s in samples:
        by_person.setdefault(s.person, []).append(s)
    member_open = member_total = stranger_open = stranger_total = 0
    for items in by_person.values():
        items.sort(key=lambda s: s.path.name)
        for i in range(0, max(0, len(items) - window + 1)):
            chunk = items[i:i + window]
            counts = Counter(decide(s, threshold) for s in chunk)
            counts.pop(UNKNOWN, None)
            opened = bool(counts) and counts.most_common(1)[0][1] >= votes
            if chunk[0].true == UNKNOWN:
                stranger_total += 1
                stranger_open += opened
            else:
                member_total += 1
                member_open += opened
    return member_open, member_total, stranger_open, stranger_total


def confusion(samples, threshold, labels):
    index = {name: i for i, name in enumerate(labels)}
    mat = np.zeros((len(labels), len(labels)), dtype=int)
    for s in samples:
        mat[index[s.true], index[decide(s, threshold)]] += 1
    return mat


def load_samples(engine, gallery, extra):
    groups = []
    test_dir = FACE_DIR / "test"
    if test_dir.is_dir():
        for folder in sorted(p for p in test_dir.iterdir() if p.is_dir()):
            groups.append((folder.name, sorted(folder.glob("*.jpg"))))
    if extra:
        for folder in sorted({p.parent for p in Path(extra).rglob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")}):
            files = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
            groups.append(("extra:" + folder.name, files))
    calib, report = [], []
    skipped = 0
    timings = []
    for person, files in groups:
        true = person if person in gallery.people else UNKNOWN
        rows = []
        for path in files:
            start = time.perf_counter()
            vec = engine.embed_image(path)
            timings.append(time.perf_counter() - start)
            if vec is None:
                skipped += 1
                continue
            pred, score = gallery.best(vec)
            rows.append(Sample(person, true, path, pred, score))
        half = len(rows) // 2
        if len(rows) == 1:
            report += rows
        else:
            calib += rows[:half]
            report += rows[half:]
    ms = 1000 * float(np.mean(timings)) if timings else 0.0
    return calib, report, skipped, ms


def pct(x):
    return "n/a" if x != x else "%.1f%%" % (100 * x)


def sweep(samples):
    ts = np.linspace(0, 1, 201)
    far, frr = [], []
    for t in ts:
        r = rates(samples, t)
        far.append(r["FAR"])
        frr.append(r["FRR"])
    return ts, np.array(far), np.array(frr)


def eer(ts, far, frr):
    ok = ~(np.isnan(far) | np.isnan(frr))
    if not ok.any():
        return None, None
    idx = int(np.nanargmin(np.abs(far - frr)))
    return float(ts[idx]), float((far[idx] + frr[idx]) / 2)


def plot(samples, threshold, out):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Khong co matplotlib, bo qua bieu do (pip install matplotlib)")
        return False
    genuine = [s.score for s in samples if s.true != UNKNOWN]
    strangers = [s.score for s in samples if s.true == UNKNOWN]
    ts, far, frr = sweep(samples)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    bins = np.linspace(-0.2, 1, 49)
    if genuine:
        ax1.hist(genuine, bins=bins, alpha=0.7, label="Thành viên")
    if strangers:
        ax1.hist(strangers, bins=bins, alpha=0.7, label="Người lạ")
    ax1.axvline(threshold, color="black", linestyle="--", label="Ngưỡng %.3f" % threshold)
    ax1.set_xlabel("Điểm cosine cao nhất")
    ax1.set_ylabel("Số ảnh")
    ax1.set_title("Phân bố điểm")
    ax1.legend()
    ax2.plot(ts, far * 100, label="FAR (người lạ được mở)")
    ax2.plot(ts, frr * 100, label="FRR (thành viên bị từ chối)")
    ax2.axvline(threshold, color="black", linestyle="--")
    ax2.set_xlabel("Ngưỡng")
    ax2.set_ylabel("%")
    ax2.set_title("FAR / FRR theo ngưỡng")
    ax2.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return True


def main():
    parser = argparse.ArgumentParser(description="Danh gia nhan dien khuon mat")
    parser.add_argument("--extra", help="thu muc anh nguoi la them (vi du LFW)")
    parser.add_argument("--far", type=float, default=0.0, help="FAR toi da khi chon nguong (mac dinh 0)")
    parser.add_argument("--margin", type=float, default=0.03, help="bien cong them vao nguong")
    parser.add_argument("--threshold", type=float, help="khong chon, dung nguong nay")
    parser.add_argument("--no-save", action="store_true", help="khong ghi threshold.json")
    args = parser.parse_args()

    gallery = Gallery()
    if not gallery.people:
        print("Kho mau trong. Chay python -m yolohome.face.enroll <ten> truoc.")
        return
    engine = FaceEngine()
    calib, report, skipped, ms = load_samples(engine, gallery, args.extra)
    if not report:
        print("Chua co anh test. Chay: python -m yolohome.face.enroll <ten> --test")
        return

    if args.threshold is not None:
        threshold, why = args.threshold, "nhap tay"
    else:
        threshold, why = pick_threshold(calib, args.far, args.margin)
        if threshold is None:
            threshold = engine.DEFAULT_THRESHOLD
            why += " -> dung nguong mac dinh %.2f. NEN chup them anh nguoi la!" % threshold

    r = rates(report, threshold)
    win, votes = config.FACE_WINDOW, config.FACE_VOTES
    m_open, m_total, s_open, s_total = simulate_scans(report, threshold, win, votes)
    ts, far, frr = sweep(report)
    eer_t, eer_v = eer(ts, far, frr)
    labels = sorted(gallery.people) + [UNKNOWN]
    labels = [lb for lb in labels if lb != UNKNOWN] + [UNKNOWN]
    mat = confusion(report, threshold, labels)

    n_members = sum(1 for s in calib + report if s.true != UNKNOWN)
    n_strangers = sum(1 for s in calib + report if s.true == UNKNOWN)
    lines = []
    lines.append("# Đánh giá nhận diện khuôn mặt")
    lines.append("")
    lines.append("Ngày chạy: " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("")
    lines.append("- Mô hình: YuNet (phát hiện) + SFace (vector 128 chiều), so khớp cosine với mẫu trung bình của từng thành viên")
    lines.append("- Thành viên đã đăng ký: %d (%s)" % (len(gallery.people), ", ".join(
        "%s: %d mẫu" % (n, len(v)) for n, v in gallery.people.items())))
    lines.append("- Ảnh test dùng được: %d thành viên, %d người lạ; bỏ %d ảnh không có đúng một mặt" % (
        n_members, n_strangers, skipped))
    lines.append("- Chia: nửa đầu mỗi người để chọn ngưỡng (%d ảnh), nửa sau để báo cáo (%d ảnh)" % (
        len(calib), len(report)))
    lines.append("- Ngưỡng: **%.3f** (%s)" % (threshold, why))
    lines.append("- Thời gian trích vector: %.1f ms / ảnh trên máy này" % ms)
    lines.append("")
    lines.append("## Theo từng ảnh (tập báo cáo)")
    lines.append("")
    lines.append("| Chỉ số | Giá trị |")
    lines.append("| --- | --- |")
    lines.append("| Accuracy (thành viên + người lạ là `unknown`) | %s |" % pct(r["accuracy"]))
    lines.append("| FAR: người lạ bị nhận là thành viên | %s (%d ảnh) |" % (pct(r["FAR"]), r["n_stranger"]))
    lines.append("| FRR: thành viên bị từ chối | %s (%d ảnh) |" % (pct(r["FRR"]), r["n_genuine"]))
    lines.append("| Thành viên bị nhận nhầm sang thành viên khác | %s |" % pct(r["swap"]))
    if eer_v is not None:
        lines.append("| EER (FAR = FRR) | %s tại ngưỡng %.3f |" % (pct(eer_v), eer_t))
    lines.append("")
    lines.append("## Theo lượt quét (mô phỏng luật %d/%d khung)" % (votes, win))
    lines.append("")
    lines.append("| | Mở cửa | Tổng lượt |")
    lines.append("| --- | --- | --- |")
    lines.append("| Thành viên | %d | %d |" % (m_open, m_total))
    lines.append("| Người lạ | %d | %d |" % (s_open, s_total))
    lines.append("")
    lines.append("## Ma trận nhầm lẫn (hàng: thật, cột: dự đoán)")
    lines.append("")
    lines.append("| | " + " | ".join(labels) + " |")
    lines.append("|" + " --- |" * (len(labels) + 1))
    for i, name in enumerate(labels):
        lines.append("| **%s** | " % name + " | ".join(str(v) for v in mat[i]) + " |")
    lines.append("")
    if n_strangers < 30:
        lines.append("> Ít ảnh người lạ (%d). FAR = 0 trên tập nhỏ chưa chứng minh được hệ thống an toàn; "
                     "nên thêm người lạ hoặc dùng `--extra` với một phần LFW." % n_strangers)
        lines.append("")
    lines.append("Hạn chế: kiểm thử trong ánh sáng phòng demo, khoảng cách 0,5–1 m, số người ít. "
                 "Chưa đánh giá tấn công bằng ảnh hoặc video nếu không bật FACE_LIVENESS.")
    text = "\n".join(lines) + "\n"

    print("Nguong: %.3f (%s)" % (threshold, why))
    print("Tap bao cao: %d anh thanh vien, %d anh nguoi la" % (r["n_genuine"], r["n_stranger"]))
    print("Accuracy %s | FAR %s | FRR %s | nham thanh vien %s" % (
        pct(r["accuracy"]), pct(r["FAR"]), pct(r["FRR"]), pct(r["swap"])))
    print("Luot quet %d/%d: thanh vien mo %d/%d, nguoi la mo %d/%d" % (
        votes, win, m_open, m_total, s_open, s_total))
    FACE_DIR.mkdir(parents=True, exist_ok=True)
    (FACE_DIR / "eval_report.md").write_text(text, encoding="utf-8")
    if plot(report, threshold, FACE_DIR / "eval_plot.png"):
        print("Bieu do:", FACE_DIR / "eval_plot.png")
    print("Bao cao:", FACE_DIR / "eval_report.md")
    if not args.no_save:
        engine.THRESHOLD_FILE.write_text(json.dumps({
            "threshold": threshold,
            "chosen": datetime.now().isoformat(timespec="seconds"),
            "FAR": r["FAR"], "FRR": r["FRR"],
        }, indent=2), encoding="utf-8")
        print("Da ghi nguong %.3f vao %s" % (threshold, engine.THRESHOLD_FILE))


if __name__ == "__main__":
    main()
