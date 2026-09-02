#!/usr/bin/env python3
"""Verify ESP32-S3 pin functions + detect short conflicts on PCB."""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pcb_parse import NetTable

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from s3_pinmap import (  # noqa: E402
    BUZZER_GPIO,
    ENC_GPIO,
    LEFT_PINS,
    MOSFET_GPIO,
    OPTO_GPIO,
    PIN_BY_NAME,
    RIGHT_PINS,
    SHIFT_GPIO,
    SPARE_GPIO,
    TFT_GPIO,
    TMC_GPIO,
)

PCB = ROOT / "esp32_baseboard.kicad_pcb"

FORBIDDEN_GPIO = {35, 36, 37}
RESERVED_GPIO = {0, 19, 20, 43, 44}

EXPECTED_NET: dict[int, str] = {}
for i, (gpio, _name) in enumerate(OPTO_GPIO, 1):
    EXPECTED_NET[gpio] = f"OPTO_OUT{i}"
EXPECTED_NET[SHIFT_GPIO["SER"]] = "SER"
EXPECTED_NET[SHIFT_GPIO["SRCLK"]] = "SRCLK"
EXPECTED_NET[SHIFT_GPIO["RCLK"]] = "RCLK"
EXPECTED_NET[SHIFT_GPIO["OE"]] = "OE_595"
EXPECTED_NET[ENC_GPIO["A"]] = "ENC_A"
EXPECTED_NET[ENC_GPIO["B"]] = "ENC_B"
EXPECTED_NET[TMC_GPIO["STEP"]] = "STEP"
EXPECTED_NET[TMC_GPIO["DIR"]] = "DIR"
EXPECTED_NET[TMC_GPIO["EN"]] = "EN_TMC"
EXPECTED_NET[TFT_GPIO["SCK"]] = "TFT_SCK"
EXPECTED_NET[TFT_GPIO["MOSI"]] = "TFT_MOSI"
EXPECTED_NET[TFT_GPIO["MISO"]] = "TFT_MISO"
EXPECTED_NET[TFT_GPIO["CS"]] = "TFT_CS"
EXPECTED_NET[TFT_GPIO["DC"]] = "TFT_DC"
EXPECTED_NET[TFT_GPIO["RST"]] = "TFT_RST"
EXPECTED_NET[TFT_GPIO["BL"]] = "TFT_BL"
EXPECTED_NET[TFT_GPIO["T_CS"]] = "T_CS"
EXPECTED_NET[TFT_GPIO["T_IRQ"]] = "T_IRQ"
EXPECTED_NET[BUZZER_GPIO] = "BUZZER"
EXPECTED_NET[MOSFET_GPIO] = "BLOWER"

STRAP_NOTES = {
    3: "BLOWER — need R3 10k PD",
    13: "OE_595 — need R4 10k PU",
    45: "TFT_BL — internal PD safe at boot",
    46: "TFT_RST — internal PD safe at boot",
    38: "ENC_A — DevKit v1.1 WS2812 also on IO38",
}


def parse_all_pads(text: str, table=None):
    by_ref = {}
    for b in re.split(r"\n\t\(footprint ", text)[1:]:
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        if not rm:
            continue
        ref = rm.group(1)
        pads = []
        for pad_block in re.finditer(r'\(pad "([^"]*)"((?:(?!\(pad ")[\s\S])*)', b):
            pname = pad_block.group(1)
            body = pad_block.group(2)
            nm = re.search(r'\(net\s+(?:\d+\s+)?"([^"]*)"\)', body)
            if not nm:
                continue
            pads.append((pname, table.id_of(nm.group(1)), nm.group(1)))
        by_ref[ref] = pads
    return by_ref


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    table = NetTable(text)
    pads_by_ref = parse_all_pads(text, table)
    nets = {int(k): v for k, v in dict(table.by_id).items()}

    print("=== 1) Pinmap conflicts ===")
    gpios = list(EXPECTED_NET.keys())
    dups = [g for g, n in Counter(gpios).items() if n > 1]
    print(f"Assigned GPIOs: {len(gpios)}")
    print("PASS no duplicate GPIO" if not dups else f"FAIL {dups}")
    forbid = [g for g in gpios if g in FORBIDDEN_GPIO]
    print("PASS no IO35/36/37" if not forbid else f"FAIL {forbid}")
    reserved_hit = [g for g in gpios if g in RESERVED_GPIO]
    print("PASS USB/UART0/BOOT free" if not reserved_hit else f"FAIL {reserved_hit}")

    print("\n=== 2) U1 pad nets ===")
    u1 = {p: (nid, nn) for p, nid, nn in pads_by_ref.get("U1", [])}
    fails, oks = [], []
    for gpio, want in sorted(EXPECTED_NET.items()):
        name = f"IO{gpio}"
        pad = str(PIN_BY_NAME[name])
        if pad not in u1:
            fails.append(f"{name}: no net")
            continue
        got = u1[pad][1]
        got_n = got[1:] if got.startswith("/") else got
        note = STRAP_NOTES.get(gpio, "")
        extra = f" [{note}]" if note else ""
        if got_n == want:
            oks.append(f"{name:5} pad{pad:>2} -> {got_n}{extra}")
        else:
            fails.append(f"{name}: got {got!r} want {want!r}")
    print(f"IO function OK: {len(oks)}/{len(EXPECTED_NET)}")
    for line in oks:
        print(" ", line)
    for line in fails:
        print(" FAIL", line)

    print("\n=== 3b) Spare ===")
    spare_ok = True
    for g in SPARE_GPIO:
        p = str(PIN_BY_NAME[f"IO{g}"])
        if p in u1 and not str(u1[p][1]).startswith("unconnected-"):
            print(f" FAIL IO{g} routed")
            spare_ok = False
        else:
            print(f"  OK IO{g} free")
    print(f"PASS spare {SPARE_GPIO}" if spare_ok else "FAIL spare")

    print("\n=== 6) Leftovers ===")
    sr = [v for v in nets.values() if v.startswith("BYJ") and "_IN_" in v]
    print("direct BYJ_IN leftovers:", sr or "none (good)")
    if sr:
        fails.append(str(sr))

    ok = not dups and not forbid and not reserved_hit and not fails and spare_ok
    print("\n=== SUMMARY ===")
    print("OVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
