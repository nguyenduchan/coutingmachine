"""Verify groove guide chutes vs Malta (math + collision). freecadcmd."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from l_flap_divert import verify_guide_chutes  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    print("=== Guide chutes (math + Malta sweep collision) ===")
    r = verify_guide_chutes(n_sweep=9)
    path = OUT / "l_flap_guide_chutes_verify.json"
    path.write_text(json.dumps(r, indent=2), encoding="utf-8")
    print(
        "pass=%s width=%s keepout=%s z=%s cont=%s coll=%s gap=%s ov=%.3f jam=%s"
        % (
            r["pass"],
            r["width_ok"],
            r["keepout_ok"],
            r["under_z_ok"],
            r["continuity_ok"],
            r["collision_ok"],
            r["gap_ok"],
            r["max_overlap_mm3"],
            r["jam_hits"],
        )
    )
    print(
        "  keepout_r=%.2f tip_clear=%.2f under_h=%.2f inlet_L=%.1f"
        % (r["keepout_r_mm"], r["tip_clear_mm"], r["under_h_mm"], r["inlet_len_mm"])
    )
    for s in r["sweep"]:
        print(
            "  open=%6.2f malta=%6.1f ov=%.3f"
            % (s["open_mm"], s["malta_deg"], s["overlap_mm3"])
        )
    print("Wrote", path)
    if not r["pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
