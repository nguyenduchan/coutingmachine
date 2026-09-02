import re
from pathlib import Path
t=Path("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
m=re.search(r'\(gr_rect \(start ([0-9.]+) ([0-9.]+)\) \(end ([0-9.]+) ([0-9.]+)\)', t)
print("edge", m.groups() if m else None)
for ref in ["U1","U2","U3","U4","U5","U6","U7","U9","U10","U11","J1","H1","H2","H3","H4","C20","C21","J5","J8"]:
    for b in re.split(r"\n\t\(footprint ", t)[1:]:
        if f'(property "Reference" "{ref}"' in b:
            am=re.search(r"\(at ([0-9.\-]+) ([0-9.\-]+)(?:\s+([0-9.\-]+))?\)", b)
            print(ref, am.groups() if am else "?")
            break
