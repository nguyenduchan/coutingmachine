"""Verify Malta indexes at most once per forward / once per reverse (multi-turn)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from l_flap_divert import (  # noqa: E402
    geneva_math_report,
    verify_geneva_bidirectional,
    verify_geneva_knob_rotation,
    verify_malta_lock_wings,
    verify_malta_single_index,
)

OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    try:
        print("=== math ===")
        m = geneva_math_report()
        print("  pass=%s slots=%s single=%s knob_transit=%s" % (
            m["pass"], m.get("n_drive_slots"), m.get("single_slot"), m.get("transit_knob_deg")))

        print("=== lock wings (anti free-spin) ===")
        lw = verify_malta_lock_wings()
        (OUT / "l_flap_malta_lock_wings_verify.json").write_text(
            json.dumps(lw, indent=2), encoding="utf-8"
        )
        print("pass=%s parks=%s" % (
            lw["pass"],
            [(p["park"], p["ok"], p["ov_park_mm3"], p["jam_plus_mm3"], p["jam_minus_mm3"])
             for p in lw["parks"]],
        ))

        print("=== single-index (3+ extra turns) ===")
        r = verify_malta_single_index(n_extra_turns=3)
        path = OUT / "l_flap_malta_single_index_verify.json"
        path.write_text(json.dumps(r, indent=2), encoding="utf-8")
        print(
            "pass=%s fwd_rise=%s rev_fall=%s reseat=%s jam=%s"
            % (
                r["pass"],
                r["forward"]["rise_count"],
                r["reverse"]["fall_count"],
                r["extra_forward_pin_seats"],
                r["jam_hits"],
            )
        )
        print("  fwd once=%s rev once=%s" % (r["forward"]["once_ok"], r["reverse"]["once_ok"]))

        print("=== knob + bidirectional (regression) ===")
        k = verify_geneva_knob_rotation(n_steps=8)
        b = verify_geneva_bidirectional()
        (OUT / "l_flap_geneva_knob_verify.json").write_text(
            json.dumps(k, indent=2), encoding="utf-8"
        )
        (OUT / "l_flap_geneva_bidirectional_verify.json").write_text(
            json.dumps(b, indent=2), encoding="utf-8"
        )
        print("knob=%s bidir=%s" % (k["pass"], b["pass"]))

        print("Wrote", path)
        if not (lw["pass"] and r["pass"] and k["pass"] and b["pass"]):
            print("VERIFY FAIL")
            sys.exit(1)
        print("VERIFY PASS")
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)


main()
