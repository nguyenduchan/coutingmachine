import re
from pathlib import Path
text = Path(__file__).with_name("esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")
nets = {int(a): b for a, b in re.findall(r'\(net\s+(\d+)\s+"([^"]*)"\)', text)}
for want in ("/DC1_IN1", "/DC1_IN2", "/DC2_IN1"):
    print("===", want, "===")
    ni = [k for k, v in nets.items() if v == want][0]
    for m in re.finditer(
        r'\(segment\s+\(start\s+([\d.-]+)\s+([\d.-]+)\)\s+\(end\s+([\d.-]+)\s+([\d.-]+)\)'
        r'\s+\(width\s+([\d.-]+)\)\s+\(layer\s+"([^"]+)"\)\s+\(net\s+(\d+)\)',
        text,
    ):
        if int(m.group(7)) != ni:
            continue
        print(f"  {m.group(6)} {m.group(1)},{m.group(2)} -> {m.group(3)},{m.group(4)}")
