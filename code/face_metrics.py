# -*- coding: utf-8 -*-
"""Do do chinh xac nhan dien, khong can OpenCV.

Moi lan thu la mot anh: label that, nhan doan (nguoi trong bo mau), va diem.
Diem cosine cang cao cang giong. Diem LBPH la khoang cach, cang thap cang giong.

Cua nha: mo nham (nguoi la duoc nhan) nang hon khoa nham (chu nha phai bam nut).
Nguong duoc chon theo thu tu: FAR thap nhat, roi nhan nham nguoi trong nha, roi FRR.
"""

import random

UNKNOWN = "unknown"
# Khi khong co anh nguoi la, khong ha nguong de "do cho dep". Giu FRR muc tieu roi lay nguong nghiem.
TARGET_FRR = 0.10


def stratified_split(groups, seed=42, test_ratio=0.3):
    """Chia moi nguoi rieng, cung mot seed thi ra cung mot tap.

    groups: dict ten -> list duong dan da sap xep duoc. Moi nguoi can it nhat 2 anh
    de con it nhat 1 anh train va 1 anh test.
    Tra ve (train, test), moi cai la dict ten -> list duong dan.
    """
    if not groups:
        raise ValueError("Chua co anh nao")
    rng = random.Random(seed)
    train = {}
    test = {}
    for label in sorted(groups):
        items = list(groups[label])
        if len(items) < 2:
            raise ValueError("Moi nguoi can it nhat 2 anh, thieu: " + str(label))
        items.sort()
        rng.shuffle(items)
        n_test = int(round(len(items) * test_ratio))
        n_test = max(1, min(n_test, len(items) - 1))
        test[label] = items[-n_test:]
        train[label] = items[:-n_test]
    return train, test


def accepts(score, threshold, higher_is_better):
    if score is None:
        return False
    if higher_is_better:
        return score >= threshold
    return score <= threshold


def threshold_grid(higher_is_better, scores):
    """Luoi nguong co dinh, cong them bien cua diem do duoc de khong bo sot vung dang xet."""
    if higher_is_better:
        grid = [i / 100.0 for i in range(20, 81, 2)]
        grid.append(0.363)  # nguong cosine OpenCV khuyen nghi cho SFace
    else:
        grid = [float(value) for value in range(10, 161, 5)]
    finite = [float(value) for value in scores if value is not None]
    if finite:
        lo = min(finite)
        hi = max(finite)
        if hi > lo:
            for step in range(21):
                grid.append(lo + (hi - lo) * step / 20.0)
    # Sap xep va bo trung, de CSV on dinh.
    cleaned = []
    for value in sorted(grid):
        rounded = round(float(value), 4)
        if not cleaned or abs(cleaned[-1] - rounded) > 1e-6:
            cleaned.append(rounded)
    return cleaned


def summarize(trials, threshold, higher_is_better):
    """FAR: nguoi la bi nhan. FRR: nguoi trong nha bi tu choi. misid: nhan dung nguoi khac trong nha."""
    known = [trial for trial in trials if trial["kind"] == "known"]
    unknown = [trial for trial in trials if trial["kind"] == "unknown"]

    def passed(trial):
        return accepts(trial["score"], threshold, higher_is_better)

    result = {
        "threshold": threshold,
        "n_known": len(known),
        "n_unknown": len(unknown),
        "far": None,
        "frr": None,
        "misid": None,
        "open_accuracy": None,
    }
    if known:
        rejected = sum(1 for trial in known if not passed(trial))
        wrong = sum(1 for trial in known if passed(trial) and trial["predicted"] != trial["label"])
        correct = sum(1 for trial in known if passed(trial) and trial["predicted"] == trial["label"])
        result["frr"] = rejected / float(len(known))
        result["misid"] = wrong / float(len(known))
        result["open_accuracy"] = correct / float(len(known))
    if unknown:
        result["far"] = sum(1 for trial in unknown if passed(trial)) / float(len(unknown))
    return result


def choose_threshold(rows, higher_is_better):
    """Chon mot dong trong ban sweep.

    Co anh nguoi la: uu tien FAR = 0, roi misid, roi FRR. Hoa thi lay nguong nghiem hon
    (cosine cao hon, khoang cach LBPH thap hon) de kho mo nham.
    Khong co anh nguoi la: trong cac nguong co FRR <= 10%, lay nguong nghiem nhat.
    """
    if not rows:
        raise ValueError("Khong co nguong nao de chon")
    measured = [row for row in rows if row.get("far") is not None]
    if measured:
        def rank(row):
            if higher_is_better:
                strict = -row["threshold"]
            else:
                strict = row["threshold"]
            return (row["far"], row["misid"], row["frr"], strict)

        best = min(measured, key=rank)
        return best, "min_far_then_misid_then_frr"
    eligible = [row for row in rows if row.get("frr") is not None and row["frr"] <= TARGET_FRR]
    pool = eligible or rows

    def strict_rank(row):
        if higher_is_better:
            return (-row["threshold"], row["frr"])
        return (row["threshold"], row["frr"])

    best = min(pool, key=strict_rank)
    return best, "no_impostor_strict_under_frr_0.10"


def closed_set(trials):
    """Doan danh tinh, khong co nguong tu choi. Chi tinh anh cua nguoi da dang ky."""
    known = [trial for trial in trials if trial["kind"] == "known"]
    labels = sorted(set(trial["label"] for trial in known))
    size = len(labels)
    matrix = [[0 for _ in range(size)] for _ in range(size)]
    if not known or not labels:
        return {"accuracy": None, "labels": labels, "matrix": matrix, "per_class": []}
    correct = 0
    for trial in known:
        row = labels.index(trial["label"])
        if trial["predicted"] in labels:
            col = labels.index(trial["predicted"])
            matrix[row][col] += 1
        if trial["predicted"] == trial["label"]:
            correct += 1
    per_class = []
    for index, label in enumerate(labels):
        support = sum(matrix[index])
        predicted_count = sum(matrix[row][index] for row in range(size))
        tp = matrix[index][index]
        recall = tp / float(support) if support else 0.0
        precision = tp / float(predicted_count) if predicted_count else 0.0
        per_class.append({
            "label": label,
            "precision": precision,
            "recall": recall,
            "support": support,
        })
    return {
        "accuracy": correct / float(len(known)),
        "labels": labels,
        "matrix": matrix,
        "per_class": per_class,
    }


def open_confusion(trials, threshold, higher_is_better):
    """Ma tran co them cot 'reject' va hang 'unknown' neu co nguoi la."""
    known_labels = sorted(set(trial["label"] for trial in trials if trial["kind"] == "known"))
    has_unknown = any(trial["kind"] == "unknown" for trial in trials)
    rows = list(known_labels)
    if has_unknown:
        rows.append(UNKNOWN)
    cols = list(known_labels) + ["reject"]
    matrix = [[0 for _ in cols] for _ in rows]
    for trial in trials:
        row_name = trial["label"] if trial["kind"] == "known" else UNKNOWN
        if row_name not in rows:
            continue
        if accepts(trial["score"], threshold, higher_is_better) and trial["predicted"] in known_labels:
            col_name = trial["predicted"]
        else:
            col_name = "reject"
        matrix[rows.index(row_name)][cols.index(col_name)] += 1
    return {"rows": rows, "cols": cols, "matrix": matrix}


def pick_winner(reports):
    """reports: dict ten model -> report co operating, closed, latency.

    Cung thu tu voi chon nguong: FAR, misid, FRR, roi accuracy kin cao hon, roi nhanh hon.
    FAR khong do duoc thi coi nhu xau (1.0) de model co do FAR that duoc uu tien.
    """
    if not reports:
        raise ValueError("Khong co model nao")

    def rank(name):
        report = reports[name]
        operating = report["operating"]
        far = operating["far"]
        if far is None:
            far = 1.0
        misid = operating["misid"]
        if misid is None:
            misid = 1.0
        frr = operating["frr"]
        if frr is None:
            frr = 1.0
        accuracy = report["closed"]["accuracy"]
        if accuracy is None:
            accuracy = 0.0
        latency = report["latency"]["median_ms"]
        return (far, misid, frr, -accuracy, latency)

    return min(reports, key=rank)
