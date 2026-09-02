"""One-shot ESP32 pin sanity vs PCB."""
from __future__ import annotations

import re
from pathlib import Path

from s3_pinmap import (
    BUZZER_GPIO,
    BYJ_GPIO,
    ENC_GPIO,
    MOSFET_GPIO,
    OPTO_GPIO,
    PIN_BY_NAME,
    TFT_GPIO,
    TMC_GPIO,
)

ROOT = Path(__file__).resolve().parent
pcb = (ROOT / "esp32_baseboard.kicad_pcb").read_text(encoding="utf-8")


def pads_of(ref: str) -> dict[str, str]:
    for b in re.split(r"\n\t\(footprint ", pcb)[1:]:
        if not re.search(rf'property "Reference" "{ref}"', b):
            continue
        out = {}
        for m in re.finditer(r'\(pad "([^"]*)"((?:(?!\(pad ")[\s\S])*)', b):
            nm = re.search(r'\(net\s+(?:\d+\s+)?"([^"]*)"\)', m.group(2))
            if nm:
                n = nm.group(1)
                out[m.group(1)] = n[1:] if n.startswith("/") else n
        return out
    return {}


u1 = pads_of("U1")
expect: dict[int, str] = {}
for i, (g, _) in enumerate(OPTO_GPIO, 1):
    expect[g] = f"OPTO_OUT{i}"
for ax, ph in BYJ_GPIO.items():
    for p, g in ph.items():
        expect[g] = f"BYJ{ax}_IN_{p}"
for k, g in TMC_GPIO.items():
    expect[g] = {"STEP": "STEP", "DIR": "DIR", "EN": "EN_TMC"}[k]
for k, g in TFT_GPIO.items():
    expect[g] = {
        "SCK": "TFT_SCK",
        "MOSI": "TFT_MOSI",
        "CS": "TFT_CS",
        "DC": "TFT_DC",
        "RST": "TFT_RST",
    }[k]
expect[ENC_GPIO["A"]] = "ENC_A"
expect[ENC_GPIO["B"]] = "ENC_B"
expect[BUZZER_GPIO] = "BUZZER"
expect[MOSFET_GPIO] = "BLOWER"

bad = []
for g, want in sorted(expect.items()):
    pad = str(PIN_BY_NAME[f"IO{g}"])
    got = u1.get(pad)
    if got != want:
        bad.append((g, pad, got, want))
print("U1 vs pinmap:", "OK" if not bad else bad)

for ax, uref in ((1, "U5"), (2, "U6"), (3, "U7")):
    ub = pads_of(uref)
    for i, ph in enumerate("ABCD", 1):
        want = f"BYJ{ax}_IN_{ph}"
        g = BYJ_GPIO[ax][ph]
        up = u1.get(str(PIN_BY_NAME[f"IO{g}"]))
        got = ub.get(str(i))
        if got != want or up != want:
            print(f"FAIL {uref}.IN{i}={got} U1.IO{g}={up} want {want}")
print("ULN IN links: checked")

for ref in ("J17", "J18", "J23", "J15", "U3"):
    print(ref, pads_of(ref))

print("\nCaveats (DevKit, not net errors):")
print("  IO38 = BYJ3_IN_A — DevKitC-1 v1.1 onboard WS2812 also on GPIO38")
print("  IO3  = BLOWER — strapping; R3 10k PD required (present)")
print("  IO45 = ENC_B — strapping + KY-040 PU; TFT_BL hardwired +3V3")
print("  IO46 = TFT_RST — strapping internal PD OK at boot")
print("  Touch T_CS/MISO/IRQ NC — intentional")
