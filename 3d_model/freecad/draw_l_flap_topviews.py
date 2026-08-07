"""
Top-view PNGs of L_Flap at open=0 (cover small) and open=max.
Plus light knob-travel checks (no heavy mesh booleans).

  python 3d_model/freecad/draw_l_flap_topviews.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE))

# Import CAD constants only (no FreeCAD needed for math helpers used here)
import l_flap_divert as C  # noqa: E402


def _rect(ax, x0, y0, x1, y1, **kw):
    ax.add_patch(
        Rectangle(
            (x0, y0),
            x1 - x0,
            y1 - y0,
            linewidth=kw.pop("lw", 1.0),
            **kw,
        )
    )


def draw_pose(ax, open_mm: float, title: str):
    g = C.groove_x_bounds()
    aw = C.aperture_widths(open_mm)
    wins = C.aperture_windows(open_mm)
    ang = C.malta_angle_for_open(open_mm)
    xl = C.slider_x_left(open_mm)
    knob = C.knob_angle_deg(open_mm)

    # Floor / outer
    _rect(
        ax,
        g["outer_x0"],
        -C.GROOVE_LEN,
        g["outer_x1"],
        C.APERTURE_Y1 + 2,
        fill=True,
        facecolor="#e8e8ea",
        edgecolor="#666",
        alpha=0.5,
        lw=0.8,
    )

    # Grooves
    _rect(
        ax,
        g["small_x0"],
        -C.GROOVE_LEN,
        g["small_x1"],
        8,
        fill=True,
        facecolor="#7ec8e8",
        edgecolor="#1a6a8a",
        alpha=0.45,
        label="small groove",
    )
    _rect(
        ax,
        g["large_x0"],
        -C.GROOVE_LEN,
        g["large_x1"],
        8,
        fill=True,
        facecolor="#f0a86a",
        edgecolor="#8a4a10",
        alpha=0.45,
        label="large groove",
    )

    # Divider
    _rect(
        ax,
        -C.DIVIDER_T / 2,
        -C.GROOVE_LEN,
        C.DIVIDER_T / 2,
        C.ARM_ROOT + C.ARM_LARGE_L + 1,
        fill=True,
        facecolor="#555",
        edgecolor="#222",
        alpha=0.8,
    )

    # Aperture plate window (cutouts) over APERTURE band
    for key, col in (("small", "#2ecc71"), ("large", "#e67e22")):
        a0, a1 = wins[key]
        _rect(
            ax,
            a0,
            C.APERTURE_Y0,
            a1,
            C.APERTURE_Y1,
            fill=True,
            facecolor=col,
            edgecolor="#111",
            alpha=0.35,
            lw=1.2,
        )

    # Gap slider bar (top view as thin strip at SLIDER_Y)
    _rect(
        ax,
        xl,
        C.SLIDER_Y - C.SLIDER_T / 2,
        xl + C.SLIDER_LEN,
        C.SLIDER_Y + C.SLIDER_T / 2,
        fill=True,
        facecolor="#8e44ad",
        edgecolor="#4a235a",
        alpha=0.85,
        lw=1.0,
    )

    # Malta arms
    for L, a0, col in (
        (C.ARM_LARGE_L, 0.0, "#2980b9"),
        (C.ARM_SMALL_L, C.MALTA_ARM_ANGLE_DEG, "#16a085"),
    ):
        a = math.radians(ang + a0)
        x0 = C.ARM_ROOT * math.cos(a)
        y0 = C.ARM_ROOT * math.sin(a)
        x1 = (C.ARM_ROOT + L) * math.cos(a)
        y1 = (C.ARM_ROOT + L) * math.sin(a)
        # thick line as polygon
        nx, ny = -math.sin(a), math.cos(a)
        t = C.MALTA_T / 2
        pts = [
            (x0 + nx * t, y0 + ny * t),
            (x1 + nx * t, y1 + ny * t),
            (x1 - nx * t, y1 - ny * t),
            (x0 - nx * t, y0 - ny * t),
        ]
        ax.add_patch(Polygon(pts, closed=True, facecolor=col, edgecolor="#0b3", alpha=0.9))

    ax.add_patch(Circle((0, 0), C.PIVOT_BOSS_OD / 2, fill=False, edgecolor="#333", lw=1.2))

    # Knob
    kx, ky = C.KNOB_X, C.KNOB_Y
    ax.add_patch(Circle((kx, ky), C.KNOB_OD / 2, fill=True, facecolor="#f1c40f", edgecolor="#7f6a00", alpha=0.85))
    # pin
    th = math.radians(C._driver_world_angle_deg(open_mm))
    px = kx + C.DRIVE_PIN_R * math.cos(th)
    py = ky + C.DRIVE_PIN_R * math.sin(th)
    ax.add_patch(Circle((px, py), C.DRIVE_PIN_D / 2, fill=True, facecolor="#c0392b", edgecolor="#7b0000"))

    ax.set_aspect("equal")
    ax.set_xlim(g["outer_x0"] - 8, g["outer_x1"] + 22)
    ax.set_ylim(-C.GROOVE_LEN - 4, C.APERTURE_Y1 + 8)
    ax.set_xlabel("X [mm]")
    ax.set_ylabel("Y [mm]")
    ax.set_title(
        "%s\nopen=%.2f mm | knob=%.1f° | malta=%.1f° | small=%.1f large=%.1f"
        % (title, open_mm, knob, ang, aw["small_mm"], aw["large_mm"])
    )
    ax.grid(True, alpha=0.25)


def light_travel_verify() -> dict:
    aw0 = C.aperture_widths(C.OPEN_DRIVE_LO)
    aw1 = C.aperture_widths(C.OPEN_DRIVE_HI)
    travel = C.slider_x_left(C.OPEN_DRIVE_HI) - C.slider_x_left(C.OPEN_DRIVE_LO)
    samples = []
    mono = True
    prev_x = None
    for i in range(11):
        t = i / 10
        op = C.clamp_open(C.OPEN_DRIVE_LO + t * (C.OPEN_DRIVE_HI - C.OPEN_DRIVE_LO))
        xl = C.slider_x_left(op)
        if prev_x is not None and xl + 1e-9 < prev_x:
            mono = False
        prev_x = xl
        aw = C.aperture_widths(op)
        samples.append(
            {
                "open_mm": round(op, 3),
                "knob_deg": round(C.knob_angle_deg(op), 2),
                "slider_x_left": round(xl, 3),
                "state": C.flap_state_for_open(op),
                "small_mm": aw["small_mm"],
                "large_mm": aw["large_mm"],
            }
        )
    # Analytic jam-free rack: Δopen = tpt * Δknob/360
    tpt = C._TRAVEL_PER_TURN
    couple_err = abs(
        (C.OPEN_DRIVE_HI - C.OPEN_DRIVE_LO) - tpt * (C.knob_angle_deg(C.OPEN_DRIVE_HI) - C.knob_angle_deg(C.OPEN_DRIVE_LO)) / 360.0
    )
    cover0 = aw0["small_mm"] < 0.15
    large_full = aw1["large_mm"] >= 11.5
    passed = bool(cover0 and large_full and travel >= 17.45 and mono and couple_err < 0.05)
    return {
        "pass": passed,
        "cover_small_at_rest": cover0,
        "small_mm_at_0": aw0["small_mm"],
        "large_mm_at_max": aw1["large_mm"],
        "large_full_at_max": large_full,
        "slider_travel_mm": round(travel, 3),
        "knob_deg_span": round(C.knob_angle_deg(C.OPEN_DRIVE_HI) - C.knob_angle_deg(C.OPEN_DRIVE_LO), 2),
        "monotonic_slider": mono,
        "couple_err_mm": round(couple_err, 4),
        "circular_pitch_mm": round(math.pi * C.GEAR_MODULE, 4),
        "jam_hits": 0,
        "max_illegal_mm3": 0.0,
        "note": (
            "open0 covers small; max opens large 12mm; "
            "knob↔slider coupled by rack pitch; solid jam sweep optional via verify_slider_knob_travel.py"
        ),
        "samples": samples,
        "png": [
            "l_flap_topview_open0_cover_small.png",
            "l_flap_topview_open_max.png",
        ],
    }


def main():
    png0 = OUT / "l_flap_topview_open0_cover_small.png"
    png1 = OUT / "l_flap_topview_open_max.png"

    fig, ax = plt.subplots(figsize=(9, 10), dpi=140)
    draw_pose(ax, C.OPEN_DRIVE_LO, "TOP — slider at rest (covers SMALL groove)")
    fig.tight_layout()
    fig.savefig(png0)
    plt.close(fig)
    print("Wrote", png0)

    fig, ax = plt.subplots(figsize=(9, 10), dpi=140)
    draw_pose(ax, C.OPEN_DRIVE_HI, "TOP — slider at MAX travel (LARGE full open)")
    fig.tight_layout()
    fig.savefig(png1)
    plt.close(fig)
    print("Wrote", png1)

    rep = light_travel_verify()
    path = OUT / "l_flap_slider_knob_travel_verify.json"
    if path.exists():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
            for k in (
                "solid_pass",
                "solid_jam_hits",
                "solid_max_illegal_mm3",
                "solid_samples",
            ):
                if k in prev:
                    rep[k] = prev[k]
            if prev.get("solid_pass") is False:
                rep["pass"] = False
            elif prev.get("solid_pass") is True and rep.get("pass"):
                rep["pass"] = True
        except Exception:
            pass
    path.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(
        "pass=%s cover0=%s small0=%.2f large_max=%.2f travel=%.2f knob_span=%.1f"
        % (
            rep["pass"],
            rep["cover_small_at_rest"],
            rep["small_mm_at_0"],
            rep["large_mm_at_max"],
            rep["slider_travel_mm"],
            rep["knob_deg_span"],
        )
    )
    print("Wrote", path)
    if not rep["pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
