#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script chạy full test suite (pytest) cho MTranslator.
Dùng sau các cải tiến rate-limit, OCR timeout, format convert (to_thread), v.v.

Cách chạy (từ thư mục gốc dự án):
  python scripts/run_full_test_suite.py
  python scripts/run_full_test_suite.py --quick   # chỉ nhóm test ưu tiên
  python scripts/run_full_test_suite.py --list    # liệt kê test sẽ chạy
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def project_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    if not (root / "src").is_dir() or not (root / "tests").is_dir():
        raise SystemExit("Project root not found (src/, tests/). Run from project root.")
    return root


# Nhóm test ưu tiên (liên quan cải tiến vừa rồi)
PRIORITY_TESTS = [
    "tests/test_api_key_rpd_quota.py",
    "tests/test_smart_key_distributor_errors.py",
    "tests/test_execution_manager.py",
    "tests/test_integration_master_txt_pipeline.py",
    "tests/test_quality_profile_phase13.py",
    "tests/test_html_exporter_phase11.py",
    "tests/test_ocr_ai_processor.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy full test suite (pytest)")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Chỉ chạy nhóm test ưu tiên (key, distributor, execution, integration master, html_exporter, ocr ai)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Liệt kê test sẽ chạy rồi thoát.",
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Tham số thêm cho pytest (vd. -v, -x, --tb=short).",
    )
    args = parser.parse_args()

    root = project_root()
    os.chdir(root)

    # Đảm bảo PYTHONPATH có root (để import src)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) if not env.get("PYTHONPATH") else f"{root}{os.pathsep}{env['PYTHONPATH']}"

    if args.list:
        targets = PRIORITY_TESTS if args.quick else ["tests/"]
        print("Pytest targets:", " ".join(targets))
        if args.pytest_args:
            print("Extra args:", args.pytest_args)
        return 0

    cmd = [sys.executable, "-m", "pytest"]
    if args.quick:
        cmd.extend(PRIORITY_TESTS)
    else:
        cmd.append("tests/")
    cmd.extend(["-v", "--tb=short"])
    cmd.extend(args.pytest_args)

    print("Run:", " ".join(cmd))
    print("PYTHONPATH=%s\n" % env.get("PYTHONPATH", ""))
    result = subprocess.run(cmd, env=env)
    if result.returncode == 0:
        print("\n[OK] All tests passed.")
    else:
        print("\n[FAIL] Some tests failed. Exit code:", result.returncode)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
