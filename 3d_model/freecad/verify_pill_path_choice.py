"""
Probe one object from outside: which lane it can take, and jam risk.

Path: inlet chute (+Y) → aperture plate → Malta gate → groove (−Y exit).

  freecadcmd -c "import runpy; runpy.run_path(r'.../verify_pill_path_choice.py')"
  python 3d_model/freecad/verify_pill_path_choice.py   # math-only subset if no FreeCAD
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE))

import l_flap_divert as C  # noqa: E402


# Typical part diameters (must fit groove + CLEAR margin)
PILL_SMALL_D = 4.0  # fits 5.5 mm lane
PILL_LARGE_D = 10.0  # fits 12 mm lane only
PROBE_OVERLAP_JAM = 2.0  # mm³ solid ∩ blockers ⇒ stuck
# Under-arm puck: pills travel on floor under Malta (not through hub Z)
PROBE_H = min(2.2, C.PILL_CLEAR_H - 0.4)


def _lane_x(tag: str) -> float:
    g = C.groove_x_bounds()
    if tag == "small":
        return 0.5 * (g["small_x0"] + g["small_x1"])
    return 0.5 * (g["large_x0"] + g["large_x1"])


def _lane_open_x(open_mm: float, tag: str) -> float | None:
    """Center X of (aperture window ∩ groove) — where a part actually threads."""
    g = C.groove_x_bounds()
    wins = C.aperture_windows(open_mm)
    if tag == "small":
        a0, a1 = wins["small"]
        b0, b1 = g["small_x0"], g["small_x1"]
    else:
        a0, a1 = wins["large"]
        b0, b1 = g["large_x0"], g["large_x1"]
    c0, c1 = max(a0, b0), min(a1, b1)
    if c1 - c0 < 0.5:
        return None
    return 0.5 * (c0 + c1)


def _y_stations() -> list[tuple[str, float]]:
    """Waypoints from outside inlet toward groove exit (floor flow)."""
    y_in = 18.0
    y_ap = 0.5 * (C.APERTURE_Y0 + C.APERTURE_Y1)
    y_gate = 0.0
    y_groove = -20.0
    y_exit = -C.GROOVE_LEN + 10.0  # stay clear of end wall
    return [
        ("inlet", y_in),
        ("aperture", y_ap),
        ("gate", y_gate),
        ("groove", y_groove),
        ("exit", y_exit),
    ]


def math_path_choice(open_mm: float, pill_d: float) -> dict:
    """Aperture + Malta park decide which lane a diameter can use (no mesh)."""
    aw = C.aperture_widths(open_mm)
    malta = C.malta_angle_for_open(open_mm)
    # Clearance vs aperture window width on each lane
    fit_s = aw["small_mm"] + 1e-6 >= pill_d
    fit_l = aw["large_mm"] + 1e-6 >= pill_d
    # Malta: @0° large arm on +X blocks LARGE; @90° small arm on −X blocks SMALL
    # Soft model: lane blocked if corresponding arm tip projects into lane X band
    g = C.groove_x_bounds()
    ang = math.radians(malta)
    # Large arm tip at rest local (ARM_ROOT+ARM_LARGE_L, 0) → rotate
    tip_l = (
        (C.ARM_ROOT + C.ARM_LARGE_L) * math.cos(ang),
        (C.ARM_ROOT + C.ARM_LARGE_L) * math.sin(ang),
    )
    tip_s = (
        (C.ARM_ROOT + C.ARM_SMALL_L) * math.cos(ang + math.radians(C.MALTA_ARM_ANGLE_DEG)),
        (C.ARM_ROOT + C.ARM_SMALL_L) * math.sin(ang + math.radians(C.MALTA_ARM_ANGLE_DEG)),
    )

    def _overlap(a0, a1, b0, b1):
        return max(0.0, min(a1, b1) - max(a0, b0))

    def tip_blocks_lane(tip_xy, x0, x1) -> bool:
        """Arm along ±X (tip near Y=0) covers X from hub→tip and blocks that groove."""
        tx, ty = tip_xy
        if abs(ty) > 2.0:
            return False  # arm swung to ±Y (pocket / clear of groove floor)
        xa, xb = sorted([0.0, tx])
        return _overlap(xa, xb, x0, x1) > 1.0

    block_s = tip_blocks_lane(tip_s, g["small_x0"], g["small_x1"]) or tip_blocks_lane(
        tip_l, g["small_x0"], g["small_x1"]
    )
    block_l = tip_blocks_lane(tip_l, g["large_x0"], g["large_x1"]) or tip_blocks_lane(
        tip_s, g["large_x0"], g["large_x1"]
    )

    open_s = fit_s and not block_s
    open_l = fit_l and not block_l
    if open_s and not open_l:
        choice = "SMALL"
    elif open_l and not open_s:
        choice = "LARGE"
    elif open_s and open_l:
        choice = "BOTH"
    elif fit_s or fit_l:
        choice = "BLOCKED_AT_GATE"
    else:
        choice = "BLOCKED_AT_APERTURE"

    return {
        "open_mm": round(open_mm, 3),
        "pill_d_mm": pill_d,
        "aperture_small_mm": aw["small_mm"],
        "aperture_large_mm": aw["large_mm"],
        "malta_deg": round(malta, 2),
        "fit_aperture_small": fit_s,
        "fit_aperture_large": fit_l,
        "malta_blocks_small": block_s,
        "malta_blocks_large": block_l,
        "path_open_small": open_s,
        "path_open_large": open_l,
        "chosen_path": choice,
    }


def solid_probe_lane(open_mm: float, lane: str, pill_d: float) -> dict:
    """Sweep a flat puck on the floor under Malta; report ∩ with blockers."""
    r = pill_d * 0.5
    h = PROBE_H
    z0 = C.FLOOR_T + 0.15
    x_open = _lane_open_x(open_mm, lane)
    x = x_open if x_open is not None else _lane_x(lane)
    # Shrink puck laterally if open sector is narrower than pill (cannot fit)
    aw = C.aperture_widths(open_mm)
    sector = aw["small_mm"] if lane == "small" else aw["large_mm"]
    if sector + 1e-6 < pill_d:
        return {
            "lane": lane,
            "open_mm": round(open_mm, 3),
            "pill_d_mm": pill_d,
            "probe_x": round(x, 3),
            "max_overlap_mm3": None,
            "stuck_at": "aperture",
            "clear": False,
            "skipped_solid": True,
            "reason": "open_sector_narrower_than_pill",
        }
    malta = C.make_malta_cross(C.malta_angle_for_open(open_mm))
    ap = C.make_aperture_plate(open_mm)
    frame = C.make_divert_frame()
    try:
        floor_slab = C._box(220.0, 220.0, C.FLOOR_T + 0.6, -110.0, -110.0, -0.3)
        frame_walls = frame.cut(floor_slab)
    except Exception:
        frame_walls = frame
    hits = []
    max_ov = 0.0
    stuck_at = None
    for name, y in _y_stations():
        # At aperture use open-sector X; downstream use groove center once past gate
        xx = x if name in ("inlet", "aperture") else _lane_x(lane)
        puck = C._box(pill_d * 0.92, pill_d * 0.92, h, xx - r * 0.92, y - r * 0.92, z0)
        if name == "aperture":
            blockers = [ap, frame_walls]
        elif name in ("gate", "groove"):
            blockers = [malta, frame_walls]
        else:
            blockers = [frame_walls]
        ov = 0.0
        for b in blockers:
            ov = max(ov, C.common_volume(puck, b))
        max_ov = max(max_ov, ov)
        jammed = ov >= PROBE_OVERLAP_JAM
        hits.append({"station": name, "y": y, "x": round(xx, 3), "overlap_mm3": round(ov, 3), "jammed": jammed})
        if jammed and stuck_at is None:
            stuck_at = name
    clear = stuck_at is None and max_ov < PROBE_OVERLAP_JAM
    return {
        "lane": lane,
        "open_mm": round(open_mm, 3),
        "pill_d_mm": pill_d,
        "probe_h_mm": h,
        "probe_x_aperture": round(x, 3),
        "max_overlap_mm3": round(max_ov, 3),
        "stuck_at": stuck_at,
        "clear": clear,
        "stations": hits,
    }


def run_solid(poses=None, pills=None) -> dict:
    poses = poses or [C.OPEN_DRIVE_LO, C.THRESHOLD_MM * 0.8, C.OPEN_TRANSIT_LO, 0.5 * (C.OPEN_TRANSIT_LO + C.OPEN_TRANSIT_HI), C.OPEN_TRANSIT_HI, C.OPEN_DRIVE_HI]
    pills = pills or [("small_pill", PILL_SMALL_D), ("large_pill", PILL_LARGE_D)]
    math_rows = []
    solid_rows = []
    jam_hits = 0
    for op in poses:
        for tag, d in pills:
            m = math_path_choice(op, d)
            m["pill"] = tag
            math_rows.append(m)
            # solid: try the lane that math says is open; if BOTH try both; if blocked still probe intended
            lanes = []
            if m["chosen_path"] == "SMALL":
                lanes = ["small"]
            elif m["chosen_path"] == "LARGE":
                lanes = ["large"]
            elif m["chosen_path"] == "BOTH":
                lanes = ["small", "large"]
            else:
                # intended by size
                lanes = ["small"] if d <= C.SMALL_GROOVE_W else ["large"]
            for lane in lanes:
                # skip solid if aperture clearly too narrow (save time) — still record blocked
                if lane == "small" and not m["fit_aperture_small"]:
                    solid_rows.append({
                        "lane": lane, "open_mm": round(op, 3), "pill_d_mm": d,
                        "max_overlap_mm3": None, "stuck_at": "aperture", "clear": False,
                        "skipped_solid": True, "reason": "aperture_too_narrow",
                    })
                    jam_hits += 1
                    continue
                if lane == "large" and not m["fit_aperture_large"]:
                    solid_rows.append({
                        "lane": lane, "open_mm": round(op, 3), "pill_d_mm": d,
                        "max_overlap_mm3": None, "stuck_at": "aperture", "clear": False,
                        "skipped_solid": True, "reason": "aperture_too_narrow",
                    })
                    jam_hits += 1
                    continue
                s = solid_probe_lane(op, lane, d)
                s["pill"] = tag
                s["math_choice"] = m["chosen_path"]
                solid_rows.append(s)
                if not s["clear"]:
                    jam_hits += 1

    # Summary scenarios user cares about
    scenarios = []
    for op, label in (
        (C.OPEN_DRIVE_LO, "rest_cover_small"),
        (4.0, "small_lane_metering"),
        (C.OPEN_DRIVE_HI, "max_large_open"),
    ):
        for tag, d in pills:
            m = math_path_choice(op, d)
            scenarios.append({
                "scenario": label,
                "pill": tag,
                "pill_d_mm": d,
                **{k: m[k] for k in (
                    "open_mm", "aperture_small_mm", "aperture_large_mm", "malta_deg",
                    "chosen_path", "path_open_small", "path_open_large",
                )},
            })

    # Stuck risk: transit when malta swings while aperture may still allow wrong lane
    transit_risk = []
    for i in range(5):
        t = i / 4.0
        op = C.OPEN_TRANSIT_LO + t * (C.OPEN_TRANSIT_HI - C.OPEN_TRANSIT_LO)
        for tag, d in pills:
            m = math_path_choice(op, d)
            risk = m["chosen_path"] in ("BLOCKED_AT_GATE", "BOTH") or (
                m["fit_aperture_small"] and m["malta_blocks_small"]
            ) or (m["fit_aperture_large"] and m["malta_blocks_large"])
            transit_risk.append({
                "open_mm": round(op, 3),
                "pill": tag,
                "chosen_path": m["chosen_path"],
                "risk_jam": risk,
                "ap_s": m["aperture_small_mm"],
                "ap_l": m["aperture_large_mm"],
                "block_s": m["malta_blocks_small"],
                "block_l": m["malta_blocks_large"],
            })

    # Pass: at rest small pill cannot pass (covered); at max large pill takes LARGE;
    # no solid jam when path is declared open
    rest_small = math_path_choice(C.OPEN_DRIVE_LO, PILL_SMALL_D)
    max_large = math_path_choice(C.OPEN_DRIVE_HI, PILL_LARGE_D)
    open_clears = [s for s in solid_rows if s.get("math_choice") in ("SMALL", "LARGE", "BOTH") and not s.get("skipped_solid")]
    solid_ok = all(s.get("clear") for s in open_clears) if open_clears else True
    passed = (
        rest_small["chosen_path"] == "BLOCKED_AT_APERTURE"
        and max_large["chosen_path"] == "LARGE"
        and solid_ok
    )
    return {
        "pass": passed,
        "solid_ok": solid_ok,
        "jam_hits_when_path_open": sum(1 for s in open_clears if not s.get("clear")),
        "path_logic": (
            "Outside -> guide chute (+Y) -> aperture window -> Malta gate -> groove (-Y). "
            "Lane chosen by which aperture is open AND which arm is clear; "
            "object diameter must fit window."
        ),
        "scenarios": scenarios,
        "transit_risk": transit_risk,
        "math_samples": math_rows,
        "solid_samples": solid_rows,
        "pill_sizes_mm": {"small_pill": PILL_SMALL_D, "large_pill": PILL_LARGE_D},
    }


def main():
    # Detect FreeCAD for solid probes
    try:
        C._fc()
        has_fc = True
    except Exception:
        has_fc = False

    if has_fc:
        rep = run_solid()
    else:
        # math-only
        rows = []
        for op in (0.0, 4.0, 5.5, 7.5, 9.5, 17.5):
            for tag, d in (("small_pill", PILL_SMALL_D), ("large_pill", PILL_LARGE_D)):
                m = math_path_choice(op, d)
                m["pill"] = tag
                rows.append(m)
        rep = {
            "pass": False,
            "note": "math_only_no_freecad",
            "math_samples": rows,
            "path_logic": run_solid.__doc__,
        }

    path = OUT / "l_flap_pill_path_verify.json"
    path.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("pass=%s solid_ok=%s" % (rep.get("pass"), rep.get("solid_ok")))
    print("logic:", rep.get("path_logic"))
    for s in rep.get("scenarios", []):
        print(
            "  [%s] %s d=%.1f -> %s (ap s=%.1f L=%.1f malta=%.0f)"
            % (
                s["scenario"],
                s["pill"],
                s["pill_d_mm"],
                s["chosen_path"],
                s["aperture_small_mm"],
                s["aperture_large_mm"],
                s["malta_deg"],
            )
        )
    risks = [t for t in rep.get("transit_risk", []) if t.get("risk_jam")]
    print("transit_risk_hits=%d" % len(risks))
    for t in risks[:8]:
        print("  risk open=%.2f %s -> %s" % (t["open_mm"], t["pill"], t["chosen_path"]))
    print("Wrote", path)
    if not rep.get("pass"):
        sys.exit(1)


if __name__ == "__main__":
    main()
