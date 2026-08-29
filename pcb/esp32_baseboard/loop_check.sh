#!/bin/sh
# One iteration of the fix loop:
#   1. generate placement + nets (no routing)
#   2. rebuild the schematic from the board, and name its netless pads
#   3. route with FreeRouting -- it must see those nets, or it lays copper over
#      pads it thinks are free and KiCad reports the result as shorts
#   4. re-sync the footprint library from what was actually placed
#   5. KiCad DRC, including schematic parity
set -e
KI="$LOCALAPPDATA/Programs/KiCad/10.0/bin"
PCB_SKIP_MAZE=1 python gen_power_carrier.py > _gen.log 2>&1
python gen_schematic_from_pcb.py
"$KI/python.exe" route_freerouting.py > _route.log 2>&1
grep -E "unrouted\)" _route.log | tail -1 || true
python sync_footprint_lib.py
"$KI/kicad-cli.exe" pcb drc --severity-error --severity-warning \
  --schematic-parity --units mm --format report -o drc_report.txt \
  esp32_baseboard.kicad_pcb > /dev/null 2>&1
grep -oE '^\[[a-z_]+\]' drc_report.txt | sort | uniq -c | sort -rn || echo "  DRC clean"
