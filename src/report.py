"""검수 결과 CSV 리포트 저장."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, List

from .rules import Finding

CSV_HEADERS = ["검수시각", "대상폴더", "결과", "항목", "대상", "내용"]


def write_report(results: Dict[str, List[Finding]], output_path: str) -> str:
    """{디바이스 폴더명: findings} → CSV 저장 (엑셀용 BOM 포함 UTF-8)."""
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(output_path, "w", encoding="utf-8-sig", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(CSV_HEADERS)
        for folder, findings in results.items():
            for f in findings:
                w.writerow([stamp, folder, f.level, f.category, f.target, f.message])
    return output_path


def default_report_path(base_dir: str = "output") -> str:
    return os.path.join(base_dir, f"검수결과_{datetime.now():%Y%m%d_%H%M%S}.csv")
