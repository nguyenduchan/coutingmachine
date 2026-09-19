#!/usr/bin/env python3
"""Rewire esp32_baseboard.kicad_sch into functional clusters.

Keeps lib_symbols, references, footprints and net names. Draws wires inside
each cluster; global labels join the same net across clusters (and to the PCB).
"""
from __future__ import annotations

import re
import uuid
from collections import defaultdict
from pathlib import Path

from gen_schematic_from_pcb import GRID, _block, parse_footprints, snap, uid

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "esp32_baseboard.kicad_pcb"
SCH = ROOT / "esp32_baseboard.kicad_sch"

# A1: room for U1 (LQFP48 ~122 mm) plus satellite clusters.
PAPER = "A1"
SHEET_UUID = "104f720f-6c0d-4cdd-b2ff-299bfce56fbe"

CLUSTERS: list[tuple[str, float, float, list[str]]] = [
    ("24V IN / SNS", 25.4, 20.0, [
        "J1", "D3", "F1", "D1", "C21", "J_P24S",
        "PTC_SNS", "R10", "C10", "C11", "C26",
    ]),
    ("BUCK +5V", 250.0, 20.0, [
        "U2", "L1", "D4", "Cbst", "Cc", "R_FREQ", "Rfb1", "Rfb2",
        "C5", "C51", "C27", "C53", "D5",
    ]),
    ("3V3", 500.0, 20.0, [
        "U6", "C3", "C31", "C52",
    ]),
    ("USB-UART", 620.0, 20.0, [
        "J_USB", "U5", "Y1", "C_XI", "C_XO", "C_V3",
    ]),
    ("MCU STM32G030", 25.4, 160.0, [
        "U1", "C_MCU", "C_MCU2", "C_NRST", "R_NRST", "R_BOOT", "R_SWDIO",
        "SW_BOOT", "SW_NRST", "R2", "R2B",
        "R_PD_STEP", "R_PD_DIR", "R_PD_STEP2", "R_PD_DIR2",
    ]),
    ("TMC1", 300.0, 160.0, [
        "U3", "PTC_MOT", "C20", "C24", "J_MOT1",
    ]),
    ("TMC2", 470.0, 160.0, [
        "U4", "PTC_MOT2", "C20B", "C24B", "J_MOT2",
    ]),
    ("DO / VIB", 640.0, 160.0, [
        "U_PWR1", "U_PWR2", "U_VIB",
        "R_PD_PWM1", "R_PD_EN1", "R_PD_PWM2", "R_PD_EN2", "R_PD_VIB",
        "R_PWR_FLT", "R_VIB_FLT",
    ]),
    ("OPTO IN", 25.4, 440.0, [
        "J14", "J15", "R1", "R44", "U44", "R48",
        "J_IN2", "R45", "U45", "R49",
        "J_IN3", "R46", "U46", "R50",
        "J_CNT5", "R47", "U47", "R51",
    ]),
    ("HMI", 560.0, 440.0, [
        "J_KEY", "J_DISP",
    ]),
]


def extract_lib_symbols(sch: str) -> str:
    start = sch.index("(lib_symbols")
    return "\t" + _block(sch, start)


def parse_lib_pins(lib_block: str) -> dict[str, dict[str, tuple[float, float]]]:
    """lib_id -> {pin_number: (x, y)} in symbol space (Y up)."""
    out: dict[str, dict[str, tuple[float, float]]] = {}
    for m in re.finditer(r'\(symbol "([^"]+)"', lib_block):
        name = m.group(1)
        if re.search(r"_\d+_\d+$", name.split(":")[-1]):
            continue
        blk = _block(lib_block, m.start())
        pins: dict[str, tuple[float, float]] = {}
        for pm in re.finditer(
            r"\(pin\s+\w+\s+\w+\s*\(at\s+(\S+)\s+(\S+)",
            blk,
        ):
            rest = blk[pm.end() : pm.end() + 400]
            num = re.search(r'\(number\s+"([^"]*)"', rest)
            if num:
                pins[num.group(1)] = (float(pm.group(1)), float(pm.group(2)))
        out[name] = pins
        short = name.split(":")[-1]
        out.setdefault(short, pins)
        out.setdefault(f"ESP32_Carrier:{short}", pins)
    return out


def parse_sch_meta(sch: str) -> dict[str, dict]:
    """ref -> lib_id, value, footprint, pin numbers on the instance."""
    meta: dict[str, dict] = {}
    for m in re.finditer(r"\n\t\(symbol \(lib_id ", sch):
        blk = _block(sch, m.start() + 1)
        lib = re.search(r'\(lib_id "([^"]+)"', blk)
        ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
        val = re.search(r'\(property "Value" "([^"]+)"', blk)
        fp = re.search(r'\(property "Footprint" "([^"]+)"', blk)
        if not (lib and ref):
            continue
        pins = re.findall(r'\t\t\(pin "([^"]+)"', blk)
        meta[ref.group(1)] = {
            "lib_id": lib.group(1),
            "value": val.group(1) if val else ref.group(1),
            "fp": fp.group(1) if fp else "",
            "pins": pins,
        }
    return meta


def pin_sheet(sx: float, sy: float, px: float, py: float) -> tuple[float, float]:
    return sx + px, sy - py


def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


def symbol_block(ref, meta, ix, iy, pins_xy, sheet_uuid) -> str:
    ys = [p[1] for p in pins_xy.values()] or [0.0]
    span = (max(ys) - min(ys)) if ys else 5.08
    pin_lines = "".join(f'\t\t(pin "{n}" (uuid "{uid()}"))\n' for n in meta["pins"] or pins_xy)
    return (
        f'\t(symbol (lib_id "{meta["lib_id"]}") (at {fmt(ix)} {fmt(iy)} 0) (unit 1)\n'
        "\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n"
        f'\t\t(uuid "{uid()}")\n'
        f'\t\t(property "Reference" "{ref}" (at {fmt(ix)} {fmt(iy - span / 2 - 5.08)} 0)\n'
        "\t\t\t(effects (font (size 1.27 1.27))))\n"
        f'\t\t(property "Value" "{meta["value"]}" (at {fmt(ix)} {fmt(iy + span / 2 + 5.08)} 0)\n'
        "\t\t\t(effects (font (size 1.27 1.27))))\n"
        f'\t\t(property "Footprint" "{meta["fp"]}" (at {fmt(ix)} {fmt(iy)} 0)\n'
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes)))\n"
        f'\t\t(property "Datasheet" "~" (at {fmt(ix)} {fmt(iy)} 0)\n'
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes)))\n"
        f"{pin_lines}"
        "\t\t(instances\n"
        '\t\t\t(project "esp32_baseboard"\n'
        f'\t\t\t\t(path "/{sheet_uuid}"\n'
        f'\t\t\t\t\t(reference "{ref}") (unit 1)\n'
        "\t\t\t\t)\n"
        "\t\t\t)\n"
        "\t\t)\n"
        "\t)"
    )


def wire(x1, y1, x2, y2) -> str:
    if abs(x1 - x2) < 0.01 and abs(y1 - y2) < 0.01:
        return ""
    return (
        "\t(wire\n"
        f"\t\t(pts (xy {fmt(x1)} {fmt(y1)}) (xy {fmt(x2)} {fmt(y2)}))\n"
        "\t\t(stroke (width 0) (type default))\n"
        f'\t\t(uuid "{uid()}")\n'
        "\t)"
    )


def glabel(net: str, x: float, y: float, rot: int = 180) -> str:
    just = "right" if rot in (180, 270) else "left"
    return (
        f'\t(global_label "{net}"\n'
        "\t\t(shape input)\n"
        f"\t\t(at {fmt(x)} {fmt(y)} {rot})\n"
        f"\t\t(effects (font (size 1.27 1.27)) (justify {just}))\n"
        f'\t\t(uuid "{uid()}")\n'
        "\t)"
    )


def noconnect(x, y) -> str:
    return f'\t(no_connect (at {fmt(x)} {fmt(y)}) (uuid "{uid()}"))'


def title(text: str, x: float, y: float) -> str:
    return (
        f'\t(text "{text}"\n'
        "\t\t(exclude_from_sim no)\n"
        f"\t\t(at {fmt(x)} {fmt(y)} 0)\n"
        "\t\t(effects (font (size 2.54 2.54) (bold yes)) (justify left bottom))\n"
        f'\t\t(uuid "{uid()}")\n'
        "\t)"
    )


def place_cluster_refs(refs: list[str], ox: float, oy: float, meta, lib_pins, pads):
    """Hub IC on the right, 2-pin/small parts in a left column."""
    hub_names = {
        "U1", "U2", "U3", "U4", "U5", "U6",
        "U44", "U45", "U46", "U47",
        "U_PWR1", "U_PWR2", "U_VIB",
    }
    hubs = [r for r in refs if r in hub_names]
    # Prefer the largest pin-count hub.
    def pin_count(r):
        return len(lib_pins.get(meta[r]["lib_id"], {})) if r in meta else 0

    hub = max(hubs, key=pin_count) if hubs else None
    others = [r for r in refs if r != hub]
    pos: dict[str, tuple[float, float]] = {}
    if hub:
        hpins = lib_pins[meta[hub]["lib_id"]]
        hspan = max(p[1] for p in hpins.values()) - min(p[1] for p in hpins.values())
        pos[hub] = (snap(ox + 45.0), snap(oy + 15.0 + hspan / 2))
        below = hspan > 40.0
    else:
        hspan = 0.0
        below = False
    for i, r in enumerate(others):
        if r not in meta:
            continue
        pins = lib_pins[meta[r]["lib_id"]]
        ys = [p[1] for p in pins.values()] or [0.0]
        span = max(ys) - min(ys)
        col, row = i % 5, i // 5
        if below:
            pos[r] = (
                snap(ox + 12.7 + col * 22.86),
                snap(oy + 20.0 + hspan + 20.0 + row * 22.86 + span / 2),
            )
        else:
            pos[r] = (
                snap(ox + 12.7 + col * 22.86),
                snap(oy + 22.86 + row * 22.86 + span / 2),
            )
            if hub:
                pos[hub] = (snap(ox + 130.0), snap(oy + 40.0 + hspan / 2))
    return pos, hub


def wire_cluster(pos, refs, meta, lib_pins, pads, hub=None) -> list[str]:
    """Label every pin with the PCB net; add short same-row wires only.

    Generic symbols put every pin on the left, so a vertical series bus would
    run through the other pin of the same part. A horizontal wire is drawn
    only when two same-net pins share a Y and nothing foreign sits between.
    """
    del hub  # placement-only; labels carry nets across the hub
    items: list[str] = []
    pins_out: list[tuple[str, float, float]] = []

    for ref in refs:
        if ref not in pos or ref not in meta:
            continue
        ix, iy = pos[ref]
        pins = lib_pins[meta[ref]["lib_id"]]
        padmap = pads.get(ref, {})
        for num, (px, py) in pins.items():
            x, y = pin_sheet(ix, iy, px, py)
            net = padmap.get(num)
            if net is None or (isinstance(net, str) and net.startswith("unconnected-")):
                items.append(noconnect(x, y))
                continue
            items.append(glabel(net, x, y))
            pins_out.append((net, x, y))

    drawn: set[tuple[float, float, float, float]] = set()
    for i, (n1, x1, y1) in enumerate(pins_out):
        for n2, x2, y2 in pins_out[i + 1 :]:
            if n1 != n2 or abs(y1 - y2) > 0.15:
                continue
            if abs(x1 - x2) < 2.0:
                continue
            xa, xb = min(x1, x2), max(x1, x2)
            blocked = False
            for n3, x3, y3 in pins_out:
                if n3 == n1:
                    continue
                if abs(y3 - y1) < 1.2 and xa + 0.4 < x3 < xb - 0.4:
                    blocked = True
                    break
            if blocked:
                continue
            key = (round(xa, 2), round(y1, 2), round(xb, 2), round(y1, 2))
            if key in drawn:
                continue
            drawn.add(key)
            w = wire(x1, y1, x2, y2)
            if w:
                items.append(w)
    return items


def main() -> int:
    sch = SCH.read_text(encoding="utf-8")
    lib_block = extract_lib_symbols(sch)
    lib_pins = parse_lib_pins(lib_block)
    meta = parse_sch_meta(sch)
    comps = parse_footprints(PCB.read_text(encoding="utf-8"))
    pads = {c["ref"]: c["pads"] for c in comps}

    missing = [r for _, _, _, refs in CLUSTERS for r in refs if r not in meta]
    extra = set(meta) - {r for _, _, _, refs in CLUSTERS for r in refs}
    if missing:
        print("missing from schematic:", missing)
        return 1
    if extra:
        print("not clustered (will omit):", sorted(extra))

    body: list[str] = []
    for title_s, ox, oy, refs in CLUSTERS:
        body.append(title(title_s, ox, oy))
        pos, hub = place_cluster_refs(refs, ox, oy, meta, lib_pins, pads)
        for ref, (ix, iy) in pos.items():
            pins = lib_pins[meta[ref]["lib_id"]]
            body.append(symbol_block(ref, meta[ref], ix, iy, pins, SHEET_UUID))
        body.extend(wire_cluster(pos, refs, meta, lib_pins, pads, hub=hub))

    out = [
        "(kicad_sch",
        "\t(version 20250114)",
        '\t(generator "layout_sch_clusters.py")',
        '\t(generator_version "1.0")',
        f'\t(uuid "{SHEET_UUID}")',
        f'\t(paper "{PAPER}")',
        lib_block,
        *body,
        "\t(sheet_instances",
        '\t\t(path "/" (page "1"))',
        "\t)",
        ")",
        "",
    ]
    SCH.write_text("\n".join(out), encoding="utf-8")
    print(f"clustered schematic -> {SCH.name}  paper {PAPER}  clusters {len(CLUSTERS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
