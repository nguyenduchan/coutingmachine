#!/usr/bin/env python3
"""Connectivity audit: ESP32 ↔ 74HC595-24IO module ↔ ULN ↔ jacks."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from s3_pinmap import (  # noqa: E402
    BUZZER_GPIO,
    ENC_GPIO,
    MOSFET_GPIO,
    OPTO_GPIO,
    PIN_BY_NAME,
    SHIFT_GPIO,
    SPARE_GPIO,
    TFT_GPIO,
    TMC_GPIO,
)

PCB = ROOT / "esp32_baseboard.kicad_pcb"


def _norm_net(n):
    if not isinstance(n, str):
        return n
    if n.startswith("unconnected-("):
        return None
    return n[1:] if n.startswith("/") else n


def parse_pads(text: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for b in re.split(r"\n\t\(footprint ", text)[1:]:
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        if not rm:
            continue
        ref = rm.group(1)
        pads = {}
        for m in re.finditer(r'\(pad "([^"]*)"((?:(?!\(pad ")[\s\S])*)', b):
            nm = re.search(r'\(net\s+(?:\d+\s+)?"([^"]*)"\)', m.group(2))
            if nm:
                pads[m.group(1)] = _norm_net(nm.group(1))
        out[ref] = pads
    return out


def u1_gpio_net(pads, gpio: int):
    return pads.get("U1", {}).get(str(PIN_BY_NAME[f"IO{gpio}"]))


def check(cond, ok, fail, msg):
    (ok if cond else fail).append(msg)


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    pads = parse_pads(text)
    ok, fail = [], []

    print("=== A) ESP32 GPIO ===")
    expect = {}
    for i, (gpio, _) in enumerate(OPTO_GPIO, 1):
        expect[gpio] = f"OPTO_OUT{i}"
    expect[SHIFT_GPIO["SER"]] = "SER"
    expect[SHIFT_GPIO["SRCLK"]] = "SRCLK"
    expect[SHIFT_GPIO["RCLK"]] = "RCLK"
    expect[SHIFT_GPIO["OE"]] = "OE_595"
    expect[ENC_GPIO["A"]] = "ENC_A"
    expect[ENC_GPIO["B"]] = "ENC_B"
    expect[TMC_GPIO["STEP"]] = "STEP"
    expect[TMC_GPIO["DIR"]] = "DIR"
    expect[TMC_GPIO["EN"]] = "EN_TMC"
    for k, g in TFT_GPIO.items():
        expect[g] = {
            "SCK": "TFT_SCK", "MOSI": "TFT_MOSI", "MISO": "TFT_MISO",
            "CS": "TFT_CS", "DC": "TFT_DC", "RST": "TFT_RST", "BL": "TFT_BL",
            "T_CS": "T_CS", "T_IRQ": "T_IRQ",
        }[k]
    expect[BUZZER_GPIO] = "BUZZER"
    expect[MOSFET_GPIO] = "BLOWER"
    for g, want in sorted(expect.items()):
        got = u1_gpio_net(pads, g)
        check(got == want, ok, fail, f"U1 IO{g} = {got!r} (want {want})")
    for g in (0, 19, 20, 35, 36, 37) + tuple(SPARE_GPIO):
        check(u1_gpio_net(pads, g) is None, ok, fail, f"U1 IO{g} unconnected")

    print("\n=== B) TMC ===")
    u3 = set(pads.get("U3", {}).values())
    for n in ("STEP", "DIR", "EN_TMC", "+12V", "+3V3", "GND"):
        check(n in u3, ok, fail, f"U3 has {n}")

    print("\n=== C) Opto on-board PC817×4 (ex-M2) ===")
    for gone in ("J31A", "J31B", "J31", "J30"):
        check(gone not in pads, ok, fail, f"{gone} removed")
    for uref in ("U41", "U42", "U43", "U44"):
        check(uref in pads, ok, fail, f"{uref} on carrier")
    for rref in ("R41", "R42", "R43", "R44", "R45", "R46", "R47", "R48"):
        check(rref in pads, ok, fail, f"{rref} on carrier")
    check("C26" in pads, ok, fail, "C26 SNS HF @ opto")
    for gone in ("U45", "U46", "U47", "U48"):
        check(gone not in pads, ok, fail, f"{gone} not used (4ch only)")
    for jref in ("J8", "J10", "J12"):
        jh = pads.get(jref, {})
        check(len(jh) == 2, ok, fail, f"{jref} XH-2 pads")
        check(jh.get("2") == "+12V_SNS", ok, fail, f"{jref}.2 SNS")

    print("\n=== C2) Power protection on carrier (ex-M1) ===")
    for pref in ("D3", "F1", "D1"):
        check(pref in pads, ok, fail, f"{pref} on carrier")
    check(pads.get("D2", {}).get("2") == "BLW_RET" or "BLW_RET" in pads.get("D2", {}).values(), ok, fail, "D2 flyback")
    check("D4" not in pads, ok, fail, "D4 removed")
    check("C24" in pads and "C25" in pads, ok, fail, "C24/C25 HF")
    check("J2" not in pads, ok, fail, "J2 removed (Mot on U3)")

    print("\n=== D) 74HC595-24IO module + ULN module (28BYJ on module JST) ===")
    j24 = pads.get("J24", {})
    check(j24.get("1") == "OE_595", ok, fail, "J24.1 LDEN")
    check(j24.get("2") == "GND", ok, fail, "J24.2 GND")
    check(j24.get("3") == "+3V3", ok, fail, "J24.3 VCC")
    check(j24.get("4") == "SER", ok, fail, "J24.4 LDSI")
    check(j24.get("5") == "RCLK", ok, fail, "J24.5 LDSTR")
    check(j24.get("6") == "SRCLK", ok, fail, "J24.6 LDSCK")
    j25 = pads.get("J25", {})
    for i, n in enumerate(
        ["SR_Q0", "SR_Q1", "SR_Q2", "SR_Q3", "SR_Q4", "SR_Q5",
         "SR_Q6", "SR_Q7", "SR_Q8", "SR_Q9", "SR_Q10", "SR_Q11"],
        1,
    ):
        check(j25.get(str(i)) == n, ok, fail, f"J25.{i} {n}")
    r4 = pads.get("R4", {})
    check("+3V3" in r4.values() and "OE_595" in r4.values(), ok, fail, "R4 LDEN PU")
    for uref, qs in (
        ("U5", ("SR_Q0", "SR_Q1", "SR_Q2", "SR_Q3")),
        ("U6", ("SR_Q4", "SR_Q5", "SR_Q6", "SR_Q7")),
        ("U7", ("SR_Q8", "SR_Q9", "SR_Q10", "SR_Q11")),
    ):
        un = set(pads.get(uref, {}).values())
        check("+12V" in un and "GND" in un, ok, fail, f"{uref} +12V/GND")
        for q in qs:
            check(q in un, ok, fail, f"{uref} {q}")
        check(not any(str(n).startswith("BYJ") for n in un), ok, fail, f"{uref} no BYJ phase nets")
    for gone in ("J5", "J6", "J7"):
        check(gone not in pads, ok, fail, f"{gone} removed (28BYJ on ULN module JST)")
    check("74HC595-24IO" in text or "595-24IO" in text or "PinHeader_1x24_595Q" in text, ok, fail, "595 module on PCB")
    check("ULN2003_Module" in text, ok, fail, "ULN2003_Module footprint")

    print("\n=== E) HMI ===")
    j17 = pads.get("J17", {})
    for p, w in {"1": "+3V3", "2": "GND", "3": "TFT_CS", "4": "TFT_RST",
                 "5": "TFT_DC", "6": "TFT_MOSI", "7": "TFT_SCK", "8": "TFT_BL"}.items():
        check(j17.get(p) == w, ok, fail, f"J17.{p}")
    j23 = pads.get("J23", {})
    for p, w in {"1": "TFT_SCK", "2": "T_CS", "3": "TFT_MOSI", "4": "TFT_MISO", "5": "T_IRQ"}.items():
        check(j23.get(p) == w, ok, fail, f"J23.{p}")
    j18 = pads.get("J18", {})
    for p, w in {"1": "GND", "2": "+3V3", "3": "ENC_A", "4": "ENC_B"}.items():
        check(j18.get(p) == w, ok, fail, f"J18.{p}")

    print(f"\nSUMMARY: {len(ok)} OK, {len(fail)} FAIL")
    for m in fail:
        print(" FAIL", m)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
