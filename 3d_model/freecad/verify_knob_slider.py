"""Verify knob → Gap_Slider rack drive (fine ~1 mm pitch pinion). freecadcmd."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from l_flap_divert import (  # noqa: E402
    geneva_math_report,
    verify_knob_slider_drive,
)

OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    print("=== Gear / knob->slider ===")
    gear = verify_knob_slider_drive()
    path = OUT / "l_flap_knob_slider_verify.json"
    path.write_text(json.dumps(gear, indent=2), encoding="utf-8")
    print(
        "pass=%s m=%.4f z=%d p=%.3f mm tpt=%.2f | 1mm->%.1f deg knob | couple=%s mesh=%s ov=%.1f"
        % (
            gear["pass"],
            gear["module"],
            gear["teeth"],
            gear["circular_pitch_mm"],
            gear["travel_per_turn_mm"],
            gear["knob_deg_per_1mm"],
            gear["couple_ok"],
            gear["mesh_ok"],
            gear["max_overlap_mm3"],
        )
    )
    for s in gear["samples"][:8]:
        print(
            "  open=%5.2f knob=%6.1f err=%.3f ov=%s"
            % (
                s["open_mm"],
                s["knob_deg"],
                s["couple_err_mm"],
                s.get("overlap_mm3", "-"),
            )
        )
    print("Wrote", path)

    print("=== Geneva math (after KNOB_Y change) ===")
    m = geneva_math_report()
    print("  math_pass", m.get("pass"), "index_open", m.get("transit_open_mm"))
    # Skip full bidirectional here (slow); math + gear mesh is enough for this check
    if not gear["pass"] or not m.get("pass"):
        sys.exit(1)


if __name__ == "__main__":
    main()
