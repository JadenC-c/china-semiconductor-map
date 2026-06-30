#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
DATA_PATH = ROOT / "data" / "research_data.json"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> int:
    if len(CATALOG["nodes"]) != 20:
        fail(f"节点数应为 20，实际 {len(CATALOG['nodes'])}")
    slots = sum(len(node["companies"]) for node in CATALOG["nodes"])
    if slots != 80:
        fail(f"截图位置应为 80，实际 {slots}")
    node_ids = {node["id"] for node in CATALOG["nodes"]}
    for chain in CATALOG["chains"]:
        missing = set(chain["nodeIds"]) - node_ids
        if missing:
            fail(f"产业链 {chain['name']} 引用了不存在节点：{missing}")
    for edge in CATALOG["edges"]:
        if edge["from"] not in node_ids or edge["to"] not in node_ids:
            fail(f"无效边：{edge}")

    if not DATA_PATH.exists():
        print("PASS: 目录结构校验通过；尚未生成 research_data.json")
        return 0
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if data["meta"]["screenshotSlotCount"] != 80:
        fail("输出截图位置不是 80")
    names = [company["name"] for company in data["companies"]]
    if len(names) != len(set(names)):
        fail("公司去重失败")
    for company in data["companies"]:
        years = [row["year"] for row in company["financials"]]
        if len(years) != len(set(years)):
            fail(f"{company['name']} 财务年份重复")
        if any(year not in range(2021, 2026) for year in years):
            fail(f"{company['name']} 出现非 2021–2025 年数据")
        for listing in company["listings"]:
            if listing["peTtm"] is not None and listing["peTtm"] <= 0:
                fail(f"{company['name']} 存在无效 PE")
    print(f"PASS: 20 节点 / 80 位置 / {len(names)} 家唯一公司，数据结构校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
