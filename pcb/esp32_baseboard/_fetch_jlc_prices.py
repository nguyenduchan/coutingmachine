#!/usr/bin/env python3
"""Fetch JLCPCB warehouse unit prices for every SMT LCSC on the carrier."""
from __future__ import annotations

import csv
import json
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAP = ROOT / "jlc_lcsc.csv"
OUT = ROOT / "out" / "jlc_part_cost.json"
FX = 26000  # VND / USD mid 2026-09

API = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"


def jlc_search(code: str) -> dict | None:
    body = json.dumps({"keyword": code, "currentPage": 1, "pageSize": 10}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://jlcpcb.com",
            "Referer": "https://jlcpcb.com/",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read().decode("utf-8"))
    rows = (((payload or {}).get("data") or {}).get("componentPageInfo") or {}).get("list") or []
    for row in rows:
        if (row.get("componentCode") or "").strip().upper() == code.upper():
            return row
    return rows[0] if rows else None


def unit_at(prices: list, qty: int) -> float | None:
    if not prices:
        return None
    for p in prices:
        start = int(p.get("startNumber") or 1)
        end = int(p.get("endNumber") or -1)
        if qty >= start and (end < 0 or qty <= end):
            return float(p["productPrice"])
    return float(prices[-1]["productPrice"])


def main() -> None:
    rows = list(csv.DictReader(MAP.open(encoding="utf-8")))
    by_code: dict[str, dict] = {}
    for r in rows:
        code = r["LCSC"].strip()
        rec = by_code.setdefault(
            code,
            {
                "lcsc": code,
                "mfr": r["Mfr"],
                "mpn": r["MPN"],
                "package": r["Package"],
                "refs": [],
                "qty": 0,
            },
        )
        rec["refs"].append(r["Designator"])
        rec["qty"] += 1

    catalog = {}
    missing = []
    for i, code in enumerate(sorted(by_code)):
        print(f"[{i+1}/{len(by_code)}] {code}", flush=True)
        try:
            hit = jlc_search(code)
        except Exception as e:
            hit = None
            print("  ERR", e)
        if not hit:
            missing.append(code)
            catalog[code] = None
        else:
            catalog[code] = {
                "code": hit.get("componentCode"),
                "brand": hit.get("componentBrandEn"),
                "mpn": hit.get("componentModelEn"),
                "pkg": hit.get("componentSpecificationEn"),
                "lib": hit.get("componentLibraryType"),
                "stock": hit.get("stockCount"),
                "prices": hit.get("componentPrices") or [],
                "buy_prices": hit.get("buyComponentPrices") or [],
                "initial": hit.get("initialPrice"),
            }
        time.sleep(0.35)

    lots = (1, 5, 10, 100)
    lines = []
    lot_totals = {q: 0.0 for q in lots}
    for code, rec in sorted(by_code.items(), key=lambda kv: kv[1]["qty"], reverse=True):
        info = catalog.get(code) or {}
        prices = info.get("prices") or []
        row = {
            **rec,
            "lib": info.get("lib"),
            "stock": info.get("stock"),
            "jlc_mpn": info.get("mpn"),
            "usd_each": {},
            "usd_board": {},
            "vnd_board": {},
        }
        for q in lots:
            unit = unit_at(prices, rec["qty"] * q)
            row["usd_each"][str(q)] = unit
            board = (unit or 0.0) * rec["qty"]
            row["usd_board"][str(q)] = round(board, 4)
            row["vnd_board"][str(q)] = round(board * FX)
            lot_totals[q] += board
        lines.append(row)

    lines.sort(key=lambda r: r["usd_board"]["1"], reverse=True)
    report = {
        "fx_vnd_per_usd": FX,
        "source": "JLCPCB SMT componentPrices 2026-09-17",
        "smt_unique": len(by_code),
        "smt_places": sum(r["qty"] for r in by_code.values()),
        "missing": missing,
        "usd_per_board": {str(q): round(v, 4) for q, v in lot_totals.items()},
        "vnd_per_board": {str(q): round(v * FX) for q, v in lot_totals.items()},
        "lines": lines,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("missing", "usd_per_board", "vnd_per_board")}, indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
