#!/usr/bin/env python3
"""Fetch and normalize A/H share financial data for the research page.

The script deliberately separates the editable industry catalog from volatile
market data. Failed requests reuse the last successful company snapshot.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

try:
    import akshare as ak
except ImportError as exc:  # pragma: no cover - friendly CLI error
    raise SystemExit("缺少 akshare，请先运行：pip install akshare pandas") from exc


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "catalog.json"
OUTPUT_PATH = ROOT / "data" / "research_data.json"
REPORT_PATH = ROOT / "data" / "validation_report.json"
RAW_DIR = ROOT / "data" / "raw"
YEARS = list(range(2021, 2026))


def clean_number(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, 4) if math.isfinite(number) else None


def rounded(value: Any, digits: int = 2) -> float | None:
    number = clean_number(value)
    return round(number, digits) if number is not None else None


def dataframe_records(df: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    available = [column for column in columns if column in df.columns]
    if not available:
        return []
    subset = df[available].copy()
    for column in subset.columns:
        if "DATE" in column.upper() or column == "日期":
            subset[column] = subset[column].astype(str)
    return json.loads(subset.to_json(orient="records", force_ascii=False))


def market_suffix(code: str) -> tuple[str, str]:
    if code.startswith(("5", "6", "9")):
        return f"{code}.SH", f"SH{code}"
    if code.startswith(("4", "8")):
        return f"{code}.BJ", f"BJ{code}"
    return f"{code}.SZ", f"SZ{code}"


def load_previous() -> dict[str, Any]:
    if not OUTPUT_PATH.exists():
        return {}
    try:
        data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        return {company["name"]: company for company in data.get("companies", [])}
    except (json.JSONDecodeError, KeyError):
        return {}


def previous_listing(company: dict[str, Any], market: str, code: str | None = None) -> dict[str, Any]:
    """Return the last successful listing snapshot for a market/code pair."""
    for listing in company.get("listings", []):
        if listing.get("market") != market:
            continue
        if code is None or str(listing.get("code", "")) == str(code):
            return listing
    return {}


def annual_rows(df: pd.DataFrame, date_column: str) -> dict[int, pd.Series]:
    if df.empty or date_column not in df.columns:
        return {}
    work = df.copy()
    work[date_column] = pd.to_datetime(work[date_column], errors="coerce")
    work = work[(work[date_column].dt.month == 12) & (work[date_column].dt.day == 31)]
    work["_year"] = work[date_column].dt.year
    work = work.sort_values(date_column, ascending=False).drop_duplicates("_year", keep="first")
    return {int(row[date_column].year): row for _, row in work.iterrows()}


def fetch_financials(name: str, code: str, delay: float = 0.0) -> dict[str, Any]:
    if delay:
        time.sleep(delay)
    em_symbol, _ = market_suffix(code)
    errors: list[str] = []
    em_df = pd.DataFrame()
    sina_df = pd.DataFrame()

    try:
        em_df = ak.stock_financial_analysis_indicator_em(symbol=em_symbol, indicator="按报告期")
    except Exception as exc:  # noqa: BLE001 - network adapters vary by release
        errors.append(f"东方财富财务指标：{type(exc).__name__}: {exc}")

    try:
        sina_df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2021")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"新浪财务指标：{type(exc).__name__}: {exc}")

    em_rows = annual_rows(em_df, "REPORT_DATE")
    sina_rows = annual_rows(sina_df, "日期")
    financials: list[dict[str, Any]] = []
    for year in YEARS:
        em = em_rows.get(year)
        sina = sina_rows.get(year)
        revenue = clean_number(em.get("TOTALOPERATEREVE")) if em is not None else None
        em_cash_ratio = clean_number(em.get("JYXJLYYSR")) if em is not None else None
        sina_cash_ratio = clean_number(sina.get("经营现金净流量对销售收入比率(%)")) if sina is not None else None
        cash_ratio = em_cash_ratio if em_cash_ratio is not None else sina_cash_ratio
        # Both providers expose this ratio as a decimal despite Sina's legacy column label containing "%".
        operating_cash = revenue * cash_ratio if revenue is not None and cash_ratio is not None else None
        financials.append(
            {
                "year": year,
                "currency": "CNY",
                "revenue": rounded(revenue / 1e8 if revenue is not None else None),
                "revenueYoY": rounded(em.get("TOTALOPERATEREVETZ") if em is not None else None, 1),
                "netProfit": rounded(
                    clean_number(em.get("PARENTNETPROFIT")) / 1e8
                    if em is not None and clean_number(em.get("PARENTNETPROFIT")) is not None
                    else None
                ),
                "netProfitYoY": rounded(em.get("PARENTNETPROFITTZ") if em is not None else None, 1),
                "grossMargin": rounded(
                    (em.get("GROSS_PROFIT_RATIO") if "GROSS_PROFIT_RATIO" in em.index else em.get("XSMLL"))
                    if em is not None else None, 1
                ),
                "roe": rounded(
                    (em.get("ROE_DILUTED") if "ROE_DILUTED" in em.index else em.get("ROEJQ"))
                    if em is not None else None, 1
                ),
                "operatingCashFlow": rounded(operating_cash / 1e8 if operating_cash is not None else None),
                "debtRatio": rounded(
                    (em.get("ZCFZL") if em is not None and "ZCFZL" in em.index else sina.get("资产负债率(%)"))
                    if em is not None or sina is not None else None, 1
                ),
            }
        )

    raw = {
        "name": name,
        "code": code,
        "fetchedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "eastmoney": dataframe_records(
            em_df,
            [
                "REPORT_DATE", "TOTALOPERATEREVE", "PARENTNETPROFIT",
                "TOTALOPERATEREVETZ", "PARENTNETPROFITTZ", "GROSS_PROFIT_RATIO", "ROE_DILUTED",
                "XSMLL", "ROEJQ", "JYXJLYYSR", "ZCFZL"
            ],
        ),
        "sina": dataframe_records(
            sina_df,
            ["日期", "资产负债率(%)", "经营现金净流量对销售收入比率(%)"],
        ),
        "errors": errors,
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{code}.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"financials": financials, "errors": errors}


def fetch_pe_batch(a_codes: list[str], h_codes: list[str]) -> tuple[dict[str, float | None], dict[str, float | None]]:
    """Fetch only the requested quotes instead of crawling the full 5,000-stock table."""
    secids = []
    for code in a_codes:
        market = "1" if code.startswith(("5", "6", "9")) else "0"
        secids.append(f"{market}.{code}")
    secids.extend(f"116.{str(code).zfill(5)}" for code in h_codes)
    if not secids:
        return {}, {}
    response = requests.get(
        "https://push2.eastmoney.com/api/qt/ulist.np/get",
        params={"secids": ",".join(secids), "fields": "f12,f14,f9,f115", "fltt": "2", "invt": "2"},
        timeout=20,
    )
    response.raise_for_status()
    rows = (response.json().get("data") or {}).get("diff") or []
    a_pe: dict[str, float | None] = {}
    h_pe: dict[str, float | None] = {}
    h_set = {str(code).zfill(5) for code in h_codes}
    for row in rows:
        code = str(row.get("f12", ""))
        value = clean_number(row.get("f115")) or clean_number(row.get("f9"))
        if code.zfill(5) in h_set:
            h_pe[code.zfill(5)] = value
        else:
            a_pe[code.zfill(6)] = value
    return a_pe, h_pe


def fetch_a_listing_fast() -> dict[str, str]:
    """Read the Eastmoney A-share list concurrently; avoids slow exchange-by-exchange pagination."""
    url = "https://82.push2.eastmoney.com/api/qt/clist/get"
    base = {
        "pz": "100", "po": "1", "np": "1", "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2", "invt": "2", "fid": "f12",
        "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
        "fields": "f12,f14",
    }

    def fetch_page(page: int) -> dict[str, Any]:
        response = requests.get(url, params={**base, "pn": str(page)}, timeout=20)
        response.raise_for_status()
        return response.json().get("data") or {}

    first = fetch_page(1)
    page_count = max(1, math.ceil(int(first.get("total", 0)) / 100))
    rows = list(first.get("diff") or [])
    with ThreadPoolExecutor(max_workers=8) as executor:
        for page_data in executor.map(fetch_page, range(2, page_count + 1)):
            rows.extend(page_data.get("diff") or [])
    return {
        str(row.get("f14", "")): str(row.get("f12", "")).zfill(6)
        for row in rows if row.get("f12") and row.get("f14")
    }


def load_market_tables(target_names: list[str], hk_codes: list[str]) -> tuple[dict[str, str], dict[str, float | None], dict[str, float | None], list[str]]:
    errors: list[str] = []
    name_to_code: dict[str, str] = {}
    a_pe: dict[str, float | None] = {}
    h_pe: dict[str, float | None] = {}

    try:
        name_to_code = fetch_a_listing_fast()
    except Exception as exc:  # noqa: BLE001
        errors.append(f"A股代码表：{type(exc).__name__}: {exc}")

    try:
        requested_codes = [name_to_code[name] for name in target_names if name in name_to_code]
        a_pe, h_pe = fetch_pe_batch(requested_codes, hk_codes)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"A/H 股估值快照：{type(exc).__name__}: {exc}")

    return name_to_code, a_pe, h_pe, errors


def build_company_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    companies: dict[str, dict[str, Any]] = {}
    for node in catalog["nodes"]:
        for name in node["companies"]:
            record = companies.setdefault(
                name,
                {"name": name, "nodeIds": [], "screenshotSlots": 0, "auditNotes": []},
            )
            record["nodeIds"].append(node["id"])
            record["screenshotSlots"] += 1
            if node.get("auditNote") and node["auditNote"] not in record["auditNotes"]:
                record["auditNotes"].append(node["auditNote"])
    return companies


def main() -> int:
    parser = argparse.ArgumentParser(description="更新产业链公司财务与估值快照")
    parser.add_argument("--workers", type=int, default=4, help="并发抓取数，默认 4")
    parser.add_argument("--skip-financials", action="store_true", help="仅更新代码和估值")
    args = parser.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    previous = load_previous()
    company_index = build_company_index(catalog)
    as_of = datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"[1/4] 读取目录：20 个节点，{sum(c['screenshotSlots'] for c in company_index.values())} 个截图位置")
    hk_codes = [
        str(listing["code"]).zfill(5)
        for listings in catalog.get("listingOverrides", {}).values()
        for listing in listings
        if listing.get("market") == "H"
    ]
    name_to_code, a_pe, h_pe, market_errors = load_market_tables(list(company_index), hk_codes)
    name_to_code.update({name: str(code).zfill(6) for name, code in catalog.get("codeOverrides", {}).items()})

    # GitHub-hosted runners can occasionally fail to reach a quote endpoint. Preserve
    # last-known A-share codes so a transient outage never removes company profiles.
    reused_codes = 0
    for name in company_index:
        if name in name_to_code:
            continue
        old_a = previous_listing(previous.get(name, {}), "A")
        old_code = str(old_a.get("code", ""))
        if len(old_code) == 6 and old_code.isdigit():
            name_to_code[name] = old_code
            reused_codes += 1
    if reused_codes:
        market_errors.append(f"行情代码表未返回 {reused_codes} 家公司，已沿用上次成功代码。")

    # Refresh all requested PE snapshots, including codes restored from the previous
    # snapshot and aliases that may carry temporary XD/DR/ST prefixes in quote tables.
    try:
        requested_codes = [name_to_code[name] for name in company_index if name in name_to_code]
        refreshed_a_pe, refreshed_h_pe = fetch_pe_batch(requested_codes, hk_codes)
        a_pe.update(refreshed_a_pe)
        h_pe.update(refreshed_h_pe)
    except Exception as exc:  # noqa: BLE001
        market_errors.append(f"定向估值快照：{type(exc).__name__}: {exc}")
    print(f"[2/4] 代码表：匹配 {sum(1 for n in company_index if n in name_to_code)}/{len(company_index)} 家")

    fetched: dict[str, dict[str, Any]] = {}
    targets = [(name, name_to_code[name]) for name in company_index if name in name_to_code]
    if not args.skip_financials:
        print(f"[3/4] 抓取 {len(targets)} 家年度财务，workers={max(1, args.workers)}")
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            future_map = {
                executor.submit(fetch_financials, name, code, (index % max(1, args.workers)) * 0.15): name
                for index, (name, code) in enumerate(targets)
            }
            total = len(future_map)
            for done, future in enumerate(as_completed(future_map), 1):
                name = future_map[future]
                try:
                    fetched[name] = future.result()
                except Exception as exc:  # noqa: BLE001
                    fetched[name] = {"financials": [], "errors": [f"抓取异常：{type(exc).__name__}: {exc}"]}
                if done == 1 or done % 10 == 0 or done == total:
                    print(f"      {done}/{total} 完成")
    else:
        print("[3/4] 已跳过财务抓取")

    companies: list[dict[str, Any]] = []
    fetch_errors: list[dict[str, Any]] = []
    for name, base in company_index.items():
        code = name_to_code.get(name)
        old = previous.get(name, {})
        listings: list[dict[str, Any]] = []
        if code:
            _, market_symbol = market_suffix(code)
            exchange = "SSE" if market_symbol.startswith("SH") else "SZSE" if market_symbol.startswith("SZ") else "BSE"
            old_a = previous_listing(old, "A", code)
            has_fresh_pe = code in a_pe
            pe = a_pe.get(code) if has_fresh_pe else old_a.get("peTtm")
            listings.append(
                {
                    "market": "A", "code": code, "exchange": exchange, "name": name,
                    "peTtm": round(pe, 2) if pe is not None and pe > 0 else None,
                    "peAsOf": as_of[:10] if has_fresh_pe else old_a.get("peAsOf"),
                }
            )
            if not has_fresh_pe and old_a:
                base["auditNotes"].append("本次估值接口未返回该公司，沿用上次成功估值快照。")
        for override in catalog.get("listingOverrides", {}).get(name, []):
            hk_code = str(override["code"]).zfill(5)
            old_h = previous_listing(old, "H", hk_code)
            has_fresh_pe = hk_code in h_pe
            pe = h_pe.get(hk_code) if has_fresh_pe else old_h.get("peTtm")
            listings.append(
                {
                    **override, "code": hk_code, "exchange": "HKEX",
                    "peTtm": round(pe, 2) if pe is not None and pe > 0 else None,
                    "peAsOf": as_of[:10] if has_fresh_pe else old_h.get("peAsOf"),
                }
            )
            if not has_fresh_pe and old_h:
                base["auditNotes"].append("本次港股估值接口未返回该公司，沿用上次成功估值快照。")

        result = fetched.get(name, {})
        financials = result.get("financials", [])
        errors = result.get("errors", [])
        available = sum(1 for row in financials if row.get("revenue") is not None)
        if not financials or available == 0:
            financials = old.get("financials", [])
            if financials and not args.skip_financials:
                base["auditNotes"].append("本次财务接口失败，沿用上次成功快照。")
        if errors:
            fetch_errors.append({"name": name, "errors": errors})
        if not code:
            base["auditNotes"].append("未匹配到独立 A/H 上市公司代码，保留截图位置但不生成财务对比。")

        status = "unresolved" if not listings else "ok" if sum(1 for row in financials if row.get("revenue") is not None) >= 4 else "partial"
        companies.append(
            {
                "id": f"a-{code}" if code else f"unresolved-{len(companies) + 1}",
                **base,
                "listings": listings,
                "financials": financials or [
                    {
                        "year": year, "currency": "CNY", "revenue": None, "revenueYoY": None,
                        "netProfit": None, "netProfitYoY": None, "grossMargin": None, "roe": None,
                        "operatingCashFlow": None, "debtRatio": None,
                    }
                    for year in YEARS
                ],
                "status": status,
            }
        )

    companies.sort(key=lambda item: (item["status"] == "unresolved", item["name"]))
    output = {
        "meta": {
            "title": catalog["title"], "subtitle": catalog["subtitle"],
            "updatedAt": as_of, "financialYears": YEARS,
            "screenshotNodeCount": len(catalog["nodes"]),
            "screenshotSlotCount": sum(company["screenshotSlots"] for company in companies),
            "uniqueCompanyCount": len(companies),
            "currencyNote": "金额统一为亿元，并保留公司报告币种；本页公司主体财务均以人民币披露口径为主。",
            "disclaimer": "仅用于产业研究与信息整理，不构成任何投资建议。",
        },
        "chains": catalog["chains"], "nodes": catalog["nodes"], "edges": catalog["edges"],
        "companies": companies,
        "sources": [
            {"id": "eastmoney", "name": "东方财富财务分析", "url": "https://emweb.securities.eastmoney.com/", "role": "A/H 股财务指标与估值快照"},
            {"id": "sina", "name": "新浪财经财务指标", "url": "https://money.finance.sina.com.cn/", "role": "资产负债率与经营现金流交叉数据"},
            {"id": "cninfo", "name": "巨潮资讯", "url": "https://www.cninfo.com.cn/", "role": "A 股法定披露核验入口"},
            {"id": "hkex", "name": "港交所披露易", "url": "https://www1.hkexnews.hk/index_c.htm", "role": "港股法定披露核验入口"}
        ],
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "generatedAt": as_of,
        "summary": {
            "nodes": len(catalog["nodes"]), "screenshotSlots": output["meta"]["screenshotSlotCount"],
            "uniqueCompanies": len(companies), "resolvedListings": sum(bool(c["listings"]) for c in companies),
            "fullFinancials": sum(c["status"] == "ok" for c in companies),
            "partialFinancials": sum(c["status"] == "partial" for c in companies),
            "unresolved": sum(c["status"] == "unresolved" for c in companies),
        },
        "marketErrors": market_errors,
        "fetchErrors": fetch_errors,
        "unresolvedCompanies": [c["name"] for c in companies if c["status"] == "unresolved"],
        "missingYears": {
            c["name"]: [row["year"] for row in c["financials"] if row["revenue"] is None]
            for c in companies if any(row["revenue"] is None for row in c["financials"])
        },
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[4/4] 写入 {OUTPUT_PATH.relative_to(ROOT)}；校验报告 {REPORT_PATH.relative_to(ROOT)}")
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
