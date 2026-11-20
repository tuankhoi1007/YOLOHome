# -*- coding: utf-8 -*-
"""Huan luyen va danh gia LBPH voi SFace tren cung mot lan chia train/test.

Ket qua ghi ra thu muc docs (JSON, CSV, PNG). Anh mat khong ghi vao docs.
Neu synthetic=True thi day la bai chay thu bang hoa tiet ve, khong phai mat nguoi.
"""

import csv
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

import face_engine
import face_metrics

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs" / "face"
DATASET_DIR = face_engine.ROOT / "data" / "faces"
MODEL_DIR = face_engine.ROOT / "models" / "face"


def _latency(calls):
    if not calls:
        return {"median_ms": None, "p95_ms": None, "n": 0}
    calls = sorted(calls)
    mid = calls[len(calls) // 2]
    p95_index = min(len(calls) - 1, int(round(0.95 * (len(calls) - 1))))
    return {
        "median_ms": round(mid, 2),
        "p95_ms": round(calls[p95_index], 2),
        "n": len(calls),
    }


def _time_call(fn, repeats):
    fn()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return _latency(samples)


def paint_pattern(person_index, shot, size=96, impostor=False):
    """Anh hoa tiet, moi nguoi mot chu ky soc khac. Dung de chay thu pipeline, khong phai mat.

    impostor ve gan mau nguoi 0 nhung lech, de FAR khong bang 0 o moi nguong.
    """
    index = 0 if impostor else person_index
    rng = np.random.default_rng(10_000 + person_index * 100 + shot + (500 if impostor else 0))
    image = np.zeros((size, size), np.uint8)
    period = 3 + index * 2
    image[::period, :] = 160 + min(index * 12, 80)
    image[:, :: (4 + index)] = 70
    center = (18 + (index * 13) % 50, 16 + (shot * 5) % 40)
    cv2.circle(image, center, 7 + index, 255, -1)
    if impostor:
        image = np.roll(image, 9, axis=0)
    noise = rng.integers(0, 18, image.shape, dtype=np.uint8)
    image = cv2.add(image, noise)
    return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)


def write_pattern_dataset(root, people=4, shots=12, unknown_shots=10):
    """Ghi bo anh synthetic vao root. Xoa thu muc con cu cua chinh no neu chay lai."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    names = []
    for index in range(people):
        name = "mau_" + chr(ord("a") + index)
        names.append(name)
        folder = root / name
        folder.mkdir(parents=True, exist_ok=True)
        for shot in range(shots):
            face_engine.write_image(folder / ("{:04d}.jpg".format(shot)), paint_pattern(index, shot))
    unknown = root / "unknown"
    unknown.mkdir(parents=True, exist_ok=True)
    for shot in range(unknown_shots):
        face_engine.write_image(unknown / ("{:04d}.jpg".format(shot)), paint_pattern(0, shot, impostor=True))
    return names


def _trials_from(items, predict):
    trials = []
    for item in items:
        label, score = predict(item)
        trials.append({
            "label": item["label"],
            "predicted": label,
            "score": float(score),
            "kind": item["kind"],
        })
    return trials


def _evaluate_trials(trials, higher_is_better):
    scores = [trial["score"] for trial in trials]
    grid = face_metrics.threshold_grid(higher_is_better, scores)
    sweep = [face_metrics.summarize(trials, threshold, higher_is_better) for threshold in grid]
    chosen, rule = face_metrics.choose_threshold(sweep, higher_is_better)
    closed = face_metrics.closed_set(trials)
    opened = face_metrics.open_confusion(trials, chosen["threshold"], higher_is_better)
    return {
        "sweep": sweep,
        "operating": chosen,
        "rule": rule,
        "closed": closed,
        "open_confusion": opened,
    }


def _loo_lbph(prepared_known, threshold):
    """Moi lan de mot nguoi ra ngoai, hoc lai LBPH, do FAR tren anh cua nguoi do."""
    labels = sorted(set(item["label"] for item in prepared_known))
    if len(labels) < 2:
        return None
    rates = []
    for held in labels:
        train = [item for item in prepared_known if item["label"] != held]
        impostors = [item for item in prepared_known if item["label"] == held]
        model = face_engine.LbphModel()
        model.fit([item["gray"] for item in train], [item["label"] for item in train])
        accepted = 0
        for item in impostors:
            _name, distance = model.predict(item["gray"])
            if face_metrics.accepts(distance, threshold, False):
                accepted += 1
        rates.append(accepted / float(len(impostors)))
    return {
        "protocol": "leave_one_person_out",
        "far_mean": sum(rates) / float(len(rates)),
        "per_person": [{"held": label, "far": rate} for label, rate in zip(labels, rates)],
        "note": "Uoc luong FAR khi mot thanh vien chua dang ky. LBPH hoc lai moi lan nen thang diem co the lech model day du.",
    }


def _loo_sface(prepared_known, threshold):
    labels = sorted(set(item["label"] for item in prepared_known))
    if len(labels) < 2:
        return None
    rates = []
    for held in labels:
        train = [item for item in prepared_known if item["label"] != held]
        impostors = [item for item in prepared_known if item["label"] == held]
        model = face_engine.SFaceModel.__new__(face_engine.SFaceModel)
        # Dung lai recognizer da tao o ngoai: gan sau. O day chi can match(), nen nhan recognizer tu item.
        model.recognizer = train[0]["recognizer"]
        model.fit([item["embedding"] for item in train], [item["label"] for item in train])
        accepted = 0
        for item in impostors:
            _name, score = model.predict_embedding(item["embedding"])
            if face_metrics.accepts(score, threshold, True):
                accepted += 1
        rates.append(accepted / float(len(impostors)))
    return {
        "protocol": "leave_one_person_out",
        "far_mean": sum(rates) / float(len(rates)),
        "per_person": [{"held": label, "far": rate} for label, rate in zip(labels, rates)],
        "note": "Cung khong gian cosine voi model day du, nen nguong chuyen duoc sang bo mau co du nguoi.",
    }


def _eval_lbph(known_train, known_test, unknown, detector):
    def prep(item):
        return face_engine.to_lbph_gray(item["image"], detector)

    train_ready = [{"label": item["label"], "gray": prep(item)} for item in known_train]
    test_ready = [{"label": item["label"], "gray": prep(item), "kind": "known"} for item in known_test]
    unknown_ready = [{"label": face_metrics.UNKNOWN, "gray": prep(item), "kind": "unknown"} for item in unknown]
    model = face_engine.LbphModel()
    model.fit([item["gray"] for item in train_ready], [item["label"] for item in train_ready])

    def predict(item):
        return model.predict(item["gray"])

    trials = _trials_from(test_ready + unknown_ready, predict)
    report = _evaluate_trials(trials, False)
    all_known = train_ready + [
        {"label": item["label"], "gray": item["gray"]} for item in test_ready
    ]
    report["loo"] = _loo_lbph(all_known, report["operating"]["threshold"])
    report["latency"] = _time_call(lambda: model.predict(test_ready[0]["gray"]), repeats=30)
    report["latency"]["what"] = "LBPH predict tren anh xam 100x100, CPU, khong tinh thoi gian YuNet"
    report["model"] = model
    report["metric"] = model.metric
    report["higher_is_better"] = False
    return report


def _eval_sface(known_train, known_test, unknown, detector, model_path):
    model = face_engine.SFaceModel(model_path)

    def embed(item):
        return model.embed(item["image"], detector)

    train_emb = [{"label": item["label"], "embedding": embed(item)} for item in known_train]
    test_emb = [{"label": item["label"], "embedding": embed(item), "kind": "known"} for item in known_test]
    unknown_emb = [
        {"label": face_metrics.UNKNOWN, "embedding": embed(item), "kind": "unknown"} for item in unknown
    ]
    model.fit([item["embedding"] for item in train_emb], [item["label"] for item in train_emb])

    def predict(item):
        return model.predict_embedding(item["embedding"])

    trials = _trials_from(test_emb + unknown_emb, predict)
    report = _evaluate_trials(trials, True)
    all_known = []
    for item in train_emb + [{"label": item["label"], "embedding": item["embedding"]} for item in test_emb]:
        all_known.append({
            "label": item["label"],
            "embedding": item["embedding"],
            "recognizer": model.recognizer,
        })
    report["loo"] = _loo_sface(all_known, report["operating"]["threshold"])
    report["latency"] = _time_call(lambda: model.predict_embedding(test_emb[0]["embedding"]), repeats=30)
    report["latency"]["what"] = "SFace cosine voi bo mau, CPU, vector da tinh san; thoi gian feature() tinh rieng"
    feature_latency = _time_call(lambda: model.embed(known_test[0]["image"], None), repeats=10)
    report["feature_latency"] = feature_latency
    report["feature_latency"]["what"] = "SFace feature() tren anh 112x112, CPU"
    report["model"] = model
    report["metric"] = model.metric
    report["higher_is_better"] = True
    return report


def _detector_latency(yunet_path):
    detector = face_engine.YuNet(yunet_path, score_threshold=0.8)
    frame = np.zeros((480, 640, 3), np.uint8)
    return _time_call(lambda: detector.detect(frame), repeats=10)


def _plot_confusion(path, matrix_info, title):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = matrix_info["rows"] if "rows" in matrix_info else matrix_info["labels"]
    cols = matrix_info["cols"] if "cols" in matrix_info else matrix_info["labels"]
    matrix = np.array(matrix_info["matrix"], dtype=float)
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(len(cols)))
    ax.set_yticks(range(len(rows)))
    ax.set_xticklabels(cols, rotation=45, ha="right")
    ax.set_yticklabels(rows)
    ax.set_xlabel("Du doan")
    ax.set_ylabel("Nhan that")
    ax.set_title(title)
    for r in range(matrix.shape[0]):
        for c in range(matrix.shape[1]):
            ax.text(c, r, str(int(matrix[r, c])), ha="center", va="center", color="black")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _plot_sweep(path, sweep, chosen, higher_is_better, title):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs = [row["threshold"] for row in sweep]
    frr = [0 if row["frr"] is None else row["frr"] for row in sweep]
    far = [row["far"] for row in sweep]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(xs, frr, label="FRR (tu choi nguoi nha)")
    if any(value is not None for value in far):
        ax.plot(xs, [0 if value is None else value for value in far], label="FAR (nhan nguoi la)")
    ax.axvline(chosen, color="black", linestyle="--", label="nguong da chon")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Nguong cosine (cao hon = chat hon)" if higher_is_better else "Nguong khoang cach LBPH (thap hon = chat hon)")
    ax.set_ylabel("Ty le")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _public_report(name, report):
    """Bo object model khoi ban ghi ra dia, giu so."""
    return {
        "name": name,
        "metric": report["metric"],
        "higher_is_better": report["higher_is_better"],
        "rule": report["rule"],
        "operating": report["operating"],
        "closed": report["closed"],
        "open_confusion": report["open_confusion"],
        "sweep": report["sweep"],
        "latency": report["latency"],
        "feature_latency": report.get("feature_latency"),
        "loo": report.get("loo"),
    }


def _justification(winner, reports, synthetic, far_source):
    lines = []
    if synthetic:
        lines.append(
            "Day la bai chay thu tren anh hoa tiet ve bang code, khong phai khuon mat. "
            "Khong duoc chep cac so nay vao bao cao nhu do chinh xac cua he thong. "
            "SFace hoc tu mat nguoi that nen tren hoa tiet no thuong kem LBPH; dieu do khong noi LBPH tot hon khi co anh that."
        )
    operating = reports[winner]["operating"]
    bits = []
    for name in sorted(reports):
        row = reports[name]["operating"]
        bit = (
            name
            + " FAR="
            + _num(row["far"])
            + " FRR="
            + _num(row["frr"])
            + " misid="
            + _num(row["misid"])
            + " closed_acc="
            + _num(reports[name]["closed"]["accuracy"])
            + " match_ms="
            + _num(reports[name]["latency"]["median_ms"])
        )
        feature = reports[name].get("feature_latency") or {}
        if feature.get("median_ms") is not None:
            bit += " feature_ms=" + _num(feature["median_ms"])
        bits.append(bit)
    lines.append("So sanh tai nguong da chon: " + "; ".join(bits) + ".")
    lines.append(
        "closed_acc la accuracy tap kin: bat buoc gan dung nguoi gan nhat, khong co quyen tu choi. "
        "FAR/FRR/misid moi la so quyet dinh mo cua. match_ms la buoc so khop (LBPH predict hoac cosine tren vector co san). "
        "feature_ms la SFace ONNX. YuNet do rieng va cong them vao moi khung."
    )
    lines.append(
        "Chon "
        + winner
        + " vi cua nha uu tien khong mo nham. Thu tu: FAR thap nhat, roi nhan nham nguoi trong nha, roi FRR, roi accuracy tap kin, roi toc do CPU."
    )
    lines.append("Nguong " + _num(operating["threshold"]) + " (" + reports[winner]["metric"] + "), quy tac " + reports[winner]["rule"] + ".")
    lines.append("Nguon FAR: " + far_source + ".")
    if reports[winner]["metric"] == "cosine":
        lines.append(
            "OpenCV goi y cosine 0.363 cho SFace. Neu nguong chon khac 0.363, do la vi tap anh nay cho FAR/FRR tot hon o diem do, khong phai vi bo qua tai lieu."
        )
    lines.append(
        "FRR cao nghia la chu nha bi tu choi va phai bam nut Mo khoa bang tay. FAR cao nghia la nguoi la mo duoc cua. Nut tay luon con, ke ca khi model tu choi."
    )
    if operating["far"] == 0 and operating["frr"] is not None and operating["frr"] >= 0.5:
        lines.append(
            "FAR bang 0 di cung FRR cao nghia la nguong an toan dang nam o cho anh nguoi nha va anh nguoi la chong diem. "
            "FAR leave-one-person-out bang 0 trong truong hop do chu yeu vi nguong tu choi gan het anh, khong phai vi model tach nguoi la rat tot."
        )
    return " ".join(lines)


def _num(value):
    if value is None:
        return "khong do"
    return "{:.4f}".format(float(value)).rstrip("0").rstrip(".")


def _write_report_md(path, summary):
    text = []
    text.append("# Ket qua nhan dien khuon mat")
    text.append("")
    if summary["synthetic"]:
        text.append("> **SYNTHETIC SMOKE TEST.** Anh dau vao la hoa tiet ve, khong phai mat nguoi. Khong dua so nay vao bao cao mon hoc.")
        text.append("")
    text.append(summary["justification"])
    text.append("")
    text.append("- Thoi diem: " + summary["created_at"])
    text.append("- May: " + summary["platform"] + ", Python " + summary["python"] + ", OpenCV " + summary["opencv"])
    text.append("- Thiet bi suy luan: CPU (khong bat CUDA)")
    text.append("- Seed chia tap: " + str(summary["seed"]) + ", ty le test: " + str(summary["test_ratio"]))
    text.append("- Nguoi hoc: " + ", ".join(summary["people"]))
    text.append("- Anh train / test / nguoi la: " + str(summary["n_train"]) + " / " + str(summary["n_test"]) + " / " + str(summary["n_unknown"]))
    text.append("- Model chon cho bai nay: **" + summary["winner"] + "**")
    text.append("- Ghi model de chay cua: " + ("co" if summary["deploy"] else "khong"))
    text.append("")
    text.append("## Tung mo hinh")
    text.append("")
    for name, report in summary["models"].items():
        op = report["operating"]
        text.append("### " + name)
        text.append("")
        text.append("- Nguong: " + _num(op["threshold"]) + " (" + report["metric"] + ")")
        text.append("- Accuracy tap kin: " + _num(report["closed"]["accuracy"]))
        text.append("- FAR: " + _num(op["far"]) + ", FRR: " + _num(op["frr"]) + ", nhan nham trong nha: " + _num(op["misid"]))
        text.append("- Do tre khop median / p95: " + _num(report["latency"]["median_ms"]) + " / " + _num(report["latency"]["p95_ms"]) + " ms. " + report["latency"]["what"])
        feature = report.get("feature_latency") or {}
        if feature.get("median_ms") is not None:
            text.append(
                "- Do tre feature median / p95: "
                + _num(feature["median_ms"])
                + " / "
                + _num(feature["p95_ms"])
                + " ms. "
                + feature.get("what", "")
            )
        if report.get("loo"):
            text.append("- FAR leave-one-person-out (trung binh): " + _num(report["loo"]["far_mean"]))
            text.append("- " + report["loo"]["note"])
        text.append("")
    text.append("## Gioi han")
    text.append("")
    text.append("- Chua co chong gia mao: anh chup hoac man hinh dien thoai cua thanh vien van co the vuot nguong.")
    text.append("- Tap nho, cung mot webcam, anh sang phong demo. So se doi khi chup lai.")
    text.append("- YuNet cong them khoang " + _num(summary["yunet_latency"]["median_ms"]) + " ms/khung tren CPU (do tren khung 640x480 trong).")
    text.append("")
    path.write_text("\n".join(text), encoding="utf-8")


def run_evaluation(
    dataset_dir,
    out_dir,
    model_dir=None,
    synthetic=False,
    seed=42,
    test_ratio=0.3,
    models=None,
    download=True,
    plots=True,
    holdout="",
    repeats_note="",
):
    """Chay danh gia. model_dir khac None va synthetic=False thi ghi model da chon de gateway tai."""
    dataset_dir = Path(dataset_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if models is None:
        models = ("lbph", "sface")
    yunet_path = None
    sface_path = None
    if download or "sface" in models:
        try:
            yunet_path, sface_path = face_engine.ensure_models()
        except face_engine.ModelMissing as exc:
            if "sface" in models and "lbph" not in models:
                raise
            print("Khong co model ONNX, bo qua SFace:", exc)
            models = tuple(name for name in models if name != "sface")
            sface_path = None
            if download:
                try:
                    yunet_path, _ignored = face_engine.ensure_models()
                except face_engine.ModelMissing:
                    yunet_path = None
    detector = face_engine.YuNet(yunet_path, score_threshold=0.6) if yunet_path else None
    enrolled, unknown_paths = face_engine.load_people(dataset_dir, holdout=holdout)
    train_paths, test_paths = face_metrics.stratified_split(enrolled, seed=seed, test_ratio=test_ratio)

    def expand(path_map, kind):
        items = []
        for label in sorted(path_map):
            for path in path_map[label]:
                items.append({"path": path, "label": label, "kind": kind})
        return items

    known_train = _attach(expand(train_paths, "known"))
    known_test = _attach(expand(test_paths, "known"))
    unknown = _attach([{"path": path, "label": face_metrics.UNKNOWN, "kind": "unknown"} for path in unknown_paths])
    if not known_test:
        raise face_engine.ModelMissing("Tap test trong")

    reports = {}
    if "lbph" in models:
        print("Danh gia LBPH...")
        reports["lbph"] = _eval_lbph(known_train, known_test, unknown, detector)
    if "sface" in models and sface_path is not None:
        print("Danh gia SFace...")
        reports["sface"] = _eval_sface(known_train, known_test, unknown, detector, sface_path)
    if not reports:
        raise face_engine.ModelMissing("Khong danh gia duoc model nao")

    winner = face_metrics.pick_winner(reports)
    far_source = "thu muc unknown/" if unknown else "khong co anh nguoi la; FAR de trong, nguong lay theo FRR"
    public = {name: _public_report(name, report) for name, report in reports.items()}
    yunet_latency = _detector_latency(yunet_path) if yunet_path else {"median_ms": None, "p95_ms": None, "n": 0}
    summary = {
        "synthetic": bool(synthetic),
        "deploy": bool(model_dir) and not synthetic,
        "warning": (
            "SYNTHETIC: hoa tiet ve, khong phai khuon mat nguoi. Khong dua vao bao cao."
            if synthetic
            else ""
        ),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "opencv": cv2.__version__,
        "device": "cpu",
        "seed": seed,
        "test_ratio": test_ratio,
        "holdout": holdout,
        "people": sorted(enrolled),
        "n_train": len(known_train),
        "n_test": len(known_test),
        "n_unknown": len(unknown),
        "far_source": far_source,
        "winner": winner,
        "threshold": public[winner]["operating"]["threshold"],
        "metric": public[winner]["metric"],
        "higher_is_better": public[winner]["higher_is_better"],
        "justification": _justification(winner, public, synthetic, far_source),
        "models": public,
        "yunet_latency": yunet_latency,
        "note": repeats_note,
    }
    _write_outputs(out_dir, summary, public, train_paths, test_paths, unknown_paths, dataset_dir, plots)
    if summary["deploy"]:
        _save_winner(Path(model_dir), reports[winner], summary)
    elif model_dir and synthetic:
        print("Khong ghi model chay that vi day la bai synthetic.")
    return summary


def _attach(items):
    loaded = []
    for item in items:
        image = face_engine.read_image(item["path"])
        if image is None:
            print("Bo qua anh hong:", item["path"])
            continue
        loaded.append({
            "path": item["path"],
            "label": item["label"],
            "kind": item["kind"],
            "image": image,
        })
    return loaded


def _rel(path, root):
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return Path(path).name


def _write_outputs(out_dir, summary, public, train_paths, test_paths, unknown_paths, dataset_dir, plots):
    (out_dir / "metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    per_class = []
    sweep_rows = []
    for name, report in public.items():
        for row in report["closed"]["per_class"]:
            per_class.append({
                "model": name,
                "label": row["label"],
                "precision": round(row["precision"], 4),
                "recall": round(row["recall"], 4),
                "support": row["support"],
            })
        for row in report["sweep"]:
            sweep_rows.append({
                "model": name,
                "threshold": row["threshold"],
                "far": "" if row["far"] is None else round(row["far"], 4),
                "frr": "" if row["frr"] is None else round(row["frr"], 4),
                "misid": "" if row["misid"] is None else round(row["misid"], 4),
                "open_accuracy": "" if row["open_accuracy"] is None else round(row["open_accuracy"], 4),
            })
        if plots:
            opened = report["open_confusion"]
            _plot_confusion(
                out_dir / ("confusion_" + name + ".png"),
                opened,
                name + " tai nguong " + _num(report["operating"]["threshold"]) + (" SYNTHETIC" if summary["synthetic"] else ""),
            )
            _plot_sweep(
                out_dir / ("threshold_" + name + ".png"),
                report["sweep"],
                report["operating"]["threshold"],
                report["higher_is_better"],
                "Sweep " + name + (" SYNTHETIC" if summary["synthetic"] else ""),
            )
    _write_csv(out_dir / "per_class.csv", per_class, ["model", "label", "precision", "recall", "support"])
    _write_csv(
        out_dir / "threshold_sweep.csv",
        sweep_rows,
        ["model", "threshold", "far", "frr", "misid", "open_accuracy"],
    )
    split = {
        "seed": summary["seed"],
        "test_ratio": summary["test_ratio"],
        "train": {label: [_rel(path, dataset_dir) for path in paths] for label, paths in train_paths.items()},
        "test": {label: [_rel(path, dataset_dir) for path in paths] for label, paths in test_paths.items()},
        "unknown": [_rel(path, dataset_dir) for path in unknown_paths],
    }
    (out_dir / "split.json").write_text(json.dumps(split, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_report_md(out_dir / "REPORT.md", summary)


def _save_winner(model_dir, report, summary):
    model_dir.mkdir(parents=True, exist_ok=True)
    report["model"].save(model_dir)
    chosen = {
        "model": summary["winner"],
        "threshold": summary["threshold"],
        "metric": summary["metric"],
        "higher_is_better": summary["higher_is_better"],
        "synthetic": False,
        "people": summary["people"],
        "trained_at": summary["created_at"],
        "justification": summary["justification"],
        "dataset": {
            "n_train": summary["n_train"],
            "n_test": summary["n_test"],
            "n_unknown": summary["n_unknown"],
        },
    }
    (model_dir / "chosen.json").write_text(
        json.dumps(chosen, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Da ghi model", summary["winner"], "vao", model_dir)
