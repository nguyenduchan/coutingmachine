"""Knob LO→HI slider travel: cover-small at rest, no blocking jam. freecadcmd."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from l_flap_divert import (  # noqa: E402
    OPEN_DRIVE_HI,
    OPEN_DRIVE_LO,
    aperture_widths,
    clamp_open,
    common_volume,
    flap_state_for_open,
    knob_angle_deg,
    make_divert_frame,
    make_gap_slider,
    make_geneva_driver,
    make_malta_cross,
    malta_angle_for_open,
    slider_x_left,
    verify_knob_slider_drive,
)

OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    print("=== Default cover small + max large ===")
    aw0 = aperture_widths(OPEN_DRIVE_LO)
    aw1 = aperture_widths(OPEN_DRIVE_HI)
    print("open0", aw0)
    print("open_max", aw1)

    print("=== Gear couple ===")
    gear = verify_knob_slider_drive(n_steps=6)
    print(
        "gear_pass=%s couple=%s p=%.3f deg_per_mm=%.1f"
        % (gear["pass"], gear["couple_ok"], gear["circular_pitch_mm"], gear["knob_deg_per_1mm"])
    )

    print("=== Sweep collisions (knob) ===")
    frame = make_divert_frame()
    n = 10
    max_ill = 0.0
    jam = 0
    rows = []
    for i in range(n):
        t = i / max(1, n - 1)
        op = clamp_open(OPEN_DRIVE_LO + t * (OPEN_DRIVE_HI - OPEN_DRIVE_LO))
        slider = make_gap_slider(op)
        malta = make_malta_cross(malta_angle_for_open(op))
        driver = make_geneva_driver(op)
        ov_sf = common_volume(slider, frame)
        ov_sm = common_volume(slider, malta)
        ov_sd = common_volume(slider, driver)
        ill = 0.0
        if ov_sf > 30.0:
            ill = max(ill, ov_sf)
        if ov_sm > 8.0:
            ill = max(ill, ov_sm)
        if ov_sd > 8.0:
            ill = max(ill, ov_sd)
        max_ill = max(max_ill, ill)
        if ill >= 30.0:
            jam += 1
        aw = aperture_widths(op)
        rows.append(
            {
                "open_mm": round(op, 3),
                "knob_deg": round(knob_angle_deg(op), 2),
                "slider_x_left": round(slider_x_left(op), 3),
                "state": flap_state_for_open(op),
                "small_mm": aw["small_mm"],
                "large_mm": aw["large_mm"],
                "ov_slider_frame": round(ov_sf, 3),
                "ov_slider_malta": round(ov_sm, 3),
                "ov_slider_driver": round(ov_sd, 3),
            }
        )
        print(
            "  open=%5.2f knob=%6.1f small=%4.1f large=%4.1f ov_f=%.1f ov_m=%.1f"
            % (op, knob_angle_deg(op), aw["small_mm"], aw["large_mm"], ov_sf, ov_sm)
        )

    travel = slider_x_left(OPEN_DRIVE_HI) - slider_x_left(OPEN_DRIVE_LO)
    mono = all(
        rows[i]["slider_x_left"] <= rows[i + 1]["slider_x_left"] + 1e-6
        for i in range(len(rows) - 1)
    )
    cover0 = aw0["small_mm"] < 0.15
    large_full = aw1["large_mm"] >= 11.5
    passed = bool(
        cover0 and large_full and travel >= 17.45 and jam == 0 and max_ill < 30.0 and gear["pass"] and mono
    )
    rep = {
        "pass": passed,
        "cover_small_at_rest": cover0,
        "small_mm_at_0": aw0["small_mm"],
        "large_mm_at_max": aw1["large_mm"],
        "large_full_at_max": large_full,
        "slider_travel_mm": round(travel, 3),
        "knob_deg_span": round(knob_angle_deg(OPEN_DRIVE_HI) - knob_angle_deg(OPEN_DRIVE_LO), 2),
        "monotonic_slider": mono,
        "jam_hits": jam,
        "max_illegal_mm3": round(max_ill, 3),
        "gear_pass": gear["pass"],
        "couple_ok": gear["couple_ok"],
        "samples": rows,
        "png": [
            "l_flap_topview_open0_cover_small.png",
            "l_flap_topview_open_max.png",
        ],
    }
    path = OUT / "l_flap_slider_knob_travel_verify.json"
    path.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(
        "RESULT pass=%s cover0=%s large_max=%s travel=%.2f jam=%s"
        % (passed, cover0, large_full, travel, jam)
    )
    print("Wrote", path)
    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
