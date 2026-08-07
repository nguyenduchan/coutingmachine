"""Verify open door nests inward against divider. freecadcmd."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from l_flap_divert import (  # noqa: E402
    geneva_math_report,
    verify_guide_chutes,
    verify_open_door_nest,
)

OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    print("=== Geneva math (90 deg inward door) ===")
    m = geneva_math_report()
    print(
        "pass=%s arms=%s open_in=%s closed=%s index=%s"
        % (
            m["pass"],
            m["arms_ok"],
            m["open_inward_ok"],
            m["closed_across_ok"],
            m["index_deg"],
        )
    )

    print("=== Open door nest ===")
    r = verify_open_door_nest()
    path = OUT / "l_flap_open_door_nest_verify.json"
    path.write_text(json.dumps(r, indent=2), encoding="utf-8")
    print(
        "pass=%s closed_across=%s mid_ov=%.2f"
        % (r["pass"], r["closed_across_large"], r["max_mid_overlap_mm3"])
    )
    for n in r["open_nests"]:
        print(
            "  park=%s arm=%s tip=%s along_Y=%s ov=%.1f"
            % (n["park_deg"], n["arm"], n["tip_xy"], n["along_plus_y"], n["overlap_frame_mm3"])
        )
    print("Wrote", path)

    print("=== Guide chutes ===")
    g = verify_guide_chutes(n_sweep=7)
    print(
        "pass=%s coll=%s ov=%.3f"
        % (g["pass"], g["collision_ok"], g["max_overlap_mm3"])
    )
    OUT.joinpath("l_flap_guide_chutes_verify.json").write_text(
        json.dumps(g, indent=2), encoding="utf-8"
    )

    if not (m["pass"] and r["pass"] and g["pass"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
