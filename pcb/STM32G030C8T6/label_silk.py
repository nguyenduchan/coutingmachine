#!/usr/bin/env python3
"""Show Reference + Value on F.SilkS; jack silk uses purpose names."""
from __future__ import annotations

import re
from pathlib import Path

PCB = Path(__file__).resolve().parent / "STM32G030C8T6.kicad_pcb"
SCH = Path(__file__).resolve().parent / "STM32G030C8T6.kicad_sch"

# Visible purpose names on the board (and schematic Value for jacks).
PURPOSE = {
    "J1": "24V IN",
    "J_USB": "USB",
    "J_MOT1": "MOTOR 1",
    "J_MOT2": "MOTOR 2",
    "J_DISP": "DISPLAY",
    "J_KEY": "KEYPAD",
    "J14": "COUNT",
    "J15": "FIBER",
    "J_IN2": "IN 2",
    "J_IN3": "IN 3",
    "J_CNT5": "COUNT 5V",
    "J_P24S": "24V AUX",
    "U_PWR1": "MOSFET 1",
    "U_PWR2": "MOSFET 2",
    "U_VIB": "VIB SSR",
    "SW_BOOT": "BOOT",
    "SW_NRST": "RESET",
    "F1": "FUSE T2A",
    "U1": "STM32G030",
    "U2": "MP1584",
    "U3": "TMC1",
    "U4": "TMC2",
    "U5": "CH340",
    "U6": "AMS1117",
}

# Existing user-silk strings to replace (pin numbers left alone).
OLD_PURPOSE = {
    "J_MOT1": "MOT1",
    "J_MOT2": "MOT2",
    "J_DISP": "TM1637",
    "J_P24S": "+24V",
    "J14": "BUP",
    "J_CNT5": "CNT 5V",
    "J_IN2": "IN2",
    "J_IN3": "IN3",
    "U_PWR1": "MOSFET",
    "U_PWR2": "MOSFET",
    "U_VIB": "SSR",
    "U3": "TMC2209",
    "U4": "TMC2209",
    "F1": "RUT ONG",
}


def _block(text: str, start: int) -> str:
    d, i = 0, start
    while i < len(text):
        if text[i] == "(":
            d += 1
        elif text[i] == ")":
            d -= 1
            if d == 0:
                return text[start : i + 1]
        i += 1
    raise ValueError("unbalanced")


def _set_prop(blk: str, name: str, *, show: bool, silk: bool, value: str | None = None) -> str:
    m = re.search(rf'\(property "{name}" "', blk)
    if not m:
        return blk
    start = m.start()
    orig = _block(blk, start)
    prop = orig
    if value is not None:
        prop = re.sub(
            rf'\(property "{name}" "[^"]*"',
            f'(property "{name}" "{value}"',
            prop,
            count=1,
        )
    if silk:
        prop = re.sub(r'\(layer "F\.Fab"\)', '(layer "F.SilkS")', prop, count=1)
    if show:
        prop = re.sub(r"\n\t\t\t\(hide yes\)", "", prop, count=1)
    elif "(hide yes)" not in prop:
        prop = re.sub(
            r'(\(layer "[^"]+"\))',
            r'\1\n\t\t\t(hide yes)',
            prop,
            count=1,
        )
    return blk[:start] + prop + blk[start + len(orig) :]


def _add_user_silk(blk: str, text: str, y: float = -5.2) -> str:
    if re.search(rf'\(fp_text user "{re.escape(text)}"', blk):
        return blk
    insert = (
        f'\t\t(fp_text user "{text}"\n'
        f"\t\t\t(at 0 {y:g} 0)\n"
        f'\t\t\t(layer "F.SilkS")\n'
        f"\t\t\t(effects\n"
        f"\t\t\t\t(font\n"
        f"\t\t\t\t\t(size 0.7 0.7)\n"
        f"\t\t\t\t\t(thickness 0.1)\n"
        f"\t\t\t\t)\n"
        f"\t\t\t)\n"
        f"\t\t)\n"
    )
    pad = re.search(r"\n\t\t\(pad ", blk)
    if not pad:
        pad = re.search(r"\n\t\t\(embedded_fonts ", blk)
    if not pad:
        return blk
    return blk[: pad.start() + 1] + insert + blk[pad.start() + 1 :]


def label_pcb() -> None:
    text = PCB.read_text(encoding="utf-8")
    chunks: list[tuple[int, int, str]] = []
    n_show = n_purpose = 0
    for m in re.finditer(r'\n\t\(footprint "', text):
        start = m.start() + 1
        blk = _block(text, start)
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not rm:
            continue
        ref = rm.group(1)
        show_ref = True
        show_val = not ref.startswith("H")
        blk = _set_prop(blk, "Reference", show=show_ref, silk=True)
        purpose = PURPOSE.get(ref)
        is_jack = (
            ref.startswith("J") or ref.startswith("U_PWR") or ref.startswith("U_VIB")
            or ref.startswith("SW") or ref in {"U3", "U4"}
        )
        if is_jack and purpose:
            blk = _set_prop(blk, "Value", show=False, silk=False, value=purpose)
        else:
            blk = _set_prop(blk, "Value", show=show_val, silk=True)
        n_show += 1
        old = OLD_PURPOSE.get(ref)
        if purpose:
            if old and old != purpose:
                blk = re.sub(
                    rf'\(fp_text user "{re.escape(old)}"',
                    f'(fp_text user "{purpose}"',
                    blk,
                    count=1,
                )
                n_purpose += 1
            elif old == purpose:
                n_purpose += 1
            elif not re.search(rf'\(fp_text user "{re.escape(purpose)}"', blk):
                y = -5.2 if not ref.startswith("SW") else -4.4
                if ref == "F1":
                    y = -6.6
                blk = _add_user_silk(blk, purpose, y=y)
                n_purpose += 1
        chunks.append((start, start + len(_block(text, start)), blk))
    for start, end, nblk in reversed(chunks):
        text = text[:start] + nblk + text[end:]
    PCB.write_text(text, encoding="utf-8")
    print(f"PCB: showed names on {n_show} footprints, purpose silk {n_purpose}")


def label_sch() -> None:
    text = SCH.read_text(encoding="utf-8")
    n = 0

    def block(s, start):
        return _block(s, start)

    chunks = []
    for m in re.finditer(r"\n\t\(symbol \(lib_id ", text):
        start = m.start() + 1
        blk = block(text, start)
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not rm:
            continue
        ref = rm.group(1)
        purpose = PURPOSE.get(ref)
        if not purpose:
            continue
        if not (ref.startswith("J") or ref.startswith("U_PWR") or ref.startswith("U_VIB")
                or ref.startswith("SW") or ref in {"F1", "U3", "U4"}):
            continue
        vm = re.search(r'\(property "Value" "([^"]+)"', blk)
        if not vm:
            continue
        if vm.group(1) == purpose:
            continue
        blk = blk[: vm.start()] + f'(property "Value" "{purpose}"' + blk[vm.end() :]
        chunks.append((start, start + len(block(text, start)), blk))
        n += 1
    for start, end, nblk in reversed(chunks):
        text = text[:start] + nblk + text[end:]
    SCH.write_text(text, encoding="utf-8")
    print(f"SCH: purpose values on {n} symbols")


if __name__ == "__main__":
    label_pcb()
    label_sch()
