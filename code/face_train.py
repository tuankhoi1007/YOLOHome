# -*- coding: utf-8 -*-
"""Huan luyen va danh gia hai cach nhan dien, roi chon nguong.

Anh that:
  .\\.venv\\Scripts\\python.exe face_train.py

Bai chay thu (hoa tiet, khong phai mat, khong ghi model chay cua):
  .\\.venv\\Scripts\\python.exe face_train.py --smoke

So lieu that ghi vao docs/face/. Bai chay thu ghi vao docs/face/smoke/ va co co synthetic.
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import face_engine
import face_study

SMOKE_DIR = face_study.DOCS_DIR / "smoke"


def run_smoke(out_dir=None):
    out_dir = Path(out_dir) if out_dir else SMOKE_DIR
    temporary = Path(tempfile.mkdtemp(prefix="yolohome-smoke-"))
    try:
        face_study.write_pattern_dataset(temporary)
        summary = face_study.run_evaluation(
            temporary,
            out_dir,
            model_dir=None,
            synthetic=True,
            download=True,
            plots=True,
            repeats_note="Smoke test: anh hoa tiet, khong phai nguoi.",
        )
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
    print("Da ghi bai chay thu vao", out_dir)
    print("SYNTHETIC. Model chon tren hoa tiet:", summary["winner"], "nguong", summary["threshold"])
    print("Khong dung so nay lam do chinh xac that.")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Huan luyen va danh gia nhan dien khuon mat")
    parser.add_argument("--data", default=str(face_study.DATASET_DIR))
    parser.add_argument("--out", default=str(face_study.DOCS_DIR))
    parser.add_argument("--model-dir", default=str(face_study.MODEL_DIR))
    parser.add_argument("--holdout", default="", help="Ten thu muc bo khoi tap hoc, dung lam nguoi la")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--smoke", action="store_true", help="Sinh anh hoa tiet va danh gia, khong ghi model")
    args = parser.parse_args(argv)
    try:
        if args.smoke:
            run_smoke(args.out if args.out != str(face_study.DOCS_DIR) else SMOKE_DIR)
            return 0
        summary = face_study.run_evaluation(
            args.data,
            args.out,
            model_dir=args.model_dir,
            synthetic=False,
            seed=args.seed,
            holdout=args.holdout,
            download=True,
            plots=True,
        )
    except face_engine.ModelMissing as exc:
        print(exc)
        return 1
    print("Model chon:", summary["winner"], "nguong", summary["threshold"])
    print("Da ghi", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
