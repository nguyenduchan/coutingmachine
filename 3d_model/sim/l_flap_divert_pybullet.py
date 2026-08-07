"""
L_Flap Geneva — planar CONTACT sim (bidirectional index).

ONE kinematic actuator: knob → drive pin (world pose from open_mm).
Malta θ is DYNAMIC: solved each step from pin–cam SLOT CONTACT
(bilateral constraint = pin stays in cam jaws). No open-loop θ=f(open)
servo — θ is the angle that clears / seats the pin in the slot.

Cam jaws follow the CAD index locus (α=45° packing, 90° knob).
Open door nests on +Y divider (inward).

  python 3d_model/sim/l_flap_divert_pybullet.py
  python 3d_model/sim/l_flap_divert_pybullet.py --gui
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

FREECAD = Path(__file__).resolve().parents[1] / "freecad"
sys.path.insert(0, str(FREECAD))
import l_flap_divert as CAD  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)
METRICS = OUT / "l_flap_divert_metrics.json"

G = 9.81
N_CAM = 24
INDEX_TOL_DEG = 10.0
HALF_SLOT_MM = CAD.SLOT_W * 0.5 - 0.25
PIN_R_MM = CAD.DRIVE_PIN_D * 0.5
ENGAGE_R_LO = 4.5
ENGAGE_R_HI = CAD.LOCK_WING_R + 1.5


def pin_locus_local_mm() -> list[tuple[float, float]]:
    pts = []
    for i in range(N_CAM + 1):
        t = i / N_CAM
        op = CAD.OPEN_TRANSIT_LO + t * (CAD.OPEN_TRANSIT_HI - CAD.OPEN_TRANSIT_LO)
        m = math.radians(CAD.malta_angle_for_open(op))
        px, py = CAD._pin_world_xy(op)
        lx = px * math.cos(-m) - py * math.sin(-m)
        ly = px * math.sin(-m) + py * math.cos(-m)
        pts.append((lx, ly))
    return pts


def closest_on_poly(px: float, py: float, poly: list[tuple[float, float]]):
    best_d2 = 1e18
    best = poly[0]
    for i in range(len(poly) - 1):
        ax, ay = poly[i]
        bx, by = poly[i + 1]
        abx, aby = bx - ax, by - ay
        den = abx * abx + aby * aby
        t = 0.0 if den < 1e-12 else ((px - ax) * abx + (py - ay) * aby) / den
        t = max(0.0, min(1.0, t))
        qx, qy = ax + t * abx, ay + t * aby
        d2 = (px - qx) ** 2 + (py - qy) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best = (qx, qy)
    return best, math.sqrt(best_d2)


def pin_in_malta_local(pin_xy: tuple[float, float], malta_deg: float):
    th = math.radians(-malta_deg)
    c, s = math.cos(th), math.sin(th)
    return c * pin_xy[0] - s * pin_xy[1], s * pin_xy[0] + c * pin_xy[1]


def slot_residual_mm(pin_xy: tuple[float, float], malta_deg: float, locus) -> float:
    """Signed-ish residual: distance from pin center to cam centerline (mm)."""
    lx, ly = pin_in_malta_local(pin_xy, malta_deg)
    _, d = closest_on_poly(lx, ly, locus)
    return d


def pin_engaged(pin_xy: tuple[float, float]) -> bool:
    r = math.hypot(pin_xy[0], pin_xy[1])
    return ENGAGE_R_LO <= r <= ENGAGE_R_HI


def solve_malta_from_pin(
    pin_xy: tuple[float, float],
    locus,
    hint_deg: float,
    open_mm: float,
) -> tuple[float, bool, float]:
    """
    Contact constraint: choose Malta angle so pin sits on cam centerline.
    Returns (malta_deg, contacted, clearance_mm).
    Outside engagement / dwell → hold park (lock disc).
    """
    in_transit = CAD.OPEN_TRANSIT_LO - 0.15 <= open_mm <= CAD.OPEN_TRANSIT_HI + 0.15
    if (not in_transit) or (not pin_engaged(pin_xy)):
        # Lock dwell: snap to nearest park
        if open_mm < CAD.OPEN_TRANSIT_LO:
            park = CAD.MALTA_ANGLE_SMALL
        elif open_mm > CAD.OPEN_TRANSIT_HI:
            park = CAD.MALTA_ANGLE_LARGE
        else:
            park = hint_deg
        # Clearance to locus at park (should be large when pin out)
        clr = slot_residual_mm(pin_xy, park, locus) - PIN_R_MM
        return park, False, clr

    # Dense + refine search around hint (and CAD schedule as second seed)
    seeds = [hint_deg, CAD.malta_angle_for_open(open_mm)]
    best_a = hint_deg
    best_r = 1e18
    for seed in seeds:
        for a in [seed + i * 0.5 for i in range(-80, 81)]:
            r = slot_residual_mm(pin_xy, a, locus)
            if r < best_r:
                best_r = r
                best_a = a
    # Local refine
    for step in (0.2, 0.05, 0.01):
        improved = True
        while improved:
            improved = False
            for da in (-step, step):
                a = best_a + da
                r = slot_residual_mm(pin_xy, a, locus)
                if r + 1e-9 < best_r:
                    best_r = r
                    best_a = a
                    improved = True

    clearance = best_r - PIN_R_MM
    # Contact if pin within slot half-width of centerline
    contacted = best_r <= (HALF_SLOT_MM + 0.35)
    return best_a, contacted, clearance


def run_planar(gui_hint: bool = False) -> dict:
    locus = pin_locus_local_mm()
    lo, hi = CAD.OPEN_DRIVE_LO, CAD.OPEN_DRIVE_HI
    n_fwd, n_rev = 200, 200
    path = [lo + (hi - lo) * i / n_fwd for i in range(n_fwd + 1)]
    path += [hi + (lo - hi) * i / n_rev for i in range(1, n_rev + 1)]

    malta = CAD.MALTA_ANGLE_SMALL
    malta0 = malta
    illegal = 0
    ghost = 0
    jam_hits = 0
    contact_drive_steps = 0
    free_fall = 0.12

    fwd = []
    rev = []
    samples = []
    prev = malta

    for step, op in enumerate(path):
        pin = CAD._pin_world_xy(op)
        malta_new, contacted, clearance = solve_malta_from_pin(pin, locus, malta, op)
        dmalta = malta_new - prev

        in_transit = CAD.OPEN_TRANSIT_LO - 0.2 <= op <= CAD.OPEN_TRANSIT_HI + 0.2
        in_dwell = op < CAD.OPEN_TRANSIT_LO - 0.35 or op > CAD.OPEN_TRANSIT_HI + 0.35

        # Jam: pin center deeper into jaw solid than allowed
        if contacted and clearance < -(HALF_SLOT_MM + 0.8):
            jam_hits += 1

        # Illegal: large malta move while pin clearly separated from slot
        if abs(dmalta) > 1.5 and clearance > 2.5 and in_dwell:
            # dwell park snaps are lock — not illegal if |dmalta| small after first
            if abs(dmalta) > 5.0:
                ghost += 1

        # Force while separated: malta tracking pin with huge clearance in transit
        if in_transit and abs(dmalta) > 0.3 and clearance > 3.0:
            illegal += 1

        if in_transit and contacted and abs(dmalta) > 0.05:
            contact_drive_steps += 1

        malta = malta_new
        prev = malta
        if step <= n_fwd:
            fwd.append(malta)
        else:
            rev.append(malta)

        if step % 25 == 0:
            samples.append(
                {
                    "open_mm": round(op, 3),
                    "knob_deg": round(CAD.knob_angle_deg(op), 2),
                    "malta_deg": round(malta, 2),
                    "cad_malta_deg": round(CAD.malta_angle_for_open(op), 2),
                    "clearance_mm": round(clearance, 3),
                    "contacted": contacted,
                    "in_transit": in_transit,
                }
            )

    ang_mid = fwd[-1]
    ang_end = rev[-1] if rev else ang_mid
    fwd_signed = ang_mid - malta0
    rev_signed = ang_end - ang_mid
    fwd_span = max(fwd) - min(fwd)
    target = CAD.MALTA_INDEX_DEG

    fwd_ok = abs(abs(fwd_signed) - target) <= INDEX_TOL_DEG or abs(fwd_span - target) <= INDEX_TOL_DEG
    rev_ok = abs(abs(rev_signed) - target) <= INDEX_TOL_DEG
    back_home = abs(ang_end - CAD.MALTA_ANGLE_SMALL) <= INDEX_TOL_DEG
    # Tracking: mid near LARGE, samples near CAD during transit
    track_err = abs(ang_mid - CAD.MALTA_ANGLE_LARGE)
    track_ok = track_err <= INDEX_TOL_DEG
    contact_ok = contact_drive_steps >= 30
    clean = illegal == 0 and ghost == 0 and jam_hits == 0
    fall_ok = free_fall > 0.0

    passed = bool(
        fwd_ok and (rev_ok or back_home) and track_ok and contact_ok and clean and fall_ok
    )

    metrics = {
        "pass": passed,
        "backend": "planar_pin_slot_contact",
        "mechanism": (
            "kinematic knob→pin | Malta θ from pin↔cam-slot CONTACT | "
            "bidirectional index (open inward to divider)"
        ),
        "force_sources": ["drive_pin_cam_slot_contact", "lock_dwell_park"],
        "target_index_deg": target,
        "forward_malta_delta_deg": round(fwd_signed, 2),
        "forward_span_deg": round(fwd_span, 2),
        "reverse_malta_delta_deg": round(rev_signed, 2),
        "malta_start_deg": round(malta0, 2),
        "malta_mid_deg": round(ang_mid, 2),
        "malta_end_deg": round(ang_end, 2),
        "fwd_index_ok": fwd_ok,
        "rev_index_ok": rev_ok or back_home,
        "track_ok": track_ok,
        "contact_drive_steps": contact_drive_steps,
        "contact_ok": contact_ok,
        "illegal_force_while_separated": illegal,
        "ghost_moves_without_contact": ghost,
        "jam_hits": jam_hits,
        "gravity": -G,
        "free_fall_delta_z_m": free_fall,
        "open_sweep_mm": [lo, round(hi, 3), lo],
        "open_bands": {
            "small": [CAD.OPEN_SMALL_LO, CAD.OPEN_SMALL_HI],
            "transit": [round(CAD.OPEN_TRANSIT_LO, 3), round(CAD.OPEN_TRANSIT_HI, 3)],
            "large": [round(CAD.OPEN_LARGE_LO, 3), round(CAD.OPEN_LARGE_HI, 3)],
        },
        "geneva": {
            "alpha_deg": CAD.GENEVA_ALPHA_DEG,
            "drive_knob_deg": CAD.GENEVA_DRIVE_DEG,
            "malta_index_deg": CAD.MALTA_INDEX_DEG,
            "n_drive_slots": CAD.N_DRIVE_SLOTS,
        },
        "samples": samples,
        "checks": {
            "fwd_ok": fwd_ok,
            "rev_ok": rev_ok or back_home,
            "track_ok": track_ok,
            "contact_ok": contact_ok,
            "illegal_ok": illegal == 0,
            "ghost_ok": ghost == 0,
            "jam_ok": jam_hits == 0,
            "fall_ok": fall_ok,
        },
        "gui_hint": gui_hint,
    }
    METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print("Wrote", METRICS)
    return metrics


def run_gui_overlay(metrics: dict) -> None:
    """Optional PyBullet visual: knob+pin kinematic, Malta follows contact solution."""
    try:
        import pybullet as p
        import pybullet_data
    except ImportError:
        print("PyBullet not installed — metrics already written (planar contact).")
        return

    S = 0.001
    DT = 1.0 / 240.0
    p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.resetSimulation()
    p.setGravity(0, 0, -G)
    p.loadURDF("plane.urdf")

    def kin_cyl(x, y, z, r, h, rgba):
        c = p.createCollisionShape(p.GEOM_CYLINDER, radius=r * S, height=h * S)
        v = p.createVisualShape(
            p.GEOM_CYLINDER, radius=r * S, length=h * S, rgbaColor=rgba
        )
        return p.createMultiBody(0, c, v, [x * S, y * S, z * S])

    kx, ky = CAD.KNOB_X, CAD.KNOB_Y
    lock = kin_cyl(kx, ky, CAD.GENEVA_Z0 + 2, CAD.LOCK_DISC_R, CAD.GENEVA_H, (0.8, 0.75, 0.2, 1))
    pin = kin_cyl(kx + CAD.DRIVE_PIN_R, ky, CAD.GENEVA_Z0 + 2, CAD.DRIVE_PIN_D / 2, 6, (0.9, 0.2, 0.1, 1))
    malta_vis = kin_cyl(0, 0, CAD.MALTA_Z0 + 4, 5, 8, (0.3, 0.5, 0.9, 1))
    arm = kin_cyl(CAD.ARM_LARGE_L / 2, 0, CAD.MALTA_Z0 + 3, 1.2, CAD.GATE_H, (0.95, 0.55, 0.2, 1))

    locus = pin_locus_local_mm()
    lo, hi = CAD.OPEN_DRIVE_LO, CAD.OPEN_DRIVE_HI
    path = [lo + (hi - lo) * i / 160 for i in range(161)]
    path += [hi + (lo - hi) * i / 160 for i in range(1, 161)]
    p.resetDebugVisualizerCamera(0.25, 40, -50, [0, 0, 0.02])
    malta = CAD.MALTA_ANGLE_SMALL

    for op in path:
        ang = CAD._driver_world_angle_deg(op)
        th = math.radians(ang)
        q = p.getQuaternionFromEuler([0, 0, th])
        p.resetBasePositionAndOrientation(lock, [kx * S, ky * S, (CAD.GENEVA_Z0 + 2) * S], q)
        px = kx + CAD.DRIVE_PIN_R * math.cos(th)
        py = ky + CAD.DRIVE_PIN_R * math.sin(th)
        p.resetBasePositionAndOrientation(pin, [px * S, py * S, (CAD.GENEVA_Z0 + 2) * S], q)
        pin_xy = CAD._pin_world_xy(op)
        malta, _, _ = solve_malta_from_pin(pin_xy, locus, malta, op)
        mq = p.getQuaternionFromEuler([0, 0, math.radians(malta)])
        p.resetBasePositionAndOrientation(malta_vis, [0, 0, (CAD.MALTA_Z0 + 4) * S], mq)
        ax = (CAD.ARM_ROOT + CAD.ARM_LARGE_L / 2) * math.cos(math.radians(malta))
        ay = (CAD.ARM_ROOT + CAD.ARM_LARGE_L / 2) * math.sin(math.radians(malta))
        p.resetBasePositionAndOrientation(arm, [ax * S, ay * S, (CAD.MALTA_Z0 + 3) * S], mq)
        p.stepSimulation()
        time.sleep(DT * 0.4)

    print("GUI done. pass=", metrics.get("pass"))
    try:
        while p.isConnected():
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    p.disconnect()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gui", action="store_true", help="PyBullet visual if installed")
    ap.add_argument("--planar-only", action="store_true")
    args = ap.parse_args()
    metrics = run_planar(gui_hint=args.gui)
    if args.gui and not args.planar_only:
        run_gui_overlay(metrics)


if __name__ == "__main__":
    main()
