#!/usr/bin/env python3
"""Regression test: a total quote outage must not erase the last good site."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.update_data as update  # noqa: E402


def main() -> int:
    source = ROOT / "data" / "research_data.json"
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        output = temp / "research_data.json"
        report = temp / "validation_report.json"
        output.write_bytes(source.read_bytes())
        old_argv = sys.argv
        sys.argv = ["update_data.py", "--skip-financials"]
        try:
            with (
                patch.object(update, "ROOT", temp),
                patch.object(update, "OUTPUT_PATH", output),
                patch.object(update, "REPORT_PATH", report),
                patch.object(
                    update,
                    "load_market_tables",
                    return_value=({}, {}, {}, ["模拟行情接口失败"]),
                ),
                patch.object(update, "fetch_pe_batch", side_effect=RuntimeError("模拟估值接口失败")),
            ):
                result = update.main()
        finally:
            sys.argv = old_argv

        data = json.loads(output.read_text(encoding="utf-8"))
        unresolved = [company["name"] for company in data["companies"] if not company["listings"]]
        pe_count = sum(
            listing.get("peTtm") is not None
            for company in data["companies"]
            for listing in company["listings"]
        )
        if result != 0 or len(data["companies"]) != 79 or unresolved or pe_count == 0:
            raise SystemExit(
                f"FAIL: fallback regression; companies={len(data['companies'])}, "
                f"unresolved={unresolved}, peSnapshots={pe_count}"
            )
        print(f"PASS: 接口全断时保留 79 家上市映射和 {pe_count} 个 PE 快照")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
