#!/usr/bin/env python3
"""JLCPCB SMT assembly BOM / CPL gates.

Bare PCB can fab without LCSC numbers. Economic SMT cannot: every placed
SMD must have an LCSC C-code in the schematic (property LCSC / LCSC Part)
or jlc_lcsc.csv. THT jacks/sockets stay 'hand solder' / Do Not Place.

  python verify_jlc_bom.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import jlcpcb_limits as JLC
from verify_jlcpcb import parse_fps

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "esp32_baseboard.kicad_pcb"
SCH = ROOT / "esp32_baseboard.kicad_sch"
MAP = ROOT / "jlc_lcsc.csv"
OUT = ROOT / "out"
JSON_OUT = OUT / "jlc_bom_verify.json"
CSV_OUT = OUT / "jlc_bom.csv"

THT_DNP = set(JLC.NORTH_JACKS) | set(JLC.SOUTH_JACKS)
THT_DNP |= {"H1", "H2", "H3", "H4", "U3", "U4",
            "U_PWR1", "U_PWR2", "U_VIB"}
# USB Micro-B is SMT (5+2 pads) even though J_USB sits on the north jack row.
SMT_FORCE = {"J_USB"}
THT_DNP -= SMT_FORCE
LCSC_RE = re.compile(r"^C\d{3,}$")


def sch_lcsc() -> dict[str, str]:
    if not SCH.exists():
        return {}
    text = SCH.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for m in re.finditer(r'\(property "Reference" "([^"]+)"', text):
        ref = m.group(1)
        if not ref or ref.endswith("?"):
            continue
        window = text[m.start() : m.start() + 5000]
        for key in ("LCSC", "LCSC Part", "lcsc", "LCSC_Part"):
            pm = re.search(rf'\(property "{key}" "([^"]+)"', window)
            if pm and LCSC_RE.match(pm.group(1).strip()):
                out[ref] = pm.group(1).strip()
                break
    return out


def file_lcsc() -> dict[str, str]:
    if not MAP.exists():
        return {}
    out = {}
    with MAP.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ref = (row.get("Designator") or row.get("ref") or "").strip()
            code = (row.get("LCSC") or row.get("lcsc") or "").strip()
            if ref and LCSC_RE.match(code):
                out[ref] = code
    return out


def main() -> int:
    fps = parse_fps(PCB.read_text(encoding="utf-8"))
    lcsc = {**file_lcsc(), **sch_lcsc()}
    fails, warns, gates = [], [], []

    def gate(name: str, ok: bool, detail: str = "") -> None:
        gates.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            fails.append(f"{name}: {detail}" if detail else name)
        print(("  PASS " if ok else "  FAIL ") + name + (f"  {detail}" if detail else ""))

    def warn(name: str, detail: str) -> None:
        warns.append(f"{name}: {detail}")
        print(f"  WARN {name}  {detail}")

    print("=== JLCPCB SMT BOM / polarity ===")
    rows = []
    smt_missing = []
    polarized_ok = []
    polarized_bad = []
    by_fp: dict[str, list[str]] = defaultdict(list)

    for fp in fps:
        if fp["board_only"]:
            continue
        ref = fp["ref"]
        smd = fp["smd"] or any(p["type"] == "smd" for p in fp["pads"])
        tht = (not smd) or ref in THT_DNP or any(p["type"] == "thru_hole" for p in fp["pads"])
        # sockets with mixed pads: treat as DNP SMT if in THT_DNP
        place = "SMT" if smd and ref not in THT_DNP else "DNP-THT"
        code = lcsc.get(ref, "")
        by_fp[place].append(ref)
        rows.append({
            "Designator": ref,
            "Comment": "",
            "Footprint": "",
            "LCSC": code,
            "Place": place,
            "Rot": f"{fp['rot']:.1f}",
            "X": f"{fp['x']:.4f}",
            "Y": f"{fp['y']:.4f}",
        })
        if place == "SMT" and not LCSC_RE.match(code):
            smt_missing.append(ref)
        if ref in JLC.POLARIZED_REFS:
            pins = {p["num"] for p in fp["pads"]}
            if "1" in pins or "MH1" in pins:
                polarized_ok.append(ref)
            else:
                polarized_bad.append(ref)

    OUT.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Designator", "Comment", "Footprint", "LCSC", "Place", "Rot", "X", "Y"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["Designator"]))

    smt_n = sum(1 for r in rows if r["Place"] == "SMT")
    gate("SMT parts exist for assembly line", smt_n > 0, f"{smt_n} SMT, {len(rows) - smt_n} DNP-THT")
    gate(
        "Every SMT part has LCSC C-code (schematic or jlc_lcsc.csv)",
        not smt_missing,
        f"{len(smt_missing)} missing: " + ", ".join(smt_missing[:20]) if smt_missing else "ok",
    )
    gate("Polarized parts have pin 1 (or USB MH)", not polarized_bad,
         ",".join(polarized_bad) if polarized_bad else f"{len(polarized_ok)} ok")

    # CPL rotation must be 0/90/180/270 for JLC
    odd_rot = [r["Designator"] for r in rows if r["Place"] == "SMT"
               and abs((float(r["Rot"]) % 90)) > 0.5]
    gate("SMT rotations are 0/90/180/270 (JLC CPL)", not odd_rot,
         ",".join(odd_rot[:8]) if odd_rot else "ok")

    if not MAP.exists() and smt_missing:
        warn("jlc_lcsc.csv absent", "copy out/jlc_bom.csv, fill LCSC, save as jlc_lcsc.csv")

    overall = all(g["ok"] for g in gates)
    report = {
        "overall": "PASS" if overall else "FAIL",
        "smt": smt_n,
        "dnp_tht": len(rows) - smt_n,
        "lcsc_missing": smt_missing,
        "gates": gates,
        "fails": fails,
        "warns": warns,
        "csv": str(CSV_OUT),
    }
    JSON_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nOVERALL: {report['overall']}  ({len(fails)} fail, {len(warns)} warn)")
    print(f"Wrote {CSV_OUT}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
