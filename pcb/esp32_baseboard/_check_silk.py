# -*- coding: utf-8 -*-
import re
from pathlib import Path

t = Path("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
texts = re.findall(r'\(gr_text "([^"]+)"[\s\S]*?\(layer "F\.SilkS"\)', t)
print(f"{len(texts)} gr_text on F.SilkS")
for s in texts:
    print(" ", s)
