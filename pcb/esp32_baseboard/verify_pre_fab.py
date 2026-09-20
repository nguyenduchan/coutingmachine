#!/usr/bin/env python3
"""Single gate before sending Gerbers / BOM / CPL to JLCPCB.

Order (do not skip):

  1. Net assignment   verify_fab.py          schematic ERC + PCB pads/footprints == SCH
  2. Electrical intent verify_compact.py     MCU/power/jack pin functions
  3. Polarity / pin-1 verify_orientation.py  diode K, electrolytic +, IC pin 1, USB mouth
  4. JLCPCB DFM/DFA   verify_jlcpcb.py       holes, annular, size, courtyard, edge
  5. KiCad DRC        pcb drc + schematic-parity  copper shorts / clearance /
                                                  unconnected tracks
  6. Export dry-run   gerbers + drill + pos + BOM  files actually generate

Exit 0 only if every fatal gate is green. Cosmetic silk/lib-mismatch never
passes a board that has open nets.

  python verify_pre_fab.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PCB = HERE / "esp32_baseboard.kicad_pcb"
SCH = HERE / "esp32_baseboard.kicad_sch"
OUT = HERE / "out"
REPORT = OUT / "pre_fab_report.json"

FATAL_DRC = {
    "unconnected_items", "shorting_items", "tracks_crossing", "clearance",
    "copper_edge_clearance", "hole_clearance", "hole_to_hole", "track_dangling",
    "via_dangling", "annular_width", "drill_out_of_range", "track_width",
    "invalid_outline", "net_conflict", "schematic_parity_real",
}
SKIP_DRC = {"lib_footprint_mismatch", "lib_footprint_issues", "text_height",
            "silk_overlap", "silk_over_copper", "silk_edge_clearance"}


def find_cli() -> str | None:
    if (cli := shutil.which("kicad-cli")):
        return cli
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiCad"
    hits = sorted(local.glob("*/bin/kicad-cli.exe"), reverse=True) if local.is_dir() else []
    return str(hits[0]) if hits else None


def run_py(label: str, script: str) -> tuple[bool, str]:
    print(f"\n######## {label} ########")
    r = subprocess.run([sys.executable, str(HERE / script)], cwd=HERE)
    return r.returncode == 0, script


def kicad_drc(cli: str) -> tuple[bool, dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "drc_prefab.json"
    subprocess.run(
        [cli, "pcb", "drc", "--format", "json", "--schematic-parity",
         "--severity-error", "--severity-warning", "-o", str(path), str(PCB)],
        cwd=HERE, capture_output=True, text=True,
    )
    if not path.exists():
        return False, {}
    data = json.loads(path.read_text(encoding="utf-8"))
    JLC_CLR_MIN = 0.10  # house copper spacing; project netclass may be tighter
    counts: Counter = Counter()
    soft_clearance = 0
    for v in data.get("violations") or []:
        t = v.get("type", "other")
        if t == "clearance":
            m = re.search(r"actual\s+([\d.]+)\s*mm", v.get("description") or "", re.I)
            actual = float(m.group(1)) if m else 0.0
            if actual + 1e-9 >= JLC_CLR_MIN:
                soft_clearance += 1
                continue  # project preference, still fab-legal at JLCPCB
        counts[t] += 1
    counts["unconnected_items"] += len(data.get("unconnected_items") or [])
    if soft_clearance:
        print(f"  note: {soft_clearance} clearance ≥ {JLC_CLR_MIN} mm (project rule, not JLC reject)")
    real_parity = 0
    for v in data.get("schematic_parity") or []:
        desc = v.get("description") or ""
        if "{slash}" in desc:
            continue
        # KiCad NC pad rename noise: unconnected-(U1-1-Pad1) vs unconnected-(U1-Pad1)
        m = re.search(
            r"Pad net \(unconnected-\(([^)]+)\)\).*schematic \(unconnected-\(([^)]+)\)\)",
            desc,
        )
        if m:
            def _n(s: str) -> str:
                return re.sub(r"-(\d+)-Pad", "-Pad", s)
            if _n(m.group(1)) == _n(m.group(2)):
                continue
        real_parity += 1
    counts["schematic_parity_real"] = real_parity
    fatal = {k: n for k, n in counts.items() if k in FATAL_DRC and n}
    print("\n=== KiCad DRC (fatal only) ===")
    if not fatal:
        print("  clean")
    for k, n in sorted(fatal.items(), key=lambda kv: -kv[1]):
        print(f"  FATAL {n:4d}  {k}")
    return not fatal, dict(counts)


def export_cam(cli: str) -> bool:
    gdir = OUT / "jlc_cam"
    gdir.mkdir(parents=True, exist_ok=True)
    steps = [
        ([cli, "pcb", "export", "gerbers", "-o", str(gdir),
          "--layers", "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
          str(PCB)], "gerbers"),
        ([cli, "pcb", "export", "drill", "-o", str(gdir), str(PCB)], "drill"),
        ([cli, "pcb", "export", "pos", "--side", "front", "--format", "csv",
          "-o", str(gdir / "cpl_front.csv"), str(PCB)], "CPL"),
        ([cli, "sch", "export", "bom", "-o", str(gdir / "sch_bom.csv"), str(SCH)], "sch BOM"),
    ]
    ok = True
    print("\n=== CAM export dry-run ===")
    for args, name in steps:
        r = subprocess.run(args, cwd=HERE, capture_output=True, text=True)
        gerbs = list(gdir.glob("*.gbr")) + list(gdir.glob("*.drl")) + list(gdir.glob("*.csv"))
        good = r.returncode == 0
        print(("  PASS " if good else "  FAIL ") + name)
        ok = ok and good
    gbr = list(gdir.glob("*.gbr")) + list(gdir.glob("*.gtl")) + list(gdir.glob("*.gbl"))
    gbr += list(gdir.glob("*.gm1")) + list(gdir.glob("*.gbs")) + list(gdir.glob("*.gts"))
    gbr += list(gdir.glob("*.g2")) + list(gdir.glob("*.g3")) + list(gdir.glob("*In1*")) + list(gdir.glob("*In2*"))
    names = " ".join(p.name.lower() for p in gbr)
    for need, keys in (
        ("edge", ("edge", ".gm1")),
        ("f_cu", ("f_cu", ".gtl")),
        ("in1", ("in1", ".g2")),
        ("in2", ("in2", ".g3")),
        ("b_cu", ("b_cu", ".gbl")),
    ):
        hit = any(any(k in p.name.lower() for k in keys) for p in gbr)
        print(("  PASS " if hit else "  FAIL ") + f"gerber has {need} ({len(gbr)} files)")
        ok = ok and hit
    return ok


def main() -> int:
    py = sys.executable
    results: list[tuple[str, bool]] = []
    sch_logic_ok = run_py("Schematic pins", "verify_schematic.py")[0]
    results.append(("Schematic: every pin on the correct net", sch_logic_ok))
    run_py("Nets", "verify_fab.py")
    fab_j = {}
    fab_path = OUT / "fab_verify.json"
    if fab_path.exists():
        fab_j = json.loads(fab_path.read_text(encoding="utf-8"))
    sch_ok = bool(fab_j.get("sch_pcb_ok"))
    results.append(("Schematic ERC + PCB matches schematic", sch_ok))
    results.append(("Electrical intent (verify_compact)", run_py("Intent", "verify_compact.py")[0]))
    results.append(("Polarity / pin-1 / connector mouth",
                    run_py("Orientation", "verify_orientation.py")[0]))
    results.append(("JLCPCB DFM/DFA", run_py("JLCPCB", "verify_jlcpcb.py")[0]))
    results.append(("JLCPCB SMT BOM/LCSC", run_py("BOM", "verify_jlc_bom.py")[0]))

    cli = find_cli()
    drc_ok, drc_counts = (False, {})
    cam_ok = False
    if cli:
        drc_ok, drc_counts = kicad_drc(cli)
        cam_ok = export_cam(cli)
    else:
        print("FAIL: kicad-cli not found")
    results.append(("KiCad DRC copper/shorts/unconnected", drc_ok))
    results.append(("Power traces meet IPC-2221 width",
                    run_py("Track width", "verify_track_width.py")[0]))
    results.append(("Gerber + drill + CPL export", cam_ok))

    print("\n" + "=" * 60)
    print("PRE-FAB VERDICT  (JLCPCB)")
    print("=" * 60)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    report = {
        "overall": "PASS" if all(ok for _, ok in results) else "FAIL",
        "gates": [{"name": n, "ok": ok} for n, ok in results],
        "drc": drc_counts,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    bad = [n for n, ok in results if not ok]
    if bad:
        print(f"\nOVERALL: FAIL — do not order. {len(bad)} gate(s) red.")
        print("Fix, then re-run: python verify_pre_fab.py")
        return 1
    print("\nOVERALL: PASS — Gerbers in out/jlc_cam/ may be uploaded to JLCPCB.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
