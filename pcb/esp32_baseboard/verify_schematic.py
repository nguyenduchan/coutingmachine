#!/usr/bin/env python3
"""Schematic is the source of truth: every pin must be wired correctly.

  python verify_schematic.py

Fails if ERC is dirty, a signal net has only one pin, or a known power/MCU
pin is on the wrong net. Does not look at copper — that is verify_fab.py.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from stm32_pinmap import LQFP48_PINS
from verify_fab import _u1_intent, sanity

ROOT = Path(__file__).resolve().parent
SCH = ROOT / "esp32_baseboard.kicad_sch"
OUT = ROOT / "out"
JSON_OUT = OUT / "sch_verify.json"

FATAL_ERC = {
    "pin_to_pin", "hier_label_mismatch", "confliction", "different_unit",
    "duplicate_reference", "power_pin_not_driven", "pin_not_connected",
    "similar_labels", "label_dangling", "global_label_dangling",
}

# ref.pad → required net (schematic pin numbers)
WANT: dict[tuple[str, str], str] = {
    ("J1", "1"): "+24V_RAW", ("J1", "2"): "GND",
    ("D3", "1"): "+24V_RAW", ("D3", "2"): "+24V_PRE",
    ("F1", "1"): "+24V_PRE", ("F1", "2"): "+24V",
    ("D1", "1"): "GND", ("D1", "2"): "+24V",
    ("J_USB", "1"): "+5V", ("J_USB", "2"): "/USB_DM", ("J_USB", "3"): "/USB_DP",
    ("J_USB", "5"): "GND", ("J_USB", "MH1"): "GND", ("J_USB", "MH2"): "GND",
    ("U6", "1"): "GND", ("U6", "2"): "+3V3", ("U6", "3"): "+5V", ("U6", "TAB"): "+3V3",
    ("U5", "2"): "/UART_RX", ("U5", "3"): "/UART_TX",
    ("U5", "5"): "/USB_DP", ("U5", "6"): "/USB_DM",
    ("U3", "9"): "+24V_MOT", ("U3", "15"): "+3V3",
    ("U3", "7"): "/STEP", ("U3", "8"): "/DIR", ("U3", "1"): "/EN_TMC",
    ("U4", "9"): "+24V_MOT2", ("U4", "15"): "+3V3",
    ("U4", "7"): "/STEP2", ("U4", "8"): "/DIR2", ("U4", "1"): "/EN_TMC2",
    ("J_MOT1", "1"): "/MotA2", ("J_MOT1", "4"): "/MotB2",
    ("J_MOT2", "1"): "/Mot2A2", ("J_MOT2", "4"): "/Mot2B2",
    ("J_DISP", "1"): "/TM_CLK", ("J_DISP", "2"): "/TM_DIO",
    ("J_DISP", "3"): "+5V", ("J_DISP", "4"): "GND",
}


def _canon(n: str | None) -> str | None:
    if not n:
        return None
    if n.startswith("unconnected"):
        return None
    return n.replace("{slash}", "/")


def find_cli() -> str | None:
    if (cli := shutil.which("kicad-cli")):
        return cli
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiCad"
    hits = sorted(base.glob("*/bin/kicad-cli.exe"), reverse=True) if base.is_dir() else []
    return str(hits[0]) if hits else None


def parse_sch_xml(path: Path) -> dict[str, dict[str, str | None]]:
    tree = ET.parse(path)
    out: dict[str, dict[str, str | None]] = defaultdict(dict)
    for net in tree.getroot().findall(".//net"):
        name = _canon(net.attrib.get("name") or net.attrib.get("Name"))
        for node in net.findall("node"):
            ref = node.attrib.get("ref") or node.attrib.get("Ref")
            pin = node.attrib.get("pin") or node.attrib.get("Pin")
            if ref and pin:
                out[ref][pin] = name
    return dict(out)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cli = find_cli()
    xml_path = OUT / "sch_netlist.xml"
    erc_path = OUT / "erc_sch.json"
    if not cli:
        print("FAIL: kicad-cli not found")
        return 1
    subprocess.run(
        [cli, "sch", "export", "netlist", "--format", "kicadxml",
         "-o", str(xml_path), str(SCH)],
        cwd=ROOT, capture_output=True, text=True,
    )
    subprocess.run(
        [cli, "sch", "erc", "--format", "json", "--severity-error",
         "-o", str(erc_path), str(SCH)],
        cwd=ROOT, capture_output=True, text=True,
    )
    if not xml_path.exists():
        print("FAIL: schematic netlist not exported")
        return 1
    sch = parse_sch_xml(xml_path)

    erc_counts: dict[str, int] = defaultdict(int)
    if erc_path.exists():
        data = json.loads(erc_path.read_text(encoding="utf-8"))
        for sheet in data.get("sheets") or []:
            for v in sheet.get("violations") or []:
                erc_counts[v.get("type", "other")] += 1
        for v in data.get("violations") or []:
            erc_counts[v.get("type", "other")] += 1
    erc_fatal = {t: n for t, n in erc_counts.items() if t in FATAL_ERC and n}

    pin_fail: list[str] = []
    for (ref, pad), want in sorted(WANT.items()):
        got = _canon((sch.get(ref) or {}).get(pad))
        if got != want:
            pin_fail.append(f"{ref}.{pad} SCH={got!r} want {want!r}")

    gpio = {str(num): name for num, name in LQFP48_PINS}
    for pad, net in sorted(_u1_intent().items(), key=lambda kv: int(kv[0])):
        got = _canon((sch.get("U1") or {}).get(pad))
        if got != net:
            pin_fail.append(f"U1.{pad}({gpio.get(pad, '')}) SCH={got!r} want {net!r}")

    sanity_fail = sanity(sch, "SCH")

    by_net: dict[str, list[str]] = defaultdict(list)
    for ref, pads in sch.items():
        if str(ref).startswith("H"):
            continue
        for pad, net in pads.items():
            n = _canon(net)
            if n:
                by_net[n].append(f"{ref}.{pad}")
    orphans = [n for n, pins in by_net.items()
               if n.startswith("/") and len(pins) < 2]

    gates = [
        ("netlist exported", bool(sch)),
        ("ERC fatal = 0", not erc_fatal),
        ("required pin nets", not pin_fail),
        ("electrical sanity", not sanity_fail),
        ("signal nets ≥2 pins", not orphans),
        ("F1 present on schematic", "F1" in sch),
    ]
    ok = all(g[1] for g in gates)
    report = {
        "overall": "PASS" if ok else "FAIL",
        "gates": [{"name": n, "ok": v} for n, v in gates],
        "erc_fatal": erc_fatal,
        "pin_fail": pin_fail[:80],
        "sanity_fail": sanity_fail,
        "orphans": orphans[:40],
        "sch_refs": len(sch),
        "sch_pins": sum(len(p) for p in sch.values()),
    }
    JSON_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("=== Schematic verify (source of truth) ===")
    for name, gok in gates:
        print(f"  {'PASS' if gok else 'FAIL'}  {name}")
    for s in pin_fail[:40]:
        print(f"  FAIL {s}")
    for s in sanity_fail:
        print(f"  FAIL {s}")
    if erc_fatal:
        print("ERC fatal:", dict(erc_fatal))
    if orphans:
        print("orphan signals:", orphans[:20])
    print(f"OVERALL: {report['overall']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
