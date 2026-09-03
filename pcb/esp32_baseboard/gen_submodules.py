#!/usr/bin/env python3
"""JLCPCB-ready pluggable sub-modules for esp32_baseboard.

  M3 ULN2003     — commercial ULN board is Dupont-only → DIP + JST-XH 5P

(M1 POWER_PROT removed — D3/F1/D1 on carrier.)
(M2 OPTO4 removed — PC817×4 + 2k2/10k on carrier; `_m2_layout()` kept for place.)

Generates:
  modules/m3_uln2003.kicad_pcb      - ULN2003AN + JST-XH 5P 28BYJ, 1x6 pin
  modules/submodules_panel.kicad_pcb - M3 + mousebites

Carrier mates (straight 2.54 mm pin header):
  U5-U7   1x6  ULN/M3   (IN1-4, GND, +12V) ×3
"""
from __future__ import annotations

import json
import math
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOD = ROOT / "modules"
PRETTY = ROOT / "libraries" / "ESP32_Carrier.pretty"
PITCH = 2.54

# Match carrier: placement only unless EMIT_TRACKS=1
EMIT_TRACKS = os.environ.get("EMIT_TRACKS", "") == "1"

# M2 geometry is computed by _m2_layout() (AABB pack → min height).
M3_W, M3_H = 36.0, 28.0
XH_PITCH = 2.5
PANEL_GAP = 8.0
PANEL_MARGIN = 5.0


@dataclass(frozen=True)
class M2Layout:
    """P1 top / P2 bottom; 4 channel columns — IN/OUT stay on column X."""
    w: float
    h: float
    hdr_edge: float
    hdr_dy: float
    hx: float
    hy_in: float
    hy_out: float
    ch_xs: tuple[float, ...]
    cy: float       # PC817 row
    ry_in: float    # 2k2 centers (north of chip)
    ry_out: float   # 10k centers (south of chip)
    ch_pitch: float
    fan: float


def _m2_layout() -> M2Layout:
    """Route-friendly pack: 4 columns, signal flow only along each column X.

      P1 ──FAN (empty)── R2k2 ── PC817 ── R10k ──FAN── P2
           ↑ only horizontal jog here ↑              ↑

    Resistors sit *on* the column (not beside), so board stays moderately
    wide while IN/OUT tracks never cut through neighboring channels.
    """
    n_ch = 4
    clear = 0.70
    hdr_edge = 2.0
    fan = 2.8
    edge_x = 1.5
    chip_hx, chip_hy = 2.0, 2.0
    r_hx, r_hy = 1.50, 3.75 + 0.80
    # Vertical gap chip center ↔ R center
    d_r = chip_hy + clear + r_hy  # ~7.25
    # Column pitch: R silk is narrow in X when @90°
    col_half = max(chip_hx, r_hx)
    ch_pitch = 2.0 * col_half + clear + 1.2  # ~6.1 → room for pad clearance
    ch_pitch = min(max(ch_pitch, 6.0), 8.0)  # moderate width
    col_span = (n_ch - 1) * ch_pitch  # center-to-center of outer columns
    # Board width: columns + half-parts each side + edge margin
    w = col_span + 2.0 * (col_half + 0.5 + edge_x)
    w = math.ceil(w * 2.0) / 2.0
    # Center the 4 channel columns on the board
    ch_mid = w / 2.0
    ch_xs = tuple(ch_mid + (i - 1.5) * ch_pitch for i in range(n_ch))

    # Height from stacked R–U–R + fans + pin edges
    parts_span = 2.0 * (d_r + r_hy)  # outer R pad to outer R pad via chip
    h_min = 2.0 * hdr_edge + 2.0 * fan + parts_span
    # Locked board size 26x34 (was auto-computed 33.5); hdr_edge is untouched
    # so P1/P2 stay at the same offset from the top/bottom edges — the extra
    # 0.5 mm only widens the two fan bands around the R–U–R stack.
    h = 34.0
    assert h >= h_min, f"34.0 too small for parts (need >= {h_min:.2f})"

    hy_in = hdr_edge
    hy_out = h - hdr_edge
    cy = 0.5 * (hy_in + hy_out)
    ry_in = cy - d_r
    ry_out = cy + d_r
    # Ensure fan bands stay empty of R pads
    assert ry_in - r_hy >= hy_in + fan - 1e-6
    assert ry_out + r_hy <= hy_out - fan + 1e-6

    # P1 / P2 centered on top & bottom edges (not shifted to a side)
    pin_span = 5 * PITCH  # pin1 … pin6
    hx = (w - pin_span) / 2.0

    return M2Layout(
        w=w,
        h=h,
        hdr_edge=hdr_edge,
        hdr_dy=hy_out - hy_in,
        hx=hx,
        hy_in=hy_in,
        hy_out=hy_out,
        ch_xs=ch_xs,
        cy=cy,
        ry_in=ry_in,
        ry_out=ry_out,
        ch_pitch=ch_pitch,
        fan=fan,
    )


# Resolved once at import — floorplan / docs read these.
_M2 = _m2_layout()
M2_W, M2_H = _M2.w, _M2.h
M2_HDR_EDGE = _M2.hdr_edge
M2_HDR_DY = _M2.hdr_dy
M2_CHIP_PITCH = _M2.ch_pitch
PANEL_W = M3_W + 2 * PANEL_MARGIN
PANEL_H = M3_H + 20.0


def uid() -> str:
    return str(uuid.uuid4())


def _pcb_header(title: str, paper: str = "A4") -> list[str]:
    return [
        "(kicad_pcb",
        "\t(version 20241229)",
        '\t(generator "gen_submodules.py")',
        '\t(generator_version "1.0")',
        "\t(general (thickness 1.6) (legacy_teardrops no))",
        f'\t(paper "{paper}")',
        '\t(title_block',
        f'\t\t(title "{title}")',
        '\t\t(comment 1 "JLCPCB 2L HASL; via 0.8/0.4; 2.54 pin header")',
        "\t)",
        "\t(layers",
        '\t\t(0 "F.Cu" signal)',
        '\t\t(2 "B.Cu" signal)',
        '\t\t(9 "F.Adhes" user "F.Adhesive")',
        '\t\t(11 "B.Adhes" user "B.Adhesive")',
        '\t\t(13 "F.Paste" user)',
        '\t\t(15 "B.Paste" user)',
        '\t\t(17 "F.SilkS" user "F.Silkscreen")',
        '\t\t(19 "B.SilkS" user "B.Silkscreen")',
        '\t\t(21 "F.Mask" user)',
        '\t\t(23 "B.Mask" user)',
        '\t\t(25 "Dwgs.User" user "User.Drawings")',
        '\t\t(27 "Cmts.User" user "User.Comments")',
        '\t\t(33 "Edge.Cuts" user)',
        '\t\t(37 "F.CrtYd" user "F.Courtyard")',
        '\t\t(41 "F.Fab" user "F.Fabrication")',
        "\t)",
        "\t(setup",
        "\t\t(pad_to_mask_clearance 0)",
        "\t\t(allow_soldermask_bridges_in_footprints no)",
        "\t\t(pcbplotparams",
        "\t\t\t(layerselection 0x00010fc_ffffffff)",
        "\t\t\t(plot_on_all_layers_selection 0x0000000_00000000)",
        "\t\t\t(disableapertmacros no)",
        "\t\t\t(usegerberextensions no)",
        "\t\t\t(usegerberattributes yes)",
        "\t\t\t(usegerberadvancedattributes yes)",
        "\t\t\t(creategerberjobfile yes)",
        "\t\t\t(svgprecision 4)",
        "\t\t\t(outputformat 1)",
        '\t\t\t(outputdirectory "")',
        "\t\t)",
        "\t)",
        '\t(net 0 "")',
    ]


def _edge_rect(a, x0, y0, x1, y1):
    a("\t(gr_rect")
    a(f"\t\t(start {x0} {y0})")
    a(f"\t\t(end {x1} {y1})")
    a('\t\t(stroke (width 0.1) (type default))')
    a("\t\t(fill none)")
    a('\t\t(layer "Edge.Cuts")')
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")


def _silk(a, txt, x, y, size=1.0):
    a(f'\t(gr_text "{txt}"')
    a(f"\t\t(at {x} {y} 0)")
    a('\t\t(layer "F.SilkS")')
    a(
        f"\t\t(effects (font (size {size} {size}) "
        f"(thickness {max(0.12, size * 0.15)})) (justify left))"
    )
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")


def _silk_line(a, x0, y0, x1, y1, w=0.15):
    a("\t(gr_line")
    a(f"\t\t(start {x0} {y0})")
    a(f"\t\t(end {x1} {y1})")
    a(f"\t\t(stroke (width {w}) (type solid))")
    a('\t\t(layer "F.SilkS")')
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")


def _silk_rect(a, x0, y0, x1, y1, w=0.15):
    a("\t(gr_rect")
    a(f"\t\t(start {x0} {y0})")
    a(f"\t\t(end {x1} {y1})")
    a(f"\t\t(stroke (width {w}) (type solid))")
    a("\t\t(fill none)")
    a('\t\t(layer "F.SilkS")')
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")


def _silk_poly(a, pts, fill=True, w=0.12):
    a("\t(gr_poly")
    a("\t\t(pts")
    for x, y in pts:
        a(f"\t\t\t(xy {x} {y})")
    a("\t\t)")
    a(f"\t\t(stroke (width {w}) (type solid))")
    a(f'\t\t(fill {"solid" if fill else "none"})')
    a('\t\t(layer "F.SilkS")')
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")


def _key_tri(a, cx, cy, tip_left=True, s=1.4):
    if tip_left:
        _silk_poly(a, [(cx, cy), (cx + s, cy - s * 0.7), (cx + s, cy + s * 0.7)])
    else:
        _silk_poly(a, [(cx, cy), (cx - s, cy - s * 0.7), (cx - s, cy + s * 0.7)])


def _seg(a, x1, y1, x2, y2, net, layer="F.Cu", w=0.5):
    if not EMIT_TRACKS:
        return
    a("\t(segment")
    a(f"\t\t(start {x1} {y1})")
    a(f"\t\t(end {x2} {y2})")
    a(f"\t\t(width {w})")
    a(f'\t\t(layer "{layer}")')
    a(f"\t\t(net {net})")
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")


def _via(a, x, y, net):
    if not EMIT_TRACKS:
        return
    a("\t(via")
    a(f"\t\t(at {x} {y})")
    a("\t\t(size 0.8)")
    a("\t\t(drill 0.4)")
    a('\t\t(layers "F.Cu" "B.Cu")')
    a(f"\t\t(net {net})")
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")


def _mh(a, *args, **kwargs):
    """Manhattan H then V (or V then H) on one layer — never diagonal."""
    x1, y1, x2, y2, net = args[:5]
    layer = kwargs.get("layer", "F.Cu")
    w = kwargs.get("w", 0.5)
    if abs(x1 - x2) < 1e-6 or abs(y1 - y2) < 1e-6:
        _seg(a, x1, y1, x2, y2, net, layer=layer, w=w)
        return
    # elbow: prefer H then V
    _seg(a, x1, y1, x2, y1, net, layer=layer, w=w)
    _seg(a, x2, y1, x2, y2, net, layer=layer, w=w)


def _hdr_male(a, ref: str, n: int, labels: list[str], x: float, y: float,
              nets: list[tuple[int, str]], mate: str = "Jxx", rot: int = 0):
    """1xN male pin header 2.54 — plugs into carrier female."""
    span = (n - 1) * PITCH
    a(f'\t(footprint "ESP32_Carrier:PinHeader_1x{n:02d}_Module"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {x} {y} {rot})")
    a(f'\t\t(property "Reference" "{ref}"')
    a(f"\t\t\t(at 0 {-2.6} {rot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a(f'\t\t(property "Value" "1x{n}_to_{mate}"')
    a(f"\t\t\t(at 0 {span + 2.6} {rot})")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 0.6 0.6) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    a("\t\t(fp_rect")
    a("\t\t\t(start -1.9 -1.7)")
    a(f"\t\t\t(end 1.9 {span + 1.7})")
    a('\t\t\t(stroke (width 0.12) (type solid))')
    a("\t\t\t(fill none)")
    a('\t\t\t(layer "F.SilkS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(fp_line (start -1.9 -0.5) (end -2.8 0)")
    a('\t\t\t(stroke (width 0.15) (type solid)) (layer "F.SilkS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    for i, (lab, (ni, nn)) in enumerate(zip(labels, nets)):
        yi = i * PITCH
        a(f'\t\t(fp_text user "{lab}"')
        a(f"\t\t\t(at 2.6 {yi} {rot})")
        a('\t\t\t(layer "F.SilkS")')
        a('\t\t\t(effects (font (size 0.5 0.5) (thickness 0.08)) (justify left))')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t\t(pad "{i + 1}" thru_hole {shape}')
        a(f"\t\t\t(at 0 {yi})")
        a("\t\t\t(size 1.7 1.7)")
        a("\t\t\t(drill 1.0)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(net {ni} "{nn}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")


def _do41(a, ref: str, val: str, x: float, y: float, net_a: tuple[int, str], net_k: tuple[int, str], rot=0):
    a('\t(footprint "ESP32_Carrier:Diode_TVS_DO41"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {x} {y} {rot})")
    a(f'\t\t(property "Reference" "{ref}"')
    a(f"\t\t\t(at 0 -2.6 {rot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a(f'\t\t(property "Value" "{val}"')
    a(f"\t\t\t(at 0 2.6 {rot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.6 0.6) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    a("\t\t(fp_rect")
    a("\t\t\t(start -5.0 -1.8)")
    a("\t\t\t(end 5.0 1.8)")
    a('\t\t\t(stroke (width 0.12) (type solid))')
    a("\t\t\t(fill none)")
    a('\t\t\t(layer "F.SilkS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(fp_line')
    a("\t\t\t(start 2.2 -1.2)")
    a("\t\t\t(end 2.2 1.2)")
    a('\t\t\t(stroke (width 0.15) (type solid))')
    a('\t\t\t(layer "F.SilkS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "1" thru_hole rect')
    a("\t\t\t(at -3.75 0)")
    a("\t\t\t(size 1.7 1.7)")
    a("\t\t\t(drill 0.9)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a(f'\t\t\t(net {net_a[0]} "{net_a[1]}")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" thru_hole circle')
    a("\t\t\t(at 3.75 0)")
    a("\t\t\t(size 1.7 1.7)")
    a("\t\t\t(drill 0.9)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a(f'\t\t\t(net {net_k[0]} "{net_k[1]}")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")


def _ptc(a, ref: str, x: float, y: float, n1: tuple[int, str], n2: tuple[int, str]):
    """Legacy PTC helper — prefer _fuse_5x20 for field-replaceable F1."""
    a('\t(footprint "ESP32_Carrier:Fuse_PTC_Radial_5.1mm"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {x} {y})")
    a(f'\t\t(property "Reference" "{ref}"')
    a('\t\t\t(at 0 -4.2 0)')
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "PTC_3A"')
    a('\t\t\t(at 0 4.2 0)')
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.6 0.6) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    a("\t\t(fp_rect")
    a("\t\t\t(start -3.8 -3.8)")
    a("\t\t\t(end 3.8 3.8)")
    a('\t\t\t(stroke (width 0.12) (type solid))')
    a("\t\t\t(fill none)")
    a('\t\t\t(layer "F.SilkS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "1" thru_hole rect (at -2.55 0) (size 1.8 1.8) (drill 1.0)')
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a(f'\t\t\t(net {n1[0]} "{n1[1]}")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" thru_hole circle (at 2.55 0) (size 1.8 1.8) (drill 1.0)')
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a(f'\t\t\t(net {n2[0]} "{n2[1]}")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")


def write_fuse_holder_5x20() -> Path:
    """Open PCB clips for 5×20 mm cartridge — field-replaceable."""
    half = FUSE_5X20_HALF
    lines: list[str] = []
    a = lines.append
    a('(footprint "Fuse_Holder_5x20_Open"')
    a("\t(version 20260206)")
    a('\t(generator "gen_submodules.py")')
    a('\t(layer "F.Cu")')
    a('\t(descr "Open fuse clips 5x20mm pad span 22.5mm — replaceable cartridge")')
    a('\t(tags "fuse holder 5x20 replaceable")')
    a('\t(property "Reference" "F**"')
    a(f"\t\t(at 0 {-half - 2.5} 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.9 0.9) (thickness 0.12)))")
    a("\t)")
    a('\t(property "Value" "5x20 T3.15A"')
    a(f"\t\t(at 0 {half + 2.5} 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a("\t)")
    a("\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        a(f"\t\t(start {-half - 2.2} -4.0)")
        a(f"\t\t(end {half + 2.2} 4.0)")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")
    a('\t(fp_text user "RUT ONG"')
    a("\t\t(at 0 -5.2 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.55 0.55) (thickness 0.08)))')
    a("\t)")
    a('\t(pad "1" thru_hole rect')
    a(f"\t\t(at {-half} 0)")
    a("\t\t(size 2.2 2.8)")
    a("\t\t(drill 1.2)")
    a('\t\t(layers "*.Cu" "*.Mask")')
    a("\t)")
    a('\t(pad "2" thru_hole circle')
    a(f"\t\t(at {half} 0)")
    a("\t\t(size 2.2 2.8)")
    a("\t\t(drill 1.2)")
    a('\t\t(layers "*.Cu" "*.Mask")')
    a("\t)")
    a(")")
    out = PRETTY / "Fuse_Holder_5x20_Open.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _fuse_5x20(
    a, ref: str, x: float, y: float,
    n1: tuple[int, str], n2: tuple[int, str], rot: int = 0,
):
    """5×20 open holder — pad1=PRE, pad2=+12V; rot=0 pads along X."""
    a('\t(footprint "ESP32_Carrier:Fuse_Holder_5x20_Open"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {x} {y} {rot})")
    a(f'\t\t(property "Reference" "{ref}"')
    a(f"\t\t\t(at 0 {-FUSE_5X20_HALF - 2.8} {rot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "5x20 T3.15A"')
    a(f"\t\t\t(at 0 {FUSE_5X20_HALF + 2.8} {rot})")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.65 0.65) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    a("\t\t(fp_rect")
    a(f"\t\t\t(start {-FUSE_5X20_HALF - 2.2} -4.0)")
    a(f"\t\t\t(end {FUSE_5X20_HALF + 2.2} 4.0)")
    a('\t\t\t(stroke (width 0.12) (type solid))')
    a("\t\t\t(fill none)")
    a('\t\t\t(layer "F.SilkS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(fp_text user "RUT ONG"')
    a(f"\t\t\t(at 0 {-FUSE_5X20_HALF - 4.2} {rot})")
    a('\t\t\t(layer "F.SilkS")')
    a('\t\t\t(effects (font (size 0.5 0.5) (thickness 0.08)))')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "1" thru_hole rect')
    a(f"\t\t\t(at {-FUSE_5X20_HALF} 0)")
    a("\t\t\t(size 2.2 2.8)")
    a("\t\t\t(drill 1.2)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a(f'\t\t\t(net {n1[0]} "{n1[1]}")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" thru_hole circle')
    a(f"\t\t\t(at {FUSE_5X20_HALF} 0)")
    a("\t\t\t(size 2.2 2.8)")
    a("\t\t\t(drill 1.2)")
    a('\t\t\t(layers "*.Cu" "*.Mask")')
    a(f'\t\t\t(net {n2[0]} "{n2[1]}")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")


def write_module_header_fps():
    PRETTY.mkdir(parents=True, exist_ok=True)
    for n in (4, 5, 6, 11):
        name = f"PinHeader_1x{n:02d}_Module"
        lines = [
            f'(footprint "{name}"',
            "\t(version 20260206)",
            '\t(generator "gen_submodules.py")',
            '\t(layer "F.Cu")',
            f'\t(descr "1x{n} male 2.54 to carrier socket")',
            "\t(attr through_hole)",
            ")",
        ]
        (PRETTY / f"{name}.kicad_mod").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_jst_xh_05_byj() -> Path:
    """JST-XH 5P female for 28BYJ-48 on M3 (A B C D +12V)."""
    names = ["A", "B", "C", "D", "+12V"]
    n = len(names)
    span = (n - 1) * XH_PITCH
    lines: list[str] = []
    a = lines.append
    a('(footprint "JST_XH_05_BYJ"')
    a("\t(version 20260206)")
    a('\t(generator "gen_submodules.py")')
    a('\t(layer "F.Cu")')
    a('\t(descr "JST-XH 5P female keyed — 28BYJ A B C D +12V on M3")')
    a('\t(tags "JST XH 28BYJ")')
    a('\t(property "Reference" "J**"')
    a("\t\t(at 0 -2.8 0)")
    a('\t\t(layer "F.SilkS")')
    a("\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a("\t)")
    a('\t(property "Value" "JST_XH_05_BYJ"')
    a(f"\t\t(at 0 {span + 2.8} 0)")
    a('\t\t(layer "F.Fab")')
    a("\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a("\t)")
    a("\t(attr through_hole)")
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        a("\t\t(start -3.2 -2.0)")
        a(f"\t\t(end 3.2 {span + 2.0})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a("\t\t(fill none)")
        a(f'\t\t(layer "{layer}")')
        a("\t)")
    a("\t(fp_line (start -3.2 -0.6) (end -4.2 0)")
    a('\t\t(stroke (width 0.15) (type solid)) (layer "F.SilkS")')
    a("\t)")
    a("\t(fp_line (start -4.2 0) (end -3.2 0.6)")
    a('\t\t(stroke (width 0.15) (type solid)) (layer "F.SilkS")')
    a("\t)")
    a('\t(fp_text user "KEY"')
    a("\t\t(at -5.2 0 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))')
    a("\t)")
    for i, name in enumerate(names):
        y = i * XH_PITCH
        a(f'\t(fp_text user "{name}"')
        a(f"\t\t(at 4.2 {y} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.65 0.65) (thickness 0.1)) (justify left))')
        a("\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t(pad "{i + 1}" thru_hole {shape}')
        a(f"\t\t(at 0 {y})")
        a("\t\t(size 1.6 1.6)")
        a("\t\t(drill 0.9)")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t)")
    a(")")
    out = PRETTY / "JST_XH_05_BYJ.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def gen_m1() -> Path:
    """POWER_PROT: P1 | D3 | F1 5×20 holder (field-replaceable) | D1."""
    lines = _pcb_header("M1 POWER_PROT — D3+F1(5x20)+D1")
    a = lines.append
    nets = {1: "+12V_RAW", 2: "GND", 3: "+12V_PRE", 4: "+12V"}
    for i, n in nets.items():
        a(f'\t(net {i} "{n}")')
    ox, oy, w, h = 10.0, 10.0, M1_W, M1_H
    _edge_rect(a, ox, oy, ox + w, oy + h)
    hx, hy = ox + 3.5, oy + 5.0
    _silk(a, f"M1 {int(M1_W)}x{int(M1_H)}", ox + 1.0, oy + 1.4, 0.75)
    _silk(a, "P1->J30 FUSE RUT", ox + 1.0, oy + 2.7, 0.5)
    _key_tri(a, hx - 2.6, hy, tip_left=True, s=1.2)
    _hdr_male(
        a, "P1", 4,
        ["RAW", "GND", "+12V", "GND"],
        hx, hy,
        [(1, "+12V_RAW"), (2, "GND"), (4, "+12V"), (2, "GND")],
        mate="J30",
    )
    # Align D3 cathode X with F1 pad1 (PRE); fuse horizontal along X
    fx, fy = ox + 22.0, oy + 16.5
    d3x = fx - FUSE_5X20_HALF - 3.75
    d3y = oy + 7.0
    d1x = ox + 30.0
    d1_mid = oy + 8.5
    d1_gnd_y = d1_mid + 3.75
    d1_12_y = d1_mid - 3.75
    y12 = oy + h - 3.5
    yg = y12 + 1.8
    pre_x = fx - FUSE_5X20_HALF
    out_x = fx + FUSE_5X20_HALF
    anode_x = d3x - 3.75
    _do41(a, "D3", "SS54", d3x, d3y, (1, "+12V_RAW"), (3, "+12V_PRE"))
    _fuse_5x20(a, "F1", fx, fy, (3, "+12V_PRE"), (4, "+12V"))
    _do41(a, "D1", "P6KE15A", d1x, d1_mid, (2, "GND"), (4, "+12V"), rot=90)
    # RAW: P1.1 → D3 anode
    _seg(a, hx, hy, anode_x, hy, 1, w=0.9)
    _seg(a, anode_x, hy, anode_x, d3y, 1, w=0.9)
    # PRE: D3 cathode → F1 pad1 (same X)
    _seg(a, pre_x, d3y, pre_x, fy, 3, w=0.9)
    # +12V: F1 pad2 → south rail → P1.3; D1 cathode taps pad2 column
    ap12 = hx + 2.2
    apg = hx - 2.2
    _seg(a, out_x, fy, out_x, y12, 4, w=0.9)
    _seg(a, out_x, y12, ap12, y12, 4, w=0.9)
    _seg(a, ap12, y12, ap12, hy + 2 * PITCH, 4, w=0.9)
    _seg(a, ap12, hy + 2 * PITCH, hx, hy + 2 * PITCH, 4, w=0.9)
    _seg(a, d1x, d1_12_y, out_x, d1_12_y, 4, w=0.7)
    _seg(a, out_x, d1_12_y, out_x, fy, 4, w=0.7)
    # GND west of header; B.Cu under +12V rail (A5)
    _seg(a, hx, hy + PITCH, apg, hy + PITCH, 2, w=0.7)
    _seg(a, apg, hy + PITCH, apg, yg, 2, w=0.7)
    _via(a, apg, yg, 2)
    _seg(a, apg, yg, d1x, yg, 2, layer="B.Cu", w=0.7)
    _seg(a, d1x, yg, d1x, d1_gnd_y, 2, layer="B.Cu", w=0.7)
    _via(a, d1x, d1_gnd_y, 2)
    _via(a, apg, hy + PITCH, 2)
    _silk(a, "RAW>D3>F5x20>+12V", ox + 12.0, oy + h - 1.6, 0.5)
    a(")")
    out = MOD / "m1_power_prot.kicad_pcb"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def gen_m2() -> Path:
    """OPTO4 place-only: 4 route columns; P1 top / P2 bottom; short fan bands."""
    lay = _m2_layout()
    lines = _pcb_header(
        f"M2 OPTO4 — {lay.w:.0f}x{lay.h:.0f} 4-col route (no route yet)"
    )
    a = lines.append
    nets = {
        1: "OPTO_IN1", 2: "OPTO_IN2", 3: "OPTO_IN3", 4: "OPTO_IN4",
        5: "+12V_SNS", 6: "GND",
        7: "OPTO_OUT1", 8: "OPTO_OUT2", 9: "OPTO_OUT3", 10: "OPTO_OUT4",
        11: "+3V3",
        20: "OPTO_A1", 21: "OPTO_A2", 22: "OPTO_A3", 23: "OPTO_A4",
    }
    for i, n in nets.items():
        a(f'\t(net {i} "{n}")')
    ox, oy, w, h = 10.0, 10.0, lay.w, lay.h
    _edge_rect(a, ox, oy, ox + w, oy + h)
    hx = ox + lay.hx
    hy_in = oy + lay.hy_in
    hy_out = oy + lay.hy_out
    _silk(
        a,
        f"M2 {lay.w:.0f}x{lay.h:.0f} 4-col",
        ox + 0.8, oy + h / 2.0 - 1.2, 0.5,
    )
    _silk(a, "FAN empty — no cross", ox + 0.8, oy + h / 2.0 + 0.2, 0.35)
    _key_tri(a, hx - 1.6, hy_in, tip_left=True, s=0.9)
    _key_tri(a, hx - 1.6, hy_out, tip_left=True, s=0.9)
    _hdr_male(
        a, "P1", 6,
        ["IN1", "IN2", "IN3", "IN4", "SNS", "GND"],
        hx, hy_in,
        [
            (1, "OPTO_IN1"), (2, "OPTO_IN2"), (3, "OPTO_IN3"), (4, "OPTO_IN4"),
            (5, "+12V_SNS"), (6, "GND"),
        ],
        mate="J31A", rot=90,
    )
    _hdr_male(
        a, "P2", 5,
        ["OUT1", "OUT2", "OUT3", "OUT4", "3V3"],
        hx, hy_out,
        [
            (7, "OPTO_OUT1"), (8, "OPTO_OUT2"), (9, "OPTO_OUT3"), (10, "OPTO_OUT4"),
            (11, "+3V3"),
        ],
        mate="J31B", rot=90,
    )

    # +12V_SNS arrives at P1 pin5 but was a dead-end single-pad net (nothing
    # on the module consumed it — LED excitation comes back through the
    # field NC-switch loop on OPTO_INx, not locally). Give it a local HF
    # bypass to GND, same "star SNS filter" role as C11 on the carrier —
    # place only, in the free top-right corner clear of the header silk
    # (x<=21.05) and clear of the column1..4 parts (y>=4.95).
    cap_x, cap_y = ox + 23.0, oy + 2.5
    a('\t(footprint "ESP32_Carrier:C_0805_100n"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {cap_x} {cap_y})")
    a('\t\t(property "Reference" "C1"')
    a("\t\t\t(at 0 -1.8 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "100n SNS"')
    a("\t\t\t(at 0 1.8 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.6 0.6) (thickness 0.08)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr smd)")
    a("\t\t(fp_rect (start -1.1 -0.7) (end 1.1 0.7)")
    a('\t\t\t(stroke (width 0.1) (type solid)) (fill none) (layer "F.SilkS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "1" smd roundrect')
    a("\t\t\t(at -0.95 0)")
    a("\t\t\t(size 0.8 1.2)")
    a('\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")')
    a('\t\t\t(roundrect_rratio 0.25)')
    a('\t\t\t(net 5 "+12V_SNS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" smd roundrect')
    a("\t\t\t(at 0.95 0)")
    a("\t\t\t(size 0.8 1.2)")
    a('\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")')
    a('\t\t\t(roundrect_rratio 0.25)')
    a('\t\t\t(net 6 "GND")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")

    cy = oy + lay.cy
    ry_in = oy + lay.ry_in
    ry_out = oy + lay.ry_out
    for i, cx_rel in enumerate(lay.ch_xs):
        cx = ox + cx_rel
        uref = f"U{i + 1}"
        aid, aname = 20 + i, f"OPTO_A{i + 1}"
        iid, iname = i + 1, f"OPTO_IN{i + 1}"
        oid, oname = 7 + i, f"OPTO_OUT{i + 1}"
        _silk(a, f"CH{i + 1}", cx - 1.0, cy, 0.35)
        a('\t(footprint "ESP32_Carrier:PC817_DIP4"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {cx} {cy})")
        a(f'\t\t(property "Reference" "{uref}"')
        a('\t\t\t(at 2.4 0 0)')
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.4 0.4) (thickness 0.06)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(property "Value" "PC817"')
        a('\t\t\t(at -2.4 0 0)')
        a('\t\t\t(layer "F.Fab")')
        a("\t\t\t(effects (font (size 0.3 0.3) (thickness 0.05)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        # A/K west-north toward R2k2; C/E east — OUT jogs east then south in-column
        for num, px, py, ni, nn in (
            ("1", -1.27, -1.27, aid, aname),
            ("2", -1.27, 1.27, 6, "GND"),
            ("3", 1.27, 1.27, 6, "GND"),
            ("4", 1.27, -1.27, oid, oname),
        ):
            a(f'\t\t(pad "{num}" thru_hole circle')
            a(f"\t\t\t(at {px} {py})")
            a("\t\t\t(size 1.4 1.4)")
            a("\t\t\t(drill 0.8)")
            a('\t\t\t(layers "*.Cu" "*.Mask")')
            a(f'\t\t\t(net {ni} "{nn}")')
            a(f'\t\t\t(uuid "{uid()}")')
            a("\t\t)")
        a("\t)")
        # 2k2 @270° on column, north of chip — IN corridor = ch_x.
        # rot=90 put pad1(IN) south (near U) and pad2(A) north (near header) —
        # backwards from the top(header)->bottom(chip) signal flow, forcing
        # the IN and A ratsnest lines to cross past the resistor body. 270°
        # swaps that: pad1(IN) lands north (toward P1), pad2(A) lands south
        # (toward the chip), so both runs stay straight down the column.
        a('\t(footprint "ESP32_Carrier:R_Axial_4k7_BUP"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {cx} {ry_in} 270)")
        a(f'\t\t(property "Reference" "R{i + 1}"')
        a('\t\t\t(at 1.6 0 270)')
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.35 0.35) (thickness 0.05)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(property "Value" "2k2"')
        a('\t\t\t(at -1.6 0 270)')
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.3 0.3) (thickness 0.05)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        a("\t\t(fp_rect (start -4.5 -1.4) (end 4.5 1.4)")
        a('\t\t\t(stroke (width 0.1) (type solid)) (fill none) (layer "F.SilkS")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        # @270° pad1 north=IN (toward P1), pad2 south=A (toward chip)
        a('\t\t(pad "1" thru_hole rect (at -3.75 0) (size 1.3 1.3) (drill 0.8)')
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(net {iid} "{iname}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(pad "2" thru_hole circle (at 3.75 0) (size 1.3 1.3) (drill 0.8)')
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(net {aid} "{aname}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t)")
        # 10k @90° on column, south of chip — OUT corridor = ch_x
        a('\t(footprint "ESP32_Carrier:R_Axial_4k7_BUP"')
        a('\t\t(layer "F.Cu")')
        a(f'\t\t(uuid "{uid()}")')
        a(f"\t\t(at {cx} {ry_out} 90)")
        a(f'\t\t(property "Reference" "R{i + 5}"')
        a('\t\t\t(at 1.6 0 90)')
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.35 0.35) (thickness 0.05)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(property "Value" "10k"')
        a('\t\t\t(at -1.6 0 90)')
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.3 0.3) (thickness 0.05)))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t\t(attr through_hole)")
        a("\t\t(fp_rect (start -4.5 -1.4) (end 4.5 1.4)")
        a('\t\t\t(stroke (width 0.1) (type solid)) (fill none) (layer "F.SilkS")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        # pad1 north=+3V3 (daisy in FAN/B); pad2 south=OUT→P2
        a('\t\t(pad "1" thru_hole rect (at -3.75 0) (size 1.3 1.3) (drill 0.8)')
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a('\t\t\t(net 11 "+3V3")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a('\t\t(pad "2" thru_hole circle (at 3.75 0) (size 1.3 1.3) (drill 0.8)')
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(net {oid} "{oname}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a("\t)")

    _silk(a, "UNROUTED", ox + 0.8, oy + h / 2.0, 0.35)
    a(")")
    out = MOD / "m2_opto4.kicad_pcb"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def gen_m3() -> Path:
    """ULN2003AN + JST-XH 5P 28BYJ — plugs into carrier U5/U6/U7 (1×6).

    P1 left (IN1-4 GND +12V) → ULN DIP → J1 right (A B C D +12V).
    COM=+12V; unused IN5-7 tied to GND.
    """
    lines = _pcb_header("M3 ULN2003 — DIP + JST 28BYJ")
    a = lines.append
    nets = {
        1: "IN1", 2: "IN2", 3: "IN3", 4: "IN4",
        5: "GND", 6: "+12V",
        10: "OUT1", 11: "OUT2", 12: "OUT3", 13: "OUT4",
    }
    for i, n in nets.items():
        a(f'\t(net {i} "{n}")')
    ox, oy, w, h = 10.0, 10.0, M3_W, M3_H
    _edge_rect(a, ox, oy, ox + w, oy + h)
    _silk(a, f"M3 {int(M3_W)}x{int(M3_H)} ULN", ox + 1.0, oy + 1.4, 0.7)
    _silk(a, "P1->U5/6/7", ox + 1.0, oy + 2.7, 0.5)

    # P1 male 1×6 — pin1 top, mates carrier ULN socket
    hx, hy = ox + 3.5, oy + 6.0
    _key_tri(a, hx - 2.6, hy, tip_left=True, s=1.2)
    _hdr_male(
        a, "P1", 6,
        ["IN1", "IN2", "IN3", "IN4", "GND", "+12V"],
        hx, hy,
        [(1, "IN1"), (2, "IN2"), (3, "IN3"), (4, "IN4"), (5, "GND"), (6, "+12V")],
        mate="U5-7",
    )

    # ULN2003AN DIP-16 — center
    ux, uy = ox + 16.0, oy + 14.0
    dip_hx = 3.81
    y0 = -3.5 * PITCH  # pin1/16 relative Y
    a('\t(footprint "ESP32_Carrier:ULN2003AN"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {ux} {uy})")
    a('\t\t(property "Reference" "U1"')
    a("\t\t\t(at 0 -11.5 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "ULN2003AN"')
    a("\t\t\t(at 0 11.5 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    # Left row pins 1-8, right 16-9 — net map for used pins
    left_nets = [
        (1, "IN1"), (2, "IN2"), (3, "IN3"), (4, "IN4"),
        (5, "GND"), (5, "GND"), (5, "GND"), (5, "GND"),  # IN5-7 + GND → GND
    ]
    right_nets = [
        (10, "OUT1"), (11, "OUT2"), (12, "OUT3"), (13, "OUT4"),
        (0, ""), (0, ""), (0, ""), (6, "+12V"),  # OUT5-7 NC, COM=+12V
    ]
    for i, (ni, nn) in enumerate(left_nets):
        num = i + 1
        py = y0 + i * PITCH
        shape = "rect" if i == 0 else "oval"
        a(f'\t\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t\t(at {-dip_hx} {py})")
        a("\t\t\t(size 1.6 1.6)")
        a("\t\t\t(drill 0.9)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        if ni:
            a(f'\t\t\t(net {ni} "{nn}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    for i, (ni, nn) in enumerate(right_nets):
        num = 16 - i
        py = y0 + i * PITCH
        a(f'\t\t(pad "{num}" thru_hole oval')
        a(f"\t\t\t(at {dip_hx} {py})")
        a("\t\t\t(size 1.6 1.6)")
        a("\t\t\t(drill 0.9)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        if ni:
            a(f'\t\t\t(net {ni} "{nn}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")

    # J1 JST-XH 5P — 28BYJ A B C D +12V
    jx, jy = ox + 31.0, oy + 6.5
    byj = [
        (10, "OUT1", "A"), (11, "OUT2", "B"), (12, "OUT3", "C"),
        (13, "OUT4", "D"), (6, "+12V", "+12V"),
    ]
    a('\t(footprint "ESP32_Carrier:JST_XH_05_BYJ"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {jx} {jy})")
    a('\t\t(property "Reference" "J1"')
    a("\t\t\t(at 0 -3.0 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "28BYJ"')
    a(f"\t\t\t(at 0 {(4 * XH_PITCH) + 3.0} 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.7 0.7) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")
    for i, (ni, nn, lab) in enumerate(byj):
        yi = i * XH_PITCH
        a(f'\t\t(fp_text user "{lab}"')
        a(f"\t\t\t(at 4.0 {yi} 0)")
        a('\t\t\t(layer "F.SilkS")')
        a('\t\t\t(effects (font (size 0.55 0.55) (thickness 0.08)) (justify left))')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        shape = "rect" if i == 0 else "circle"
        a(f'\t\t(pad "{i + 1}" thru_hole {shape}')
        a(f"\t\t\t(at 0 {yi})")
        a("\t\t\t(size 1.6 1.6)")
        a("\t\t\t(drill 0.9)")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(net {ni} "{nn}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
    a("\t)")
    _silk(a, "28BYJ", jx - 1.5, jy - 4.0, 0.55)

    # Local HF bypass near COM — @90° so pads N/S (no shared Y rail)
    cx, cy = ox + 24.5, oy + 24.5
    a('\t(footprint "ESP32_Carrier:C_0805_100n"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {cx} {cy} 90)")
    a('\t\t(property "Reference" "C1"')
    a("\t\t\t(at 1.8 0 90)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.6 0.6) (thickness 0.1)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "100n"')
    a("\t\t\t(at -1.8 0 90)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.55 0.55) (thickness 0.08)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr smd)")
    a("\t\t(fp_rect (start -1.1 -0.7) (end 1.1 0.7)")
    a('\t\t\t(stroke (width 0.1) (type solid)) (fill none) (layer "F.SilkS")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    # @90° KiCad: pad1 (-0.95,0)→ world north (cy-0.95); pad2→ south (cy+0.95)
    a('\t\t(pad "1" smd roundrect (at -0.95 0) (size 0.8 1.2)')
    a('\t\t\t(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25)')
    a('\t\t\t(net 6 "+12V")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(pad "2" smd roundrect (at 0.95 0) (size 0.8 1.2)')
    a('\t\t\t(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25)')
    a('\t\t\t(net 5 "GND")')
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t)")

    # --- Manhattan routes ---
    # IN1-4: P1 → west pads of ULN
    for i in range(4):
        ni = i + 1
        py_p = hy + i * PITCH
        py_u = uy + y0 + i * PITCH
        px_u = ux - dip_hx
        jx1 = hx + 2.5 + i * 0.35
        _seg(a, hx, py_p, jx1, py_p, ni, w=0.45)
        _seg(a, jx1, py_p, jx1, py_u, ni, w=0.45)
        _seg(a, jx1, py_u, px_u, py_u, ni, w=0.45)

    # GND: P1.5 → ULN.8 on B (clear of +12V / DIP body)
    py_g = hy + 4 * PITCH
    py_u8 = uy + y0 + 7 * PITCH
    gx = hx + 4.5
    _seg(a, hx, py_g, gx, py_g, 5, w=0.6)
    _via(a, gx, py_g, 5)
    _seg(a, gx, py_g, gx, py_u8, 5, layer="B.Cu", w=0.6)
    _via(a, gx, py_u8, 5)
    _seg(a, gx, py_u8, ux - dip_hx, py_u8, 5, w=0.6)
    # GND → C1 pad2 south (cy+0.95)
    c1_gnd_y = cy + 0.95
    _seg(a, gx, py_u8, gx, c1_gnd_y, 5, layer="B.Cu", w=0.5)
    _via(a, cx, c1_gnd_y, 5)
    _seg(a, cx, c1_gnd_y, cx, cy + 0.95, 5, w=0.4)

    # +12V: P1.6 → B south of DIP → COM / J1 / C1 (avoid ULN pad row)
    py_12 = hy + 5 * PITCH
    py_com = uy + y0 + 7 * PITCH
    px_com = ux + dip_hx
    y_south = oy + h - 2.0  # 36.0
    vx = ox + 22.0
    stub = hx + 2.2
    _seg(a, hx, py_12, stub, py_12, 6, w=0.7)
    _via(a, stub, py_12, 6)
    _seg(a, stub, py_12, stub, y_south, 6, layer="B.Cu", w=0.7)
    _seg(a, stub, y_south, vx, y_south, 6, layer="B.Cu", w=0.7)
    _seg(a, vx, y_south, vx, py_com, 6, layer="B.Cu", w=0.7)
    _via(a, vx, py_com, 6)
    _seg(a, vx, py_com, px_com, py_com, 6, w=0.7)
    # J1.5
    jy5 = jy + 4 * XH_PITCH
    _seg(a, vx, py_com, vx, jy5, 6, layer="B.Cu", w=0.7)
    _via(a, jx - 2.0, jy5, 6)
    _seg(a, vx, jy5, jx - 2.0, jy5, 6, layer="B.Cu", w=0.7)
    _seg(a, jx - 2.0, jy5, jx, jy5, 6, w=0.7)
    # C1 pad1 north (cy-0.95)
    c1_12_y = cy - 0.95
    _seg(a, vx, y_south, cx, y_south, 6, layer="B.Cu", w=0.5)
    _via(a, cx, c1_12_y, 6)
    _seg(a, cx, y_south, cx, c1_12_y, 6, layer="B.Cu", w=0.5)
    _seg(a, cx, c1_12_y, cx, cy - 0.95, 6, w=0.4)

    # OUT1-4: ULN east → J1 (A..D) — B.Cu to avoid crossing +12V
    for i in range(4):
        ni = 10 + i
        py_u = uy + y0 + i * PITCH
        px_u = ux + dip_hx
        jyi = jy + i * XH_PITCH
        stub_o = px_u + 1.8
        _seg(a, px_u, py_u, stub_o, py_u, ni, w=0.5)
        _via(a, stub_o, py_u, ni)
        bx = ox + 27.5 + i * 0.4
        _seg(a, stub_o, py_u, bx, py_u, ni, layer="B.Cu", w=0.5)
        _seg(a, bx, py_u, bx, jyi, ni, layer="B.Cu", w=0.5)
        _via(a, bx, jyi, ni)
        _seg(a, bx, jyi, jx, jyi, ni, w=0.5)

    _silk(a, "COM=+12V IN5-7=GND", ox + 10.0, oy + h - 1.5, 0.45)
    a(")")
    out = MOD / "m3_uln2003.kicad_pcb"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def gen_panel() -> Path:
    lines = _pcb_header(
        f"SUBMODULES PANEL {int(PANEL_W)}x{int(PANEL_H)} - snap M3", "A4"
    )
    a = lines.append
    a('	(net 1 "GND")')
    px0, py0, pw, ph = 20.0, 20.0, PANEL_W, PANEL_H
    _edge_rect(a, px0, py0, px0 + pw, py0 + ph)
    _silk(a, f"PANEL {int(PANEL_W)}x{int(PANEL_H)}: M3", px0 + 2, py0 + 3, 0.85)
    _silk(a, "JLCPCB 2L - SNAP | pin 2.54", px0 + 2, py0 + 5.0, 0.65)
    m3x = px0 + PANEL_MARGIN
    m3y = py0 + 10.0
    _edge_rect(a, m3x, m3y, m3x + M3_W, m3y + M3_H)
    _silk(a, f"M3 {int(M3_W)}x{int(M3_H)}", m3x + 1.5, m3y + 2.5, 0.75)
    _silk(a, "Break tabs after fab", px0 + 2, py0 + ph - 2.5, 0.6)
    a(")")
    out = MOD / "submodules_panel.kicad_pcb"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_readme_modules() -> Path:
    text = f"""# Pluggable sub-modules (JLCPCB)

## Không cắm trực tiếp (cần giắc + board rời)

| Module mua sẵn / linh kiện | Vì sao không cắm flush | Giắc carrier | Board rời |
|----------------------------|------------------------|--------------|-----------|
| ULN2003 driver Shopee | Chỉ Dupont/JST lỏng, không mate PCB | **U5–U7** 1×6 ×3 | **M3** `m3_uln2003` ×3 |

**Hàn trên carrier:** D3+F1+D1; **PC817×4 + 2k2/10k** (không còn M1/M2).

**Cắm được trực tiếp:** ESP32-S3 DevKit (U1), MP1584 (U2), TMC2209 (U3), 74HC595-24IO (J24/J25), TFT (J17+J23).

## Files

| File | Board | Size | Contents |
|------|-------|------|----------|
| `m3_uln2003.kicad_pcb` | M3 | **{M3_W:.0f}×{M3_H:.0f} mm** | ULN2003AN + JST-XH 5P 28BYJ |
| `submodules_panel.kicad_pcb` | Panel | **{PANEL_W:.0f}×{PANEL_H:.0f} mm** | M3 mousebite |

**U5–U7 / M3 P1 (1×6):** 1–4=`INx` · 5=`GND` · 6=`+12V`  
**M3 J1 (XH-5):** 1=`A` 2=`B` 3=`C` 4=`D` 5=`+12V` → 28BYJ-48 **12V**
"""
    out = MOD / "README.md"
    out.write_text(text, encoding="utf-8")
    return out


def write_pro(name: str) -> Path:
    pro = {
        "meta": {"filename": f"{name}.kicad_pro", "version": 3},
        "boards": [],
        "sheets": [],
        "text_variables": {},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "pcbnew": {"last_paths": {"plot": ""}, "page_layout_descr_file": ""},
        "net_settings": {
            "classes": [{
                "name": "Default",
                "clearance": 0.2,
                "track_width": 0.35,
                "via_diameter": 0.8,
                "via_drill": 0.4,
            }],
            "meta": {"version": 3},
        },
    }
    out = MOD / f"{name}.kicad_pro"
    out.write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> None:
    MOD.mkdir(parents=True, exist_ok=True)
    write_module_header_fps()
    write_jst_xh_05_byj()
    outs = [
        gen_m3(),
        gen_panel(),
        write_readme_modules(),
        write_pro("m3_uln2003"),
        write_pro("submodules_panel"),
    ]
    for obsolete in (
        "m1_power_prot.kicad_pcb",
        "m1_power_prot.kicad_pro",
        "m2_opto4.kicad_pcb",
        "m2_opto4.kicad_pro",
        "~m1_power_prot.kicad_pcb.lck",
        "~m1_power_prot.kicad_pro.lck",
        "~m2_opto4.kicad_pcb.lck",
        "~m2_opto4.kicad_pro.lck",
    ):
        p = MOD / obsolete
        if p.is_file():
            p.unlink()
            print("Removed", p)
    print("Wrote sub-modules:")
    for p in outs:
        print(" ", p)


if __name__ == "__main__":
    main()
