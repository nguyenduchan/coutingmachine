# -*- coding: utf-8 -*-
"""
Mathematical mesh check — spur rack & pinion (SolidWorks-style).

References (same relations as SW Toolbox / AGMA standard full-depth 20°):
  circular pitch p = π · m
  pitch diameter d = m · z
  no-slip: rack travel = r · θ = (π m z) · turns
  successive teeth: Δθ = 2π/z ↔ rack step = p
  contact ratio ε_α ≥ 1 for continuous drive without loss of contact
  backlash / center distance for no jam

Run:
  python 3d_model/freecad/out/rack_pinion_math_check.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

# --- Design (match box_settings height_bar.drive.rack) ---
M = 2.0  # module [mm]
Z = 18  # pinion teeth (>=17 no undercut at 20°)
ALPHA_DEG = 20.0  # pressure angle (SolidWorks default)
TOOTH_CLEAR = 0.40  # circumferential thinning [mm] (print)
CENTER_BACKLASH = 0.25  # extra pitch-line offset [mm] (print)
STROKE = 20.0

OUT = Path(__file__).resolve().parent / "rack_pinion_math_check.json"


def sw_spur_rack_math(
    m: float,
    z: int,
    alpha_deg: float,
    tooth_clear: float,
    center_backlash: float,
) -> dict:
    alpha = math.radians(alpha_deg)
    # --- Basic (SolidWorks / ISO full-depth) ---
    p = math.pi * m  # circular pitch
    d = m * z  # pitch diameter
    r = 0.5 * d
    ha = 1.0 * m  # addendum
    hf = 1.25 * m  # dedendum
    c_clearance = 0.25 * m  # bottom clearance
    da = m * (z + 2)  # tip diameter
    df = m * (z - 2.5)  # root diameter
    ra, rf = 0.5 * da, 0.5 * df
    db = d * math.cos(alpha)  # base diameter
    rb = 0.5 * db

    # Standard zero-backlash tooth thickness at pitch circle
    s_std = 0.5 * p  # π m / 2
    e_std = 0.5 * p  # space = tooth for rack/pinion standard

    # Our printable thinning on both sides ≈ tooth_clear total on thickness
    s_pin = max(0.1, s_std - 0.5 * tooth_clear)
    s_rack = max(0.1, s_std - 0.5 * tooth_clear)
    e_pin = p - s_pin
    e_rack = p - s_rack

    # Pitch line of rack: tangent to pitch circle + center backlash (extra CD)
    # Standard CD for rack = r; we use r + center_backlash
    pitch_line_offset = r + center_backlash

    # --- No-slip kinematics (pure rolling at pitch point) ---
    # Arc on pitch circle = rack translation
    travel_per_rad = r  # s = r θ
    travel_per_rev = 2.0 * math.pi * r  # = π d = π m z
    travel_per_tooth = p  # one tooth ↔ one circular pitch on rack
    angle_per_tooth_deg = 360.0 / z

    # Successive tooth pairing: after Δθ = 2π/z, next pinion tooth arrives
    # at the pitch point while rack has advanced exactly p — no slip.
    phase_match = abs(travel_per_tooth - (travel_per_rev / z)) < 1e-9

    # --- Contact ratio (rack–pinion), SW/AGMA style ---
    # ε_α = (sqrt(ra^2 - rb^2) + ha/sin(α) - r sin(α)) / (π m cos(α))
    # (standard rack addendum ha, pitch radius r)
    numer = math.sqrt(max(0.0, ra * ra - rb * rb)) + (ha / math.sin(alpha)) - r * math.sin(
        alpha
    )
    denom = math.pi * m * math.cos(alpha)
    epsilon = numer / denom if denom > 1e-12 else 0.0

    # Center-distance backlash effect: increasing CD reduces effective contact
    # Approximate length-of-path reduction ≈ center_backlash * sin(α)
    numer_bl = numer - center_backlash * math.sin(alpha)
    epsilon_with_cd = numer_bl / denom if denom > 1e-12 else 0.0

    # --- Interference / undercut (pinion vs rack) ---
    # Min teeth without undercut for standard rack, α=20°: z_min ≈ 2 / sin²(α) ≈ 17
    z_min_no_undercut = 2.0 / (math.sin(alpha) ** 2)
    undercut_risk = z < z_min_no_undercut

    # Tip of pinion vs rack root: working depth
    working_depth = 2.0 * ha  # standard
    # With center backlash, radial engagement depth decreases
    radial_engagement = working_depth - center_backlash
    # Tip-to-tip mesh depth (how much tips overlap radially)
    # pinion tip at ra; rack tip at pitch_line_offset - ha + ... 
    # rack tip distance from pinion axis = pitch_line_offset - ha + tip_setback
    # tip_setback from tooth_clear on rack tip ≈ tooth_clear (our CAD)
    rack_tip_from_axis = pitch_line_offset - ha + tooth_clear
    tip_overlap = ra - rack_tip_from_axis  # >0 means tips share radial band

    # Circumferential jam check at pitch line:
    # pinion tooth must fit in rack space: s_pin < e_rack
    # rack tooth must fit in pinion space: s_rack < e_pin
    fit_pin_in_rack = s_pin < e_rack - 1e-9
    fit_rack_in_pin = s_rack < e_pin - 1e-9
    circumferential_clearance = min(e_rack - s_pin, e_pin - s_rack)

    # Path of contact continuous if ε >= 1
    continuous_drive = epsilon_with_cd >= 1.0

    # Next-tooth engagement without collision:
    # When pinion advances one pitch angle, contact point advances one pitch
    # on the line of action; previous pair leaves after path of contact.
    # Requires ε >= 1 and circumferential_clearance > 0.
    next_tooth_ok = continuous_drive and fit_pin_in_rack and fit_rack_in_pin

    # No-slip statement
    no_slip = {
        "law": "s = r * theta (pitch circle rolls on pitch line)",
        "travel_per_revolution_mm": travel_per_rev,
        "travel_per_tooth_mm": travel_per_tooth,
        "angle_per_tooth_deg": angle_per_tooth_deg,
        "identity_pi_m_z_equals_z_times_p": phase_match,
    }

    checks = {
        "same_circular_pitch_pinion_and_rack": True,  # both p = π m
        "no_slip_pure_rolling": phase_match,
        "contact_ratio_std_ge_1": epsilon >= 1.0,
        "contact_ratio_with_CD_ge_1": continuous_drive,
        "pinion_tooth_fits_rack_space": fit_pin_in_rack,
        "rack_tooth_fits_pinion_space": fit_rack_in_pin,
        "circumferential_clearance_positive": circumferential_clearance > 0,
        "radial_engagement_positive": radial_engagement > 0.5,
        "next_tooth_meshes_without_jam": next_tooth_ok,
        "undercut_warning_z_below_min": undercut_risk,
    }

    overall = all(
        [
            checks["same_circular_pitch_pinion_and_rack"],
            checks["no_slip_pure_rolling"],
            checks["contact_ratio_with_CD_ge_1"],
            checks["pinion_tooth_fits_rack_space"],
            checks["rack_tooth_fits_pinion_space"],
            checks["next_tooth_meshes_without_jam"],
            checks["radial_engagement_positive"],
        ]
    )

    return {
        "standard": "ISO/AGMA full-depth spur + rack, pressure angle like SolidWorks Toolbox",
        "inputs": {
            "module_mm": m,
            "pinion_teeth": z,
            "pressure_angle_deg": alpha_deg,
            "tooth_clear_mm": tooth_clear,
            "center_backlash_mm": center_backlash,
            "stroke_mm": STROKE,
        },
        "geometry": {
            "circular_pitch_p_mm": p,
            "pitch_diameter_d_mm": d,
            "pitch_radius_r_mm": r,
            "tip_diameter_da_mm": da,
            "root_diameter_df_mm": df,
            "base_diameter_db_mm": db,
            "addendum_ha_mm": ha,
            "dedendum_hf_mm": hf,
            "bottom_clearance_mm": c_clearance,
            "pitch_line_offset_from_axis_mm": pitch_line_offset,
            "tooth_thickness_std_mm": s_std,
            "tooth_thickness_pinion_mm": s_pin,
            "tooth_thickness_rack_mm": s_rack,
            "space_pinion_mm": e_pin,
            "space_rack_mm": e_rack,
            "circumferential_clearance_mm": circumferential_clearance,
            "working_depth_mm": working_depth,
            "radial_engagement_mm": radial_engagement,
            "tip_overlap_radial_mm": tip_overlap,
            "z_min_no_undercut": z_min_no_undercut,
        },
        "kinematics_no_slip": no_slip,
        "contact_ratio": {
            "epsilon_alpha_standard_CD": epsilon,
            "epsilon_alpha_with_center_backlash": epsilon_with_cd,
            "formula": (
                "eps = (sqrt(ra^2-rb^2) + ha/sin(a) - r*sin(a) - CD_extra*sin(a))"
                " / (pi*m*cos(a))"
            ),
            "requirement": "eps >= 1 for continuous contact (next tooth engages before previous leaves)",
        },
        "successive_teeth": {
            "pinion_step_deg": angle_per_tooth_deg,
            "rack_step_mm": p,
            "relation": "rotate 360/z deg => rack advances exactly p = pi*m (no slip)",
            "ok": next_tooth_ok,
        },
        "turns_for_stroke": STROKE / travel_per_rev,
        "checks": checks,
        "overall_pass": overall,
        "notes": [
            "Pure rolling (no slip) is defined on the pitch circle / pitch line, not the tip.",
            "CAD teeth are approximate (not true involute); math assumes standard involute proportions.",
            "z=18 >= z_min≈17 at 20 deg => no undercut (SolidWorks/AGMA).",
            "CAD uses involute pinion + straight α rack flanks; tooth_clear/CD match math.",
        ],
    }


def main() -> None:
    report = sw_spur_rack_math(M, Z, ALPHA_DEG, TOOTH_CLEAR, CENTER_BACKLASH)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    g = report["geometry"]
    k = report["kinematics_no_slip"]
    c = report["contact_ratio"]
    ch = report["checks"]

    print("=== SolidWorks-style spur rack-pinion math ===")
    print("m=%.1f  z=%d  alpha=%.0f deg  p=pi*m=%.4f mm" % (M, Z, ALPHA_DEG, g["circular_pitch_p_mm"]))
    print()
    print("NO-SLIP (pitch circle rolls on pitch line):")
    print("  s = r * theta")
    print("  travel / rev = pi*d = %.4f mm" % k["travel_per_revolution_mm"])
    print("  1 tooth: Delta_theta=%.1f deg  =>  rack += p = %.4f mm" % (
        k["angle_per_tooth_deg"], k["travel_per_tooth_mm"]))
    print("  phase identity pi*m*z == z*p :", k["identity_pi_m_z_equals_z_times_p"])
    print()
    print("CONTACT RATIO (continuous drive, next tooth engages in time):")
    print("  eps (std CD)     = %.3f  (>=1? %s)" % (c["epsilon_alpha_standard_CD"], ch["contact_ratio_std_ge_1"]))
    print("  eps (with CD+BL) = %.3f  (>=1? %s)" % (
        c["epsilon_alpha_with_center_backlash"], ch["contact_ratio_with_CD_ge_1"]))
    print()
    print("NO JAM (tooth fits opposite space):")
    print("  s_pin=%.3f < e_rack=%.3f : %s" % (
        g["tooth_thickness_pinion_mm"], g["space_rack_mm"], ch["pinion_tooth_fits_rack_space"]))
    print("  s_rack=%.3f < e_pin=%.3f : %s" % (
        g["tooth_thickness_rack_mm"], g["space_pinion_mm"], ch["rack_tooth_fits_pinion_space"]))
    print("  circumferential clearance = %.3f mm" % g["circumferential_clearance_mm"])
    print()
    print("SUCCESSIVE TEETH:", "OK" if report["successive_teeth"]["ok"] else "FAIL")
    print("UNDERCUT warning (z < %.1f):" % g["z_min_no_undercut"], ch["undercut_warning_z_below_min"])
    print()
    print("OVERALL:", "PASS" if report["overall_pass"] else "FAIL")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
