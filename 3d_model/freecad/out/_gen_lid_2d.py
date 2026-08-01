"""Lid 2D schematic — geometry from box_settings (edit that file to change sizes)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from box_settings import (  # noqa: E402
    LID,
    lid_arc_corner_params,
    lid_deck_s_rim_xy,
    lid_north_cap_xy,
    lid_plan_full,
    lid_rim_pocket_xy,
    lid_rim_seal_angles,
)

plan = lid_plan_full()
R_DISC = plan["r_disc"]
R_HUB = plan["r_hub"]
R_MOUTH = plan["r_mouth"]
W_IN, W_OUT = plan["w_in"], plan["w_out"]
N_IN, N_OUT = plan["n_in"], plan["n_out"]
E_IN, E_OUT = plan["e_in"], plan["e_out"]
Y_MOUTH, Y_EXIT = plan["y_mouth"], plan["y_exit"]
arc_in, arc_out = plan["arc_in"], plan["arc_out"]
C_IN, C_OUT = plan.get("c_in"), plan.get("c_out")
WIDTH_BAR = list(plan["width_bar"]) + [plan["width_bar"][0]]
HEIGHT_BAR = list(plan["height_bar"]) + [plan["height_bar"][0]]
_B0, _B1, _B2, _B3 = plan["width_bar"]
_H0, _H1, _H2, _H3 = plan["height_bar"]
BOX = list(plan["box"])
BOX_XL, BOX_XR = plan["box_xl"], plan["box_xr"]
BOX_YB, BOX_YT = plan["box_yb"], plan["box_yt"]
SIDE = plan["square_side"]

chute_w = float(LID["plan"]["chute"]["width"])
wide_w = float(LID["plan"]["wide_mouth"]["width"])
fc = LID["plan"]["funnel_chamber"]
ROOF_FUNNEL = bool(fc.get("roofed_by_lid_top", True))
ROOF_CHUTE = bool(fc.get("roof_chute", False))
ROOF_RIM = bool(fc.get("roof_rim_pocket", True))
ROOF_CORNER = bool(fc.get("roof_arc_corner", True))
BOTTOM_EXTRA = float(LID["plan"]["frame"]["bottom_extra"])

S = 1.0
cx, cy = 180, 175
vb_w, vb_h = 360, 360


def tx(x, y):
    return (cx + x * S, cy - y * S)


def line(p, q, stroke, sw=1.2, dash=None):
    x1, y1 = tx(*p)
    x2, y2 = tx(*q)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def circle(c, r, stroke, sw=1.2, fill="none", dash=None):
    x, y = tx(*c)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r*S:.2f}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}"{d}/>'
    )


def poly(pts, stroke, sw=2.0, fill="none", opacity=1.0):
    pp = " ".join(f"{tx(x,y)[0]:.2f},{tx(x,y)[1]:.2f}" for x, y in pts)
    return (
        f'<polyline points="{pp}" fill="{fill}" fill-opacity="{opacity}" '
        f'stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>'
    )


def text(x, y, s, size=11, anchor="middle", fill="#222"):
    px, py = tx(x, y)
    return (
        f'<text x="{px:.2f}" y="{py:.2f}" font-size="{size}" font-family="Segoe UI,Arial" '
        f'fill="{fill}" text-anchor="{anchor}">{s}</text>'
    )


def text_px(px, py, s, size=11, anchor="middle", fill="#222", weight="normal"):
    return (
        f'<text x="{px:.2f}" y="{py:.2f}" font-size="{size}" font-family="Segoe UI,Arial" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{s}</text>'
    )


funnel_chamber = [W_IN] + arc_in + [N_IN, N_OUT] + list(reversed(arc_out)) + [W_OUT]
channel = [W_IN] + arc_in + [N_IN, E_IN, E_OUT, N_OUT] + list(reversed(arc_out)) + [W_OUT]
chute = [N_IN, E_IN, E_OUT, N_OUT, N_IN]
rim_pocket = lid_rim_pocket_xy(plan)
deck_s_rim = lid_deck_s_rim_xy(plan)
arc_corner = lid_north_cap_xy(plan)  # AABB of tiny corner pocket
_cx, _cy, _sp, _or = lid_arc_corner_params(plan)

roof_note = (
    f"Vuong {SIDE:.0f}mm | day kin duoi Rim+Deck_S_Rim | mang HO duoi"
)

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{vb_w*2}" height="{vb_h*2}" viewBox="0 0 {vb_w} {vb_h}">',
    '<rect width="100%" height="100%" fill="#f7f5f0"/>',
    text_px(cx, 14, "Nap - hinh vuong kin (nhin tu tren)", 14, weight="600"),
    text_px(cx, 30, roof_note, 9, fill="#455a64"),
    # closed square fill
    poly(BOX, "#263238", 2.4, fill="#cfd8dc", opacity=0.35),
    circle((0, 0), R_DISC, "#888", 1.5, fill="#fff"),
    # bottom open over disc (dashed ring cue)
    circle((0, 0), R_DISC, "#1565c0", 1.2, dash="5 3"),
    text(0, -R_DISC * 0.55, "mat duoi HO (dia+mang)", 8, fill="#1565c0"),
    circle((0, 0), R_HUB, "#333", 1.2, fill="#2a2a2a"),
    circle((0, 0), R_MOUTH, "#999", 0.6, dash="3 2"),
    line((-R_DISC, -R_DISC), (R_DISC, -R_DISC), "#999", 0.7, dash="4 3"),
    line((BOX_XL, BOX_YB), (BOX_XR, BOX_YB), "#1565c0", 2.0),
]
if ROOF_RIM:
    parts.append(poly(rim_pocket + [rim_pocket[0]], "#607d8b", 0.5, fill="#90a4ae", opacity=0.65))
    parts.append(text(55, 55, "Rim_Pocket", 8, fill="#455a64"))
parts.append(text(-95, -20, "Out_W", 8, fill="#455a64"))
parts.append(text(-75, -85, "SW_Chute", 7, fill="#455a64"))
parts.append(text(-75, -72, "Above End", 6, fill="#607d8b"))
parts.append(text(-75, -98, "Below End", 6, fill="#607d8b"))
parts.append(text(-30, -85, "SW_Rest", 7, fill="#455a64"))
parts.append(text(70, 70, "Out_NE", 8, fill="#455a64"))
if ROOF_FUNNEL:
    parts.append(poly(funnel_chamber, "#546e7a", 0.6, fill="#90a4ae", opacity=0.55))
    parts.append(text(20, 15, "Funnel_Roof", 8, fill="#455a64"))
else:
    parts.append(poly(channel, "#1a6b8a", 0.8, fill="#3aa7d0", opacity=0.28))
if ROOF_CHUTE:
    parts.append(poly(chute, "#546e7a", 0.6, fill="#78909c", opacity=0.5))
    parts.append(text(-55, -35, "Chute_Roof", 8, fill="#455a64"))
else:
    parts.append(poly(chute, "#ef9a9a", 0.5, fill="#ffcdd2", opacity=0.35))
    parts.append(text(-55, -35, "mang HO tren", 8, fill="#b71c1c"))
parts.append(text(-40, -40, "Deck_S_Rim", 7, fill="#455a64"))
parts.append(text(-25, -40, "Hub_L", 7, fill="#455a64"))
parts.append(text(40, -40, "Hub_R", 7, fill="#455a64"))
parts.append(text(0, 50, "Deck_N", 7, fill="#455a64"))

# Rim seal wall outside disc (2mm) — wide mouth → chute via north
_rs = LID["plan"]["funnel_chamber"].get("rim_seal_wall", {})
if bool(_rs.get("enabled", True)):
    import math

    _d0, _d1, _ri, _ro = lid_rim_seal_angles(plan)
    _steps = max(24, int(round((_d1 - _d0) % 360)))
    _rim_outer = [
        (
            _ro * math.cos(math.radians(_d0 + (_d1 - _d0) * i / _steps)),
            _ro * math.sin(math.radians(_d0 + (_d1 - _d0) * i / _steps)),
        )
        for i in range(_steps + 1)
    ]
    _rim_inner = [
        (
            _ri * math.cos(math.radians(_d1 - (_d1 - _d0) * i / _steps)),
            _ri * math.sin(math.radians(_d1 - (_d1 - _d0) * i / _steps)),
        )
        for i in range(_steps + 1)
    ]
    parts.append(
        poly(
            _rim_outer + _rim_inner + [_rim_outer[0]],
            "#2e7d32",
            1.2,
            fill="#66bb6a",
            opacity=0.55,
        )
    )
    parts.append(text(20, -95, "Rim_Arc 2mm (cung duoi)", 8, fill="#1b5e20"))

parts += [
    poly(arc_out, "#0b5f7a", 2.5),
    poly(arc_in, "#0b5f7a", 2.5),
    line(N_IN, N_OUT, "#e65100", 3.5),
    line(N_IN, E_IN, "#b71c1c", 2.6),
    line(N_OUT, E_OUT, "#b71c1c", 2.6),
    line(E_IN, E_OUT, "#b71c1c", 2.0),
    poly(WIDTH_BAR, "#6a1b9a", 2.0, fill="#9c27b0", opacity=0.45),
    line(_B0, _B1, "#4a148c", 2.8),
    line(_B3, _B2, "#4a148c", 2.8),
    line(_B1, _B2, "#7b1fa2", 2.4),
    line(_B0, _B3, "#7b1fa2", 2.4),
    poly(HEIGHT_BAR, "#ef6c00", 2.0, fill="#ff9800", opacity=0.7),
    line(_H0, _H1, "#e65100", 2.4),
    line(_H2, _H3, "#e65100", 2.4),
    line(_H1, _H2, "#f57c00", 2.2),
    line(_H0, _H3, "#f57c00", 2.2),
    line(W_IN, W_OUT, "#c45c26", 2.6),
    # closed square outline
    line((BOX_XR, BOX_YB), (BOX_XR, BOX_YT), "#263238", 2.6),
    line((BOX_XR, BOX_YT), (BOX_XL, BOX_YT), "#263238", 2.6),
    line((BOX_XL, BOX_YT), (BOX_XL, BOX_YB), "#263238", 2.6),
    line((BOX_XL, BOX_YB), (BOX_XR, BOX_YB), "#1565c0", 2.8),
]
if C_OUT is not None:
    parts += [
        circle(C_OUT, 2.0, "#6a1b9a", 1, fill="#6a1b9a"),
        circle(C_IN, 2.0, "#6a1b9a", 1, fill="#6a1b9a"),
    ]
parts += [
    line((R_DISC, 0), (R_DISC + 12, 0), "#222", 1.3),
    text(R_DISC + 18, 0, "3h", 11),
    text(-R_DISC - 8, 16, "9h", 11),
    text(0, R_DISC + 14, "12h", 10),
    text(0, BOX_YB - 12, f"canh duoi +{BOTTOM_EXTRA:.0f}mm", 9, fill="#1565c0"),
    text(52, 12, f"cua rong {wide_w/10:.1f} cm", 9, fill="#c45c26"),
    text(-R_MOUTH, Y_MOUTH + 22, "chinh CAO", 9, fill="#e65100"),
    text(
        (_B1[0] + _B2[0]) / 2 + 8,
        (_B1[1] + _B2[1]) / 2 + 8,
        "chinh RONG",
        9,
        fill="#4a148c",
    ),
    text(-R_MOUTH - 28, (Y_MOUTH + Y_EXIT) / 2, "mang", 9, fill="#b71c1c"),
    text(0, -R_DISC - 8, "dia O20 cm", 9, fill="#555"),
    text(BOX_XR - 8, BOX_YT - 8, f"{SIDE:.0f}", 9, fill="#263238"),
    text_px(
        10,
        vb_h - 28,
        "frame.closed_square | bottom_extra trong box_settings.py",
        8,
        "start",
        "#444",
    ),
    text_px(
        10,
        vb_h - 12,
        f"square [{BOX_XL:.0f},{BOX_YB:.0f}]-[{BOX_XR:.0f},{BOX_YT:.0f}] side={SIDE:.0f}mm",
        8,
        "start",
        "#444",
    ),
    "</svg>",
]

out = Path(__file__).resolve().parent / "lid_aperture_2d.svg"
out.write_text("\n".join(parts), encoding="utf-8")
print("wrote", out)
print(f"square {SIDE:.0f}mm bottom_extra={BOTTOM_EXTRA:.0f} yb={BOX_YB:.0f}")
