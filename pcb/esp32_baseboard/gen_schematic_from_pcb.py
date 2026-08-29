#!/usr/bin/env python3
"""Generate the schematic from the PCB's own pad->net table.

Why this direction: both files come out of gen_power_carrier.py, but the
schematic half drew its wires and labels at hardcoded coordinates that drifted
away from the symbol pin geometry, so labels landed on the wrong pins. KiCad's
schematic-parity check found J2 pin 3 wired to /EN on the schematic while the
board has /MotB1 there -- 122 conflicts of that kind.

The board side is the one that is independently verified: verify_connectivity.py
checks all 172 connections against s3_pinmap.py. So the schematic is rebuilt
from it, with a global label on every pin carrying the exact net name that pad
has. Parity then holds by construction instead of by careful drawing.

Components whose footprint has no symbol in the library (capacitors, diodes,
the PTC fuse, the buzzer and MOSFET jacks) get a generic N-pin box generated
here, so the pin count always matches the footprint.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from pcb_parse import NetTable, pad_net

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "esp32_baseboard.kicad_pcb"
SCH = ROOT / "esp32_baseboard.kicad_sch"
SYMLIB = ROOT / "libraries" / "ESP32_Carrier.kicad_sym"

GRID = 2.54
SHEET_H = 279.4  # A3


def uid() -> str:
    return str(uuid.uuid4())


def snap(v: float) -> float:
    return round(v / GRID) * GRID


def _block(text: str, start: int) -> str:
    depth, i = 0, start
    while True:
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1


def parse_footprints(text: str) -> list[dict]:
    table = NetTable(text)
    out: list[dict] = []
    for m in re.finditer(r'\n\t\(footprint "([^"]+)"', text):
        blk = _block(text, m.start() + 1)
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', blk)
        val_m = re.search(r'\(property "Value" "([^"]+)"', blk)
        if not ref_m or "board_only" in blk:
            continue  # mounting holes carry no symbol and are excluded
        pads: dict[str, str] = {}
        starts = [p.start() for p in re.finditer(r'\(pad\s+"', blk)]
        for k, ps in enumerate(starts):
            chunk = blk[ps : (starts[k + 1] if k + 1 < len(starts) else len(blk))]
            num = re.match(r'\(pad\s+"([^"]*)"', chunk).group(1)
            _nid, name = pad_net(chunk, table)
            if num:
                # Keep netless pads: they are the deliberately unrouted pins
                # (IO0, TX0/RX0, the octal-PSRAM IOs). They need a no-connect
                # flag in the schematic, or KiCad invents a net called
                # "unconnected-(U1-TX0-Pad24)" and parity reports a conflict
                # against the board's bare pad.
                pads[num] = name or None
        if any(pads.values()):
            out.append({
                "ref": ref_m.group(1),
                "fp": m.group(1),
                "value": val_m.group(1) if val_m else ref_m.group(1),
                "pads": pads,
            })
    out.sort(key=lambda c: (re.sub(r"\d+", "", c["ref"]),
                           int(re.sub(r"\D", "", c["ref"]) or 0)))
    return out


def parse_symbols(text: str) -> dict[str, dict]:
    syms: dict[str, dict] = {}
    for m in re.finditer(r'\n\t\(symbol "([A-Za-z0-9_.]+)"', text):
        name = m.group(1)
        if re.search(r"_\d+_\d+$", name):
            continue
        blk = _block(text, m.start() + 1)
        fp_m = re.search(r'\(property "Footprint" "([^"]*)"', blk)
        pins: dict[str, tuple[float, float]] = {}
        for pm in re.finditer(
            r"\(pin\s+\w+\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)\s*"
            r'\(length\s+([\d.]+)\)[\s\S]*?\(number\s+"([^"]*)"',
            blk,
        ):
            pins[pm.group(5)] = (float(pm.group(1)), float(pm.group(2)))
        names: dict[str, str] = {}
        for pm in re.finditer(
            r'\(name\s+"([^"]*)"[\s\S]{0,80}?\(number\s+"([^"]*)"', blk
        ):
            names[pm.group(2)] = pm.group(1)
        syms[name] = {"fp": fp_m.group(1) if fp_m else "", "pins": pins,
                      "names": names, "body": blk}
    return syms


def generic_symbol(name: str, fp: str, npins: int):
    """A plain box with N pins, for parts the library has no symbol for."""
    h = max(2, npins) * GRID
    lines = [
        f'\t\t(symbol "{name}"',
        "\t\t\t(pin_numbers (hide no))",
        "\t\t\t(pin_names (offset 0.508))",
        "\t\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)",
        f'\t\t\t(property "Reference" "U" (at 0 {h / 2 + 2.54} 0) '
        "(effects (font (size 1.27 1.27))))",
        f'\t\t\t(property "Value" "{name}" (at 0 {-h / 2 - 2.54} 0) '
        "(effects (font (size 1.27 1.27))))",
        f'\t\t\t(property "Footprint" "{fp}" (at 0 0 0) '
        "(effects (font (size 1.27 1.27)) (hide yes)))",
        f'\t\t\t(symbol "{name}_0_1"',
        f"\t\t\t\t(rectangle (start -2.54 {h / 2}) (end 2.54 {-h / 2})",
        "\t\t\t\t\t(stroke (width 0.254) (type default)) (fill (type none)))",
        "\t\t\t)",
        f'\t\t\t(symbol "{name}_1_1"',
    ]
    pins: dict[str, tuple[float, float]] = {}
    for i in range(npins):
        py = h / 2 - GRID / 2 - i * GRID
        lines += [
            "\t\t\t\t(pin passive line",
            f"\t\t\t\t\t(at -5.08 {py} 0)",
            "\t\t\t\t\t(length 2.54)",
            f'\t\t\t\t\t(name "P{i + 1}" (effects (font (size 1.27 1.27))))',
            f'\t\t\t\t\t(number "{i + 1}" (effects (font (size 1.27 1.27))))',
            "\t\t\t\t)",
        ]
        pins[str(i + 1)] = (-5.08, py)
    lines += ["\t\t\t)", "\t\t)"]
    return "\n".join(lines), pins


def main() -> int:
    sheet_uuid = uid()
    pcb_text = PCB.read_text(encoding="utf-8")
    comps = parse_footprints(pcb_text)
    syms = parse_symbols(SYMLIB.read_text(encoding="utf-8"))
    by_fp = {v["fp"].split(":")[-1]: k for k, v in syms.items() if v["fp"]}

    used: dict[str, dict] = {}
    for c in comps:
        fp_short = c["fp"].split(":")[-1]
        sym = by_fp.get(fp_short)
        if sym is None:
            sym = "GEN_" + re.sub(r"\W", "_", fp_short)
            if sym not in used:
                body, pins = generic_symbol(sym, c["fp"], len(c["pads"]))
                body = body.replace(
                    f'(symbol "{sym}"', f'(symbol "ESP32_Carrier:{sym}"', 1
                )
                used[sym] = {"pins": pins, "names": {}, "body": body}
        elif sym not in used:
            # lib_symbols entries must carry the library prefix, or the symbol
            # instances (which reference "ESP32_Carrier:Name") match nothing and
            # KiCad produces a netlist with no components at all.
            body = syms[sym]["body"].replace(
                f'(symbol "{sym}"', f'(symbol "ESP32_Carrier:{sym}"', 1
            )
            used[sym] = {"pins": syms[sym]["pins"],
                         "names": syms[sym].get("names", {}), "body": body}
        c["sym"] = sym

    # KiCad names a deliberately unconnected pin "unconnected-(U1-TX0-Pad24)"
    # in its netlist, and a bare pad on the board matches nothing. Write that
    # same name onto the board's netless pads -- it is what KiCad itself does
    # when a schematic is pushed to a layout.
    patched = pcb_text
    for c in comps:
        names = used[c["sym"]].get("names", {})
        want = {
            num: f"unconnected-({c['ref']}-{names.get(num, 'Pad' + num)}-Pad{num})"
            for num, net in c["pads"].items()
            if net is None
        }
        if not want:
            continue
        m = re.search(
            r'\n\t\(footprint "[^"]+"[\s\S]*?\(property "Reference" "%s"' % re.escape(c["ref"]),
            patched,
        )
        if not m:
            continue
        blk = _block(patched, patched.rfind("\t(footprint", 0, m.end()))
        new_blk = blk
        starts = [p.start() for p in re.finditer(r'\(pad\s+"', new_blk)]
        for k in range(len(starts) - 1, -1, -1):
            ps = starts[k]
            pe = starts[k + 1] if k + 1 < len(starts) else len(new_blk)
            chunk = new_blk[ps:pe]
            num = re.match(r'\(pad\s+"([^"]*)"', chunk).group(1)
            if num not in want or "(net " in chunk:
                continue
            um = re.search(r"(\s*)\(uuid ", chunk)
            if not um:
                continue
            ins = f'{um.group(1)}(net "{want[num]}")'
            new_blk = new_blk[:ps] + chunk[: um.start()] + ins + chunk[um.start():] + new_blk[pe:]
        patched = patched.replace(blk, new_blk, 1)
    if patched != pcb_text:
        PCB.write_text(patched, encoding="utf-8")
        print(f"patched {sum(1 for c in comps for v in c['pads'].values() if v is None)}"
              " netless pads with unconnected-() nets")

    parts: list[str] = []
    x, y, col_w = 25.4, 25.4, 0.0
    for c in comps:
        pins = used[c["sym"]]["pins"]
        ys = [p[1] for p in pins.values()] or [0.0]
        span = max(ys) - min(ys)
        if y + span + 25.4 > SHEET_H - 20.32:
            x += col_w + 50.8
            y, col_w = 25.4, 0.0
        ix, iy = snap(x), snap(y + span / 2 + 5.08)
        y += span + 25.4
        col_w = max(col_w, 25.4)

        parts.append(
            f'\t(symbol (lib_id "ESP32_Carrier:{c["sym"]}") (at {ix} {iy} 0) (unit 1)\n'
            "\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n"
            f'\t\t(uuid "{uid()}")\n'
            f'\t\t(property "Reference" "{c["ref"]}" (at {ix} {iy - span / 2 - 5.08} 0)\n'
            "\t\t\t(effects (font (size 1.27 1.27))))\n"
            f'\t\t(property "Value" "{c["value"]}" (at {ix} {iy + span / 2 + 5.08} 0)\n'
            "\t\t\t(effects (font (size 1.27 1.27))))\n"
            f'\t\t(property "Footprint" "{c["fp"]}" (at {ix} {iy} 0)\n'
            "\t\t\t(effects (font (size 1.27 1.27)) (hide yes)))\n"
            f'\t\t(property "Datasheet" "~" (at {ix} {iy} 0)\n'
            "\t\t\t(effects (font (size 1.27 1.27)) (hide yes)))\n"
            # Each pin needs its own uuid entry, and the symbol needs an
            # instances block: without them KiCad resolves neither the pins nor
            # the reference, the netlist comes out empty, and every footprint
            # then reads as "extra" against the schematic.
            + "".join(f'\t\t(pin "{n}" (uuid "{uid()}"))\n' for n in sorted(pins))
            + "\t\t(instances\n"
            '\t\t\t(project "esp32_baseboard"\n'
            f'\t\t\t\t(path "/{sheet_uuid}"\n'
            f'\t\t\t\t\t(reference "{c["ref"]}") (unit 1)\n'
            "\t\t\t\t)\n"
            "\t\t\t)\n"
            "\t\t)\n"
            "\t)"
        )
        for num, net in sorted(c["pads"].items()):
            pin = pins.get(num)
            if pin is None:
                continue
            lx, ly = ix + pin[0], iy - pin[1]
            if net is None:
                parts.append(f'\t(no_connect (at {lx} {ly}) (uuid "{uid()}"))')
                continue
            parts.append(
                f'\t(global_label "{net}"\n'
                "\t\t(shape input)\n"
                f"\t\t(at {lx} {ly} 180)\n"
                "\t\t(effects (font (size 1.27 1.27)) (justify right))\n"
                f'\t\t(uuid "{uid()}")\n'
                "\t)"
            )

    out = [
        "(kicad_sch",
        "\t(version 20250114)",
        '\t(generator "gen_schematic_from_pcb.py")',
        '\t(generator_version "1.0")',
        f'\t(uuid "{sheet_uuid}")',
        '\t(paper "A3")',
        "\t(lib_symbols",
        "\n".join(used[s]["body"] for s in used),
        "\t)",
        *parts,
        "\t(sheet_instances",
        '\t\t(path "/" (page "1"))',
        "\t)",
        ")",
        "",
    ]
    SCH.write_text("\n".join(out), encoding="utf-8")
    missing = sum(1 for c in comps if c["sym"].startswith("GEN_"))
    print(
        f"schematic rebuilt from PCB: {len(comps)} components "
        f"({missing} on generated symbols), "
        f"{sum(len(c['pads']) for c in comps)} pin labels -> {SCH.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
