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
from functools import lru_cache
from pathlib import Path

from stm32_pinmap import (
    BOOT_PINS,
    BUP_PIN,
    CNT5_PIN,
    IN2_PIN,
    IN3_PIN,
    KEYPAD_PINS,
    LQFP48_PINS,
    PWR_PINS,
    TM1637_PINS,
    TMC2_PINS,
    TMC_PINS,
    USART1_PINS,
    VIB_PINS,
)

from placement_full import (
    PlaceCfg,
    pack_parts as _pack_parts_full,
    _aabb,
    pair_courtyard_gap,
    jack_hline_union,
    NORTH_EDGE_JACKS,
    SOUTH_EDGE_JACKS,
)
from placement_saved import SAVED_BOARD_H, SAVED_BOARD_W, SAVED_POS

ROOT = Path(__file__).resolve().parent
PRETTY = ROOT / "libraries" / "ESP32_Carrier.pretty"
PCB = ROOT / "esp32_baseboard.kicad_pcb"

# Commercial outline: 160×110 fits IP65 180×130 / 200×150 and cabinet backplates.
# Not a 9TE slim DIN housing (those are ~151×82). L/R = DIN-clip / box-wall keep.
COMMERCIAL_W = 180.0
COMMERCIAL_H = 120.0
# True: ignore live XY (needed when outline/keep/jack-pack change). False: min-disp vs PCB.
FRESH_PACK = False
BOARD_W = COMMERCIAL_W
BOARD_H = COMMERCIAL_H
TARGET_BOARD_MM = 100.0
# Prefer commercial 160×110; grow if courtyard cannot clear.
BOARD_CANDIDATES = (
    (180.0, 120.0),
    (185.0, 120.0),
    (165.0, 110.0),
    (170.0, 110.0),
    (170.0, 115.0),
    (175.0, 115.0),
)
BOARD_MAX_MM = 300.0  # hard cap while auto-growing
BOARD_GROW_STEP_MM = 10.0
OX, OY = 50.0, 50.0  # Edge.Cuts origin
MARGIN = 8.0  # electronics ≥8 mm from left/right (DIN clip / box wall / duct)
JACK_SIDE_KEEP = 6.0  # field jacks ≥6 mm from L/R (inner corner radius)
JACK_MARGIN = 1.0  # field edge jacks may sit near N/S edges (panel cutouts)
GAP = 2.5  # min clear space between ALL courtyards (mm)
# Edge jacks: extra gap so two mating plugs do not hit (XH housing + finger)
JACK_PACK = 5.0
JACK_ROW_SEP = 3.0  # nearest AABB edge vs horizontal lines through jack courtyards

# No RF antenna (STM32). Keepout disabled (zeros) — PlaceCfg still accepts fields.
ANT_TIP = 0.0
ANT_CLEAR = 0.0
ANT_HALF_W = 0.0


def uid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Footprint helpers — physical connector housings (JST XH B*B-XH-A, KF301, USB)
# ---------------------------------------------------------------------------

XH_PITCH = 2.50  # JST XH
K3D = "${KICAD10_3DMODEL_DIR}"


def _kicad_model(rel: str, ox: float = 0.0, oy: float = 0.0, oz: float = 0.0, rz: float = 0.0) -> str:
    """KiCad 10 STEP from the system 3dmodels folder (visible in 3D viewer)."""
    return (
        f'\t(model "{K3D}/{rel}"\n'
        f"\t\t(offset (xyz {ox:g} {oy:g} {oz:g}))\n"
        f"\t\t(scale (xyz 1 1 1))\n"
        f"\t\t(rotate (xyz 0 0 {rz:g})))"
    )


def _xh_step(n: int) -> str:
    return (
        f"Connector_JST.3dshapes/JST_XH_B{n}B-XH-A_1x{n:02d}_P2.50mm_Vertical.step"
    )


def _fp_poly(pts: list[tuple[float, float]], layer: str, width: float) -> str:
    xy = " ".join(f"(xy {x:.2f} {y:.2f})" for x, y in pts)
    return (
        f"\t(fp_poly\n"
        f"\t\t(pts {xy})\n"
        f"\t\t(stroke (width {width}) (type solid))\n"
        f"\t\t(fill none)\n"
        f'\t\t(layer "{layer}"))'
    )


def _fp_rect(x0: float, y0: float, x1: float, y1: float, layer: str, width: float) -> str:
    return (
        f"\t(fp_rect (start {x0:.2f} {y0:.2f}) (end {x1:.2f} {y1:.2f})\n"
        f"\t\t(stroke (width {width}) (type solid)) (fill none) (layer \"{layer}\"))"
    )


def _fp_line(x0: float, y0: float, x1: float, y1: float, layer: str, width: float) -> str:
    return (
        f"\t(fp_line (start {x0:.2f} {y0:.2f}) (end {x1:.2f} {y1:.2f})\n"
        f"\t\t(stroke (width {width}) (type solid)) (layer \"{layer}\"))"
    )


def make_xh_bxa_socket(
    n: int,
    name: str,
    descr: str,
    labels: list[str] | None = None,
) -> str:
    """JST XH top-entry B*B-XH-A — same top-view as KiCad Connector_JST.

    Pads along +X (pin 1 at origin), pitch 2.50 mm.
    Housing 5.75 mm in Y (−2.35 … +3.40) × 2.5·(n−1)+4.9 mm in X.
    3D STEP uses rotate 0 so the body follows the pins (no extra 90°).
    """
    last = (n - 1) * XH_PITCH
    fab_x0, fab_x1 = -2.45, last + 2.45
    fab_y0, fab_y1 = -2.35, 3.40
    crt_x0, crt_x1 = -2.95, last + 2.95
    crt_y0, crt_y1 = -2.85, 3.90
    silk_x0, silk_x1 = -2.56, last + 2.56
    silk_y0, silk_y1 = -2.46, 3.51
    lines = [
        f'(footprint "{name}"',
        '\t(version 20240108)',
        '\t(generator "gen_compact_carrier.py")',
        '\t(layer "F.Cu")',
        f'\t(descr "{descr}")',
        '\t(tags "JST XH BXB-XH-A 2.50mm physical housing")',
        '\t(attr through_hole)',
        _fp_rect(crt_x0, crt_y0, crt_x1, crt_y1, "F.CrtYd", 0.05),
        _fp_rect(fab_x0, fab_y0, fab_x1, fab_y1, "F.Fab", 0.10),
        _fp_rect(silk_x0, silk_y0, silk_x1, silk_y1, "F.SilkS", 0.12),
        # Pin-1 mark on −Y wall (edge side when north rot=0)
        _fp_line(-0.63, fab_y0, 0.00, fab_y0 + 1.00, "F.Fab", 0.10),
        _fp_line(0.00, fab_y0 + 1.00, 0.63, fab_y0, "F.Fab", 0.10),
        _fp_line(-0.75, silk_y0 - 0.12, 0.75, silk_y0 - 0.12, "F.SilkS", 0.12),
    ]
    if labels:
        for i, lab in enumerate(labels):
            x = i * XH_PITCH
            lines.append(
                f'\t(fp_text user "{lab}" (at {x:.2f} {fab_y1 + 1.15:.2f} 0) (layer "F.SilkS")\n'
                f'\t\t(effects (font (size 0.55 0.55) (thickness 0.08))))'
            )
    for i in range(n):
        x = i * XH_PITCH
        shape = "rect" if i == 0 else "circle"
        lines.append(
            f'\t(pad "{i + 1}" thru_hole {shape} (at {x:.1f} 0) '
            f'(size 1.7 1.95) (drill 0.95) (layers "*.Cu" "*.Mask"))'
        )
    lines.append(")")
    return "\n".join(lines) + "\n"


def make_kf301_2p() -> str:
    """Degson/KF301-5.0-2P screw terminal — 10×10 mm body, pitch 5.0, screws on top."""
    # Pads at (±2.5, 0); body 10.0 × 10.0; wire entry +Y (south edge when rot=0).
    x0, x1, y0, y1 = -5.00, 5.00, -4.00, 6.00
    mrg = 0.50
    return f'''
(footprint "TerminalBlock_2P_5.0mm"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "KF301/DG128 5.0mm 2P screw terminal — 10x10 mm body")
	(tags "KF301 5.0mm screw terminal 24V")
	(attr through_hole)
{_fp_rect(x0 - mrg, y0 - mrg, x1 + mrg, y1 + mrg, "F.CrtYd", 0.05)}
{_fp_rect(x0, y0, x1, y1, "F.Fab", 0.10)}
{_fp_rect(x0, y0, x1, y1, "F.SilkS", 0.12)}
	(fp_circle (center -2.50 0.00) (end -0.70 0.00)
		(stroke (width 0.12) (type solid)) (fill none) (layer "F.Fab"))
	(fp_circle (center 2.50 0.00) (end 4.30 0.00)
		(stroke (width 0.12) (type solid)) (fill none) (layer "F.Fab"))
	(fp_circle (center -2.50 0.00) (end -0.70 0.00)
		(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
	(fp_circle (center 2.50 0.00) (end 4.30 0.00)
		(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
{_fp_line(x0 + 0.6, y1, x1 - 0.6, y1, "F.SilkS", 0.18)}
{_fp_line(-4.2, y1, -2.5, y1 + 1.4, "F.SilkS", 0.15)}
{_fp_line(-2.5, y1 + 1.4, -0.8, y1, "F.SilkS", 0.15)}
	(fp_text user "+" (at -2.50 -2.60 0) (layer "F.SilkS")
		(effects (font (size 1.1 1.1) (thickness 0.16))))
	(fp_text user "-" (at 2.50 -2.60 0) (layer "F.SilkS")
		(effects (font (size 1.1 1.1) (thickness 0.16))))
	(pad "1" thru_hole rect (at -2.5 0) (size 2.8 2.8) (drill 1.5) (layers "*.Cu" "*.Mask"))
	(pad "2" thru_hole circle (at 2.5 0) (size 2.8 2.8) (drill 1.5) (layers "*.Cu" "*.Mask"))
)
'''.strip() + "\n"


def make_usb_microb() -> str:
    """USB Micro-B SMT R/A — Molex 47346-0001 top view (KiCad Connector_USB).

    Shell 7.50 × 5.00 mm; courtyard 9.40 × 6.50 mm; mouth at local +Y (board edge).
    3D STEP offset 0 — body matches pads/courtyard.
    """
    return f'''
(footprint "USB_MicroB"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "USB Micro-B SMT R/A Molex 47346-0001 — shell 7.5x5.0 mouth +Y")
	(attr smd)
{_fp_rect(-4.70, -2.65, 4.70, 3.85, "F.CrtYd", 0.05)}
{_fp_rect(-3.75, -1.65, 3.75, 3.35, "F.Fab", 0.10)}
{_fp_rect(-3.75, -1.65, 3.75, 3.35, "F.SilkS", 0.12)}
{_fp_rect(-1.35, 2.65, 1.35, 3.35, "F.Fab", 0.08)}
	(fp_text user "USB" (at 0 -2.20 0) (layer "F.SilkS")
		(effects (font (size 0.6 0.6) (thickness 0.1))))
	(pad "1" smd rect (at -1.30 -1.46) (size 0.45 1.38) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "2" smd rect (at -0.65 -1.46) (size 0.45 1.38) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "3" smd rect (at 0.00 -1.46) (size 0.45 1.38) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "4" smd rect (at 0.65 -1.46) (size 0.45 1.38) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "5" smd rect (at 1.30 -1.46) (size 0.45 1.38) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "MH1" smd rect (at -3.375 1.20) (size 1.65 1.30) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "MH2" smd rect (at 3.375 1.20) (size 1.65 1.30) (layers "F.Cu" "F.Paste" "F.Mask"))
)
'''.strip() + "\n"


def make_keypad_kk8() -> str:
    """Molex KK 254 8P friction-lock header — 6.35 × 22.86 mm housing."""
    last = 7 * 2.54
    y0, y1 = -2.54, last + 2.54
    x0, x1 = -2.54, 3.81
    lock = [
        (x1, y0 + 4.0),
        (x1 + 1.15, y0 + 6.5),
        (x1 + 1.15, y1 - 6.5),
        (x1, y1 - 4.0),
    ]
    mrg = 0.50
    return f'''
(footprint "PinHeader_1x08_Keypad"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "Molex KK 254 1x8 friction-lock — 6.35x22.86 mm housing")
	(attr through_hole)
{_fp_rect(x0 - mrg, y0 - mrg, x1 + 1.15 + mrg, y1 + mrg, "F.CrtYd", 0.05)}
{_fp_rect(x0, y0, x1, y1, "F.Fab", 0.10)}
{_fp_rect(x0, y0, x1, y1, "F.SilkS", 0.12)}
{_fp_poly(lock, "F.Fab", 0.10)}
{_fp_poly(lock, "F.SilkS", 0.12)}
	(fp_text user "KEYPAD" (at 0 {y0 - 1.3:.2f} 0) (layer "F.SilkS")
		(effects (font (size 0.6 0.6) (thickness 0.1))))
	(pad "1" thru_hole rect (at 0 0) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "2" thru_hole circle (at 0 2.54) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "3" thru_hole circle (at 0 5.08) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "4" thru_hole circle (at 0 7.62) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "5" thru_hole circle (at 0 10.16) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "6" thru_hole circle (at 0 12.7) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "7" thru_hole circle (at 0 15.24) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
	(pad "8" thru_hole circle (at 0 17.78) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))
)
'''.strip() + "\n"


def make_female_1xn(name: str, n: int, descr: str, silk: str) -> str:
    """2.54 mm female socket housing (module header)."""
    last = (n - 1) * 2.54
    y0, y1 = -1.27, last + 1.27
    x0, x1 = -1.27, 1.27
    mrg = 0.50
    pads = []
    for i in range(n):
        y = i * 2.54
        shape = "rect" if i == 0 else "circle"
        pads.append(
            f'\t(pad "{i + 1}" thru_hole {shape} (at 0 {y:.2f}) '
            f'(size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))'
        )
    return f'''
(footprint "{name}"
	(version 20240108)
	(generator "gen_compact_carrier.py")
	(layer "F.Cu")
	(descr "{descr}")
	(attr through_hole)
{_fp_rect(x0 - mrg, y0 - mrg, x1 + mrg, y1 + mrg, "F.CrtYd", 0.05)}
{_fp_rect(x0, y0, x1, y1, "F.Fab", 0.10)}
{_fp_rect(x0, y0, x1, y1, "F.SilkS", 0.12)}
	(fp_text user "{silk}" (at 0 {y0 - 1.15:.2f} 0) (layer "F.SilkS")
		(effects (font (size 0.55 0.55) (thickness 0.08))))
{chr(10).join(pads)}
)
'''.strip() + "\n"


def extract_sexpr_blocks(text: str, names: tuple[str, ...]) -> list[str]:
    """Top-level-in-file (name ...) blocks with balanced parens."""
    blocks: list[str] = []
    i = 0
    while i < len(text):
        found_pos = None
        for name in names:
            token = f"({name}"
            p = text.find(token, i)
            if p < 0:
                continue
            nxt = p + len(token)
            if nxt < len(text) and (text[nxt].isalnum() or text[nxt] == "_"):
                continue
            if found_pos is None or p < found_pos:
                found_pos = p
        if found_pos is None:
            break
        depth = 0
        for j in range(found_pos, len(text)):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    blocks.append(text[found_pos : j + 1])
                    i = j + 1
                    break
        else:
            break
    return blocks


def set_fp_models(fp_name: str, models: list[str]) -> None:
    """Replace (model ...) blocks on a library footprint."""
    path = PRETTY / f"{fp_name}.kicad_mod"
    if not path.exists() or not models:
        return
    text = path.read_text(encoding="utf-8")
    for blk in extract_sexpr_blocks(text, ("model",)):
        text = text.replace(blk, "", 1)
    text = re.sub(r"\n{3,}", "\n\n", text).rstrip()
    if not text.endswith(")"):
        return
    text = text[:-1].rstrip() + "\n" + "\n".join(models) + "\n)\n"
    path.write_text(text, encoding="utf-8")


def attach_board_3d_models() -> None:
    """Bind KiCad system STEP models so pcbnew 3D viewer shows packages."""
    xh90 = 0.0  # official XH STEP already has pads along +X (matches our pins)
    r0805 = _kicad_model("Resistor_SMD.3dshapes/R_0805_2012Metric.step")
    c0805 = _kicad_model("Capacitor_SMD.3dshapes/C_0805_2012Metric.step")
    models: dict[str, list[str]] = {
        "JST_XH_02_Socket": [_kicad_model(_xh_step(2), rz=xh90)],
        "JST_XH_03_Socket": [_kicad_model(_xh_step(3), rz=xh90)],
        "JST_XH_04_Socket": [_kicad_model(_xh_step(4), rz=xh90)],
        "Mot_XH_04_Socket": [_kicad_model(_xh_step(4), rz=xh90)],
        "Disp_XH_04_Socket": [_kicad_model(_xh_step(4), rz=xh90)],
        "TerminalBlock_2P_5.0mm": [_kicad_model(
            "TerminalBlock_Phoenix.3dshapes/"
            "TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal.step",
            ox=-2.5,
        )],
        "USB_MicroB": [_kicad_model(
            "Connector_USB.3dshapes/USB_Micro-B_Molex_47346-0001.step",
        )],
        # Official PinSocket: pin 1 at origin, pins along +Y, rotate 0.
        # Footprint rotation already carries the STEP; extra rz=180 walked the
        # housing off the pad row in pcbnew 3D / kicad-cli render.
        "PinHeader_1x08_Keypad": [_kicad_model(
            "Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x08_P2.54mm_Vertical.step",
        )],
        "PowerMod_1CH_Sock": [_kicad_model(
            "Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x06_P2.54mm_Vertical.step",
        )],
        "VibAC_Sock": [_kicad_model(
            "Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x04_P2.54mm_Vertical.step",
        )],
        "SW_Push_6mm": [_kicad_model(
            "Button_Switch_THT.3dshapes/SW_PUSH_6mm.step",
            ox=-3.25, oy=2.25,
        )],
        "STM32G030C8T6_LQFP48": [_kicad_model(
            "Package_QFP.3dshapes/LQFP-48_7x7mm_P0.5mm.step",
        )],
        "Fuse_Holder_5x20_Open": [_kicad_model(
            "Fuse.3dshapes/Fuseholder_Cylinder-5x20mm_Schurter_0031_8201_Horizontal_Open.step",
            ox=-11.25,
        )],
        # Pin 1 at PCB (−7.62, −8.89). KiCad 3D offset Y is inverted vs footprint Y.
        "TMC2209_StepStick": [
            _kicad_model(
                "Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x08_P2.54mm_Vertical.step",
                ox=-7.62, oy=8.89,
            ),
            _kicad_model(
                "Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x08_P2.54mm_Vertical.step",
                ox=7.62, oy=8.89,
            ),
        ],
        # Passives / ICs — origin at body center (same as our pads)
        "C_0805": [c0805],
        "C_0805_100n": [c0805],
        "R_0805_10k": [r0805],
        "R_0805_4k7": [r0805],
        "R_0805_2k2": [r0805],
        "R_0805_1k": [r0805],
        "R_1206_22R": [_kicad_model("Resistor_SMD.3dshapes/R_1206_3216Metric.step")],
        "PTC_1812": [_kicad_model("Resistor_SMD.3dshapes/R_1812_4532Metric.step")],
        "Diode_SMA": [_kicad_model("Diode_SMD.3dshapes/D_SMA.step")],
        "Diode_SMB_TVS": [_kicad_model("Diode_SMD.3dshapes/D_SMB.step")],
        "Crystal_SMD_3225": [_kicad_model(
            "Crystal.3dshapes/Crystal_SMD_3225-4Pin_3.2x2.5mm.step",
        )],
        "CP_SMD_D6.3x5.8": [_kicad_model("Capacitor_SMD.3dshapes/CP_Elec_6.3x5.8.step")],
        "CP_SMD_D8x10": [_kicad_model("Capacitor_SMD.3dshapes/CP_Elec_8x10.step")],
        "L_SMD_6x6": [_kicad_model("Inductor_SMD.3dshapes/L_Sunlord_SWPA6040S.step")],
        "CH340C": [_kicad_model("Package_SO.3dshapes/SOIC-16_3.9x9.9mm_P1.27mm.step")],
        # Official KiCad SOT-223: pins −X, tab +X, pad1 = (−3.15, −2.3)
        "AMS1117_SOT223": [_kicad_model(
            "Package_TO_SOT_SMD.3dshapes/SOT-223.step",
        )],
        "MP1584EN_SOT23-8": [_kicad_model(
            "Package_TO_SOT_SMD.3dshapes/SOT-23-8.step",
        )],
        "PC817_SOP4": [_kicad_model(
            "Package_SO.3dshapes/SO-4_4.4x3.6mm_P2.54mm.step",
        )],
        "S8050_SOT23": [_kicad_model(
            "Package_TO_SOT_SMD.3dshapes/SOT-23.step",
        )],
    }
    for name, mods in models.items():
        set_fp_models(name, mods)


def ensure_extra_footprints() -> None:
    """Create any missing .kicad_mod used by this board."""
    PRETTY.mkdir(parents=True, exist_ok=True)

    def write(name: str, body: str, *, force: bool = False) -> None:
        p = PRETTY / f"{name}.kicad_mod"
        if force or not p.exists():
            p.write_text(body.strip() + "\n", encoding="utf-8")

    # Field jacks — physical housing outlines (force so packing uses real body)
    write("JST_XH_02_Socket", make_xh_bxa_socket(
        2, "JST_XH_02_Socket", "JST XH B2B-XH-A 2P — 7.4x5.75 mm housing", ["1", "2"]), force=True)
    write("JST_XH_03_Socket", make_xh_bxa_socket(
        3, "JST_XH_03_Socket", "JST XH B3B-XH-A 3P — 9.9x5.75 mm housing", ["1", "2", "3"]), force=True)
    write("JST_XH_04_Socket", make_xh_bxa_socket(
        4, "JST_XH_04_Socket", "JST XH B4B-XH-A 4P — 12.4x5.75 mm housing", ["1", "2", "3", "4"]), force=True)
    write("Mot_XH_04_Socket", make_xh_bxa_socket(
        4, "Mot_XH_04_Socket", "JST XH 4P motor — A2 A1 B1 B2", ["A2", "A1", "B1", "B2"]), force=True)
    write("Disp_XH_04_Socket", make_xh_bxa_socket(
        4, "Disp_XH_04_Socket", "JST XH 4P TM1637 — CLK DIO 5V GND", ["CLK", "DIO", "5V", "GND"]), force=True)
    write("TerminalBlock_2P_5.0mm", make_kf301_2p(), force=True)
    write("USB_MicroB", make_usb_microb(), force=True)
    write("PinHeader_1x08_Keypad", make_keypad_kk8(), force=True)
    write("PowerMod_1CH_Sock", make_female_1xn(
        "PowerMod_1CH_Sock", 6, "1x6 2.54 female — MOSFET 1CH module", "MOSFET"), force=True)
    write("VibAC_Sock", make_female_1xn(
        "VibAC_Sock", 4, "1x4 2.54 female — SSR vibratory module", "SSR"), force=True)

    # STM32G030C8T6 — LQFP48 7×7 mm, 0.5 mm pitch (KiCad LQFP-48_7x7mm_P0.5mm)
    pads = []
    pitch, reach = 0.5, 4.1625
    half = 11 * pitch / 2  # 2.75
    for n in range(1, 13):  # left 1..12
        y = -half + (n - 1) * pitch
        pads.append(
            f'\t(pad "{n}" smd roundrect (at {-reach} {y:.4f}) (size 1.475 0.3)'
            f'\n\t\t(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))'
        )
    for n in range(13, 25):  # bottom 13..24
        x = -half + (n - 13) * pitch
        pads.append(
            f'\t(pad "{n}" smd roundrect (at {x:.4f} {reach}) (size 0.3 1.475)'
            f'\n\t\t(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))'
        )
    for n in range(25, 37):  # right 25..36 (bottom→top ⇒ y decreasing)
        y = half - (n - 25) * pitch
        pads.append(
            f'\t(pad "{n}" smd roundrect (at {reach} {y:.4f}) (size 1.475 0.3)'
            f'\n\t\t(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))'
        )
    for n in range(37, 49):  # top 37..48 (right→left ⇒ x decreasing)
        x = half - (n - 37) * pitch
        pads.append(
            f'\t(pad "{n}" smd roundrect (at {x:.4f} {-reach}) (size 0.3 1.475)'
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
\t(fp_rect (start -5.2 -5.2) (end 5.2 5.2)
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

    write(
        "CH340C",
        """
(footprint "CH340C"
\t(version 20240108)
\t(generator "gen_compact_carrier.py")
\t(layer "F.Cu")
\t(descr "CH340C SOP-16")
\t(attr smd)
\t(fp_rect (start -3.7 -5.4) (end 3.7 5.4)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd rect (at -2.475 -4.445) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at -2.475 -3.175) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "3" smd rect (at -2.475 -1.905) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "4" smd rect (at -2.475 -0.635) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "5" smd rect (at -2.475 0.635) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "6" smd rect (at -2.475 1.905) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "7" smd rect (at -2.475 3.175) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "8" smd rect (at -2.475 4.445) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "9" smd rect (at 2.475 4.445) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "10" smd rect (at 2.475 3.175) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "11" smd rect (at 2.475 1.905) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "12" smd rect (at 2.475 0.635) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "13" smd rect (at 2.475 -0.635) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "14" smd rect (at 2.475 -1.905) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "15" smd rect (at 2.475 -3.175) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "16" smd rect (at 2.475 -4.445) (size 1.95 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
    )

    for name, val in (("R_0805_4k7", "4k7"), ("R_0805_10k", "10k"), ("R_0805_2k2", "2k2"), ("R_0805_1k", "1k")):
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
\t(fp_rect (start -4.5 -3.4) (end 4.5 3.4)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd rect (at -3.15 -2.3) (size 2.0 1.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at -3.15 0) (size 2.0 1.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "3" smd rect (at -3.15 2.3) (size 2.0 1.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "TAB" smd rect (at 3.15 0) (size 2.0 3.8) (layers "F.Cu" "F.Paste" "F.Mask"))
)
""",
        force=True,
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
\t(fp_rect (start -2.0 -1.6) (end 2.0 1.6)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd rect (at -1.1375 -0.975) (size 1.325 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at -1.1375 -0.325) (size 1.325 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "3" smd rect (at -1.1375 0.325) (size 1.325 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "4" smd rect (at -1.1375 0.975) (size 1.325 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "5" smd rect (at 1.1375 0.975) (size 1.325 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "6" smd rect (at 1.1375 0.325) (size 1.325 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "7" smd rect (at 1.1375 -0.325) (size 1.325 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "8" smd rect (at 1.1375 -0.975) (size 1.325 0.5) (layers "F.Cu" "F.Paste" "F.Mask"))
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
\t(fp_rect (start -3.5 -3.5) (end 3.5 3.5)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(pad "1" smd rect (at -2.25 0) (size 1.7 5.7) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at 2.25 0) (size 1.7 5.7) (layers "F.Cu" "F.Paste" "F.Mask"))
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
	(pad "1" smd rect (at -2.0 0) (size 2.5 1.8) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "2" smd rect (at 2.0 0) (size 2.5 1.8) (layers "F.Cu" "F.Paste" "F.Mask"))
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
	(fp_rect (start -3.6 -1.8) (end 3.6 1.8)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(fp_line (start 1.6 -1.3) (end 1.6 1.3)
		(stroke (width 0.12) (type solid)) (layer "F.SilkS"))
	(pad "1" smd rect (at -2.15 0) (size 2.5 2.3) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "2" smd rect (at 2.15 0) (size 2.5 2.3) (layers "F.Cu" "F.Paste" "F.Mask"))
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
	(fp_rect (start -4.6 -3.8) (end 4.6 3.8)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(fp_circle (center 0 0) (end 3.15 0)
		(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
	(pad "1" smd rect (at -2.7 0) (size 3.5 1.6) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "2" smd rect (at 2.7 0) (size 3.5 1.6) (layers "F.Cu" "F.Paste" "F.Mask"))
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
	(pad "1" smd rect (at -3.25 0) (size 3.5 2.5) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "2" smd rect (at 3.25 0) (size 3.5 2.5) (layers "F.Cu" "F.Paste" "F.Mask"))
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
	(fp_rect (start -4.4 -2.2) (end 4.4 2.2)
		(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(pad "1" smd rect (at -3.15 -1.27) (size 2.0 0.64) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "2" smd rect (at -3.15 1.27) (size 2.0 0.64) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "3" smd rect (at 3.15 1.27) (size 2.0 0.64) (layers "F.Cu" "F.Paste" "F.Mask"))
	(pad "4" smd rect (at 3.15 -1.27) (size 2.0 0.64) (layers "F.Cu" "F.Paste" "F.Mask"))
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
\t(fp_rect (start -2.0 -1.6) (end 2.0 1.6)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(fp_line (start -0.7 -1.0) (end 0.7 -1.0)
\t\t(stroke (width 0.12) (type solid)) (layer "F.SilkS"))
\t(pad "1" smd rect (at -0.9375 -0.95) (size 1.475 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at -0.9375 0.95) (size 1.475 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "3" smd rect (at 0.9375 0) (size 1.475 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))
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
\t(pad "1" smd rect (at -1.1 0.85) (size 1.4 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "2" smd rect (at 1.1 0.85) (size 1.4 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "3" smd rect (at 1.1 -0.85) (size 1.4 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
\t(pad "4" smd rect (at -1.1 -0.85) (size 1.4 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
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
\t(fp_rect (start -4.5 -3.5) (end 4.5 3.5)
\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
\t(fp_rect (start -3.0 -3.0) (end 3.0 3.0)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(fp_circle (center 0 0) (end 1.2 0)
\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
\t(pad "1" thru_hole circle (at -3.25 -2.25) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
\t(pad "2" thru_hole circle (at 3.25 -2.25) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
\t(pad "3" thru_hole circle (at 3.25 2.25) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
\t(pad "4" thru_hole circle (at -3.25 2.25) (size 1.5 1.5) (drill 0.9) (layers "*.Cu" "*.Mask"))
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
    attach_board_3d_models()


@lru_cache(maxsize=None)
def footprint_aabb(fp_name: str) -> tuple[float, float, float, float]:
    """Local AABB = F.CrtYd (top-down body), else pads + 0.25 mm."""
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
    circ = re.search(
        r'\(fp_circle\s*\(center\s+([-\d.]+)\s+([-\d.]+)\)\s*\(end\s+([-\d.]+)\s+([-\d.]+)\)[\s\S]*?layer "F\.CrtYd"',
        text,
    )
    if circ:
        cx, cy, ex, ey = map(float, circ.groups())
        rad = ((ex - cx) ** 2 + (ey - cy) ** 2) ** 0.5
        return (cx - rad, cy - rad, cx + rad, cy + rad)
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


def courtyard_aabb(fp_name: str) -> tuple[float, float, float, float]:
    """Local courtyard AABB used for packing (CrtYd + 0.125 mm per side)."""
    x0, y0, x1, y1 = footprint_aabb(fp_name)
    pad = 0.125
    return (x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def courtyard_size(fp_name: str) -> tuple[float, float]:
    """Return (width, height) packing AABB from true courtyard/pad extents + margin."""
    x0, y0, x1, y1 = courtyard_aabb(fp_name)
    w, h = x1 - x0, y1 - y0
    if w < 0.5 or h < 0.5:
        return (12.0, 12.0)
    return (w, h)


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
    aabb_local: tuple[float, float, float, float] = (-6.0, -6.0, 6.0, 6.0)


# Real names on F.SilkS. Refs (U3, J14, C10…) stay in the file for nets/BOM but are hidden.
SILK_NAME = {
    "U1": "STM32G030",
    "U2": "MP1584",
    "U5": "CH340",
    "U6": "AMS1117",
    "U3": "TMC2209",
    "U4": "TMC2209",
    "U_PWR1": "MOSFET",
    "U_PWR2": "MOSFET",
    "U_VIB": "SSR",
    "J1": "24V IN",
    "J_USB": "USB",
    "J_MOT1": "MOT1",
    "J_MOT2": "MOT2",
    "J_DISP": "TM1637",
    "J_KEY": "KEYPAD",
    "J14": "BUP",
    "J15": "FIBER",
    "J_IN2": "IN2",
    "J_IN3": "IN3",
    "J_CNT5": "CNT 5V",
    "J_P24N": "+24V",
    "J_P5N": "+5V",
    "J_P24S": "+24V",
    "SW_BOOT": "BOOT",
    "SW_NRST": "RST",
}
# Generator tags — not real module names.
HIDE_FP_TEXT = frozenset({
    "THAY TMC2209", "NEMA=Mot pins", "FET 1CH", "U_VIB", "DBG",
})


def build_parts() -> list[Part]:
    ensure_extra_footprints()

    def P(ref, fp, value, cluster, pad_nets=None, rot=0.0, board_only=False):
        loc = courtyard_aabb(fp)
        w, h = loc[2] - loc[0], loc[3] - loc[1]
        if w < 0.5 or h < 0.5:
            w, h = 12.0, 12.0
            loc = (-6.0, -6.0, 6.0, 6.0)
        if rot in (90, 270):
            w, h = h, w
        return Part(
            ref, fp, value, cluster, w, h, rot,
            pad_nets=pad_nets or {}, board_only=board_only, aabb_local=loc,
        )

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
        CNT5_PIN: "/CNT5",
        PWR_PINS["PWM1"]: "/PWM_OUT1",
        PWR_PINS["PWM2"]: "/PWM_OUT2",
        PWR_PINS["EN1"]: "/PWR_EN1",
        PWR_PINS["EN2"]: "/PWR_EN2",
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
        BOOT_PINS["SWDIO"]: "/SWDIO",
        BOOT_PINS["SWCLK"]: "/SWCLK",
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
        P("J_USB", "USB_MicroB", "USB", "MCU", {
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
        P("U1", "STM32G030C8T6_LQFP48", "STM32G030", "MCU", u1_nets),
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
        P("U3", "TMC2209_StepStick", "TMC2209", "TMC", {
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
        P("U4", "TMC2209_StepStick", "TMC2209", "TMC", {
            "1": "/EN_TMC2", "7": "/STEP2", "8": "/DIR2",
            "9": "+24V_MOT2", "10": "GND",
            "11": "/Mot2A2", "12": "/Mot2A1", "13": "/Mot2B1", "14": "/Mot2B2",
            "15": "+3V3", "16": "GND",
        }, rot=0),
        P("R2B", "R_0805_10k", "10k", "TMC", {"1": "+3V3", "2": "/EN_TMC2"}),
        P("J_MOT2", "Mot_XH_04_Socket", "MOT2", "TMC", {
            "1": "/Mot2A2", "2": "/Mot2A1", "3": "/Mot2B1", "4": "/Mot2B2",
        }),
        # External TM1637 4-digit module (driver on module) — CLK DIO +5V GND
        P("J_DISP", "Disp_XH_04_Socket", "TM1637", "HMI", {
            "1": "/TM_CLK", "2": "/TM_DIO", "3": "+5V", "4": "GND",
        }),
        P("J_KEY", "PinHeader_1x08_Keypad", "KEYPAD", "HMI", {
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
        # Cheap 5V through-beam / IR count (NPN or OC→GND). Separate from 24V BUP.
        P("J_CNT5", "JST_XH_03_Socket", "CNT5V", "OPTO", {
            "1": "+5V", "2": "GND", "3": "/OPTO_IN_5V",
        }),
        P("U47", "PC817_SOP4", "PC817", "OPTO", {
            "1": "/OPTO_IN_5V", "2": "GND", "3": "GND", "4": "/CNT5",
        }),
        P("R47", "R_0805_1k", "1k", "OPTO", {"1": "+5V", "2": "/OPTO_IN_5V"}),
        P("R51", "R_0805_10k", "10k", "OPTO", {"1": "+3V3", "2": "/CNT5"}),
        P("C27", "C_0805_100n", "100n", "OPTO", {"1": "+5V", "2": "GND"}),
        # Aux power next to field I/O (sensor / DO wiring convenience)
        P("J_P24N", "JST_XH_02_Socket", "P24_N", "OPTO", {
            "1": "+24V_SNS", "2": "GND",
        }),
        P("J_P5N", "JST_XH_02_Socket", "P5_N", "OPTO", {
            "1": "+5V", "2": "GND",
        }),
        P("J_P24S", "JST_XH_02_Socket", "P24_S", "PWR", {
            "1": "+24V", "2": "GND",
        }),
        # One pluggable MOSFET module per 24V channel
        P("U_PWR1", "PowerMod_1CH_Sock", "MOSFET", "PWR", {
            "1": "+24V", "2": "GND", "3": "+3V3",
            "4": "/PWM_OUT1", "5": "/PWR_EN1", "6": "/PWR_FAULT",
        }),
        P("U_PWR2", "PowerMod_1CH_Sock", "MOSFET", "PWR", {
            "1": "+24V", "2": "GND", "3": "+3V3",
            "4": "/PWM_OUT2", "5": "/PWR_EN2", "6": "/PWR_FAULT",
        }),
        P("R_PWR_FLT", "R_0805_10k", "10k", "PWR", {"1": "+3V3", "2": "/PWR_FAULT"}),
        # Pluggable AC vibratory SSR control — socket only
        P("U_VIB", "VibAC_Sock", "SSR", "PWR", {
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


def pack_parts(parts: list[Part], seed: int = 42, anchors: dict | None = None) -> dict:
    """Place parts. With anchors: keep PCB poses, min-displacement legalize."""
    cfg = PlaceCfg(
        board_w=BOARD_W,
        board_h=BOARD_H,
        ox=OX,
        oy=OY,
        margin=MARGIN,
        jack_margin=JACK_MARGIN,
        jack_side_keep=JACK_SIDE_KEEP,
        jack_pack=JACK_PACK,
        jack_row_sep=JACK_ROW_SEP,
        gap=GAP,
        ant_tip=ANT_TIP,
        ant_clear=ANT_CLEAR,
        ant_half_w=ANT_HALF_W,
        courtyard_size=courtyard_size,
    )
    return _pack_parts_full(parts, cfg, seed=seed, anchors=anchors)


def load_pcb_anchors() -> tuple[dict[str, tuple[float, float, float]], float, float] | None:
    """Hand-tuned poses from placement_saved.py; fall back to parsing the PCB."""
    if SAVED_POS:
        return dict(SAVED_POS), float(SAVED_BOARD_W), float(SAVED_BOARD_H)
    if not PCB.exists():
        return None
    text = PCB.read_text(encoding="utf-8")
    em = re.search(
        r"\(gr_rect\s*\(start\s+([\d.-]+)\s+([\d.-]+)\)\s*\(end\s+([\d.-]+)\s+([\d.-]+)\)"
        r"[\s\S]*?Edge\.Cuts",
        text,
    )
    if not em:
        return None
    x0, y0, x1, y1 = map(float, em.groups())
    bw, bh = x1 - x0, y1 - y0
    anchors: dict[str, tuple[float, float, float]] = {}
    i = 0
    while True:
        p = text.find("(footprint ", i)
        if p < 0:
            break
        d = 0
        end = None
        for j in range(p, len(text)):
            if text[j] == "(":
                d += 1
            elif text[j] == ")":
                d -= 1
                if d == 0:
                    end = j
                    break
        if end is None:
            break
        blk = text[p : end + 1]
        i = end + 1
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', blk)
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", blk)
        if not ref_m or not at:
            continue
        anchors[ref_m.group(1)] = (
            float(at.group(1)),
            float(at.group(2)),
            float(at.group(3) or 0),
        )
    if len(anchors) < 8:
        return None
    return anchors, bw, bh


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
    45: "/NRST",
    46: "/SWDIO",
    47: "/SWCLK",
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
    70: "/PWR_EN1",
    71: "/PWR_EN2",
    72: "/PWR_FAULT",
    73: "/VIB_CTRL",
    74: "/VIB_FAULT",
    79: "/CNT5",
    80: "/OPTO_IN_5V",
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
    boxes = {p.ref: _aabb(p) for p in parts}
    _n_lo, n_hi = jack_hline_union(boxes, NORTH_EDGE_JACKS)
    s_lo, _s_hi = jack_hline_union(boxes, SOUTH_EDGE_JACKS)
    for y in (n_hi, s_lo):
        a("\t(gr_line")
        a(f"\t\t(start {OX:.4f} {y:.4f})")
        a(f"\t\t(end {OX + BOARD_W:.4f} {y:.4f})")
        a("\t\t(stroke (width 0.2) (type dash))")
        a('\t\t(layer "Dwgs.User")')
        a(f'\t\t(uuid "{uid()}")')
        a("\t)")
    for x in (OX + MARGIN, OX + BOARD_W - MARGIN):
        a("\t(gr_line")
        a(f"\t\t(start {x:.4f} {OY:.4f})")
        a(f"\t\t(end {x:.4f} {OY + BOARD_H:.4f})")
        a("\t\t(stroke (width 0.2) (type dash))")
        a('\t\t(layer "Dwgs.User")')
        a(f'\t\t(uuid "{uid()}")')
        a("\t)")
    a(f'\t(gr_text "{BOARD_W:.0f}x{BOARD_H:.0f} | L/R {MARGIN:.0f}mm DIN/clip | box 180x130 / 200x150"')
    a(f"\t\t(at {OX + 4} {OY + 3.5} 0)")
    a('\t\t(layer "Cmts.User")')
    a("\t\t(effects (font (size 0.9 0.9) (thickness 0.12)) (justify left))")
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")
    a('\t(gr_text "N: SNS/HMI/USB | S: J1 MOT1 MOT2 PWR1 PWR2 VIB P24 | TMC inland"')
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
        a("\t\t\t(hide yes)")
        a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        silk = SILK_NAME.get(p.ref, "")
        a('\t\t(property "Value" "' + p.value + '"')
        a("\t\t\t(at 0 1.5 0)")
        a('\t\t\t(layer "F.Fab")')
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

        copied_silk = False
        # Physical housing / silk / courtyard / 3D models from the library
        for g in extract_sexpr_blocks(
            raw, ("fp_rect", "fp_line", "fp_poly", "fp_circle", "fp_arc", "fp_text", "model")
        ):
            if "(property" in g:
                continue
            if g.lstrip().startswith("(fp_text"):
                um = re.search(r'\(fp_text user "([^"]*)"', g)
                if um and um.group(1) in HIDE_FP_TEXT:
                    continue
                if um and silk and um.group(1) == silk:
                    copied_silk = True
            is_model = g.lstrip().startswith("(model")
            if not is_model and "(uuid" not in g:
                g = g[:-1] + f'\n\t\t(uuid "{uid()}")\n\t)'
            for lg in g.strip().splitlines():
                a("\t\t" + lg.lstrip())

        if silk and not copied_silk:
            if "TMC2209" in p.fp:
                sx, sy = 0.0, 13.6
            else:
                x0, y0, x1, y1 = p.aabb_local
                sx, sy = (x0 + x1) / 2.0, y0 - 1.15
            a(f'\t\t(fp_text user "{silk}"')
            a(f"\t\t\t(at {sx:.2f} {sy:.2f} 0)")
            a('\t\t\t(layer "F.SilkS")')
            a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
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


def iter_board_sizes():
    """Yield (w,h) — listed candidates first, then grow W then H until BOARD_MAX_MM.

    Policy: never cram parts under GAP; enlarge the board instead.
    """
    seen: set[tuple[float, float]] = set()
    for wh in BOARD_CANDIDATES:
        if wh not in seen:
            seen.add(wh)
            yield wh
    # Auto-grow from the largest seed
    bw = max(w for w, _ in BOARD_CANDIDATES)
    bh = max(h for _, h in BOARD_CANDIDATES)
    step = BOARD_GROW_STEP_MM
    while bw <= BOARD_MAX_MM and bh <= BOARD_MAX_MM:
        grew = False
        if bw + step <= BOARD_MAX_MM:
            bw += step
            grew = True
            wh = (bw, bh)
            if wh not in seen:
                seen.add(wh)
                yield wh
        if bh + step <= BOARD_MAX_MM:
            bh += step
            grew = True
            wh = (bw, bh)
            if wh not in seen:
                seen.add(wh)
                yield wh
        if not grew:
            break


def main() -> None:
    global BOARD_W, BOARD_H
    loaded = load_pcb_anchors()
    size_changed = True
    if loaded:
        _anchors, live_w, live_h = loaded
        size_changed = (
            abs(live_w - COMMERCIAL_W) > 0.5 or abs(live_h - COMMERCIAL_H) > 0.5
        )
    # Fresh pack when adopting 8 mm L/R keep (sticky from 155/failed 160 leaves overlaps).
    if loaded and not size_changed and not FRESH_PACK:
        anchors, bw, bh = loaded
        BOARD_W, BOARD_H = COMMERCIAL_W, COMMERCIAL_H
        print(
            f"Min-disp place from placement_saved.py ({len(anchors)} parts, "
            f"{bw:.0f}x{bh:.0f} mm)"
        )
        parts = build_parts()
        metrics = pack_parts(parts, seed=42, anchors=anchors)
        print(
            f"  min-disp: overlaps={metrics['overlaps']} ant={metrics['ant_hits']} "
            f"warns={metrics.get('warns', 0)} rms={metrics.get('disp_rms', 0):.2f}mm"
        )
        if (
            metrics["overlaps"] == 0
            and metrics["ant_hits"] == 0
            and metrics.get("warns", 0) == 0
        ):
            print(f"Selected board {BOARD_W:.0f}x{BOARD_H:.0f} mm (commercial L/R keep)")
            emit_pcb_v2(parts)
            print(f"Done. size={BOARD_W:.0f}x{BOARD_H:.0f} overlaps=0 gap={GAP} jack_pack={JACK_PACK}")
            return
        print("  min-disp still overlapping — fresh pack on commercial outline")
        BOARD_W, BOARD_H = COMMERCIAL_W, COMMERCIAL_H
        parts = build_parts()
        metrics = pack_parts(parts, seed=42)
        print(
            f"  commercial fresh: overlaps={metrics['overlaps']} ant={metrics['ant_hits']} "
            f"warns={metrics.get('warns', 0)}"
        )
        if (
            metrics["overlaps"] == 0
            and metrics["ant_hits"] == 0
            and metrics.get("warns", 0) == 0
        ):
            print(f"Selected board {BOARD_W:.0f}x{BOARD_H:.0f} mm (commercial fresh)")
            emit_pcb_v2(parts)
            print(f"Done. size={BOARD_W:.0f}x{BOARD_H:.0f} overlaps=0 gap={GAP} jack_pack={JACK_PACK}")
            return

    best: tuple[tuple[float, float], list, dict] | None = None
    seeds = (42, 7)
    for bw, bh in iter_board_sizes():
        BOARD_W, BOARD_H = bw, bh
        size_clean = False
        for seed in seeds:
            parts = build_parts()
            metrics = pack_parts(parts, seed=seed)
            print(
                f"  try {bw:.0f}x{bh:.0f} seed={seed}: overlaps={metrics['overlaps']} "
                f"ant={metrics['ant_hits']} warns={metrics.get('warns', 0)}"
            )
            clean = (
                metrics["overlaps"] == 0
                and metrics["ant_hits"] == 0
                and metrics.get("warns", 0) == 0
            )
            score = (
                metrics["overlaps"],
                metrics.get("warns", 0),
                metrics["ant_hits"],
                bw * bh,
            )
            if best is None or score < (
                best[2]["overlaps"],
                best[2].get("warns", 0),
                best[2]["ant_hits"],
                best[0][0] * best[0][1],
            ):
                best = ((bw, bh), parts, metrics)
            if clean:
                size_clean = True
                break
        if size_clean:
            break
        # Still overlapping → keep growing (do not accept cramped board)
        print(f"  grow: {bw:.0f}x{bh:.0f} not clear — enlarging board…")
    assert best is not None
    BOARD_W, BOARD_H = best[0]
    best_parts = best[1]
    print(f"Selected board {BOARD_W:.0f}x{BOARD_H:.0f} mm (auto-grow OK up to {BOARD_MAX_MM:.0f})")
    emit_pcb_v2(best_parts)
    mov = [p for p in best_parts if not p.board_only]
    ov = 0
    tol = 1e-3
    for i, a in enumerate(mov):
        for b in mov[i + 1 :]:
            ax0, ay0, ax1, ay1 = _aabb(a)
            bx0, by0, bx1, by1 = _aabb(b)
            g = pair_courtyard_gap(a.ref, b.ref, GAP, JACK_PACK)
            if (
                ax1 + g - tol > bx0
                and bx1 + g - tol > ax0
                and ay1 + g - tol > by0
                and by1 + g - tol > ay0
            ):
                ov += 1
                print(f"  overlap {a.ref}/{b.ref}")
    print(f"Done. size={BOARD_W:.0f}x{BOARD_H:.0f} overlaps={ov} gap={GAP} jack_pack={JACK_PACK}")
    if ov > 0:
        raise SystemExit(
            f"placement still has {ov} courtyard overlaps (gap={GAP}, jack_pack={JACK_PACK}); "
            f"raise BOARD_MAX_MM or fix locked edge row"
        )


if __name__ == "__main__":
    main()
