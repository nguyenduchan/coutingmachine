#!/usr/bin/env python3
"""4-layer EMI stack + SMT conversion + route (2 signal layers, min vias).

Stack (JLCPCB standard 4L 1.6 mm):
    F.Cu   signal  (vertical prefer)
    In1.Cu GND plane
    In2.Cu split power  +24V south / +5V west / +3V3 east
    B.Cu   signal  (horizontal prefer)

THT stays only where a plug is required (field jacks, TMC/Power/Vib sockets,
J1 terminal). Fuse and BOOT/NRST become SMT.

Run with KiCad's Python:

    "%LOCALAPPDATA%\\Programs\\KiCad\\10.0\\bin\\python.exe" route_4layer.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PCB = HERE / "esp32_baseboard.kicad_pcb"
PRETTY = HERE / "libraries" / "ESP32_Carrier.pretty"

SMT_SWAPS = {
    "SW_BOOT": "SW_Push_6mm_SMD",
    "SW_NRST": "SW_Push_6mm_SMD",
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


def _pad_nets(blk: str) -> dict[str, str]:
    nets: dict[str, str] = {}
    starts = [m.start() for m in re.finditer(r'\(pad "', blk)]
    for i, s in enumerate(starts):
        chunk = blk[s : (starts[i + 1] if i + 1 < len(starts) else len(blk))]
        num = re.match(r'\(pad "([^"]*)"', chunk)
        net = re.search(r'\(net "([^"]*)"\)', chunk)
        if num and net:
            nets[num.group(1)] = net.group(1)
    return nets


def swap_smt_text() -> None:
    text = PCB.read_text(encoding="utf-8")
    for ref, new_name in SMT_SWAPS.items():
        hit = None
        for m in re.finditer(r'\n\t\(footprint "', text):
            blk = _block(text, m.start() + 1)
            if f'(property "Reference" "{ref}"' in blk:
                hit = (m.start() + 1, blk)
                break
        if hit is None:
            print(f"  skip {ref}: not in file")
            continue
        start, old = hit
        if f'ESP32_Carrier:{new_name}"' in old[:80]:
            print(f"  {ref} already {new_name}")
            continue
        at = re.search(r"\(at [^\n]+\)", old)
        uid = re.search(r'\(uuid "[^"]+"\)', old)
        val_m = re.search(r'\(property "Value" "([^"]*)"', old)
        val = val_m.group(1) if val_m else new_name
        nets = _pad_nets(old)
        mod = (PRETTY / f"{new_name}.kicad_mod").read_text(encoding="utf-8").strip()
        if mod.endswith(")"):
            inner = mod[mod.find("\n") + 1 : -1].rstrip()
        else:
            inner = mod
        # drop lib header fields we rewrite
        inner = re.sub(r"\n?\t*\(version [^\n]+\)", "", inner, count=1)
        inner = re.sub(r"\n?\t*\(generator [^\n]+\)", "", inner, count=1)
        inner = re.sub(r'\n?\t*\(layer "[^"]+"\)', "", inner, count=1)
        for num, net in nets.items():
            inner = re.sub(
                rf'(\(pad "{re.escape(num)}"[\s\S]*?\(layers [^)]+\))',
                rf'\1 (net "{net}")',
                inner,
                count=1,
            )
        at_s = at.group(0) if at else "(at 0 0)"
        uid_s = uid.group(0) if uid else f'(uuid "{os.urandom(8).hex()}")'
        new_blk = (
            f'(footprint "ESP32_Carrier:{new_name}"\n'
            f'\t\t(layer "F.Cu")\n'
            f"\t\t{uid_s}\n"
            f"\t\t{at_s}\n"
            f'\t\t(property "Reference" "{ref}"\n'
            f'\t\t\t(at 0 -2.2 0)\n'
            f'\t\t\t(layer "F.SilkS")\n'
            f'\t\t\t(hide yes)\n'
            f'\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12))))\n'
            f'\t\t(property "Value" "{val}"\n'
            f'\t\t\t(at 0 2.2 0)\n'
            f'\t\t\t(layer "F.Fab")\n'
            f'\t\t\t(hide yes)\n'
            f'\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1))))\n'
            f"{inner}\n\t)"
        )
        text = text[:start] + new_blk + text[start + len(old) :]
        print(f"  {ref} → {new_name} (nets {nets})")
    PCB.write_text(text, encoding="utf-8")


def set_4layer(board) -> None:
    import pcbnew

    board.SetCopperLayerCount(4)
    enabled = board.GetEnabledLayers()
    enabled.AddLayer(pcbnew.In1_Cu)
    enabled.AddLayer(pcbnew.In2_Cu)
    board.SetEnabledLayers(enabled)
    board.SetLayerName(pcbnew.In1_Cu, "In1.Cu")
    board.SetLayerName(pcbnew.In2_Cu, "In2.Cu")
    board.SetLayerType(pcbnew.F_Cu, pcbnew.LT_SIGNAL)
    board.SetLayerType(pcbnew.B_Cu, pcbnew.LT_SIGNAL)
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)
    ds = board.GetDesignSettings()
    # Through via spans all copper (F..B). House 0.8 / 0.4.
    try:
        ds.m_ViasMinSize = pcbnew.FromMM(0.8)
        ds.m_ViasMinDrill = pcbnew.FromMM(0.4)
    except AttributeError:
        pass
    print(f"  copper layers = {board.GetCopperLayerCount()}")


def setup() -> None:
    import pcbnew

    swap_smt_text()
    board = pcbnew.LoadBoard(str(PCB))
    if board is None:
        raise SystemExit("LoadBoard failed")
    set_4layer(board)
    pcbnew.SaveBoard(str(PCB), board)
    print(f"setup saved {PCB.name}")


def main() -> int:
    os.environ.setdefault("FR_CLEAR_UM", "250")
    os.environ.setdefault("FR_TIMEOUT_S", "800")
    os.environ.setdefault("FR_ATTEMPTS", "90:200,140:70,180:30")
    setup()
    # Fresh interpreter: KiCad 10 SWIG breaks after the first LoadBoard.
    return subprocess.call(
        [sys.executable, str(HERE / "route_freerouting.py")],
        cwd=str(HERE),
    )


if __name__ == "__main__":
    raise SystemExit(main())
