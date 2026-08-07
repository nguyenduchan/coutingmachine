"""Verify L_Flap_Divert: aperture + Gap_Slider travel collisions. Run with freecadcmd."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from l_flap_divert import (  # noqa: E402
    OPEN_LARGE_HI,
    OPEN_LARGE_LO,
    OPEN_SMALL_HI,
    OPEN_SMALL_LO,
    aperture_widths,
    verify_mechanism,
)

OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    print("=== aperture widths ===")
    for op in [OPEN_SMALL_LO, 3.0, OPEN_SMALL_HI, OPEN_LARGE_LO, OPEN_LARGE_HI]:
        print("  open=%6.2f  %s" % (op, aperture_widths(op)))

    print("=== Gap_Slider travel collisions ===")
    report = verify_mechanism()
    path = OUT / "l_flap_divert_verify.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        "pass=%s  jam_hits=%s  max_illegal_mm3=%s  rail_seat_ok=%s"
        % (
            report["pass"],
            report["jam_hits"],
            report["max_illegal_mm3"],
            report["rail_seat_ok"],
        )
    )
    for r in report["samples"]:
        flags = []
        if r["illegal_mm3"] >= 0.5:
            flags.append("illegal=%.2f" % r["illegal_mm3"])
        if r["overlap_slider_frame"] >= 0.5:
            flags.append("vs_frame=%.2f" % r["overlap_slider_frame"])
        if r["overlap_slider_flap"] >= 0.5:
            flags.append("vs_flap=%.2f" % r["overlap_slider_flap"])
        if r["overlap_bar_rail_walls"] >= 0.5:
            flags.append("vs_rail=%.2f" % r["overlap_bar_rail_walls"])
        if not r["in_slot_y"]:
            flags.append("OUT_SLOT_Y")
        if not r["on_rail_x"]:
            flags.append("OUT_RAIL_X")
        tag = ("  !! " + ", ".join(flags)) if flags else "  ok"
        print(
            "  open=%6.2f %-5s flap=%5.1f%s"
            % (r["open_mm"], r["state"], r["flap_deg"], tag)
        )

    print("Wrote", path)
    if not report["pass"]:
        print("VERIFY FAIL")
        sys.exit(1)
    print("VERIFY PASS")


# freecadcmd may not set __name__ == "__main__"
main()
