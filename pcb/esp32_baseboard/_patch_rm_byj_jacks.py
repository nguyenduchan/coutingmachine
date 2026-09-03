"""Remove redundant J5-J7 BYJ jacks; 28BYJ plugs into ULN2003 driver module JST.

- Keep U5-U7 as control landing for ULN2003 driver boards (IN1-4 + GND + +12V)
- Drop carrier Mot-style BYJ phase nets (same idea as Mot on TMC / no J2)
- Patch live sch + pcb; write ULN2003_Module footprint
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRETTY = ROOT / "libraries" / "ESP32_Carrier.pretty"
PITCH = 2.54


def uid() -> str:
    return str(uuid.uuid4())


def write_uln_module_fp() -> Path:
    """1x6 header for ULN2003 stepper driver board; motor JST stays on module."""
    labels = ["IN1", "IN2", "IN3", "IN4", "GND", "+12V"]
    n = len(labels)
    lines: list[str] = []
    a = lines.append
    a('(footprint "ULN2003_Module"')
    a("\t(version 20260206)")
    a('\t(generator "_patch_rm_byj_jacks.py")')
    a('\t(generator_version "1.0")')
    a('\t(layer "F.Cu")')
    a(
        '\t(descr "ULN2003 28BYJ driver board: IN1-4 GND +12V header; '
        'motor plugs into module JST (no carrier BYJ jack)")'
    )
    a('\t(tags "ULN2003 stepper 28BYJ module")')
    a('\t(property "Reference" "REF**"')
    a("\t\t(at 0 -3.8 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a("\t)")
    a('\t(property "Value" "ULN2003_Module"')
    a(f"\t\t(at 0 {(n - 1) * PITCH + 3.8} 0)")
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a("\t)")
    a("\t(attr through_hole)")
    # Module body courtyard ~35x32 mm, header near west edge
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        a("\t\t(start -2.5 -3.0)")
        a(f"\t\t(end 30.0 {(n - 1) * PITCH + 3.0})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")
    a('\t(fp_text user "28BYJ on module JST"')
    a("\t\t(at 14 6.35 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a("\t)")
    for i, lab in enumerate(labels):
        y = i * PITCH
        a(f'\t(fp_text user "{lab}"')
        a(f"\t\t(at -3.2 {y} 0)")
        a('\t\t(layer "F.SilkS")')
        a("\t\t(effects (font (size 0.65 0.65) (thickness 0.1)) (justify right))")
        a("\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t(pad "{i + 1}" thru_hole {shape}')
        a(f"\t\t(at 0 {y})")
        a("\t\t(size 1.7 1.7)")
        a("\t\t(drill 1.0)")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t)")
    a(")")
    out = PRETTY / "ULN2003_Module.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _remove_footprints(pcb: str, refs: set[str]) -> str:
    parts = re.split(r"(?=\n\t\(footprint )", pcb)
    out = [parts[0]]
    for p in parts[1:]:
        m = re.search(r'\(property "Reference"\s+"?([A-Z]+\d+)"?', p)
        if m and m.group(1) in refs:
            continue
        out.append(p)
    return "".join(out)


def _remove_segments_on_nets(pcb: str, net_names: set[str]) -> tuple[str, int]:
    """Drop track/via/arc segments whose net name is in net_names."""
    # Build net number -> name map
    net_num = {}
    for m in re.finditer(r'\(net (\d+) "([^"]*)"\)', pcb):
        net_num[int(m.group(1))] = m.group(2)
    drop_nums = {n for n, name in net_num.items() if name in net_names}

    removed = 0

    def drop_blocks(text: str, kind: str) -> str:
        nonlocal removed
        # (segment ... ) / (via ... ) at top indent
        pat = re.compile(rf"\n\t\({kind} [\s\S]*?\n\t\)")
        chunks = []
        last = 0
        for m in pat.finditer(text):
            block = m.group(0)
            nm = re.search(r'\(net (\d+)(?: "([^"]*)")?\)', block)
            kill = False
            if nm:
                num = int(nm.group(1))
                name = nm.group(2) if nm.group(2) is not None else net_num.get(num, "")
                if num in drop_nums or name in net_names:
                    kill = True
            if kill:
                removed += 1
                chunks.append(text[last : m.start()])
                last = m.end()
        chunks.append(text[last:])
        return "".join(chunks)

    for kind in ("segment", "via", "arc", "zone"):
        # zones rarely on BYJ; skip zone to be safe
        if kind == "zone":
            continue
        pcb = drop_blocks(pcb, kind)
    return pcb, removed


def _strip_add_nets(pcb: str, names: set[str]) -> str:
    for n in names:
        pcb = re.sub(rf'\n\t\t\(add_net "{re.escape(n)}"\)', "", pcb)
    return pcb


def _replace_uln_dip_with_module(pcb: str) -> str:
    """Replace U5/U6/U7 DIP footprints with ULN2003_Module, keep IN/+12V/GND nets."""
    axis = {
        "U5": ["SR_Q0", "SR_Q1", "SR_Q2", "SR_Q3"],
        "U6": ["SR_Q4", "SR_Q5", "SR_Q6", "SR_Q7"],
        "U7": ["SR_Q8", "SR_Q9", "SR_Q10", "SR_Q11"],
    }
    # Resolve net numbers for known nets
    net_by_name = {
        m.group(2): int(m.group(1))
        for m in re.finditer(r'\(net (\d+) "([^"]*)"\)', pcb)
    }

    parts = re.split(r"(?=\n\t\(footprint )", pcb)
    out = [parts[0]]
    for p in parts[1:]:
        m = re.search(r'\(property "Reference"\s+"?(U[567])"?', p)
        if not m:
            out.append(p)
            continue
        ref = m.group(1)
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", p)
        if not at:
            out.append(p)
            continue
        x, y = float(at.group(1)), float(at.group(2))
        rot = float(at.group(3)) if at.group(3) else 0.0
        qs = axis[ref]
        pad_nets = [
            (1, qs[0]),
            (2, qs[1]),
            (3, qs[2]),
            (4, qs[3]),
            (5, "GND"),
            (6, "+12V"),
        ]
        labels = ["IN1", "IN2", "IN3", "IN4", "GND", "+12V"]
        lines = [
            f'\n\t(footprint "ESP32_Carrier:ULN2003_Module"',
            '\t\t(layer "F.Cu")',
            f'\t\t(uuid "{uid()}")',
            f"\t\t(at {x} {y} {rot})",
            f'\t\t(property "Reference" "{ref}"',
            f"\t\t\t(at 0 -3.8 {rot})",
            '\t\t\t(layer "F.SilkS")',
            "\t\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))",
            f'\t\t\t(uuid "{uid()}")',
            "\t\t)",
            f'\t\t(property "Value" "ULN2003_Module"',
            f"\t\t\t(at 0 {5 * PITCH + 3.8} {rot})",
            '\t\t\t(layer "F.Fab")',
            "\t\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))",
            f'\t\t\t(uuid "{uid()}")',
            "\t\t)",
            "\t\t(attr through_hole)",
        ]
        for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
            lines += [
                "\t\t(fp_rect",
                "\t\t\t(start -2.5 -3.0)",
                f"\t\t\t(end 30.0 {5 * PITCH + 3.0})",
                f"\t\t\t(stroke (width {w}) (type solid))",
                "\t\t\t(fill none)",
                f'\t\t\t(layer "{layer}")',
                f'\t\t\t(uuid "{uid()}")',
                "\t\t)",
            ]
        lines += [
            '\t\t(fp_text user "28BYJ on module JST"',
            f"\t\t\t(at 14 6.35 {rot})",
            '\t\t\t(layer "F.SilkS")',
            "\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))",
            f'\t\t\t(uuid "{uid()}")',
            "\t\t)",
        ]
        for (pi, nname), lab in zip(pad_nets, labels):
            yy = (pi - 1) * PITCH
            lines += [
                f'\t\t(fp_text user "{lab}"',
                f"\t\t\t(at -3.2 {yy} {rot})",
                '\t\t\t(layer "F.SilkS")',
                "\t\t\t(effects (font (size 0.65 0.65) (thickness 0.1)) (justify right))",
                f'\t\t\t(uuid "{uid()}")',
                "\t\t)",
            ]
            shape = "rect" if pi == 1 else "circle"
            nnum = net_by_name.get(nname)
            lines += [
                f'\t\t(pad "{pi}" thru_hole {shape}',
                f"\t\t\t(at 0 {yy})",
                "\t\t\t(size 1.7 1.7)",
                "\t\t\t(drill 1.0)",
                '\t\t\t(layers "*.Cu" "*.Mask")',
            ]
            # KiCad 10 pcbnew style: bare net name (no numeric id)
            lines.append(f'\t\t\t(net "{nname}")')
            lines += [
                f'\t\t\t(uuid "{uid()}")',
                "\t\t)",
            ]
        lines.append("\t)")
        out.append("\n".join(lines))
    return "".join(out)


def _patch_silk_byj(pcb: str) -> str:
    pcb = re.sub(
        r'\(gr_text "J[567] 28BYJ BYJ[123]"[\s\S]*?\n\t\)',
        "",
        pcb,
    )
    pcb = pcb.replace("A1: HOME1+U5+J5", "A1: HOME1+U5 ULN mod")
    pcb = pcb.replace("A2: HOME2+U6+J6", "A2: HOME2+U6 ULN mod")
    pcb = pcb.replace("A3: HOME3+U7+J7", "A3: HOME3+U7 ULN mod")
    return pcb


def patch_pcb() -> None:
    path = ROOT / "esp32_baseboard.kicad_pcb"
    pcb = path.read_text(encoding="utf-8")
    byj_nets = {
        f"BYJ{a}_{p}" for a in (1, 2, 3) for p in "ABCD"
    }
    pcb = _remove_footprints(pcb, {"J5", "J6", "J7"})
    pcb, nseg = _remove_segments_on_nets(pcb, byj_nets)
    pcb = _strip_add_nets(pcb, byj_nets)
    pcb = _replace_uln_dip_with_module(pcb)
    pcb = _patch_silk_byj(pcb)
    # Drop orphan net declarations that only existed for BYJ (optional left in net section)
    path.write_text(pcb, encoding="utf-8")
    print(f"PCB: removed J5-J7, {nseg} BYJ copper items, U5-U7 -> ULN2003_Module")


def _remove_sch_symbols(sch: str, refs: set[str]) -> str:
    """Remove (symbol (lib_id ...) blocks whose Reference is in refs, plus
    immediately following global_labels that were BYJ/jack-local."""
    # Split on top-level symbol instances (not lib embeds)
    parts = re.split(r"(?=\n\t\(symbol \(lib_id)", sch)
    out = [parts[0]]
    for p in parts[1:]:
        m = re.search(r'\(property "Reference" "(J\d+|U\d+)"', p)
        if m and m.group(1) in refs:
            # Keep trailing content after the symbol's closing that isn't part of symbol —
            # our split already isolates until next symbol; but labels after jack are
            # inside this chunk after `\t)`. Truncate at end of symbol instance.
            # Find the instances/closing of this symbol then drop BYJ labels until next non-label
            # Simpler: drop whole chunk's symbol; keep any non-BYJ labels at end carefully.
            # Chunk = symbol + following labels until next symbol start (already split).
            # Remove symbol block and BYJ*/+12V labels that belonged to the jack.
            rest = p
            # strip leading symbol
            depth = 0
            end = None
            for i, ch in enumerate(rest):
                if rest.startswith("(symbol", i) or (i == 0):
                    pass
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end is None:
                continue
            after = rest[end:]
            # remove global_labels for BYJ* and lone +12V that sat on BYJ jack
            after = re.sub(
                r'\n\t\(global_label "BYJ\d_[ABCD]"[\s\S]*?\n\t\)',
                "",
                after,
            )
            # Only remove +12V labels that are clearly orphaned near jack — risky.
            # Leave +12V labels; duplicates OK on sch.
            out.append(after)
            continue
        out.append(p)
    return "".join(out)


def _strip_uln_byj_labels(sch: str) -> str:
    """Remove BYJ* global_labels that were attached to U5-U7 OUT pins."""
    return re.sub(
        r'\n\t\(global_label "BYJ\d_[ABCD]"[\s\S]*?\n\t\)',
        "",
        sch,
    )


def _update_uln_sch_symbols(sch: str) -> str:
    """Point U5-U7 Value/Footprint at ULN2003_Module; drop OUT pin entries if present."""
    for ref in ("U5", "U6", "U7"):
        # Value
        sch = re.sub(
            rf'(\(property "Reference" "{ref}"[\s\S]*?\(property "Value" ")ULN2003AN(")',
            rf"\1ULN2003_Module\2",
            sch,
            count=1,
        )
        sch = re.sub(
            rf'(\(property "Reference" "{ref}"[\s\S]*?\(property "Footprint" ")ESP32_Carrier:ULN2003AN(")',
            rf"\1ESP32_Carrier:ULN2003_Module\2",
            sch,
            count=1,
        )
    return sch


def patch_sch() -> None:
    path = ROOT / "esp32_baseboard.kicad_sch"
    sch = path.read_text(encoding="utf-8")
    sch = _remove_sch_symbols(sch, {"J5", "J6", "J7"})
    sch = _strip_uln_byj_labels(sch)
    sch = _update_uln_sch_symbols(sch)
    # Title / comments
    sch = sch.replace("J5-7 BYJ", "ULN module (BYJ on JST)")
    sch = sch.replace("J5-J7 BYJ", "ULN module; 28BYJ on module JST")
    path.write_text(sch, encoding="utf-8")
    print("SCH: removed J5-J7 + BYJ labels; U5-U7 -> ULN2003_Module")


def main() -> None:
    fp = write_uln_module_fp()
    print("Wrote", fp)
    patch_pcb()
    patch_sch()
    # sanity
    sch = (ROOT / "esp32_baseboard.kicad_sch").read_text(encoding="utf-8")
    pcb = (ROOT / "esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
    for ref in ("J5", "J6", "J7"):
        assert f'Reference" "{ref}"' not in sch, ref
        assert not re.search(rf'\(property "Reference"\s+"{ref}"', pcb), ref
    for ref in ("U5", "U6", "U7"):
        assert "ULN2003_Module" in pcb
    print("OK: no J5-J7 on sch/pcb")


if __name__ == "__main__":
    main()
