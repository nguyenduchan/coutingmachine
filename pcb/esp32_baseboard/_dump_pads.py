from pathlib import Path
import re

text = Path(__file__).with_name("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
for ref in [
    "U3", "U4", "U5", "U9", "J17", "J18", "J15", "J16", "J2", "J4",
    "J8", "J14", "F1", "U2", "U8", "R1", "R2", "R3", "D2", "R10", "J5",
]:
    for b in re.split(r"\n\t\(footprint ", text)[1:]:
        if f'"Reference" "{ref}"' not in b:
            continue
        pads = []
        for m in re.finditer(r'\(pad "([^"]*)"(.*?)\n\t\t\)', b, re.S):
            nm = re.search(r'\(net\s+\d+\s+"([^"]*)"\)', m.group(2))
            if nm:
                pads.append((m.group(1), nm.group(1)))
        print(ref, pads)
        break
    else:
        print(ref, "NOT FOUND")
