"""Quick PCB status for routing prep."""
from pathlib import Path
import re, math
from collections import Counter

t = Path(r"d:\Project\coutingmachine\pcb\esp32_baseboard\esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
print("ULN2003_Module", t.count("ULN2003_Module"))
print("J5 ref", bool(re.search(r'Reference"\s+"J5"', t)))
via_sz = []
for m in re.finditer(r"\n\t\(via([\s\S]*?)\n\t\)", t):
    b = m.group(1)
    s = re.search(r"\(size ([-\d.]+)\)", b)
    d = re.search(r"\(drill ([-\d.]+)\)", b)
    if s and d:
        via_sz.append((round(float(s.group(1)), 2), round(float(d.group(1)), 2)))
print("via sizes", Counter(via_sz))
fl = bl = 0
for m in re.finditer(r"\n\t\(segment([\s\S]*?)\n\t\)", t):
    b = m.group(1)
    st = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", b)
    en = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", b)
    lay = re.search(r'\(layer "([^"]+)"\)', b)
    if st and en and lay:
        L = math.hypot(float(en.group(1)) - float(st.group(1)), float(en.group(2)) - float(st.group(2)))
        if lay.group(1) == "F.Cu":
            fl += L
        else:
            bl += L
print(f"F.Cu={fl:.0f}mm B.Cu={bl:.0f}mm ratio F/B={fl/max(bl,1):.2f}")
