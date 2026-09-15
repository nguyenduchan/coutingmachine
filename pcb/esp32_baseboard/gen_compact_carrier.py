#!/usr/bin/env python3
"""Compact carrier — placement + nets only (NO tracks/vias).

  python gen_compact_carrier.py
  python gen_schematic_from_pcb.py
  python verify_compact.py

KiCad-valid S-expr; footprints copied from libraries/ESP32_Carrier.pretty.
Placement pipeline (no routing) — full EDA guide:
  1) graph partition / min-cut (FM refine)
  2) analytical quadratic wirelength (Jacobi)
  3) force-directed springs
  4) genetic / evolutionary (XY + 90 rotation)
  5) simulated annealing (XY + rotation, Metropolis)
  6) legalization + shrink Edge.Cuts

MCU: STM32G030C8T6 LQFP48 (replaces ESP32-WROOM-32).
"""

from __future__ import annotations

import math
import random
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from stm32_pinmap import (
    BUP_PIN,
    IN2_PIN,
    IN3_PIN,
    KEYPAD_PINS,
    LQFP48_PINS,
    PWR_PINS,
    SWD_PINS,
    TM1637_PINS,
    TMC2_PINS,
    TMC_PINS,
    USART1_PINS,
    VIB_PINS,
)

from placement_full import PlaceCfg, pack_parts as _pack_parts_full

ROOT = Path(__file__).resolve().parent
PRETTY = ROOT / "libraries" / "ESP32_Carrier.pretty"
PCB = ROOT / "esp32_baseboard.kicad_pcb"

# DIN vertical: clips on left/right; prefer wide board (long N/S edges for jacks)
BOARD_W = 130.0
BOARD_H = 100.0
TARGET_BOARD_MM = 100.0
# Prefer smallest that packs clean after tight north jack strip
BOARD_CANDIDATES = (
    (110.0, 100.0),
    (115.0, 100.0),
    (118.0, 100.0),
    (120.0, 100.0),
    (125.0, 100.0),
    (130.0, 100.0),
    (140.0, 110.0),
    (160.0, 120.0),
)
OX, OY = 50.0, 50.0  # Edge.Cuts origin
MARGIN = 4.0  # non-jack parts: ≥4 mm from Edge.Cuts
JACK_MARGIN = 1.0  # field edge jacks may sit near N/S edges
GAP = 2.0  # min clear space between courtyards (mm)

# No RF antenna (STM32). Keepout disabled (zeros) — PlaceCfg still accepts fields.
ANT_TIP = 0.0
ANT_CLEAR = 0.0
ANT_HALF_W = 0.0


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

    # STM32G030C8T6 — LQFP48 7×7 mm, 0.5 mm pitch (KiCad Y↓; pin1 top-left, CCW)
    pads = []
    pitch, reach = 0.5, 4.0
    half = 11 * pitch / 2  # 2.75
    for n in range(1, 13):  # left 1..12
        y = -half + (n - 1) * pitch
        shape = "rect" if n == 1 else "roundrect"
        rr = ' (roundrect_rratio 0.25)' if shape == "roundrect" else ""
        pads.append(
            f'\t(pad "{n}" smd {shape} (at {-reach} {y:.3f}) (size 1.2 0.3)'
            f'\n\t\t(layers "F.Cu" "F.Paste" "F.Mask"){rr})'
        )
    for n in range(13, 25):  # bottom 13..24
        x = -half + (n - 13) * pitch
        pads.append(
            f'\t(pad "{n}" smd roundrect (at {x:.3f} {reach}) (size 0.3 1.2)'
            f'\n\t\t(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))'
        )
    for n in range(25, 37):  # right 25..36 (bottom→top ⇒ y decreasing)
        y = half - (n - 25) * pitch
        pads.append(
            f'\t(pad "{n}" smd roundrect (at {reach} {y:.3f}) (size 1.2 0.3)'
            f'\n\t\t(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))'
        )
    for n in range(37, 49):  # top 37..48 (right→left ⇒ x decreasing)
        x = half - (n - 37) * pitch
        pads.append(
            f'\t(pad "{n}" smd roundrect (at {x:.3f} {-reach}) (size 0.3 1.2)'
            f'\n\t\t(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))'
        )
    write(
        "STM32G030C8T6_LQFP48",
        f"""
(footprint "STM32G030C8T6_LQFP48"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "STM32G030C8T6 LQFP-48 7x7mm P0.5mm")
\t(tags "STM32 G030 LQFP48")
\t(attr smd)
\t(fp_rect (start -4.5 -4.5) (end 4.5 4.5)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(fp_rect (start -3.5 -3.5) (end 3.5 3.5)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(fp_circle (center -3.2 -3.2) (end -2.9 -3.2)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(fp_text user "1" (at -5.2 -2.75 0) (layer "F.SilkS")
\t\t(effects (font (size 0.6 0.6) (thickness 0.1))))
{chr(10).join(pads)}
)
""",
        force=True,
    )
    write(
        "Cortex_Debug_10",
        """
(footprint "Cortex_Debug_10"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "ARM Cortex Debug / CoreSight-10 1.27mm 2x5; pin7 KEY (NPTH)")
\t(tags "SWD Cortex Debug FTSH-105")
\t(attr through_hole)
\t(fp_rect (start -1.8 -3.2) (end 1.8 3.2)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(fp_rect (start -1.5 -2.9) (end 1.5 2.9)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(fp_text user "DBG" (at 0 -3.6 0) (layer "F.SilkS")
\t\t(effects (font (size 0.7 0.7) (thickness 0.1))))
\t(fp_text user "1" (at -2.2 -2.54 0) (layer "F.SilkS")
\t\t(effects (font (size 0.55 0.55) (thickness 0.08))))
\t(pad "1" thru_hole rect (at -0.635 -2.54) (size 0.9 0.9) (drill 0.5) (layers "*.Cu" "*.Mask"))
\t(pad "2" thru_hole circle (at 0.635 -2.54) (size 0.9 0.9) (drill 0.5) (layers "*.Cu" "*.Mask"))
\t(pad "3" thru_hole circle (at -0.635 -1.27) (size 0.9 0.9) (drill 0.5) (layers "*.Cu" "*.Mask"))
\t(pad "4" thru_hole circle (at 0.635 -1.27) (size 0.9 0.9) (drill 0.5) (layers "*.Cu" "*.Mask"))
\t(pad "5" thru_hole circle (at -0.635 0) (size 0.9 0.9) (drill 0.5) (layers "*.Cu" "*.Mask"))
\t(pad "6" thru_hole circle (at 0.635 0) (size 0.9 0.9) (drill 0.5) (layers "*.Cu" "*.Mask"))
\t(pad "7" np_thru_hole circle (at -0.635 1.27) (size 0.9 0.9) (drill 0.7) (layers "*.Cu" "*.Mask"))
\t(pad "8" thru_hole circle (at 0.635 1.27) (size 0.9 0.9) (drill 0.5) (layers "*.Cu" "*.Mask"))
\t(pad "9" thru_hole circle (at -0.635 2.54) (size 0.9 0.9) (drill 0.5) (layers "*.Cu" "*.Mask"))
\t(pad "10" thru_hole circle (at 0.635 2.54) (size 0.9 0.9) (drill 0.5) (layers "*.Cu" "*.Mask"))
)
""",
        force=True,
    )

    # Dual-channel 24V power module socket (MOSFET / H-bridge / DC vibrator)
    pm_pads = []
    for n in range(1, 13):
        row, col = (n - 1) // 2, (n - 1) % 2
        x = -1.27 if col == 0 else 1.27
        y = -6.35 + row * 2.54
        shape = "rect" if n == 1 else "circle"
        pm_pads.append(
            f'\t(pad "{n}" thru_hole {shape} (at {x} {y:.2f}) (size 1.7 1.7)'
            f'\n\t\t(drill 1.0) (layers "*.Cu" "*.Mask"))'
        )
    write(
        "PowerMod_2CH_Sock",
        f"""
(footprint "PowerMod_2CH_Sock"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "2x6 2.54mm — MOSFET/H-bridge/DC-vib module socket (no driver on carrier)")
\t(attr through_hole)
\t(fp_rect (start -2.5 -7.3) (end 2.5 7.3)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(fp_rect (start -2.2 -7.0) (end 2.2 7.0)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(fp_text user "U_PWR" (at 0 -8.6 0) (layer "F.SilkS")
\t\t(effects (font (size 0.7 0.7) (thickness 0.1))))
\t(fp_text user "1" (at -2.4 -6.35 0) (layer "F.SilkS")
\t\t(effects (font (size 0.55 0.55) (thickness 0.08))))
{chr(10).join(pm_pads)}
)
""",
        force=True,
    )
    write(
        "VibAC_Sock",
        """
(footprint "VibAC_Sock"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "1x4 — SSR/AC vibratory module control socket")
\t(attr through_hole)
\t(fp_rect (start -1.2 -1.1) (end 1.2 8.7)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(fp_text user "U_VIB" (at 0 -1.8 0) (layer "F.SilkS")
\t\t(effects (font (size 0.65 0.65) (thickness 0.1))))
\t(pad "1" thru_hole rect (at 0 0) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
\t(pad "2" thru_hole circle (at 0 2.54) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
\t(pad "3" thru_hole circle (at 0 5.08) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
\t(pad "4" thru_hole circle (at 0 7.62) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
)
""",
        force=True,
    )
    write(
        "Mot_XH_04_Socket",
        """
(footprint "Mot_XH_04_Socket"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "JST-XH 4P keyed — NEMA17 phases A2 A1 B1 B2 on board edge")
	(tags "JST XH motor keyed")
	(attr through_hole)
	(fp_rect (start -2.9 -1.0) (end 2.9 8.5)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(fp_rect (start -2.7 -0.8) (end 2.7 8.3)
		(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
	(fp_text user "MOT" (at 0 -1.6 0) (layer "F.SilkS")
		(effects (font (size 0.7 0.7) (thickness 0.1))))
	(fp_text user "A2" (at 3.3 0.0 0) (layer "F.SilkS")
		(effects (font (size 0.55 0.55) (thickness 0.08)) (justify left)))
	(pad "1" thru_hole rect (at 0 0.0) (size 1.6 1.6) (drill 0.9) (layers "*.Cu" "*.Mask"))
	(fp_text user "A1" (at 3.3 2.5 0) (layer "F.SilkS")
		(effects (font (size 0.55 0.55) (thickness 0.08)) (justify left)))
	(pad "2" thru_hole circle (at 0 2.5) (size 1.6 1.6) (drill 0.9) (layers "*.Cu" "*.Mask"))
	(fp_text user "B1" (at 3.3 5.0 0) (layer "F.SilkS")
		(effects (font (size 0.55 0.55) (thickness 0.08)) (justify left)))
	(pad "3" thru_hole circle (at 0 5.0) (size 1.6 1.6) (drill 0.9) (layers "*.Cu" "*.Mask"))
	(fp_text user "B2" (at 3.3 7.5 0) (layer "F.SilkS")
		(effects (font (size 0.55 0.55) (thickness 0.08)) (justify left)))
	(pad "4" thru_hole circle (at 0 7.5) (size 1.6 1.6) (drill 0.9) (layers "*.Cu" "*.Mask"))
)
""",
        force=True,
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

    # USB Micro-B SMT right-angle: MOUTH at local +Y (overhangs south edge with rot=0);
    # signal pads at local −Y (toward board interior). Cable plugs from outside.
    write(
        "USB_MicroB",
        """
(footprint "USB_MicroB"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "USB Micro-B SMT R/A — mouth +Y (edge), pads -Y (inboard)")
\t(attr smd)
\t(fp_rect (start -3.5 -3.3) (end 3.5 3.6)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(fp_rect (start -3.2 -2.4) (end 3.2 2.6)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(fp_line (start -2.2 3.5) (end 2.2 3.5)
\t\t(stroke (width 0.15) (type solid)) (layer "F.SilkS"))
\t(fp_line (start -2.2 3.5) (end -2.2 2.8)
\t\t(stroke (width 0.15) (type solid)) (layer "F.SilkS"))
\t(fp_line (start 2.2 3.5) (end 2.2 2.8)
\t\t(stroke (width 0.15) (type solid)) (layer "F.SilkS"))
\t(fp_text user "OUT" (at 0 4.4 0) (layer "F.SilkS")
\t\t(effects (font (size 0.6 0.6) (thickness 0.1))))
\t(pad "1" smd rect (at -1.30 -2.50) (size 0.40 1.45) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at -0.65 -2.50) (size 0.40 1.45) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "3" smd rect (at 0.00 -2.50) (size 0.40 1.45) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "4" smd rect (at 0.65 -2.50) (size 0.40 1.45) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "5" smd rect (at 1.30 -2.50) (size 0.40 1.45) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "MH1" smd rect (at -2.90 0.20) (size 1.50 2.20) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "MH2" smd rect (at 2.90 0.20) (size 1.50 2.20) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
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
\t(fp_rect (start -1.2 -1.1) (end 1.2 18.9)
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
        force=True,
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
	(fp_rect (start -1.2 -1.1) (end 1.2 24.0)
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
    # S8050 / SS8050 NPN SOT-23: 1=B 2=E 3=C
    write(
        "S8050_SOT23",
        """
(footprint "S8050_SOT23"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "NPN S8050 SOT-23")
\t(attr smd)
\t(fp_rect (start -1.7 -1.65) (end 1.7 1.8)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(fp_line (start -0.7 -1.0) (end 0.7 -1.0)
\t\t(stroke (width 0.12) (type solid)) (layer "F.SilkS"))
\t(pad "1" smd rect (at -1.05 -1.0) (size 0.7 0.8) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at 1.05 -1.0) (size 0.7 0.8) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "3" smd rect (at 0.0 1.1) (size 0.7 0.8) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )
    # 12 MHz crystal 3225 (2-pad class / pads 1-3 used on 4-pad parts)
    write(
        "Crystal_SMD_3225",
        """
(footprint "Crystal_SMD_3225"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "Crystal 3.2x2.5mm 12MHz")
\t(attr smd)
\t(fp_rect (start -2.0 -1.7) (end 2.0 1.7)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(fp_rect (start -1.6 -1.25) (end 1.6 1.25)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(pad "1" smd rect (at -1.1 0.75) (size 1.0 0.9) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at 1.1 0.75) (size 1.0 0.9) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "3" smd rect (at 1.1 -0.75) (size 1.0 0.9) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "4" smd rect (at -1.1 -0.75) (size 1.0 0.9) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )
    # 6x6 mm tactile — hand-solder THT
    write(
        "SW_Push_6mm",
        """
(footprint "SW_Push_6mm"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "Tactile switch 6x6mm THT")
\t(attr through_hole)
\t(fp_rect (start -3.5 -3.5) (end 3.5 3.5)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(fp_rect (start -3.0 -3.0) (end 3.0 3.0)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(fp_circle (center 0 0) (end 1.2 0)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(pad "1" thru_hole circle (at -2.25 -1.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
\t(pad "2" thru_hole circle (at 2.25 -1.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
\t(pad "3" thru_hole circle (at 2.25 1.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
\t	(pad "4" thru_hole circle (at -2.25 1.5) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
)
""",
        force=True,
    )
    # SMD PTC 1812 (MF-MSMF / 1812L series, ≥30 V)
    write(
        "PTC_1812",
        """
(footprint "PTC_1812"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "Resettable PTC fuse 1812 SMD")
	(attr smd)
	(fp_rect (start -2.6 -1.5) (end 2.6 1.5)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(fp_rect (start -2.2 -1.1) (end 2.2 1.1)
		(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
	(pad "1" smd roundrect (at -1.85 0) (size 1.15 1.8)
		(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))
	(pad "2" smd roundrect (at 1.85 0) (size 1.15 1.8)
		(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))
)
""",
        force=True,
    )
    write(
        "R_1206_22R",
        """
(footprint "R_1206_22R"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "22 ohm 1206 SNS series limiter")
	(attr smd)
	(fp_rect (start -1.7 -0.9) (end 1.7 0.9)
		(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
	(fp_rect (start -1.9 -1.1) (end 1.9 1.1)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(pad "1" smd roundrect (at -1.4 0) (size 1.0 1.5)
		(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))
	(pad "2" smd roundrect (at 1.4 0) (size 1.0 1.5)
		(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))
)
""",
        force=True,
    )


def footprint_aabb(fp_name: str) -> tuple[float, float, float, float]:
    """Local-coord AABB (xmin, ymin, xmax, ymax) from F.CrtYd, else pads + 0.25 mm."""
    path = PRETTY / f"{fp_name}.kicad_mod"
    if not path.exists():
        return (-6.0, -6.0, 6.0, 6.0)
    text = path.read_text(encoding="utf-8")
    m = re.search(
        r'\(fp_rect\s*\(start\s+([-\d.]+)\s+([-\d.]+)\)\s*\(end\s+([-\d.]+)\s+([-\d.]+)\)[\s\S]*?layer "F\.CrtYd"',
        text,
    )
    if m:
        x0, y0, x1, y1 = map(float, m.groups())
        return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    xs: list[float] = []
    ys: list[float] = []
    for pm in re.finditer(
        r'\(pad\s+"[^"]+"\s+\w+\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)',
        text,
    ):
        px, py = float(pm.group(1)), float(pm.group(2))
        chunk = text[pm.start() : pm.start() + 280]
        sm = re.search(r"\(size\s+([-\d.]+)\s+([-\d.]+)\)", chunk)
        sx = float(sm.group(1)) / 2 if sm else 0.9
        sy = float(sm.group(2)) / 2 if sm else 0.9
        xs += [px - sx, px + sx]
        ys += [py - sy, py + sy]
    if not xs:
        return (-6.0, -6.0, 6.0, 6.0)
    mrg = 0.25
    return (min(xs) - mrg, min(ys) - mrg, max(xs) + mrg, max(ys) + mrg)


def courtyard_size(fp_name: str) -> tuple[float, float]:
    """Return (width, height) packing AABB from true courtyard/pad extents + margin."""
    x0, y0, x1, y1 = footprint_aabb(fp_name)
    w, h = x1 - x0, y1 - y0
    if w < 0.5 or h < 0.5:
        return (12.0, 12.0)
    # Small packing clearance beyond body (not 2× abs() inflate)
    pad = 0.25
    return (w + pad, h + pad)


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
        TMC_PINS["STEP"]: "/STEP",
        TMC_PINS["DIR"]: "/DIR",
        TMC_PINS["EN"]: "/EN_TMC",
        TMC2_PINS["STEP"]: "/STEP2",
        TMC2_PINS["DIR"]: "/DIR2",
        TMC2_PINS["EN"]: "/EN_TMC2",
        BUP_PIN: "/BUP",
        IN2_PIN: "/IN2",
        IN3_PIN: "/IN3",
        PWR_PINS["PWM1"]: "/PWM_OUT1",
        PWR_PINS["PWM2"]: "/PWM_OUT2",
        PWR_PINS["EN"]: "/PWR_EN",
        PWR_PINS["DIR"]: "/PWR_DIR",
        PWR_PINS["FAULT"]: "/PWR_FAULT",
        VIB_PINS["CTRL"]: "/VIB_CTRL",
        VIB_PINS["FAULT"]: "/VIB_FAULT",
        TM1637_PINS["CLK"]: "/TM_CLK",
        TM1637_PINS["DIO"]: "/TM_DIO",
        KEYPAD_PINS["ROW0"]: "/KEY_R0",
        KEYPAD_PINS["ROW1"]: "/KEY_R1",
        KEYPAD_PINS["ROW2"]: "/KEY_R2",
        KEYPAD_PINS["ROW3"]: "/KEY_R3",
        KEYPAD_PINS["COL0"]: "/KEY_C0",
        KEYPAD_PINS["COL1"]: "/KEY_C1",
        KEYPAD_PINS["COL2"]: "/KEY_C2",
        KEYPAD_PINS["COL3"]: "/KEY_C3",
        USART1_PINS["TX"]: "/UART_TX",
        USART1_PINS["RX"]: "/UART_RX",
        SWD_PINS["SWDIO"]: "/SWDIO",
        SWD_PINS["SWCLK"]: "/SWCLK",
        SWD_PINS["SWO"]: "/SWO",
        "NRST": "/NRST",
        "VBAT": "+3V3",
        "VREF+": "+3V3",
        "VDD": "+3V3",
        "VSS": "GND",
    }

    u1_nets: dict[str, str] = {}
    for num, name in LQFP48_PINS:
        if name in gpio_net:
            u1_nets[str(num)] = gpio_net[name]

    parts = [
        P("H1", "MountingHole_M3", "M3", "MOUNT", board_only=True),
        P("H2", "MountingHole_M3", "M3", "MOUNT", board_only=True),
        P("H3", "MountingHole_M3", "M3", "MOUNT", board_only=True),
        P("H4", "MountingHole_M3", "M3", "MOUNT", board_only=True),
        P("J_USB", "USB_MicroB", "USB_MicroB", "MCU", {
            "1": "+5V", "2": "/USB_DM", "3": "/USB_DP", "5": "GND", "MH1": "GND", "MH2": "GND",
        }),
        # CH340C UART bridge (no DTR/RTS auto-boot — STM32 uses SWD / BOOT0)
        P("U5", "CH340C", "CH340C", "MCU", {
            "1": "GND", "2": "/UART_RX", "3": "/UART_TX", "4": "+3V3",
            "5": "/USB_DP", "6": "/USB_DM",
            "7": "/CH340_XI", "8": "/CH340_XO",
            "16": "+5V",
        }),
        P("Y1", "Crystal_SMD_3225", "12MHz", "MCU", {
            "1": "/CH340_XI", "3": "/CH340_XO", "2": "GND", "4": "GND",
        }),
        P("C_XI", "C_0805", "22p", "MCU", {"1": "/CH340_XI", "2": "GND"}),
        P("C_XO", "C_0805", "22p", "MCU", {"1": "/CH340_XO", "2": "GND"}),
        P("C52", "C_0805_100n", "100n", "MCU", {"1": "+3V3", "2": "GND"}),
        P("C53", "C_0805_100n", "100n", "MCU", {"1": "+5V", "2": "GND"}),
        P("U1", "STM32G030C8T6_LQFP48", "STM32G030C8T6", "MCU", u1_nets),
        P("C_MCU", "C_0805_100n", "100n", "MCU", {"1": "+3V3", "2": "GND"}),
        P("C_MCU2", "C_0805", "1u", "MCU", {"1": "+3V3", "2": "GND"}),
        P("R_NRST", "R_0805_10k", "10k", "MCU", {"1": "+3V3", "2": "/NRST"}),
        P("C_NRST", "C_0805_100n", "100n", "MCU", {"1": "/NRST", "2": "GND"}),
        P("R_BOOT", "R_0805_10k", "10k", "MCU", {"1": "/SWCLK", "2": "GND"}),  # BOOT0 + SWCLK PD
        P("R_SWDIO", "R_0805_10k", "10k", "MCU", {"1": "+3V3", "2": "/SWDIO"}),  # SWDIO PU
        P("SW_BOOT", "SW_Push_6mm", "BOOT0", "MCU", {
            "1": "/SWCLK", "2": "/SWCLK", "3": "+3V3", "4": "+3V3",
        }),
        P("SW_NRST", "SW_Push_6mm", "NRST", "MCU", {
            "1": "/NRST", "2": "/NRST", "3": "GND", "4": "GND",
        }),
        # ARM CoreSight-10 / Cortex Debug (1.27mm): VTREF SWDIO GND SWCLK GND SWO KEY TDI GND nSRST
        P("J_DBG", "Cortex_Debug_10", "CortexDbg", "MCU", {
            "1": "+3V3",
            "2": "/SWDIO",
            "3": "GND",
            "4": "/SWCLK",
            "5": "GND",
            "6": "/SWO",
            "8": "GND",  # TDI unused in SWD — tie GND (safe)
            "9": "GND",
            "10": "/NRST",
        }),
        P("U6", "AMS1117_SOT223", "AMS1117-3.3", "MCU", {
            "1": "GND", "2": "+3V3", "3": "+5V", "TAB": "+3V3",
        }),
        P("J1", "TerminalBlock_2P_5.0mm", "24V_IN", "POWER", {"1": "+24V_RAW", "2": "GND"}),
        # Input protect: reverse (D3) → T2A fuse → TVS clamp (loads after F1 only)
        P("D3", "Diode_SMA", "SS54", "POWER", {"1": "+24V_RAW", "2": "+24V_PRE"}),
        P("F1", "Fuse_Holder_5x20_Open", "T2A", "POWER", {"1": "+24V_PRE", "2": "+24V"}, rot=90),
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
        # SNS branch: PTC then series R (short at J14/J15 trips PTC_SNS, not whole board)
        P("PTC_SNS", "PTC_1812", "0.2A", "POWER", {"1": "+24V", "2": "+24V_SNS_PRE"}),
        P("R10", "R_1206_22R", "22R", "POWER", {"1": "+24V_SNS_PRE", "2": "+24V_SNS"}),
        P("C10", "CP_SMD_D6.3x5.8", "47u/50V", "POWER", {"1": "+24V_SNS", "2": "GND"}),
        P("C11", "C_0805_100n", "100n", "POWER", {"1": "+24V_SNS", "2": "GND"}),
        P("C21", "CP_SMD_D6.3x5.8", "220u/50V", "POWER", {"1": "+24V", "2": "GND"}),
        # Motor VM: U3 on MOT1, U4 on MOT2 (separate PTC for future dual NEMA17)
        P("PTC_MOT", "PTC_1812", "1.1A", "TMC", {"1": "+24V", "2": "+24V_MOT"}),
        P("C20", "CP_SMD_D8x10", "470u/50V", "TMC", {"1": "+24V_MOT", "2": "GND"}),
        P("C24", "C_0805_100n", "100n", "TMC", {"1": "+24V_MOT", "2": "GND"}),
        P("PTC_MOT2", "PTC_1812", "1.1A", "TMC", {"1": "+24V", "2": "+24V_MOT2"}),
        P("C20B", "CP_SMD_D6.3x5.8", "220u/50V", "TMC", {"1": "+24V_MOT2", "2": "GND"}),
        P("C24B", "C_0805_100n", "100n", "TMC", {"1": "+24V_MOT2", "2": "GND"}),
        P("C5", "CP_SMD_D6.3x5.8", "100u/16V", "MCU", {"1": "+5V", "2": "GND"}),
        P("C51", "C_0805_100n", "100n", "MCU", {"1": "+5V", "2": "GND"}),
        P("D5", "Diode_SMB_TVS", "SMBJ5.0A", "MCU", {"1": "GND", "2": "+5V"}),
        P("C3", "CP_SMD_D6.3x5.8", "47u/10V", "MCU", {"1": "+3V3", "2": "GND"}),
        P("C31", "C_0805_100n", "100n", "MCU", {"1": "+3V3", "2": "GND"}),
        # U3 = motor 1 (feed/count); U4 = motor 2 (anti-jam / future) — sockets only
        P("U3", "TMC2209_StepStick", "TMC1", "TMC", {
            "1": "/EN_TMC", "7": "/STEP", "8": "/DIR",
            "9": "+24V_MOT", "10": "GND",
            "11": "/MotA2", "12": "/MotA1", "13": "/MotB1", "14": "/MotB2",
            "15": "+3V3", "16": "GND",
        }, rot=0),
        P("R2", "R_0805_10k", "10k", "TMC", {"1": "+3V3", "2": "/EN_TMC"}),
        # Board-edge motor jacks (field wiring) — same phase nets as U3/U4 Mot pads
        P("J_MOT1", "Mot_XH_04_Socket", "MOT1", "TMC", {
            "1": "/MotA2", "2": "/MotA1", "3": "/MotB1", "4": "/MotB2",
        }),
        P("U4", "TMC2209_StepStick", "TMC2", "TMC", {
            "1": "/EN_TMC2", "7": "/STEP2", "8": "/DIR2",
            "9": "+24V_MOT2", "10": "GND",
            "11": "/Mot2A2", "12": "/Mot2A1", "13": "/Mot2B1", "14": "/Mot2B2",
            "15": "+3V3", "16": "GND",
        }, rot=0),
        P("R2B", "R_0805_10k", "10k", "TMC", {"1": "+3V3", "2": "/EN_TMC2"}),
        P("J_MOT2", "Mot_XH_04_Socket", "MOT2", "TMC", {
            "1": "/Mot2A2", "2": "/Mot2A1", "3": "/Mot2B1", "4": "/Mot2B2",
        }),
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
        # Count sensors (install ONE of J14/J15)
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
        # Spare field inputs (jam / hopper / gate) — NPN OC 12–24V
        P("J_IN2", "JST_XH_03_Socket", "IN2", "OPTO", {
            "1": "+24V_SNS", "2": "GND", "3": "/OPTO_IN2",
        }),
        P("U45", "PC817_SOP4", "PC817", "OPTO", {
            "1": "/OPTO_IN2", "2": "GND", "3": "GND", "4": "/IN2",
        }),
        P("R45", "R_0805_2k2", "2k2", "OPTO", {"1": "+24V_SNS", "2": "/OPTO_IN2"}),
        P("R49", "R_0805_10k", "10k", "OPTO", {"1": "+3V3", "2": "/IN2"}),
        P("J_IN3", "JST_XH_03_Socket", "IN3", "OPTO", {
            "1": "+24V_SNS", "2": "GND", "3": "/OPTO_IN3",
        }),
        P("U46", "PC817_SOP4", "PC817", "OPTO", {
            "1": "/OPTO_IN3", "2": "GND", "3": "GND", "4": "/IN3",
        }),
        P("R46", "R_0805_2k2", "2k2", "OPTO", {"1": "+24V_SNS", "2": "/OPTO_IN3"}),
        P("R50", "R_0805_10k", "10k", "OPTO", {"1": "+3V3", "2": "/IN3"}),
        # Pluggable 24V power (MOSFET/H-bridge/DC vib) — socket only
        P("U_PWR", "PowerMod_2CH_Sock", "PWR_MOD", "PWR", {
            "1": "+24V", "2": "+24V",
            "3": "GND", "4": "GND",
            "5": "+3V3", "6": "/PWR_FAULT",
            "7": "/PWM_OUT1", "8": "/PWM_OUT2",
            "9": "/PWR_EN", "10": "/PWR_DIR",
            "11": "GND", "12": "GND",
        }),
        P("R_PWR_FLT", "R_0805_10k", "10k", "PWR", {"1": "+3V3", "2": "/PWR_FAULT"}),
        # Pluggable AC vibratory SSR control — socket only
        P("U_VIB", "VibAC_Sock", "VIB_SSR", "PWR", {
            "1": "+24V", "2": "GND", "3": "/VIB_CTRL", "4": "/VIB_FAULT",
        }),
        P("R_VIB_FLT", "R_0805_10k", "10k", "PWR", {"1": "+3V3", "2": "/VIB_FAULT"}),
    ]
    return parts




def antenna_keepout(u1: Part) -> tuple[float, float, float, float]:
    """Legacy stub — no RF keepout for STM32 (returns empty box at U1)."""
    return (u1.x, u1.y, u1.x, u1.y)


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
        jack_margin=JACK_MARGIN,
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
    14: "/TM_CLK",
    15: "/TM_DIO",
    16: "/KEY_R0",
    17: "/KEY_R1",
    18: "/KEY_R2",
    19: "/KEY_R3",
    20: "/KEY_C0",
    21: "/KEY_C1",
    22: "/KEY_C2",
    23: "/KEY_C3",
    24: "+24V_RAW",
    25: "+24V_PRE",
    26: "+24V_SNS",
    27: "/USB_DP",
    28: "/USB_DM",
    29: "/UART_TX",
    30: "/UART_RX",
    31: "/BUCK_SW",
    32: "/BUCK_FB",
    33: "/BUCK_BS",
    34: "/BUCK_COMP",
    35: "/TM_G1",
    36: "/TM_G2",
    37: "/TM_G3",
    38: "/TM_SA",
    39: "/TM_SB",
    40: "/TM_SC",
    41: "/TM_SD",
    42: "/TM_SE",
    43: "/TM_SF",
    44: "/TM_SG",
    45: "/NRST",
    46: "/SWDIO",
    47: "/SWCLK",
    48: "/SWO",
    50: "/CH340_XI",
    51: "/CH340_XO",
    54: "+24V_MOT",
    55: "+24V_SNS_PRE",
    56: "/STEP2",
    57: "/DIR2",
    58: "/EN_TMC2",
    59: "/Mot2A2",
    60: "/Mot2A1",
    61: "/Mot2B1",
    62: "/Mot2B2",
    63: "+24V_MOT2",
    64: "/IN2",
    65: "/OPTO_IN2",
    66: "/IN3",
    67: "/OPTO_IN3",
    68: "/PWM_OUT1",
    69: "/PWM_OUT2",
    70: "/PWR_EN",
    71: "/PWR_DIR",
    72: "/PWR_FAULT",
    73: "/VIB_CTRL",
    74: "/VIB_FAULT",
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
    a(f'\t(gr_text "{BOARD_W:.0f}x{BOARD_H:.0f} DIN | field jacks N/S only | W/E=rail"')
    a(f"\t\t(at {OX + 4} {OY + 3.5} 0)")
    a('\t\t(layer "Cmts.User")')
    a("\t\t(effects (font (size 0.9 0.9) (thickness 0.12)) (justify left))")
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")
    a('\t(gr_text "N: SNS/KEY/DISP | S: J1 MOT USB DBG | no side jacks"')
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

        # Courtyard / silk from true local AABB (not packing-size centered on origin)
        ax0, ay0, ax1, ay1 = footprint_aabb(p.fp)
        a("\t\t(fp_rect")
        a(f"\t\t\t(start {ax0:.3f} {ay0:.3f})")
        a(f"\t\t\t(end {ax1:.3f} {ay1:.3f})")
        a("\t\t\t(stroke (width 0.05) (type solid))")
        a("\t\t\t(fill none)")
        a('\t\t\t(layer "F.CrtYd")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        # Silk inset 0.15 mm so outline hugs body, not packing clearance
        sx0, sy0 = ax0 + 0.15, ay0 + 0.15
        sx1, sy1 = ax1 - 0.15, ay1 - 0.15
        if sx1 > sx0 and sy1 > sy0:
            a("\t\t(fp_rect")
            a(f"\t\t\t(start {sx0:.3f} {sy0:.3f})")
            a(f"\t\t\t(end {sx1:.3f} {sy1:.3f})")
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
    best: tuple[tuple[float, float], list] | None = None
    for bw, bh in BOARD_CANDIDATES:
        BOARD_W, BOARD_H = bw, bh
        found = None
        for seed in (42, 7, 99, 123, 256, 512):
            parts = build_parts()
            metrics = pack_parts(parts, seed=seed)
            clean = (
                metrics["overlaps"] == 0
                and metrics["ant_hits"] == 0
                and metrics.get("warns", 0) == 0
            )
            print(
                f"  try {bw:.0f}x{bh:.0f} seed={seed}: overlaps={metrics['overlaps']} "
                f"ant={metrics['ant_hits']} warns={metrics.get('warns', 0)}"
            )
            if clean:
                found = ((bw, bh), parts)
                break
        if found:
            best = found
            break
    if best is None:
        BOARD_W, BOARD_H = 150.0, 130.0
        parts = build_parts()
        metrics = pack_parts(parts, seed=42)
        print(
            f"FALLBACK {BOARD_W:.0f}x{BOARD_H:.0f} "
            f"overlaps={metrics['overlaps']} ant={metrics['ant_hits']} warns={metrics.get('warns')}"
        )
        best_parts = parts
    else:
        BOARD_W, BOARD_H = best[0]
        best_parts = best[1]
        print(f"Selected board {BOARD_W:.0f}x{BOARD_H:.0f} mm")
    emit_pcb_v2(best_parts)
    mov = [p for p in best_parts if not p.board_only]
    ov = 0
    for i, a in enumerate(mov):
        for b in mov[i + 1 :]:
            if abs(a.x - b.x) < (a.w + b.w) / 2 + GAP and abs(a.y - b.y) < (a.h + b.h) / 2 + GAP:
                ov += 1
                print(f"  overlap {a.ref}/{b.ref}")
    print(f"Done. size={BOARD_W:.0f}x{BOARD_H:.0f} overlaps={ov} gap={GAP}")


if __name__ == "__main__":
    main()
