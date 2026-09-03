#!/usr/bin/env python3
"""Route modules/m2_opto4.kicad_pcb with FreeRouting (not the in-house maze router).

The in-house grid router (route_m2_maze.py) got stuck: its A7 hole-keepout
radius (~1.0 mm for a 0.8 mm drill) eats almost the whole gap between pads on
this module's tight 2.54 mm pitch, so 17-19 hops never found a lattice cell.
FreeRouting works on continuous geometry instead of a fixed grid, so that
deadlock doesn't apply -- it already closes the much bigger/denser main
carrier at 0 unconnected. This reuses route_freerouting.py's DSN/SES/A7/
cleanup machinery by pointing its module-level paths at the module board
instead of esp32_baseboard.kicad_pcb, and skips fill_gnd_zones() (a daughter
board this small has no call for a copper pour the main pipeline wasn't
asked to add here).

Run with the KiCad-bundled Python (it owns the pcbnew module):
    "%LOCALAPPDATA%\\Programs\\KiCad\\10.0\\bin\\python.exe" route_m2_freerouting.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import route_freerouting as rf

HERE = Path(__file__).resolve().parent
MOD = HERE / "modules"

rf.PCB = MOD / "m2_opto4.kicad_pcb"
rf.DSN = MOD / "out_freerouting" / "m2_opto4.dsn"
rf.SES = MOD / "out_freerouting" / "m2_opto4.ses"
rf.UNROUTED = MOD / "out_freerouting" / "m2_unrouted.kicad_pcb"
rf.ROUTED = MOD / "out_freerouting" / "m2_routed.kicad_pcb"

# The first pass (500 um, same as the main carrier) passed KiCad DRC and our
# own A5-A7 checker (0 violations either way) but still LOOKED wrong: several
# diagonal shortcuts grazed past unrelated pad rings within a few tenths of a
# mm. This tiny board has plenty of slack (it was laid out with 0.7 mm part
# clearance to begin with), so push the DSN keepout well past the numeric
# minimum -- routes should visibly clear every foreign hole, not just clear
# it by the letter of the rule.
rf.A7_CLEARANCE_UM = 900


def main() -> int:
    jar = rf.find_freerouting()
    if jar is None:
        print("freerouting.jar not found (expected at ./tools/freerouting.jar).")
        return 2
    rf.export_dsn()
    best = None
    for i, (passes, via_cost) in enumerate(rf.FR_ATTEMPTS, 1):
        if not rf.run_freerouting(jar, passes, via_cost):
            print(f"  attempt {i}: no .ses produced")
            continue
        left = rf.import_ses()
        print(f"  attempt {i} (-mp {passes} -vc {via_cost}): {left} unconnected")
        if left == 0:
            best = 0
            break
        if best is None or left < best:
            best = left
            shutil.copy2(rf.ROUTED, rf.ROUTED.with_suffix(".best.kicad_pcb"))
    if best != 0:
        keep = rf.ROUTED.with_suffix(".best.kicad_pcb")
        if keep.is_file():
            shutil.copy2(keep, rf.ROUTED)
        print(f"  best attempt still leaves {best} unconnected")
    shutil.copy2(rf.ROUTED, rf.PCB)
    print(f"promoted -> {rf.PCB}")
    return 0 if best == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
