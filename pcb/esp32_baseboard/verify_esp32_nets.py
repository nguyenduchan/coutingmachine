#!/usr/bin/env python3
"""Verify ESP32-S3 pin functions + detect short conflicts on PCB."""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from s3_pinmap import (  # noqa: E402
    BUZZER_GPIO,
    DRV_MOTORS,
    ENC_GPIO,
    LEFT_PINS,
    MOSFET_GPIO,
    OPTO_GPIO,
    PIN_BY_NAME,
    RIGHT_PINS,
    TFT_GPIO,
    TMC_GPIO,
)

PCB = ROOT / "esp32_baseboard.kicad_pcb"

FORBIDDEN_GPIO = {35, 36, 37}  # octal PSRAM N16R8
RESERVED_GPIO = {0, 19, 20, 43, 44}  # BOOT / USB / UART0

# gpio_num -> expected net name on PCB
EXPECTED_NET: dict[int, str] = {}
for gpio, _name in OPTO_GPIO:
    EXPECTED_NET[gpio] = f"/OPTO_OUT{OPTO_GPIO.index((gpio, _name)) + 1}"
# Fix OUT numbering from list order
EXPECTED_NET = {}
for i, (gpio, _name) in enumerate(OPTO_GPIO, 1):
    EXPECTED_NET[gpio] = f"/OPTO_OUT{i}"

EXPECTED_NET[ENC_GPIO["A"]] = "/ENC_A"
EXPECTED_NET[ENC_GPIO["B"]] = "/ENC_B"
for uref, in1, in2, _nma, _nmb in DRV_MOTORS:
    axis = {"5": 1, "6": 2, "7": 3}[uref]
    EXPECTED_NET[in1] = f"/DC{axis}_IN1"
    EXPECTED_NET[in2] = f"/DC{axis}_IN2"
EXPECTED_NET[TMC_GPIO["STEP"]] = "/STEP"
EXPECTED_NET[TMC_GPIO["DIR"]] = "/DIR"
EXPECTED_NET[TMC_GPIO["EN"]] = "/EN_TMC"
EXPECTED_NET[TFT_GPIO["SCK"]] = "/TFT_SCK"
EXPECTED_NET[TFT_GPIO["MOSI"]] = "/TFT_MOSI"
EXPECTED_NET[TFT_GPIO["MISO"]] = "/TFT_MISO"
EXPECTED_NET[TFT_GPIO["CS"]] = "/TFT_CS"
EXPECTED_NET[TFT_GPIO["DC"]] = "/TFT_DC"
EXPECTED_NET[TFT_GPIO["RST"]] = "/TFT_RST"
EXPECTED_NET[TFT_GPIO["BL"]] = "/TFT_BL"
EXPECTED_NET[TFT_GPIO["T_CS"]] = "/T_CS"
EXPECTED_NET[BUZZER_GPIO] = "/BUZZER"
EXPECTED_NET[MOSFET_GPIO] = "/BLOWER"

STRAP_NOTES = {
    3: "no internal pull — need R3 10k PD (BLOWER)",
    45: "internal PD — safe for TFT_BL off at boot",
    46: "internal PD — safe for TFT_RST held at boot",
}


def parse_all_pads(text: str) -> dict[str, list[tuple[str, int, str]]]:
    blocks = re.split(r"\n\t\(footprint ", text)[1:]
    by_ref: dict[str, list] = {}
    for b in blocks:
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        if not rm:
            continue
        ref = rm.group(1)
        pads = []
        for pad_block in re.finditer(r'\(pad "([^"]*)"(.*?)\n\t\t\)', b, re.S):
            pname = pad_block.group(1)
            body = pad_block.group(2)
            nm = re.search(r'\(net\s+(\d+)\s+"([^"]*)"\)', body)
            if not nm:
                continue
            pads.append((pname, int(nm.group(1)), nm.group(2)))
        by_ref[ref] = pads
    return by_ref


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    pads_by_ref = parse_all_pads(text)
    nets = dict(re.findall(r'\(net\s+(\d+)\s+"([^"]*)"\)', text))
    nets = {int(k): v for k, v in nets.items()}

    print("=== 1) Pinmap conflicts (s3_pinmap) ===")
    gpios = list(EXPECTED_NET.keys())
    dups = [g for g, n in Counter(gpios).items() if n > 1]
    print(f"Assigned GPIOs: {len(gpios)}")
    if dups:
        print("FAIL duplicate:", dups)
    else:
        print("PASS no duplicate GPIO")

    forbid = [g for g in gpios if g in FORBIDDEN_GPIO]
    if forbid:
        print("FAIL forbidden IO35/36/37 used:", forbid)
    else:
        print("PASS no IO35/36/37 (octal PSRAM)")

    reserved_hit = [g for g in gpios if g in RESERVED_GPIO]
    if reserved_hit:
        print("FAIL reserved USB/UART/BOOT used:", reserved_hit)
    else:
        print("PASS USB/UART0/BOOT free")

    # IO37 on header must not be routed
    print("\n=== 2) U1 pad nets vs expected functions ===")
    u1 = {p: (nid, nn) for p, nid, nn in pads_by_ref.get("U1", [])}
    if not u1:
        print("FAIL U1 not found")
        return 1

    fails = []
    oks = []
    for gpio, want in sorted(EXPECTED_NET.items()):
        name = f"IO{gpio}"
        if name not in PIN_BY_NAME:
            fails.append(f"{name}: not in PIN_BY_NAME")
            continue
        pad = str(PIN_BY_NAME[name])
        if pad not in u1:
            fails.append(f"{name} pad{pad}: no net on U1")
            continue
        got = u1[pad][1]
        note = STRAP_NOTES.get(gpio, "")
        extra = f" [{note}]" if note else ""
        if got == want:
            oks.append(f"{name:5} pad{pad:>2} -> {got}{extra}")
        else:
            fails.append(f"{name} pad{pad}: got {got!r} want {want!r}")

    # Power pads
    for label, candidates in [
        ("+5V", ["5V"]),
        ("+3V3", ["3V3", "3V3b"]),
        ("GND", ["GND", "GNDb", "GNDc"]),
    ]:
        found = []
        for n in candidates:
            if n in PIN_BY_NAME:
                p = str(PIN_BY_NAME[n])
                if p in u1:
                    found.append((n, p, u1[p][1]))
        ok_pwr = all(nn == label for _, _, nn in found) and found
        status = "OK" if ok_pwr else "FAIL"
        print(f"  {status} {label}: {found}")

    print(f"\nIO function OK: {len(oks)}/{len(EXPECTED_NET)}")
    for line in oks:
        print(" ", line)
    if fails:
        print(f"\nIO MISMATCH: {len(fails)}")
        for line in fails:
            print("  FAIL", line)
    else:
        print("\nPASS all functional GPIOs match PCB nets")

    # Header pins that must stay NC / free
    print("\n=== 3) Unused / must-not-route header pads ===")
    must_free = {
        "IO35": FORBIDDEN_GPIO,
        "IO36": FORBIDDEN_GPIO,
        "IO37": FORBIDDEN_GPIO,
        "IO0": "BOOT",
        "IO19": "USB",
        "IO20": "USB",
        "TX0": "UART0",
        "RX0": "UART0",
        "RST": "EN",
    }
    for silk, reason in must_free.items():
        if silk not in PIN_BY_NAME:
            continue
        p = str(PIN_BY_NAME[silk])
        if p not in u1:
            print(f"  OK {silk} pad{p}: no net (unconnected)")
        else:
            nn = u1[p][1]
            # unconnected pads might still have empty or no entry
            print(f"  WARN {silk} pad{p}: net={nn} ({reason}) — should be unused")

    print("\n=== 4) Co-located pad short check ===")
    pad_pos: dict[tuple[float, float], list[tuple[str, str, str]]] = defaultdict(list)
    blocks = re.split(r"\n\t\(footprint ", text)[1:]
    for b in blocks:
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        am = re.search(r"\(at ([0-9.\-]+) ([0-9.\-]+)(?:\s+([0-9.\-]+))?\)", b)
        if not rm or not am:
            continue
        ref = rm.group(1)
        ax, ay = float(am.group(1)), float(am.group(2))
        rot = float(am.group(3) or 0)
        for pad_block in re.finditer(r'\(pad "([^"]*)"(.*?)\n\t\t\)', b, re.S):
            pname = pad_block.group(1)
            body = pad_block.group(2)
            if "np_thru_hole" in body:
                continue
            atm = re.search(r"\(at ([0-9.\-]+) ([0-9.\-]+)", body)
            nm = re.search(r'\(net\s+(\d+)\s+"([^"]*)"\)', body)
            if not atm or not nm:
                continue
            lx, ly = float(atm.group(1)), float(atm.group(2))
            if abs(rot - 180) < 1:
                wx, wy = ax - lx, ay - ly
            elif abs(rot) < 1:
                wx, wy = ax + lx, ay + ly
            else:
                # ignore odd rotations for this heuristic
                continue
            key = (round(wx, 2), round(wy, 2))
            pad_pos[key].append((ref, pname, nm.group(2)))

    shorts = []
    for pos, items in pad_pos.items():
        nets_here = {n for _, _, n in items}
        if len(items) > 1 and len(nets_here) > 1:
            shorts.append((pos, items))

    if shorts:
        print(f"FAIL overlapping pads different nets: {len(shorts)}")
        for pos, items in shorts[:25]:
            print(f"  @{pos} {items}")
    else:
        print("PASS no overlapping pads with conflicting nets")

    print("\n=== 5) GPIO tied to power? ===")
    bad = []
    for gpio in EXPECTED_NET:
        name = f"IO{gpio}"
        p = str(PIN_BY_NAME[name])
        if p in u1 and u1[p][1] in ("GND", "+5V", "+3V3", "+12V", "+12V_RAW", "+5V_BLW"):
            bad.append((name, u1[p][1]))
    if bad:
        print("FAIL", bad)
    else:
        print("PASS no GPIO shorted to power rail")

    print("\n=== 6) Design leftovers ===")
    miso = [v for v in nets.values() if "MISO" in v]
    tint = [v for v in nets.values() if "INT" in v and "TFT" in v]
    print("MISO nets:", miso or "none (good)")
    print("TFT INT nets:", tint or "none (good)")
    out8 = [v for v in nets.values() if "OUT8" in v]
    print("OPTO_OUT8 net present:", out8, "(field only — must NOT be on U1)")
    if any(nn == "/OPTO_OUT8" for _, nn in u1.values()):
        print("FAIL OPTO_OUT8 connected to U1")
    else:
        print("PASS OPTO_OUT8 not on U1 (ENC uses IO9)")

    print("\n=== SUMMARY ===")
    ok = (
        not dups
        and not forbid
        and not reserved_hit
        and not fails
        and not shorts
        and not bad
    )
    print("OVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
