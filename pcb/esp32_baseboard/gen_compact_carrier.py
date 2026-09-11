#!/usr/bin/env python3
"""Compact carrier — placement + nets only (NO tracks/vias).

  python gen_compact_carrier.py
  python gen_schematic_from_pcb.py
  python verify_compact.py

KiCad-valid S-expr; footprints copied from libraries/ESP32_Carrier.pretty.
Placement pipeline (no routing) — full EDA guide:
  1) graph partition / min-cut (FM refine)
  2) analytical quadratic wirelength (Jacobi)
  3) force-directed springs (+ antenna keepout)
  4) genetic / evolutionary (XY + 90 rotation)
  5) simulated annealing (XY + rotation, Metropolis)
  6) legalization + shrink Edge.Cuts
"""

from __future__ import annotations

import math
import random
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from esp32_pinmap import (
    BUP_GPIO,
    BUZZER_GPIO,
    KEYPAD_GPIO,
    PIN_BY_NAME,
    TM1637_GPIO,
    TMC_GPIO,
    WROOM_LEFT,
    WROOM_RIGHT,
)

from placement_full import PlaceCfg, pack_parts as _pack_parts_full

ROOT = Path(__file__).resolve().parent
PRETTY = ROOT / "libraries" / "ESP32_Carrier.pretty"
PCB = ROOT / "esp32_baseboard.kicad_pcb"

# Mutated by shrink search in main()
BOARD_W = 90.0
BOARD_H = 90.0
OX, OY = 50.0, 50.0  # Edge.Cuts origin
MARGIN = 4.0  # keep parts inside edge
GAP = 2.5  # min clear space between courtyards (mm)

# WROOM-32: antenna along local +Y; with rot=180 antenna points world −Y (board top / north).
ANT_TIP = 13.5  # mm from module origin to antenna tip (courtyard +Y)
ANT_CLEAR = 15.0  # mm keepout beyond tip (no other parts)
ANT_HALF_W = 14.0  # keepout half-width about antenna axis


def uid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Footprint helpers
# ---------------------------------------------------------------------------

def ensure_extra_footprints() -> None:
    """Create any missing .kicad_mod used by this board."""
    PRETTY.mkdir(parents=True, exist_ok=True)

    def write(name: str, body: str, *, force: bool = False) -> None:
        p = PRETTY / f"{name}.kicad_mod"
        if force or not p.exists():
            p.write_text(body.strip() + "\n", encoding="utf-8")

    # WROOM-32 (antenna +Y)
    pads = []
    pitch, y0, xl, xr = 1.27, 11.43, -9.0, 9.0
    for num, name in WROOM_LEFT:
        y = y0 - (num - 1) * pitch
        shape = "rect" if num == 1 else "roundrect"
        rr = " (roundrect_rratio 0.25)" if shape == "roundrect" else ""
        pads.append(
            f'\t(pad "{num}" smd {shape} (at {xl} {y:.3f}) (size 1.5 0.9)'
            f'\n\t\t(layers "F.Cu" "F.Paste" "F.Mask"){rr})'
        )
    for num, name in WROOM_RIGHT:
        y = y0 - (38 - num) * pitch
        pads.append(
            f'\t(pad "{num}" smd roundrect (at {xr} {y:.3f}) (size 1.5 0.9)'
            f'\n\t\t(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))'
        )
    write(
        "ESP32_WROOM_32",
        f"""
(footprint "ESP32_WROOM_32"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "ESP32-WROOM-32 soldered module")
\t(tags "ESP32 WROOM")
\t(attr smd)
\t(fp_rect (start -9.5 -13.5) (end 9.5 13.5)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(fp_rect (start -9.5 -13.5) (end 9.5 13.5)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(fp_text user "ANT" (at 0 12.2 0) (layer "F.SilkS")
\t\t(effects (font (size 0.7 0.7) (thickness 0.1))))
{chr(10).join(pads)}
)
""",
    )

    write(
        "CH340C",
        """
(footprint "CH340C"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "CH340C SOP-16")
\t(attr smd)
\t(fp_rect (start -5.2 -5.2) (end 5.2 5.2)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd rect (at -4.7 4.445) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at -4.7 3.175) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "3" smd rect (at -4.7 1.905) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "4" smd rect (at -4.7 0.635) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "5" smd rect (at -4.7 -0.635) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "6" smd rect (at -4.7 -1.905) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "7" smd rect (at -4.7 -3.175) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "8" smd rect (at -4.7 -4.445) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "9" smd rect (at 4.7 -4.445) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "10" smd rect (at 4.7 -3.175) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "11" smd rect (at 4.7 -1.905) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "12" smd rect (at 4.7 -0.635) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "13" smd rect (at 4.7 0.635) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "14" smd rect (at 4.7 1.905) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "15" smd rect (at 4.7 3.175) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "16" smd rect (at 4.7 4.445) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
    )

    write(
        "USB_MicroB",
        """
(footprint "USB_MicroB"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "USB Micro-B THT")
\t(attr through_hole)
\t(fp_rect (start -4.5 -4) (end 4.5 3.5)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(fp_rect (start -5 -4.5) (end 5 4)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" thru_hole rect (at -2.0 0) (size 1.2 1.2) (drill 0.7) (layers "*.Cu" "*.Mask"))
\t(pad "2" thru_hole circle (at -1.0 0) (size 1.2 1.2) (drill 0.7) (layers "*.Cu" "*.Mask"))
\t(pad "3" thru_hole circle (at 0.0 0) (size 1.2 1.2) (drill 0.7) (layers "*.Cu" "*.Mask"))
\t(pad "4" thru_hole circle (at 1.0 0) (size 1.2 1.2) (drill 0.7) (layers "*.Cu" "*.Mask"))
\t(pad "5" thru_hole circle (at 2.0 0) (size 1.2 1.2) (drill 0.7) (layers "*.Cu" "*.Mask"))
\t(pad "MH1" thru_hole circle (at -3.5 -2.5) (size 1.8 1.8) (drill 1.1) (layers "*.Cu" "*.Mask"))
\t(pad "MH2" thru_hole circle (at 3.5 -2.5) (size 1.8 1.8) (drill 1.1) (layers "*.Cu" "*.Mask"))
)
""",
    )

    write(
        "Buzzer_5V_THT",
        """
(footprint "Buzzer_5V_THT"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "Active buzzer 5V")
\t(attr through_hole)
\t(fp_circle (center 0 0) (end 6 0)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(fp_circle (center 0 0) (end 6.5 0)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" thru_hole rect (at -2.54 0) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask"))
\t(pad "2" thru_hole circle (at 2.54 0) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask"))
)
""",
    )

    write(
        "PinHeader_1x08_Keypad",
        """
(footprint "PinHeader_1x08_Keypad"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "1x8 keypad header")
\t(attr through_hole)
\t(fp_rect (start -1.5 -1.5) (end 1.5 19.5)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" thru_hole rect (at 0 0) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
\t(pad "2" thru_hole circle (at 0 2.54) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
\t(pad "3" thru_hole circle (at 0 5.08) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
\t(pad "4" thru_hole circle (at 0 7.62) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
\t(pad "5" thru_hole circle (at 0 10.16) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
\t(pad "6" thru_hole circle (at 0 12.7) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
\t(pad "7" thru_hole circle (at 0 15.24) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
\t(pad "8" thru_hole circle (at 0 17.78) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
)
""",
    )

    write(
        "PinHeader_1x10_7SEG",
        """
(footprint "PinHeader_1x10_7SEG"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "1x10 header — external 3-digit 7seg CC (G1-G3 + A-G)")
	(attr through_hole)
	(fp_rect (start -1.5 -1.5) (end 1.5 24.6)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(pad "1" thru_hole rect (at 0 0) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "2" thru_hole circle (at 0 2.54) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "3" thru_hole circle (at 0 5.08) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "4" thru_hole circle (at 0 7.62) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "5" thru_hole circle (at 0 10.16) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "6" thru_hole circle (at 0 12.7) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "7" thru_hole circle (at 0 15.24) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "8" thru_hole circle (at 0 17.78) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "9" thru_hole circle (at 0 20.32) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "10" thru_hole circle (at 0 22.86) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
)
""",
        force=True,
    )

    for name, val in (("R_0805_4k7", "4k7"), ("R_0805_10k", "10k"), ("R_0805_2k2", "2k2")):
        write(
            name,
            f"""
(footprint "{name}"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "0805 {val}")
\t(attr smd)
\t(fp_rect (start -1.1 -0.7) (end 1.1 0.7)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd rect (at -0.95 0) (size 0.7 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at 0.95 0) (size 0.7 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        )

    write(
        "AMS1117_SOT223",
        """
(footprint "AMS1117_SOT223"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "AMS1117-3.3 SOT-223")
\t(attr smd)
\t(fp_rect (start -3.7 -3.7) (end 3.7 4.5)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd rect (at -2.3 -2.15) (size 1.5 1.8) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at 0 -2.15) (size 1.5 1.8) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "3" smd rect (at 2.3 -2.15) (size 1.5 1.8) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "TAB" smd rect (at 0 2.9) (size 3.6 2.2) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
    )

    # Discrete MP1584EN (SOT-23-8) — NOT the Shopee module
    # Pinout MP1584: 1=SW 2=EN 3=COMP 4=FB 5=GND 6=IN 7=NC 8=BS
    write(
        "MP1584EN_SOT23-8",
        """
(footprint "MP1584EN_SOT23-8"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "MP1584EN discrete buck SOT-23-8")
\t(attr smd)
\t(fp_rect (start -2.2 -2.0) (end 2.2 2.0)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd rect (at -2.45 1.905) (size 1.0 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at -2.45 0.635) (size 1.0 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "3" smd rect (at -2.45 -0.635) (size 1.0 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "4" smd rect (at -2.45 -1.905) (size 1.0 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "5" smd rect (at 2.45 -1.905) (size 1.0 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "6" smd rect (at 2.45 -0.635) (size 1.0 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "7" smd rect (at 2.45 0.635) (size 1.0 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t	(pad "8" smd rect (at 2.45 1.905) (size 1.0 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )
    write(
        "L_SMD_6x6",
        """
(footprint "L_SMD_6x6"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "Power inductor ~6x6mm 10uH")
\t(attr smd)
\t(fp_rect (start -3.2 -3.2) (end 3.2 3.2)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd rect (at -2.8 0) (size 1.5 2.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t	(pad "2" smd rect (at 2.8 0) (size 1.5 2.5) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )
    write(
        "C_0805",
        """
(footprint "C_0805"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "0805 capacitor")
\t(attr smd)
\t(fp_rect (start -1.1 -0.7) (end 1.1 0.7)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd rect (at -0.95 0) (size 0.7 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at 0.95 0) (size 0.7 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )
    # TM1637 SOP-20 discrete — Titan: 1-6 GRID, 7-14 SEG, 15 VDD, 16 GND, 17 DIO, 18 CLK
    write(
        "TM1637_SOP20",
        """
(footprint "TM1637_SOP20"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "TM1637 LED driver SOP-20 discrete")
\t(attr smd)
\t(fp_rect (start -6.6 -7.0) (end 6.6 7.0)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd rect (at -5.9 5.715) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at -5.9 4.445) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "3" smd rect (at -5.9 3.175) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "4" smd rect (at -5.9 1.905) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "5" smd rect (at -5.9 0.635) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "6" smd rect (at -5.9 -0.635) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "7" smd rect (at -5.9 -1.905) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "8" smd rect (at -5.9 -3.175) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "9" smd rect (at -5.9 -4.445) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "10" smd rect (at -5.9 -5.715) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "11" smd rect (at 5.9 -5.715) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "12" smd rect (at 5.9 -4.445) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "13" smd rect (at 5.9 -3.175) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "14" smd rect (at 5.9 -1.905) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "15" smd rect (at 5.9 -0.635) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "16" smd rect (at 5.9 0.635) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "17" smd rect (at 5.9 1.905) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "18" smd rect (at 5.9 3.175) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "19" smd rect (at 5.9 4.445) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "20" smd rect (at 5.9 5.715) (size 1.2 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )
    write(
        "LED_7SEG_3DIG_CC",
        """
(footprint "LED_7SEG_3DIG_CC"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "3-digit 7-segment common cathode for TM1637")
	(attr through_hole)
	(fp_rect (start -12 -8) (end 12 8)
		(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
	(fp_rect (start -12.5 -8.5) (end 12.5 8.5)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(pad "1" thru_hole rect (at -7.62 6.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
	(pad "2" thru_hole circle (at -5.08 6.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
	(pad "3" thru_hole circle (at -2.54 6.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
	(pad "4" thru_hole circle (at 0 6.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
	(pad "5" thru_hole circle (at 2.54 6.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
	(pad "6" thru_hole circle (at 5.08 6.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
	(pad "7" thru_hole circle (at 7.62 6.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
	(pad "8" thru_hole circle (at -7.62 -6.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
	(pad "9" thru_hole circle (at -5.08 -6.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
	(pad "10" thru_hole circle (at -2.54 -6.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
)
""",
        force=True,
    )
    # --- All-SMT functional parts (connectors / sockets stay THT hand-solder) ---
    write(
        "Diode_SMA",
        """
(footprint "Diode_SMA"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "SMA / DO-214AC Schottky SS34 SS54")
	(attr smd)
	(fp_rect (start -2.8 -1.6) (end 2.8 1.6)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(fp_line (start 1.4 -1.1) (end 1.4 1.1)
		(stroke (width 0.12) (type solid)) (layer "F.SilkS"))
	(pad "1" smd rect (at -2.0 0) (size 1.5 1.8) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "2" smd rect (at 2.0 0) (size 1.5 1.8) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )
    write(
        "Diode_SMB_TVS",
        """
(footprint "Diode_SMB_TVS"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "SMB / DO-214AA TVS SMBJ26A")
	(attr smd)
	(fp_rect (start -3.2 -2.0) (end 3.2 2.0)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(fp_line (start 1.6 -1.3) (end 1.6 1.3)
		(stroke (width 0.12) (type solid)) (layer "F.SilkS"))
	(pad "1" smd rect (at -2.3 0) (size 1.8 2.2) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "2" smd rect (at 2.3 0) (size 1.8 2.2) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )
    write(
        "CP_SMD_D6.3x5.8",
        """
(footprint "CP_SMD_D6.3x5.8"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "SMD electrolytic ~6.3x5.8mm (47u-220u)")
	(attr smd)
	(fp_rect (start -3.8 -3.8) (end 3.8 3.8)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(fp_circle (center 0 0) (end 3.15 0)
		(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
	(pad "1" smd rect (at -2.2 0) (size 1.8 3.5) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "2" smd rect (at 2.2 0) (size 1.8 3.5) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )
    write(
        "CP_SMD_D8x10",
        """
(footprint "CP_SMD_D8x10"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "SMD electrolytic ~8x10mm (470u/50V class)")
	(attr smd)
	(fp_rect (start -5.0 -5.0) (end 5.0 5.0)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(fp_circle (center 0 0) (end 4.0 0)
		(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
	(pad "1" smd rect (at -2.8 0) (size 2.2 4.5) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "2" smd rect (at 2.8 0) (size 2.2 4.5) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )
    write(
        "PC817_SOP4",
        """
(footprint "PC817_SOP4"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "PC817 / EL817 optocoupler SOP-4")
	(attr smd)
	(fp_rect (start -3.2 -2.8) (end 3.2 2.8)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(pad "1" smd rect (at -2.3 1.27) (size 1.2 0.7) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "2" smd rect (at -2.3 -1.27) (size 1.2 0.7) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "3" smd rect (at 2.3 -1.27) (size 1.2 0.7) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "4" smd rect (at 2.3 1.27) (size 1.2 0.7) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )
    write(
        "Buzzer_SMD_5V",
        """
(footprint "Buzzer_SMD_5V"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "SMD active buzzer 5V ~9x9mm")
	(attr smd)
	(fp_rect (start -5.5 -5.5) (end 5.5 5.5)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(fp_circle (center 0 0) (end 4.5 0)
		(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
	(pad "1" smd rect (at -3.0 0) (size 1.8 2.5) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "2" smd rect (at 3.0 0) (size 1.8 2.5) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )


def courtyard_size(fp_name: str) -> tuple[float, float]:
    """Return (width, height) packing AABB: max(CrtYd/Silk/Fab, pad extents) + margin."""
    path = PRETTY / f"{fp_name}.kicad_mod"
    if not path.exists():
        return (12.0, 12.0)
    text = path.read_text(encoding="utf-8")
    half_w = half_h = 0.0
    for layer in ("F.CrtYd", "F.Fab", "F.SilkS"):
        m = re.search(
            rf'\(fp_rect\s*\(start\s+([-\d.]+)\s+([-\d.]+)\)\s*\(end\s+([-\d.]+)\s+([-\d.]+)\)[\s\S]*?layer "{layer}"',
            text,
        )
        if m:
            x0, y0, x1, y1 = map(float, m.groups())
            half_w = max(half_w, abs(x0), abs(x1), abs(x1 - x0) / 2)
            half_h = max(half_h, abs(y0), abs(y1), abs(y1 - y0) / 2)
            break
    m = re.search(r"\(fp_circle.*?\(end\s+([-\d.]+)", text, re.S)
    if m:
        r = abs(float(m.group(1)))
        half_w = max(half_w, r)
        half_h = max(half_h, r)
    # Pads often stick past silk (axial diodes, etc.)
    for pm in re.finditer(
        r'\(pad\s+"[^"]+"\s+\w+\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)',
        text,
    ):
        px, py = float(pm.group(1)), float(pm.group(2))
        chunk = text[pm.start() : pm.start() + 280]
        sm = re.search(r"\(size\s+([-\d.]+)\s+([-\d.]+)\)", chunk)
        if sm:
            sx, sy = float(sm.group(1)) / 2, float(sm.group(2)) / 2
        else:
            sx = sy = 0.9
        half_w = max(half_w, abs(px) + sx)
        half_h = max(half_h, abs(py) + sy)
    if half_w < 0.5 or half_h < 0.5:
        return (12.0, 12.0)
    # Extra packing margin so bodies/silk don't look glued
    pad = 0.8
    return (2 * half_w + pad, 2 * half_h + pad)


def inject_nets_into_mod(mod_text: str, pad_nets: dict[str, str], net_ids: dict[str, int]) -> str:
    """Return footprint body (without outer name line) with nets on pads."""

    def repl(m: re.Match) -> str:
        full = m.group(0)
        pnum = m.group(1)
        # strip existing net
        full = re.sub(r'\s*\(net\s+(?:\d+\s+)?"[^"]*"\)', "", full)
        net = pad_nets.get(pnum, "")
        if not net:
            return full
        nid = net_ids[net]
        # insert before uuid or before closing paren of pad
        if "(uuid" in full:
            return full.replace("(uuid", f'(net {nid} "{net}")\n\t\t\t(uuid', 1)
        # pad ends with )
        return full[:-1] + f'\n\t\t(net {nid} "{net}")\n\t)'

    # match each pad block
    return re.sub(
        r'\(pad\s+"([^"]+)"[\s\S]*?\n\t\)',
        repl,
        mod_text,
        flags=re.M,
    )


def load_mod_body(fp_name: str) -> str:
    text = (PRETTY / f"{fp_name}.kicad_mod").read_text(encoding="utf-8")
    # strip outer (footprint "name" ... final )
    text = text.strip()
    if text.startswith("(footprint"):
        # remove first line and last )
        lines = text.splitlines()
        # drop first line, drop last )
        body = "\n".join(lines[1:])
        if body.rstrip().endswith(")"):
            # remove final closing of footprint
            body = body.rstrip()
            # find last lone )
            body = body[: body.rfind(")")].rstrip()
        return body
    return text


# ---------------------------------------------------------------------------
# Placement algorithm
# ---------------------------------------------------------------------------

@dataclass
class Part:
    ref: str
    fp: str
    value: str
    cluster: str
    w: float
    h: float
    rot: float = 0.0
    x: float = 0.0  # world center
    y: float = 0.0
    pad_nets: dict[str, str] = field(default_factory=dict)
    board_only: bool = False


def build_parts() -> list[Part]:
    ensure_extra_footprints()

    def P(ref, fp, value, cluster, pad_nets=None, rot=0.0, board_only=False):
        w, h = courtyard_size(fp)
        if rot in (90, 270):
            w, h = h, w
        return Part(ref, fp, value, cluster, w, h, rot, pad_nets=pad_nets or {}, board_only=board_only)

    gpio_net = {
        TMC_GPIO["STEP"]: "/STEP",
        TMC_GPIO["DIR"]: "/DIR",
        TMC_GPIO["EN"]: "/EN_TMC",
        BUP_GPIO: "/BUP",
        BUZZER_GPIO: "/BUZZER",
        TM1637_GPIO["CLK"]: "/TM_CLK",
        TM1637_GPIO["DIO"]: "/TM_DIO",
        **{KEYPAD_GPIO[k]: f"/KEY_{k.replace('ROW','R').replace('COL','C')}" for k in KEYPAD_GPIO},
    }
    # normalize KEY names
    gpio_net = {
        TMC_GPIO["STEP"]: "/STEP",
        TMC_GPIO["DIR"]: "/DIR",
        TMC_GPIO["EN"]: "/EN_TMC",
        BUP_GPIO: "/BUP",
        BUZZER_GPIO: "/BUZZER",
        TM1637_GPIO["CLK"]: "/TM_CLK",
        TM1637_GPIO["DIO"]: "/TM_DIO",
        KEYPAD_GPIO["ROW0"]: "/KEY_R0",
        KEYPAD_GPIO["ROW1"]: "/KEY_R1",
        KEYPAD_GPIO["ROW2"]: "/KEY_R2",
        KEYPAD_GPIO["ROW3"]: "/KEY_R3",
        KEYPAD_GPIO["COL0"]: "/KEY_C0",
        KEYPAD_GPIO["COL1"]: "/KEY_C1",
        KEYPAD_GPIO["COL2"]: "/KEY_C2",
        KEYPAD_GPIO["COL3"]: "/KEY_C3",
    }

    u1_nets: dict[str, str] = {}
    for num, name in WROOM_LEFT + WROOM_RIGHT:
        if name == "GND":
            u1_nets[str(num)] = "GND"
        elif name == "3V3":
            u1_nets[str(num)] = "+3V3"
        elif name == "EN":
            u1_nets[str(num)] = "+3V3"
        elif name == "TXD0":
            u1_nets[str(num)] = "/UART_TX"
        elif name == "RXD0":
            u1_nets[str(num)] = "/UART_RX"
        elif name.startswith("IO") and name[2:].isdigit():
            g = int(name[2:])
            if g in gpio_net:
                u1_nets[str(num)] = gpio_net[g]

    parts = [
        P("H1", "MountingHole_M3", "M3", "MOUNT", board_only=True),
        P("H2", "MountingHole_M3", "M3", "MOUNT", board_only=True),
        P("H3", "MountingHole_M3", "M3", "MOUNT", board_only=True),
        P("H4", "MountingHole_M3", "M3", "MOUNT", board_only=True),
        P("J_USB", "USB_MicroB", "USB", "MCU", {
            "1": "+5V", "2": "/USB_DM", "3": "/USB_DP", "5": "GND", "MH1": "GND", "MH2": "GND",
        }),
        P("U5", "CH340C", "CH340C", "MCU", {
            "1": "GND", "2": "/UART_RX", "3": "/UART_TX", "4": "+3V3",
            "5": "/USB_DP", "6": "/USB_DM", "16": "+5V",
        }),
        P("U1", "ESP32_WROOM_32", "WROOM-32", "MCU", u1_nets, rot=180),
        P("U6", "AMS1117_SOT223", "AMS1117-3.3", "MCU", {
            "1": "GND", "2": "+3V3", "3": "+5V", "TAB": "+3V3",
        }),
        P("J1", "TerminalBlock_2P_5.0mm", "24V_IN", "POWER", {"1": "+24V_RAW", "2": "GND"}),
        # Input protect SMT (fuse holder = hand-solder socket later)
        P("D3", "Diode_SMA", "SS54", "POWER", {"1": "+24V_RAW", "2": "+24V_PRE"}),
        P("F1", "Fuse_Holder_5x20_Open", "T2.5A", "POWER", {"1": "+24V_PRE", "2": "+24V"}, rot=90),
        P("D1", "Diode_SMB_TVS", "SMBJ26A", "POWER", {"1": "GND", "2": "+24V"}),  # A=GND K=+24V
        # Discrete buck 24V→5V: U2 + L1 + D4 + Rfb + Cbst
        P("U2", "MP1584EN_SOT23-8", "MP1584EN", "POWER", {
            "1": "/BUCK_SW", "2": "+24V", "3": "/BUCK_COMP", "4": "/BUCK_FB",
            "5": "GND", "6": "+24V", "8": "/BUCK_BS",
        }),
        P("L1", "L_SMD_6x6", "10uH", "POWER", {"1": "/BUCK_SW", "2": "+5V"}),
        P("D4", "Diode_SMA", "SS34", "POWER", {"1": "GND", "2": "/BUCK_SW"}),
        P("Rfb1", "R_0805_4k7", "52k3", "POWER", {"1": "+5V", "2": "/BUCK_FB"}),
        P("Rfb2", "R_0805_10k", "10k", "POWER", {"1": "/BUCK_FB", "2": "GND"}),
        P("Cbst", "C_0805", "10n", "POWER", {"1": "/BUCK_BS", "2": "/BUCK_SW"}),
        P("Cc", "C_0805", "3n3", "POWER", {"1": "/BUCK_COMP", "2": "GND"}),
        P("R10", "R_1206_10R", "10R", "POWER", {"1": "+24V", "2": "+24V_SNS"}),
        P("C10", "CP_SMD_D6.3x5.8", "47u/50V", "POWER", {"1": "+24V_SNS", "2": "GND"}),
        P("C11", "C_0805_100n", "100n", "POWER", {"1": "+24V_SNS", "2": "GND"}),
        P("C21", "CP_SMD_D6.3x5.8", "220u/50V", "POWER", {"1": "+24V", "2": "GND"}),
        P("C20", "CP_SMD_D8x10", "470u/50V", "TMC", {"1": "+24V", "2": "GND"}),
        P("C24", "C_0805_100n", "100n", "TMC", {"1": "+24V", "2": "GND"}),
        P("C5", "CP_SMD_D6.3x5.8", "100u/16V", "MCU", {"1": "+5V", "2": "GND"}),
        P("C51", "C_0805_100n", "100n", "MCU", {"1": "+5V", "2": "GND"}),
        P("C3", "CP_SMD_D6.3x5.8", "47u/10V", "MCU", {"1": "+3V3", "2": "GND"}),
        P("C31", "C_0805_100n", "100n", "MCU", {"1": "+3V3", "2": "GND"}),
        P("U3", "TMC2209_StepStick", "TMC_SOCK", "TMC", {
            "1": "/EN_TMC", "7": "/STEP", "8": "/DIR",
            "9": "+24V", "10": "GND",
            "11": "/MotA2", "12": "/MotA1", "13": "/MotB1", "14": "/MotB2",
            "15": "+3V3", "16": "GND",
        }, rot=270),
        P("R2", "R_0805_10k", "10k", "TMC", {"1": "+3V3", "2": "/EN_TMC"}),
        P("U7", "TM1637_SOP20", "TM1637", "HMI", {
            "1": "/TM_G1", "2": "/TM_G2", "3": "/TM_G3",
            "7": "/TM_SA", "8": "/TM_SB", "9": "/TM_SC", "10": "/TM_SD",
            "11": "/TM_SE", "12": "/TM_SF", "13": "/TM_SG",
            "15": "+5V", "16": "GND", "17": "/TM_DIO", "18": "/TM_CLK",
        }),
        P("J_DISP", "PinHeader_1x10_7SEG", "7SEG_EXT", "HMI", {
            "1": "/TM_G1", "2": "/TM_G2", "3": "/TM_G3",
            "4": "/TM_SA", "5": "/TM_SB", "6": "/TM_SC", "7": "/TM_SD",
            "8": "/TM_SE", "9": "/TM_SF", "10": "/TM_SG",
        }),
        P("J_KEY", "PinHeader_1x08_Keypad", "KEYPAD_EXT", "HMI", {
            "1": "/KEY_R0", "2": "/KEY_R1", "3": "/KEY_R2", "4": "/KEY_R3",
            "5": "/KEY_C0", "6": "/KEY_C1", "7": "/KEY_C2", "8": "/KEY_C3",
        }),
        P("BZ1", "Buzzer_SMD_5V", "BUZZ", "HMI", {"1": "+5V", "2": "/BUZZER"}),
        P("J14", "JST_XH_04_Socket", "BUP_U", "OPTO", {
            "1": "+24V_SNS", "2": "GND", "3": "/OPTO_IN_BUP",
        }),
        P("J15", "JST_XH_03_Socket", "FIBER", "OPTO", {
            "1": "+24V_SNS", "2": "GND", "3": "/OPTO_IN_BUP",
        }),
        P("U44", "PC817_SOP4", "PC817", "OPTO", {
            "1": "/OPTO_IN_BUP", "2": "GND", "3": "GND", "4": "/BUP",
        }),
        P("R44", "R_0805_2k2", "2k2", "OPTO", {"1": "+24V_SNS", "2": "/OPTO_IN_BUP"}),
        P("R48", "R_0805_10k", "10k", "OPTO", {"1": "+3V3", "2": "/BUP"}),
        P("R1", "R_0805_4k7", "4k7", "OPTO", {"1": "+24V_SNS", "2": "/OPTO_IN_BUP"}),
        P("C26", "C_0805_100n", "100n", "OPTO", {"1": "+24V_SNS", "2": "GND"}),
    ]
    return parts




def antenna_keepout(u1: Part) -> tuple[float, float, float, float]:
    """World AABB in front of WROOM antenna (rot=180 -> tip north/top), to board margin."""
    tip_x = u1.x
    tip_y = u1.y - ANT_TIP
    return (
        tip_x - ANT_HALF_W,
        OY + MARGIN - 0.5,
        tip_x + ANT_HALF_W,
        tip_y,
    )


def rects_overlap(
    ax0: float, ay0: float, ax1: float, ay1: float,
    bx0: float, by0: float, bx1: float, by1: float,
) -> bool:
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def part_aabb(p: Part) -> tuple[float, float, float, float]:
    return (p.x - p.w / 2, p.y - p.h / 2, p.x + p.w / 2, p.y + p.h / 2)


def pack_parts(parts: list[Part], seed: int = 42) -> dict:
    """Full EDA-style placer: min-cut + quadratic + force + GA + SA."""
    cfg = PlaceCfg(
        board_w=BOARD_W,
        board_h=BOARD_H,
        ox=OX,
        oy=OY,
        margin=MARGIN,
        gap=GAP,
        ant_tip=ANT_TIP,
        ant_clear=ANT_CLEAR,
        ant_half_w=ANT_HALF_W,
        courtyard_size=courtyard_size,
    )
    return _pack_parts_full(parts, cfg, seed=seed)


# ---------------------------------------------------------------------------
# PCB emit
# ---------------------------------------------------------------------------

NETS = {
    0: "",
    1: "+24V",
    2: "GND",
    3: "+5V",
    4: "+3V3",
    5: "/STEP",
    6: "/DIR",
    7: "/EN_TMC",
    8: "/MotA2",
    9: "/MotA1",
    10: "/MotB1",
    11: "/MotB2",
    12: "/BUP",
    13: "/OPTO_IN_BUP",
    14: "/BUZZER",
    15: "/TM_CLK",
    16: "/TM_DIO",
    17: "/KEY_R0",
    18: "/KEY_R1",
    19: "/KEY_R2",
    20: "/KEY_R3",
    21: "/KEY_C0",
    22: "/KEY_C1",
    23: "/KEY_C2",
    24: "/KEY_C3",
    25: "+24V_RAW",
    26: "+24V_PRE",
    27: "+24V_SNS",
    28: "/USB_DP",
    29: "/USB_DM",
    30: "/UART_TX",
    31: "/UART_RX",
    32: "/BUCK_SW",
    33: "/BUCK_FB",
    34: "/BUCK_BS",
    35: "/BUCK_COMP",
    36: "/TM_G1",
    37: "/TM_G2",
    38: "/TM_G3",
    39: "/TM_SA",
    40: "/TM_SB",
    41: "/TM_SC",
    42: "/TM_SD",
    43: "/TM_SE",
    44: "/TM_SF",
    45: "/TM_SG",
}


def emit_pcb(parts: list[Part]) -> None:
    net_ids = {name: i for i, name in NETS.items() if name}
    lines: list[str] = []
    a = lines.append

    a("(kicad_pcb")
    a("\t(version 20240108)")
    a('\t(generator "gen_compact_carrier.py")')
    a('\t(generator_version "2.0")')
    a("\t(general")
    a("\t\t(thickness 1.6)")
    a("\t)")
    a('\t(paper "A4")')
    a("\t(layers")
    a('\t\t(0 "F.Cu" signal)')
    a('\t\t(31 "B.Cu" signal)')
    a('\t\t(32 "B.Adhes" user "B.Adhesive")')
    a('\t\t(33 "F.Adhes" user "F.Adhesive")')
    a('\t\t(34 "B.Paste" user)')
    a('\t\t(35 "F.Paste" user)')
    a('\t\t(36 "B.SilkS" user "B.Silkscreen")')
    a('\t\t(37 "F.SilkS" user "F.Silkscreen")')
    a('\t\t(38 "B.Mask" user)')
    a('\t\t(39 "F.Mask" user)')
    a('\t\t(40 "Dwgs.User" user "User.Drawings")')
    a('\t\t(41 "Cmts.User" user "User.Comments")')
    a('\t\t(42 "Eco1.User" user "User.Eco1")')
    a('\t\t(43 "Eco2.User" user "User.Eco2")')
    a('\t\t(44 "Edge.Cuts" user)')
    a('\t\t(45 "Margin" user)')
    a('\t\t(46 "B.CrtYd" user "B.Courtyard")')
    a('\t\t(47 "F.CrtYd" user "F.Courtyard")')
    a('\t\t(48 "B.Fab" user "B.Fabrication")')
    a('\t\t(49 "F.Fab" user "F.Fabrication")')
    a("\t)")
    a("\t(setup")
    a("\t\t(pad_to_mask_clearance 0)")
    a('\t\t(pcbplotparams')
    a("\t\t\t(layerselection 0x00010fc_ffffffff)")
    a("\t\t\t(plot_on_all_layers_selection 0x0000000_00000000)")
    a("\t\t\t(disableapertmacros no)")
    a("\t\t\t(usegerberextensions no)")
    a("\t\t\t(usegerberattributes yes)")
    a("\t\t)")
    a("\t)")

    for nid, name in sorted(NETS.items()):
        a(f'\t(net {nid} "{name}")')

    # Edge.Cuts
    a("\t(gr_rect")
    a(f"\t\t(start {OX} {OY})")
    a(f"\t\t(end {OX + BOARD_W} {OY + BOARD_H})")
    a("\t\t(stroke (width 0.1) (type default))")
    a("\t\t(fill none)")
    a('\t\t(layer "Edge.Cuts")')
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")

    a('\t(gr_text "COMPACT 100x100 — placement only (no copper routes)"')
    a(f"\t\t(at {OX + 4} {OY + 3.2} 0)")
    a('\t\t(layer "Cmts.User")')
    a("\t\t(effects (font (size 1.0 1.0) (thickness 0.15)) (justify left))")
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")

    for p in parts:
        mod_path = PRETTY / f"{p.fp}.kicad_mod"
        if not mod_path.exists():
            raise FileNotFoundError(mod_path)
        raw = mod_path.read_text(encoding="utf-8")
        # Apply nets to pad blocks in the library text, then embed
        body = raw.strip()
        # remove wrapping (footprint "name" ... )
        if body.startswith("(footprint"):
            # keep from after first line
            rest = body[body.find("\n") + 1 :]
            if rest.rstrip().endswith(")"):
                rest = rest.rstrip()[:-1].rstrip()
        else:
            rest = body

        # strip version/generator/layer/descr/tags/attr we will rewrite header
        # Instead: take full file and replace header + inject nets

        # Simpler approach: parse pads from lib, rebuild footprint cleanly
        a(f'\t(footprint "ESP32_Carrier:{p.fp}"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {p.x:.4f} {p.y:.4f} {p.rot})")

        a('\t\t(property "Reference" "' + p.ref + '"')
        a(f"\t\t\t(at 0 {-p.h / 2 - 1.2:.2f} {p.rot})")
        a('\t\t\t(layer "F.SilkS")')
        if p.board_only:
            a("\t\t\t(hide yes)")
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")

        a('\t\t(property "Value" "' + p.value + '"')
        a(f"\t\t\t(at 0 {p.h / 2 + 1.2:.2f} {p.rot})")
        a('\t\t\t(layer "F.Fab")')
        if p.board_only:
            a("\t\t\t(hide yes)")
        a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")

        if p.board_only:
            a("\t\t(attr through_hole board_only exclude_from_pos_files exclude_from_bom)")
        elif "smd" in raw and "thru_hole" not in raw.split("(attr")[1][:40] if "(attr" in raw else "":
            a("\t\t(attr smd)")
        else:
            # detect from file
            am = re.search(r"\(attr ([^)\n]+)", raw)
            if am:
                a(f"\t\t(attr {am.group(1).strip()})")
            else:
                a("\t\t(attr through_hole)")

        # copy graphics + pads from lib (local coords), add nets
        # graphics: fp_rect, fp_line, fp_circle, fp_text, fp_arc
        for gm in re.finditer(
            r"\t(\((?:fp_rect|fp_line|fp_circle|fp_arc|fp_text|fp_poly)[\s\S]*?\n\t\))",
            raw,
        ):
            g = gm.group(1)
            # ensure uuid
            if "(uuid" not in g:
                g = g[:-1] + f'\n\t\t(uuid "{uid()}")\n\t)'
            # indent as footprint child
            g = "\t\t" + g[1:] if g.startswith("(") else g
            # fix: g is like (fp_rect ... ) — prepend tab
            lines_g = g.splitlines()
            a("\t\t" + lines_g[0].lstrip())
            for lg in lines_g[1:]:
                a("\t\t" + lg.lstrip() if lg.strip().startswith("(") or lg.strip().startswith(")") else "\t\t" + lg)

        # Actually graphics copy is fragile. Copy pad-by-pad + courtyard only.
        # Reset: don't use above loop — clear and do pads + one courtyard.

    # The graphics loop above is messy mid-footprint. Rewrite emit more carefully.
    raise RuntimeError("internal: use emit_pcb_v2")


def emit_pcb_v2(parts: list[Part]) -> None:
    net_ids = {name: i for i, name in NETS.items() if name}
    lines: list[str] = []
    a = lines.append

    a("(kicad_pcb")
    a("\t(version 20240108)")
    a('\t(generator "gen_compact_carrier.py")')
    a('\t(generator_version "2.0")')
    a("\t(general")
    a("\t\t(thickness 1.6)")
    a("\t)")
    a('\t(paper "A4")')
    a("\t(layers")
    a('\t\t(0 "F.Cu" signal)')
    a('\t\t(31 "B.Cu" signal)')
    a('\t\t(32 "B.Adhes" user)')
    a('\t\t(33 "F.Adhes" user)')
    a('\t\t(34 "B.Paste" user)')
    a('\t\t(35 "F.Paste" user)')
    a('\t\t(36 "B.SilkS" user)')
    a('\t\t(37 "F.SilkS" user)')
    a('\t\t(38 "B.Mask" user)')
    a('\t\t(39 "F.Mask" user)')
    a('\t\t(40 "Dwgs.User" user)')
    a('\t\t(41 "Cmts.User" user)')
    a('\t\t(42 "Eco1.User" user)')
    a('\t\t(43 "Eco2.User" user)')
    a('\t\t(44 "Edge.Cuts" user)')
    a('\t\t(45 "Margin" user)')
    a('\t\t(46 "B.CrtYd" user)')
    a('\t\t(47 "F.CrtYd" user)')
    a('\t\t(48 "B.Fab" user)')
    a('\t\t(49 "F.Fab" user)')
    a("\t)")
    a("\t(setup")
    a("\t\t(pad_to_mask_clearance 0)")
    a("\t)")
    for nid, name in sorted(NETS.items()):
        a(f'\t(net {nid} "{name}")')

    a("\t(gr_rect")
    a(f"\t\t(start {OX} {OY})")
    a(f"\t\t(end {OX + BOARD_W} {OY + BOARD_H})")
    a("\t\t(stroke (width 0.1) (type default))")
    a("\t\t(fill none)")
    a('\t\t(layer "Edge.Cuts")')
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")
    a(f'\t(gr_text "{BOARD_W:.0f}x{BOARD_H:.0f} placement-only — ANT keepout north of U1; J1 west"')
    a(f"\t\t(at {OX + 4} {OY + 3.5} 0)")
    a('\t\t(layer "Cmts.User")')
    a("\t\t(effects (font (size 0.9 0.9) (thickness 0.12)) (justify left))")
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")
    _u1 = next(p for p in parts if p.ref == "U1")
    _kx0, _ky0, _kx1, _ky1 = antenna_keepout(_u1)
    a("\t(gr_rect")
    a(f"\t\t(start {_kx0:.3f} {_ky0:.3f})")
    a(f"\t\t(end {_kx1:.3f} {_ky1:.3f})")
    a("\t\t(stroke (width 0.2) (type dash))")
    a("\t\t(fill none)")
    a('\t\t(layer "Eco1.User")')
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")
    a('\t(gr_text "ANT KEEPOUT"')
    a(f"\t\t(at {(_kx0+_kx1)/2:.3f} {(_ky0+_ky1)/2:.3f} 0)")
    a('\t\t(layer "Eco1.User")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.1)))")
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")
    a('\t(gr_text "J_DISP=7SEG ext | J_KEY=keypad ext | J14/J15 fit ONE"')
    a(f"\t\t(at {OX + 4} {OY + BOARD_H - 3.5} 0)")
    a('\t\t(layer "Cmts.User")')
    a("\t\t(effects (font (size 0.75 0.75) (thickness 0.1)) (justify left))")
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")

    for p in parts:
        raw = (PRETTY / f"{p.fp}.kicad_mod").read_text(encoding="utf-8")
        a(f'\t(footprint "ESP32_Carrier:{p.fp}"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {p.x:.4f} {p.y:.4f} {int(p.rot)})")
        a('\t\t(property "Reference" "' + p.ref + '"')
        a("\t\t\t(at 0 -1.5 0)")
        a('\t\t\t(layer "F.SilkS")')
        if p.board_only:
            a("\t\t\t(hide yes)")
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(property "Value" "' + p.value + '"')
        a("\t\t\t(at 0 1.5 0)")
        a('\t\t\t(layer "F.Fab")')
        if p.board_only:
            a("\t\t\t(hide yes)")
        a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        am = re.search(r"\(attr ([^\n)]+)", raw)
        attr = am.group(1).strip() if am else "through_hole"
        if p.board_only:
            a("\t\t(attr through_hole board_only exclude_from_pos_files exclude_from_bom)")
        else:
            a(f"\t\t(attr {attr})")

        # courtyard box from sizes
        hw, hh = p.w / 2, p.h / 2
        # if rotated 90/270, courtyard_size already swapped w/h for packing,
        # but local courtyard in footprint is unrotated — use unrotated from file
        uw, uh = courtyard_size(p.fp)
        a("\t\t(fp_rect")
        a(f"\t\t\t(start {-uw / 2:.3f} {-uh / 2:.3f})")
        a(f"\t\t\t(end {uw / 2:.3f} {uh / 2:.3f})")
        a("\t\t\t(stroke (width 0.05) (type solid))")
        a("\t\t\t(fill none)")
        a('\t\t\t(layer "F.CrtYd")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(fp_rect")
        a(f"\t\t\t(start {-uw / 2:.3f} {-uh / 2:.3f})")
        a(f"\t\t\t(end {uw / 2:.3f} {uh / 2:.3f})")
        a("\t\t\t(stroke (width 0.12) (type solid))")
        a("\t\t\t(fill none)")
        a('\t\t\t(layer "F.SilkS")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")

        for m in re.finditer(
            r'\(pad\s+"([^"]+)"\s+(\w+)\s+(\w+)(?:\s*\n\s*|\s+)\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)',
            raw,
        ):
            pnum, ptype, shape, lx, ly = m.group(1), m.group(2), m.group(3), float(m.group(4)), float(m.group(5))
            chunk = raw[m.start() : m.start() + 600]
            sm = re.search(r"\(size\s+([-\d.]+)\s+([-\d.]+)\)", chunk)
            dm = re.search(r"\(drill\s+([-\d.]+)\)", chunk)
            rrm = re.search(r"\(roundrect_rratio\s+([-\d.]+)\)", chunk)
            sx = float(sm.group(1)) if sm else 1.5
            sy = float(sm.group(2)) if sm else sx
            drill = float(dm.group(1)) if dm else None
            a(f'\t\t(pad "{pnum}" {ptype} {shape}')
            a(f"\t\t\t(at {lx} {ly})")
            a(f"\t\t\t(size {sx} {sy})")
            if drill is not None and ptype in ("thru_hole", "np_thru_hole"):
                a(f"\t\t\t(drill {drill})")
            if rrm and shape == "roundrect":
                a(f"\t\t\t(roundrect_rratio {rrm.group(1)})")
            if ptype == "smd":
                a('\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")')
            elif ptype == "np_thru_hole":
                a('\t\t\t(layers "F&B.Cu" "*.Mask")')
            else:
                a('\t\t\t(layers "*.Cu" "*.Mask")')
            net = p.pad_nets.get(pnum, "")
            if net:
                a(f'\t\t\t(net {net_ids[net]} "{net}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")

        a("\t)")

    # NO segments, NO vias
    a(")")
    text = "\n".join(lines) + "\n"
    # validate parens
    if text.count("(") != text.count(")"):
        raise RuntimeError(f"paren mismatch {text.count('(')} vs {text.count(')')}")
    PCB.write_text(text, encoding="utf-8")
    print(f"Wrote {PCB} ({BOARD_W}x{BOARD_H} mm, {len(parts)} footprints, 0 tracks)")


def main() -> None:
    global BOARD_W, BOARD_H
    best: tuple[float, list[Part], dict] | None = None
    # Prefer shrink; few seeds
    for size in (85.0, 88.0, 90.0, 92.0, 95.0, 100.0, 110.0, 120.0, 150.0):
        BOARD_W = BOARD_H = size
        found = None
        for seed in (42, 7):
            parts = build_parts()
            metrics = pack_parts(parts, seed=seed)
            clean = (
                metrics["overlaps"] == 0
                and metrics["ant_hits"] == 0
                and metrics.get("warns", 0) == 0
            )
            print(
                f"  try {size:.0f} seed={seed}: overlaps={metrics['overlaps']} "
                f"ant={metrics['ant_hits']} warns={metrics.get('warns', 0)}"
            )
            if clean:
                found = (size, parts, metrics)
                break
        if found:
            best = found
            break
    if best is None:
        BOARD_W = BOARD_H = 150.0
        parts = build_parts()
        metrics = pack_parts(parts, seed=42)
        print(
            f"FALLBACK {BOARD_W:.0f}x{BOARD_H:.0f} "
            f"overlaps={metrics['overlaps']} ant={metrics['ant_hits']} warns={metrics.get('warns')}"
        )
    else:
        BOARD_W = BOARD_H = best[0]
        parts, metrics = best[1], best[2]
        print(f"Selected board {BOARD_W:.0f}x{BOARD_H:.0f} mm")
    emit_pcb_v2(parts)
    mov = [p for p in parts if not p.board_only]
    u1 = next(p for p in mov if p.ref == "U1")
    kx0, ky0, kx1, ky1 = antenna_keepout(u1)
    ov = 0
    for i, a in enumerate(mov):
        for b in mov[i + 1 :]:
            if abs(a.x - b.x) < (a.w + b.w) / 2 + GAP and abs(a.y - b.y) < (a.h + b.h) / 2 + GAP:
                ov += 1
                print(f"  overlap {a.ref}/{b.ref}")
    ant = 0
    for pt in mov:
        if pt.ref == "U1":
            continue
        px0, py0, px1, py1 = part_aabb(pt)
        # same expanded keepout as placer (gap clearance)
        if rects_overlap(
            px0, py0, px1, py1,
            kx0 - GAP, ky0 - GAP, kx1 + GAP, ky1 + GAP,
        ):
            ant += 1
            print(f"  ANT keepout hit {pt.ref}")
    print(f"Done. size={BOARD_W:.0f}x{BOARD_H:.0f} overlaps={ov} ant_hits={ant} gap={GAP}")


if __name__ == "__main__":
    main()
