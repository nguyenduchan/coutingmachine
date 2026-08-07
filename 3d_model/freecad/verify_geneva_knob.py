"""Verify Malta/Geneva math + collisions while knob rotates. Run with freecadcmd."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from l_flap_divert import (  # noqa: E402
    OPEN_TRANSIT_HI,
    OPEN_TRANSIT_LO,
    geneva_math_report,
    pin_slot_engagement,
    verify_geneva_knob_rotation,
)

OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    try:
        print("=== Geneva math ===")
        m = geneva_math_report()
        for k, v in m.items():
            print("  %s: %s" % (k, v))
        print("=== Pin seat at THRESHOLD ===")
        print(" ", pin_slot_engagement(OPEN_TRANSIT_LO))

        print("=== Knob rotation collisions ===")
        report = verify_geneva_knob_rotation(n_steps=10)
        path = OUT / "l_flap_geneva_knob_verify.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        print(
            "pass=%s jam=%s max_illegal=%.2f engage_ok=%s dwell_ok=%s"
            % (
                report["pass"],
                report["jam_hits"],
                report["max_illegal_mm3"],
                report["engage_ok"],
                report["dwell_ok"],
            )
        )
        for r in report["samples"]:
            interesting = (
                r["in_transit"]
                or r["illegal_mm3"] >= 0.5
                or r.get("pin_engaged")
                or abs(r["open_mm"] - OPEN_TRANSIT_LO) < 0.02
                or abs(r["open_mm"] - OPEN_TRANSIT_HI) < 0.02
                or round(r["open_mm"], 1) in (1.0, 5.5, 19.3)
            )
            if not interesting:
                continue
            flags = []
            if r["illegal_mm3"] >= 0.5:
                flags.append("ill=%.1f" % r["illegal_mm3"])
            if r.get("pin_engaged"):
                flags.append("SEAT d=%.1f" % r.get("pin_slot_delta_deg", 0))
            if r["overlap_pin_malta_mm3"] >= 2:
                flags.append("pin_solid=%.1f" % r["overlap_pin_malta_mm3"])
            if r["overlap_driver_frame_mm3"] >= 5:
                flags.append("df=%.1f" % r["overlap_driver_frame_mm3"])
            tag = ("  " + ", ".join(flags)) if flags else "  ok"
            print(
                "  open=%6.2f knob=%6.1f malta=%5.1f %-5s%s"
                % (r["open_mm"], r["knob_deg"], r["malta_deg"], r["state"], tag)
            )

        print("Wrote", path)
        if not report["pass"]:
            print("VERIFY FAIL")
            sys.exit(1)
        print("VERIFY PASS")
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)


main()
