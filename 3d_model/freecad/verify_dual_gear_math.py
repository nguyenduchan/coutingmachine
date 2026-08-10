"""Math verify: dual discontinuous sequential gears."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

try:
    HERE = Path(__file__).resolve().parent
except NameError:
    HERE = Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad")
sys.path.insert(0, str(HERE))

from width_chute_selector import (  # noqa: E402
    TRAVEL_MAX,
    aperture_mm,
    cassette_y_for_travel,
    drive_phase_bounds,
    gear1_active,
    gear2_active,
    gear1_phases,
    gear2_phases,
    gear_math,
    knob_angle_deg,
    selector_state,
    verify_dwell_jump_math,
)


def main() -> None:
    g = gear_math()
    r = g["pitch_radius"]
    ph = drive_phase_bounds()
    report = {
        "gear": {
            "module": g["module"],
            "z": g["teeth"],
            "r_mm": r,
            "dual_discontinuous_sequential": True,
        },
        "phases": {k: ph[k] for k in ("gear1_a", "gear2_1", "gear1_b", "gear2_2", "gear1_c")},
        "pass": False,
    }

    print("=== DUAL SEQUENTIAL GEARS ===")
    print("m=%.2f z=%d r=%.4f TRAVEL_MAX=%.2f" % (g["module"], g["teeth"], r, TRAVEL_MAX))

    err_max = 0.0
    both = 0
    for q in [i * 0.5 for i in range(int(TRAVEL_MAX * 2) + 1)]:
        th = knob_angle_deg(q)
        err = abs(abs(th) * math.pi / 180.0 * r - q)
        err_max = max(err_max, err)
        if gear1_active(q) and gear2_active(q):
            both += 1

    print("max θ↔q err=%.2e  both_active_samples=%d" % (err_max, both))

    print("\n=== GEAR1 phases: aperture moves, cassette still ===")
    g1_ok = True
    for a, b, name in gear1_phases():
        dap = aperture_mm(b) - aperture_mm(a)
        dcy = abs(cassette_y_for_travel(b) - cassette_y_for_travel(a))
        ok = dap > 0.5 and dcy < 1e-6
        g1_ok = g1_ok and ok
        print("  %s dap=%.2f dcy=%.4f ok=%s" % (name, dap, dcy, ok))

    print("\n=== GEAR2 phases: cassette moves, aperture frozen ===")
    g2_ok = True
    for a, b, name, *_ in gear2_phases():
        dap = abs(aperture_mm(b) - aperture_mm(a))
        dcy = abs(cassette_y_for_travel(b) - cassette_y_for_travel(a))
        ok = dap < 1e-9 and dcy > 1.0
        g2_ok = g2_ok and ok
        print("  %s dap=%.4f dcy=%.2f ok=%s" % (name, dap, dcy, ok))

    math_v = verify_dwell_jump_math()
    report["verify_checks"] = math_v["checks"]
    report["pass"] = bool(
        err_max < 1e-6 and both == 0 and g1_ok and g2_ok and math_v["pass"]
    )
    out = HERE / "out" / "width_chute_dual_gear_math.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nWrote", out)
    print("pass:", report["pass"], math_v["checks"])
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
