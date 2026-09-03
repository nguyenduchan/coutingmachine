#!/usr/bin/env python3
"""Run A5–A7 geometry checks on any .kicad_pcb (carrier or sub-module)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Reuse carrier checker by pointing PCB path
import _check_signal_routing as csr


def main() -> int:
    paths = sys.argv[1:] or [
        str(ROOT / "esp32_baseboard.kicad_pcb"),
        str(ROOT / "modules" / "m1_power_prot.kicad_pcb"),
        str(ROOT / "modules" / "m2_opto4.kicad_pcb"),
    ]
    bad = 0
    for p in paths:
        path = Path(p)
        if not path.is_file():
            print(f"SKIP missing {path}")
            continue
        print(f"\n######## {path.name} ########")
        csr.PCB = path
        rc = csr.main()
        if rc:
            bad += 1
    print(f"\n==== A5-A7 boards FAIL: {bad}/{len(paths)} ====")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
