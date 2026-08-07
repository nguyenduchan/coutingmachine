"""Verify Malta/Geneva bidirectional knob (forward + reverse door). freecadcmd."""
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
    verify_geneva_bidirectional,
)

OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    try:
        print("=== Geneva math ===")
        m = geneva_math_report()
        for k in (
            "pass",
            "index_deg",
            "transit_open_mm",
            "transit_knob_deg",
            "index_knob_matches_90",
            "malta_index_delta_deg",
        ):
            print("  %s: %s" % (k, m.get(k)))

        print("=== Seat LO / HI ===")
        print("  LO", pin_slot_engagement(OPEN_TRANSIT_LO))
        print("  HI", pin_slot_engagement(OPEN_TRANSIT_HI))

        print("=== Bidirectional knob ===")
        report = verify_geneva_bidirectional()
        path = OUT / "l_flap_geneva_bidirectional_verify.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        print(
            "pass=%s fwd_ok=%s rev_ok=%s seat_lo=%s seat_rev_to_lo=%s "
            "pin_exit_hi=%s door=%s sym=%s mono=%s/%s knob_transit=%.1f"
            % (
                report["pass"],
                report["forward"]["ok"],
                report["reverse"]["ok"],
                report["seat_forward_entry"],
                report["seat_reverse_return_to_lo"],
                report["pin_exits_at_hi_ok"],
                report["door_logic_ok"],
                report["pose_symmetric"],
                report["forward"].get("monotonic"),
                report["reverse"].get("monotonic"),
                report["transit_knob_deg"],
            )
        )
        print(
            "  forward malta_delta=%s ill=%s"
            % (report["forward"]["malta_delta_deg"], report["forward"]["max_illegal_mm3"])
        )
        print(
            "  reverse malta_delta=%s ill=%s"
            % (report["reverse"]["malta_delta_deg"], report["reverse"]["max_illegal_mm3"])
        )

        for leg_name in ("forward", "reverse"):
            print("---", leg_name, report[leg_name]["meaning"])
            for r in report[leg_name]["samples"]:
                if not (
                    r["in_transit"]
                    or r["pin_engaged"]
                    or r["illegal_mm3"] >= 0.5
                    or abs(r["open_mm"] - OPEN_TRANSIT_LO) < 0.05
                    or abs(r["open_mm"] - OPEN_TRANSIT_HI) < 0.05
                    or round(r["open_mm"], 1) in (1.0, 3.0)
                ):
                    continue
                tag = []
                if r["pin_engaged"]:
                    tag.append("SEAT")
                if r["illegal_mm3"] >= 0.5:
                    tag.append("ill=%.1f" % r["illegal_mm3"])
                print(
                    "  open=%6.2f knob=%6.1f malta=%5.1f %-5s %s"
                    % (
                        r["open_mm"],
                        r["knob_deg"],
                        r["malta_deg"],
                        r["state"],
                        " ".join(tag) or "ok",
                    )
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
