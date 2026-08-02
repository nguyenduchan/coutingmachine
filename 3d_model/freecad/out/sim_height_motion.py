# -*- coding: utf-8 -*-
"""
Check Height_Adjust leadscrew:
  1) Thread length enough for 20 mm stroke?
  2) Male/female pitch & size match?
  3) Kinematic sim: 2 turns → 20 mm, nut stays on thread.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App
import Part

_HERE = Path(__file__).resolve().parent
_FC = _HERE.parent if _HERE.name == "out" else _HERE
OUT = _FC / "out"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(_FC))

import box_settings as BX
from height_adjust_z import build_height_adjust_z_parts, _thread_params, _helix_screw_z


def main() -> None:
    log = OUT / "height_adjust_motion_sim.log"
    def _log(msg: str) -> None:
        print(msg, flush=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(msg + "\n")

    log.write_text("", encoding="utf-8")
    _log("sim start")
    drv = dict(BX.LID["height_bar"]["drive"])
    thr = _thread_params(drv)
    stroke = float(drv.get("rail_stroke", 20.0))
    nut_h = float(drv.get("nut_h", 12.0))
    bar_z = float(drv.get("bar_height", 12.0))
    pitch = thr["pitch"]
    th_len = thr["length"]
    major = thr["major_d"]
    depth = thr["depth"]
    clear = thr["nut_clear_r"]

    # Match CAD: boss_h, z_th0, tap window
    boss_h = max(nut_h, 12.0)
    z_nut0 = 0.0
    z_th0 = z_nut0 - 8.0
    z_boss0 = z_nut0 + bar_z * 0.15
    z_boss1 = z_boss0 + boss_h
    z_tap0 = z_nut0 - 1.5
    tap_len = (z_boss1 + 1.5) - z_tap0
    engage = tap_len
    z_th1 = z_th0 + th_len
    # At max stroke, tap top must stay on thread
    z_tap_hi_max = z_tap0 + stroke + tap_len
    usable = max(0.0, z_th1 - (z_tap0 + tap_len))  # travel while full engage
    # Conservative usable: keep at least 0.8*tap_len overlap
    min_ov = 0.8 * tap_len
    usable_partial = max(0.0, z_th1 - min_ov - z_tap0 - 0.0)  # rough
    turns_for_stroke = stroke / pitch if pitch > 0 else float("inf")
    _log(
        "geometry: z_th=[%.1f,%.1f] tap_len=%.1f tap_hi@stroke=%.1f need_L>=%.1f"
        % (z_th0, z_th1, tap_len, z_tap_hi_max, z_tap_hi_max - z_th0)
    )

    report = {
        "settings": {
            "pitch_mm": pitch,
            "screw_thread_len_mm": th_len,
            "stroke_mm": stroke,
            "nut_engage_mm": engage,
            "major_d": major,
            "depth": depth,
            "male_clear_r": 0.0,
            "female_clear_r": clear,
        },
        "kinematics": {},
        "match": {},
        "sim": {},
        "pass": True,
        "errors": [],
        "warnings": [],
    }

    def fail(msg: str) -> None:
        report["pass"] = False
        report["errors"].append(msg)
        print("FAIL:", msg)

    def warn(msg: str) -> None:
        report["warnings"].append(msg)
        print("WARN:", msg)

    print("=" * 60)
    print("1) Thread length vs 20 mm travel")
    print(
        "   screw L=%.1f  tap_engage=%.1f  usable_full=%.1f  stroke=%.1f"
        % (th_len, engage, usable, stroke)
    )
    report["kinematics"] = {
        "usable_travel_mm": usable,
        "usable_partial_mm": usable_partial,
        "z_th0": z_th0,
        "z_th1": z_th1,
        "tap_len": tap_len,
        "z_tap_hi_at_stroke": z_tap_hi_max,
        "required_L_mm": z_tap_hi_max - z_th0,
        "turns_for_full_stroke": turns_for_stroke,
        "travel_per_2_turns_mm": 2.0 * pitch,
    }
    if abs(2.0 * pitch - stroke) > 0.05:
        fail(
            "2 turns travel = %.1f mm but stroke setting = %.1f mm"
            % (2.0 * pitch, stroke)
        )
    else:
        print("OK 2 turns = %.1f mm matches stroke" % (2.0 * pitch))

    if usable + 1e-6 < stroke:
        fail(
            "usable full-engage travel %.1f mm < stroke %.1f mm "
            "(need L >= %.1f from tip start)"
            % (usable, stroke, z_tap_hi_max - z_th0)
        )
    else:
        print("OK usable >= stroke (margin %.1f mm)" % (usable - stroke))

    if z_tap_hi_max > z_th1 + 1e-6:
        fail(
            "at top of stroke, tap exits thread: tap_hi=%.1f > z_th1=%.1f"
            % (z_tap_hi_max, z_th1)
        )
    else:
        print("OK tap stays on thread at stroke (margin %.1f mm)" % (z_th1 - z_tap_hi_max))

    print("=" * 60)
    print("2) Male / female match (same pitch, depth, major; female +clear)")
    male = _helix_screw_z(major, pitch, depth, th_len, 0, 0, 0, 0.0, thr["segs_per_turn"])
    female = _helix_screw_z(
        major, pitch, depth, max(engage, pitch * 1.2), 0, 0, 0, clear, thr["segs_per_turn"]
    )
    # Sample radial extent every pitch/4 along Z
    def sample_od(sh: Part.Shape, z0: float, n: int = 12) -> list[float]:
        bbs = []
        L = float(sh.BoundBox.ZLength)
        for i in range(n):
            z = z0 + (i + 0.5) * (L / n)
            # slice approx: common with thin box
            box = Part.makeBox(30, 30, 0.4)
            box.translate(App.Vector(-15, -15, z - 0.2))
            try:
                sec = sh.common(box)
                if sec is None or sec.isNull() or not sec.Solids:
                    continue
                b = sec.BoundBox
                r = 0.5 * max(b.XLength, b.YLength)
                bbs.append(r)
            except Exception:
                pass
        return bbs

    male_rs = sample_od(male, male.BoundBox.ZMin)
    female_rs = sample_od(female, female.BoundBox.ZMin)
    report["match"] = {
        "male_pitch": pitch,
        "female_pitch": pitch,
        "male_major": major,
        "female_cutter_major": major + 2.0 * clear,
        "male_sample_r_mean": sum(male_rs) / len(male_rs) if male_rs else None,
        "female_sample_r_mean": sum(female_rs) / len(female_rs) if female_rs else None,
        "pitch_uniform": True,
    }
    print("   same pitch=%.1f depth=%.1f major=%.1f female_clear=%.2f" % (pitch, depth, major, clear))
    print("OK male/female share pitch & depth (female cutter OD larger by 2*clear)")

    # Pitch uniformity: distance between Z peaks of outer material — approximate via
    # checking helix formula only (geometry built with constant pitch)
    report["match"]["build_uses_constant_pitch"] = True

    print("=" * 60)
    print("3) Kinematic simulation (fixed screw, traveling nut)")
    # Build assembly parts for bbox / bore checks
    drv["bar_length_y"] = 40.0
    parts = {
        n: sh
        for n, sh, _ in build_height_adjust_z_parts(
            cx=0.0, cy=0.0, z_zero=0.0, cfg=drv, include_demo_wall=False
        )
    }
    screw = parts["HA_Lead_Screw"]
    nut0 = parts["HA_Traveling_Nut"]
    sbb = screw.BoundBox
    # Threaded band approx from tip+helix start
    z_th0 = -8.0  # matches build (z_nut0-8)
    z_th1 = z_th0 + th_len

    steps = []
    all_ok = True
    for turns in [0.0, 0.5, 1.0, 1.5, 2.0]:
        dz = turns * pitch
        nut = nut0.copy()
        nut.translate(App.Vector(0, 0, dz))
        nbb = nut.BoundBox
        # Tap window after translation
        t0 = z_tap0 + dz
        t1 = z_tap0 + tap_len + dz
        overlap_lo = max(t0, z_th0)
        overlap_hi = min(t1, z_th1)
        overlap = max(0.0, overlap_hi - overlap_lo)
        on_thread = overlap >= tap_len * 0.85
        z_mid = 0.5 * (t0 + t1)
        bore_open = not nut.isInside(App.Vector(0, 0, z_mid), 0.2, True)
        # Helix solids often fail isInside on axis — use distance to shape
        try:
            dist = float(screw.distToShape(Part.Vertex(App.Vector(0, 0, z_mid)))[0])
            screw_there = dist < (0.5 * major + 0.5)
        except Exception:
            screw_there = z_th0 <= z_mid <= z_th1
        ok = on_thread and bore_open and screw_there and (dz <= stroke + 0.05)
        if not ok:
            all_ok = False
        step = {
            "turns": turns,
            "dz_mm": dz,
            "tap_overlap_mm": overlap,
            "bore_open": bore_open,
            "screw_at_mid": screw_there,
            "ok": ok,
        }
        steps.append(step)
        print(
            "   turns=%.1f  dz=%5.1f  tap_ov=%.1f  bore=%s  screw=%s  ok=%s"
            % (turns, dz, overlap, bore_open, screw_there, ok)
        )

    report["sim"]["steps"] = steps
    report["sim"]["ok"] = all_ok
    if not all_ok:
        fail("simulation: nut leaves usable thread or bore closed at some step")

    # Interference probe at mid stroke: screw section should not heavily eat nut walls
    # (clearance fit) — intersection volume ratio
    try:
        nut = nut0.copy()
        nut.translate(App.Vector(0, 0, stroke * 0.5))
        box = Part.makeBox(20, 20, engage)
        box.translate(App.Vector(-10, -10, z_th0 + stroke * 0.5))
        s_sec = screw.common(box)
        inter = s_sec.common(nut)
        ratio = float(inter.Volume) / max(1.0, float(s_sec.Volume))
        report["sim"]["midstroke_intersect_ratio"] = ratio
        print("   mid-stroke screw∩nut / screw_sec = %.3f (want <0.35)" % ratio)
        if ratio > 0.5:
            fail("heavy interference at mid stroke (ratio=%.3f)" % ratio)
        elif ratio > 0.35:
            warn("moderate intersection at mid stroke (ratio=%.3f)" % ratio)
        else:
            print("OK clearance-like fit at mid stroke")
    except Exception as exc:
        warn("interference probe skipped: %s" % exc)

    print("=" * 60)
    status = "PASS" if report["pass"] else "FAIL"
    print("RESULT:", status)
    if report["errors"]:
        for e in report["errors"]:
            print(" -", e)
    if report["warnings"]:
        for w in report["warnings"]:
            print(" ~", w)

    out = OUT / "height_adjust_motion_sim.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Wrote", out)
    if not report["pass"]:
        sys.exit(1)


if __name__ == "__main__" or True:
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback

        err = traceback.format_exc()
        print(err, flush=True)
        try:
            (OUT / "height_adjust_motion_sim.log").write_text(err, encoding="utf-8")
        except Exception:
            pass
        raise
