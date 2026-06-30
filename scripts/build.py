#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DIST = ROOT / "dist"
DATA_PATH = ROOT / "data" / "research_data.json"


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit("缺少 data/research_data.json，请先运行 python scripts/update_data.py")
    html = (SRC / "index.html").read_text(encoding="utf-8")
    css = (SRC / "styles.css").read_text(encoding="utf-8")
    js = (SRC / "app.js").read_text(encoding="utf-8")
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = html.replace("/*__INLINE_CSS__*/", css)
    html = html.replace("/*__INLINE_DATA__*/", f"window.RESEARCH_DATA={payload};")
    html = html.replace("/*__INLINE_APP__*/", js)
    DIST.mkdir(parents=True, exist_ok=True)
    for filename in ["index.html", "中国半导体与AI算力产业链研究.html"]:
        (DIST / filename).write_text(html, encoding="utf-8")
    print(f"已生成单文件网页：{DIST / '中国半导体与AI算力产业链研究.html'}")


if __name__ == "__main__":
    main()
