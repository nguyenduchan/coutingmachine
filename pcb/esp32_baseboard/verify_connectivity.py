#!/usr/bin/env python3
"""Deep connectivity audit: ESP32 ↔ modules ↔ jacks (same nets, correct pins).

Path-only routing is ignored — only pad net membership matters.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from s3_pinmap import (  # noqa: E402
    BUZZER_GPIO,
    DRV_MOTORS,
    ENC_GPIO,
    MOSFET_GPIO,
    OPTO_GPIO,
    PIN_BY_NAME,
    TFT_GPIO,
    TMC_GPIO,
)

PCB = ROOT / "esp32_baseboard.kicad_pcb"


def _norm_net(n):
    """Normalise a pad's net for comparison.

    Two things to absorb: the board now carries KiCad-native bare names (STEP)
    where these tables were written against the old "/STEP" form, and a pin
    deliberately left unconnected carries KiCad's placeholder net
    "unconnected-(U1-IO0-Pad36)", which means exactly "no connection".
    """
    if not isinstance(n, str):
        return n
    if n.startswith("unconnected-("):
        return None
    return n[1:] if n.startswith("/") else n


def parse_pads(text: str) -> dict[str, dict[str, str]]:
    """ref -> {pad_name: net_name}"""
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


def u1_gpio_net(pads: dict[str, dict[str, str]], gpio: int) -> str | None:
    name = f"IO{gpio}"
    p = str(PIN_BY_NAME[name])
    return pads.get("U1", {}).get(p)


def check(cond: bool, ok: list, fail: list, msg: str) -> None:
    (ok if cond else fail).append(msg)


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    pads = parse_pads(text)
    ok: list[str] = []
    fail: list[str] = []
    warn: list[str] = []

    # --- ESP32 control nets present ---
    print("=== A) ESP32 GPIO -> expected nets ===")
    expect = {}
    for i, (gpio, _) in enumerate(OPTO_GPIO, 1):
        expect[gpio] = f"OPTO_OUT{i}"
    expect[ENC_GPIO["A"]] = "ENC_A"
    expect[ENC_GPIO["B"]] = "ENC_B"
    for uref, in1, in2, _, _ in DRV_MOTORS:
        ax = {"5": 1, "6": 2, "7": 3}[uref]
        expect[in1] = f"DC{ax}_IN1"
        expect[in2] = f"DC{ax}_IN2"
    expect[TMC_GPIO["STEP"]] = "STEP"
    expect[TMC_GPIO["DIR"]] = "DIR"
    expect[TMC_GPIO["EN"]] = "EN_TMC"
    for k, g in TFT_GPIO.items():
        expect[g] = {
            "SCK": "TFT_SCK",
            "MOSI": "TFT_MOSI",
            "MISO": "TFT_MISO",
            "CS": "TFT_CS",
            "DC": "TFT_DC",
            "RST": "TFT_RST",
            "BL": "TFT_BL",
            "T_CS": "T_CS",
        }[k]
    expect[BUZZER_GPIO] = "BUZZER"
    expect[MOSFET_GPIO] = "BLOWER"

    for g, want in sorted(expect.items()):
        got = u1_gpio_net(pads, g)
        check(got == want, ok, fail, f"U1 IO{g} = {got!r} (want {want})")

    # Forbidden / free
    for g in (0, 19, 20, 35, 36, 37):
        got = u1_gpio_net(pads, g)
        check(got is None, ok, fail, f"U1 IO{g} unconnected (got {got})")

    # Power on U1
    check(pads["U1"].get(str(PIN_BY_NAME["5V"])) == "+5V", ok, fail, "U1 5V = +5V")
    check(pads["U1"].get(str(PIN_BY_NAME["3V3"])) == "+3V3", ok, fail, "U1 3V3 = +3V3")
    check(pads["U1"].get(str(PIN_BY_NAME["GND"])) == "GND", ok, fail, "U1 GND = GND")

    # --- TMC2209 ---
    print("\n=== B) U3 TMC2209 <-> ESP32 / power / J2 ===")
    u3 = pads.get("U3", {})
    # Common stepstick silk: often EN/STEP/DIR/VM/GND/VIO/A1/A2/B1/B2 — check by net presence
    tmc_want = {
        "STEP": TMC_GPIO["STEP"],
        "DIR": TMC_GPIO["DIR"],
        "EN_TMC": TMC_GPIO["EN"],
        "+12V": None,
        "+3V3": None,
        "GND": None,
        "MotA1": None,
        "MotA2": None,
        "MotB1": None,
        "MotB2": None,
    }
    u3_nets = set(u3.values())
    for n in tmc_want:
        check(n in u3_nets, ok, fail, f"U3 has net {n}")
    for n, g in [("STEP", TMC_GPIO["STEP"]), ("DIR", TMC_GPIO["DIR"]), ("EN_TMC", TMC_GPIO["EN"])]:
        check(u1_gpio_net(pads, g) == n and n in u3_nets, ok, fail, f"U1 IO{g} <-> U3 on {n}")

    j2 = pads.get("J2", {})
    for n in ("MotA2", "MotA1", "MotB1", "MotB2"):
        check(n in j2.values() and n in u3_nets, ok, fail, f"J2 <-> U3 on {n}")

    # EN pull-up R2
    r2 = pads.get("R2", {})
    check("+3V3" in r2.values() and "EN_TMC" in r2.values(), ok, fail, "R2 bridges +3V3 <-> /EN_TMC")

    # --- Opto U4/U9 ---
    print("\n=== C) Opto U4/U9 <-> ESP32 / field / limits / BUP ===")
    # OUT1..7 on MCU; OUT8 must NOT be on U1
    for i, (gpio, _) in enumerate(OPTO_GPIO, 1):
        n = f"OPTO_OUT{i}"
        check(u1_gpio_net(pads, gpio) == n, ok, fail, f"OPTO_OUT{i} → IO{gpio}")
        # OUT pads on U4 (ch1-4) / U9 (ch5-7)
        if i <= 4:
            check(n in pads.get("U4", {}).values(), ok, fail, f"U4 carries {n}")
        else:
            check(n in pads.get("U9", {}).values(), ok, fail, f"U9 carries {n}")

    check("OPTO_OUT8" in pads.get("U9", {}).values(), ok, fail, "U9 has OPTO_OUT8 (field only)")
    check("OPTO_OUT8" not in pads.get("U1", {}).values(), ok, fail, "U1 has no /OPTO_OUT8")
    check(u1_gpio_net(pads, 9) == "BUZZER", ok, fail, "IO9 = BUZZER (not OPTO_OUT8)")

    # Field IN shared GND/VCC
    for ref in ("U4", "U9"):
        nets = set(pads.get(ref, {}).values())
        check("GND" in nets, ok, fail, f"{ref} has GND")
        check("OPTO_VCC_I" in nets, ok, fail, f"{ref} has /OPTO_VCC_I")
        check("+3V3" in nets, ok, fail, f"{ref} MCU-side +3V3")

    # Limit jacks J8-J13 → OPTO_IN1..6
    lim_map = [
        ("J8", "OPTO_IN1"),
        ("J9", "OPTO_IN2"),
        ("J10", "OPTO_IN3"),
        ("J11", "OPTO_IN4"),
        ("J12", "OPTO_IN5"),
        ("J13", "OPTO_IN6"),
    ]
    for jref, nin in lim_map:
        jnets = set(pads.get(jref, {}).values())
        check(nin in jnets and "+12V_SNS" in jnets, ok, fail, f"{jref} = +12V_SNS + {nin}")
        # IN must appear on U4 or U9
        on_u = nin in pads.get("U4", {}).values() or nin in pads.get("U9", {}).values()
        check(on_u, ok, fail, f"{nin} on U4 or U9")

    # BUP J14
    j14 = pads.get("J14", {})
    check("+12V_SNS" in j14.values(), ok, fail, "J14 has +12V_SNS")
    check("GND" in j14.values(), ok, fail, "J14 has GND")
    check("OPTO_IN7" in j14.values(), ok, fail, "J14 OUT = /OPTO_IN7")
    check("OPTO_IN7" in pads.get("U9", {}).values(), ok, fail, "U9 has /OPTO_IN7 (BUP)")
    r1 = pads.get("R1", {})
    check("+12V_SNS" in r1.values() and "OPTO_IN7" in r1.values(), ok, fail, "R1 pullup +12V_SNS <-> /OPTO_IN7")

    # J4 field header should carry IN1..8 + power
    j4 = pads.get("J4", {})
    check(j4.get("1") == "GND", ok, fail, "J4.1 = GND")
    check(j4.get("2") == "OPTO_VCC_I", ok, fail, "J4.2 = /OPTO_VCC_I")
    for i in range(1, 9):
        check(j4.get(str(i + 2)) == f"OPTO_IN{i}", ok, fail, f"J4.{i+2} = /OPTO_IN{i}")

    # Channel pairing: OPTO_INk and OPTO_OUTk on same module
    for i in range(1, 5):
        u4n = set(pads["U4"].values())
        check(f"OPTO_IN{i}" in u4n and f"OPTO_OUT{i}" in u4n, ok, fail, f"U4 pairs IN{i}/OUT{i}")
    for i in range(5, 9):
        u9n = set(pads["U9"].values())
        check(f"OPTO_IN{i}" in u9n and f"OPTO_OUT{i}" in u9n, ok, fail, f"U9 pairs IN{i}/OUT{i}")

    # --- DRV8871 ---
    print("\n=== D) DRV8871 U5-U7 <-> ESP32 / motors / power ===")
    for uref, in1, in2, nma, nmb in DRV_MOTORS:
        ref = f"U{uref}"
        ax = {"5": 1, "6": 2, "7": 3}[uref]
        unets = set(pads.get(ref, {}).values())
        check(f"DC{ax}_IN1" in unets, ok, fail, f"{ref} has /DC{ax}_IN1")
        check(f"DC{ax}_IN2" in unets, ok, fail, f"{ref} has /DC{ax}_IN2")
        check(u1_gpio_net(pads, in1) == f"DC{ax}_IN1", ok, fail, f"IO{in1} <-> {ref} IN1")
        check(u1_gpio_net(pads, in2) == f"DC{ax}_IN2", ok, fail, f"IO{in2} <-> {ref} IN2")
        check("+12V" in unets, ok, fail, f"{ref} +12V")
        check("GND" in unets, ok, fail, f"{ref} GND")
        jmot = f"J{uref}"  # J5/J6/J7
        jnets = set(pads.get(jmot, {}).values())
        check(f"MotDC{ax}_A" in jnets and f"MotDC{ax}_A" in unets, ok, fail, f"{jmot} <-> {ref} MotDC{ax}_A")
        check(f"MotDC{ax}_B" in jnets and f"MotDC{ax}_B" in unets, ok, fail, f"{jmot} <-> {ref} MotDC{ax}_B")

    # --- HMI jacks ---
    print("\n=== E) J17 TFT / J18 ENC / J15 buzzer / J16 blower ===")
    # J17 pin order (XPT remap): 1 GND, 2 3V3, 3 SCK, 4 MOSI, 5 MISO, 6 CS, 7 DC, 8 RST, 9 BL, 10 T_CS
    j17 = pads.get("J17", {})
    # Pads may be numbered 1..10
    j17_expect = {
        "1": "GND",
        "2": "+3V3",
        "3": "TFT_SCK",
        "4": "TFT_MOSI",
        "5": "TFT_MISO",
        "6": "TFT_CS",
        "7": "TFT_DC",
        "8": "TFT_RST",
        "9": "TFT_BL",
        "10": "T_CS",
    }
    for p, want in j17_expect.items():
        got = j17.get(p)
        check(got == want, ok, fail, f"J17.{p} = {got!r} (want {want})")
        if want.startswith("/"):
            # match ESP32
            gkey = {
                "TFT_SCK": TFT_GPIO["SCK"],
                "TFT_MOSI": TFT_GPIO["MOSI"],
                "TFT_MISO": TFT_GPIO["MISO"],
                "TFT_CS": TFT_GPIO["CS"],
                "TFT_DC": TFT_GPIO["DC"],
                "TFT_RST": TFT_GPIO["RST"],
                "TFT_BL": TFT_GPIO["BL"],
                "T_CS": TFT_GPIO["T_CS"],
            }[want]
            check(u1_gpio_net(pads, gkey) == want, ok, fail, f"J17.{p} <-> U1 IO{gkey}")

    j18 = pads.get("J18", {})
    j18_expect = {"1": "GND", "2": "+3V3", "3": "ENC_A", "4": "ENC_B"}
    for p, want in j18_expect.items():
        got = j18.get(p)
        check(got == want, ok, fail, f"J18.{p} = {got!r} (want {want})")
    check(u1_gpio_net(pads, ENC_GPIO["A"]) == "ENC_A", ok, fail, "ENC_A <-> IO9")
    check(u1_gpio_net(pads, ENC_GPIO["B"]) == "ENC_B", ok, fail, "ENC_B <-> IO41")

    j15 = pads.get("J15", {})
    check("BUZZER" in j15.values() and u1_gpio_net(pads, BUZZER_GPIO) == "BUZZER", ok, fail, "J15 SIG <-> IO38 /BUZZER")
    check("+5V" in j15.values() or any("5V" in v for v in j15.values()), ok, warn, f"J15 power nets: {j15}")

    j16 = pads.get("J16", {})
    check("BLOWER" in j16.values() and u1_gpio_net(pads, MOSFET_GPIO) == "BLOWER", ok, fail, "J16 PWM <-> IO3 /BLOWER")
    check("+12V" in j16.values(), ok, fail, "J16 has +12V (pump supply)")
    r3 = pads.get("R3", {})
    check("BLOWER" in r3.values() and "GND" in r3.values(), ok, fail, "R3 PD /BLOWER <-> GND")
    d2 = pads.get("D2", {})
    check("+12V" in d2.values() and "BLW_RET" in d2.values(), ok, fail, "D2 freewheel +12V <-> /BLW_RET")

    # --- Power tree ---
    print("\n=== F) Power tree ===")
    j1 = pads.get("J1", {})
    check("+12V_RAW" in j1.values() or "+12V" in j1.values(), ok, warn, f"J1 nets: {j1}")
    f1 = pads.get("F1", {})
    check("+12V_RAW" in f1.values() and "+12V" in f1.values(), ok, fail, "F1 PTC RAW→+12V")
    u2 = pads.get("U2", {})
    check("+12V" in u2.values() and "+5V" in u2.values(), ok, fail, "U2 MP1584 +12V->+5V")
    check("U8" not in pads, ok, fail, "U8 removed (single 5V buck U2 only)")
    r10 = pads.get("R10", {})
    check("+12V" in r10.values() and "+12V_SNS" in r10.values(), ok, fail, "R10 +12V->+12V_SNS")

    # --- Summary ---
    print("\n=== SUMMARY ===")
    print(f"PASS {len(ok)}  FAIL {len(fail)}  WARN {len(warn)}")
    if fail:
        print("\nFAILURES:")
        for m in fail:
            print(" ", m)
    if warn:
        print("\nWARNINGS:")
        for m in warn:
            print(" ", m)
    print("\nOVERALL:", "PASS" if not fail else "FAIL")
    return 0 if not fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
