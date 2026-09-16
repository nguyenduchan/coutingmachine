#!/usr/bin/env python3
"""Connectivity / size audit for compact STM32G030 carrier."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from pcb_parse import NetTable, pad_net

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "esp32_baseboard.kicad_pcb"


def _block(text: str, start: int) -> str:
    depth, i = 0, start
    while True:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1


def pad_table(text: str) -> dict[str, dict[str, str]]:
    table = NetTable(text)
    out: dict[str, dict[str, str]] = {}
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not ref_m or "board_only" in blk:
            continue
        ref = ref_m.group(1)
        pads: dict[str, str] = {}
        starts = [p.start() for p in re.finditer(r'\(pad\s+"', blk)]
        for k, ps in enumerate(starts):
            chunk = blk[ps : (starts[k + 1] if k + 1 < len(starts) else len(blk))]
            num = re.match(r'\(pad\s+"([^"]*)"', chunk).group(1)
            _nid, name = pad_net(chunk, table)
            if num and name and not name.startswith("unconnected"):
                pads[num] = name
        out[ref] = pads
    return out


def check(cond: bool, ok: list, fail: list, msg: str) -> None:
    (ok if cond else fail).append(msg)
    print(("  OK  " if cond else " FAIL "), msg)


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    ok: list[str] = []
    fail: list[str] = []

    print("=== A) Board size (from Edge.Cuts) ===")
    em = re.search(
        r'\(gr_rect\s*\(start\s+([\d.]+)\s+([\d.]+)\)\s*\(end\s+([\d.]+)\s+([\d.]+)\)[\s\S]*?layer "Edge\.Cuts"',
        text,
    )
    check(em is not None, ok, fail, "Edge.Cuts rect present")
    bw = bh = 0.0
    if em:
        x0, y0, x1, y1 = map(float, em.groups())
        bw, bh = x1 - x0, y1 - y0
        check(abs(x0 - 50.0) < 0.01 and abs(y0 - 50.0) < 0.01, ok, fail, "Edge.Cuts origin @50,50")
        check(bw >= 99.5 and bh >= 99.5, ok, fail, f"size {bw:.0f}x{bh:.0f} >= 100x100")
        check(bw <= 300.01 and bh <= 300.01, ok, fail, f"size {bw:.0f}x{bh:.0f} <= 300")
        check(bw >= bh - 0.01, ok, fail, f"wide board for DIN N/S edges ({bw:.0f}x{bh:.0f})")
    check("gen_compact_carrier" in text, ok, fail, "generator gen_compact_carrier")
    check("U_PWR1" in text and "U_PWR2" in text and "U_VIB" in text, ok, fail, "power/vib socket silk or refs")
    check("J_MOT1" in text and "J_MOT2" in text, ok, fail, "edge motor jacks J_MOT1/2")
    check("Mot_XH_04_Socket" in text, ok, fail, "Mot_XH_04 footprint")
    check("ANT KEEPOUT" not in text, ok, fail, "no ESP antenna keepout")
    check("ESP32_WROOM" not in text, ok, fail, "no WROOM footprint")

    print("=== B) Required refs ===")
    pads = pad_table(text)
    for ref in (
        "U1", "U2", "U3", "U4", "U5", "U6", "U44", "U45", "U46", "U_PWR1", "U_PWR2", "U_VIB",
        "J1", "J_MOT1", "J_MOT2", "J_P24S",
        "J14", "J15", "J_IN2", "J_IN3", "J_CNT5", "J_P24N", "J_P5N",
        "J_USB", "J_KEY", "J_DISP",
        "D3", "D1", "D4", "D5", "F1", "L1", "R2", "R2B", "R10", "R44", "R48", "Rfb1", "Rfb2",
        "PTC_SNS", "PTC_MOT", "PTC_MOT2",
        "C10", "C11", "C20", "C20B", "C21", "C24", "C24B", "C26", "Cbst", "Cc",
        "C5", "C51", "C3", "C31", "C_MCU", "C_MCU2",
        "Y1", "C_XI", "C_XO", "C52", "C53",
        "R_NRST", "C_NRST", "R_BOOT", "R_SWDIO", "SW_BOOT", "SW_NRST",
        "R45", "R49", "R46", "R50", "R47", "R51", "C27", "U47", "R_PWR_FLT", "R_VIB_FLT",
    ):
        check(ref in pads, ok, fail, f"ref {ref}")
    for gone in ("Q1", "Q2", "R_DTR", "R_RTS", "C_DTR", "C_RTS", "R_EN", "R_IO0", "R_IO2", "SW_EN", "J_SWD", "U7"):
        check(gone not in pads, ok, fail, f"removed legacy part {gone}")

    print("=== B2) STM32 + USB-UART boot (no J_DBG) ===")
    u1 = pads.get("U1", {})
    u5 = pads.get("U5", {})
    check("STM32G030C8T6_LQFP48" in text, ok, fail, "STM32 LQFP48 footprint")
    check("J_DBG" not in pads, ok, fail, "no J_DBG (USB program only)")
    check("/SWO" not in text, ok, fail, "no SWO net")
    check(u1.get("6") == "+3V3" and u1.get("7") == "GND", ok, fail, "U1 VDD/VSS")
    check(u1.get("4") == "+3V3" and u1.get("5") == "+3V3", ok, fail, "U1 VBAT/VREF+")
    check(u1.get("10") == "/NRST", ok, fail, "U1 NRST")
    check(u1.get("29") == "/UART_TX" and u1.get("32") == "/UART_RX", ok, fail, "U1 USART1 PA9/PA10")
    check(u1.get("35") == "/SWDIO" and u1.get("36") == "/SWCLK", ok, fail, "U1 SWDIO/BOOT0 pins")
    check("42" not in u1 or u1.get("42") != "/SWO", ok, fail, "PB3 free (no SWO)")
    check(u5.get("7") == "/CH340_XI" and u5.get("8") == "/CH340_XO", ok, fail, "U5 XI/XO crystal")
    check("10" not in u5 and "15" not in u5, ok, fail, "U5 DTR/RTS not wired")
    check(u5.get("2") == "/UART_RX" and u5.get("3") == "/UART_TX", ok, fail, "CH340-USART cross nets")
    check(pads.get("R_NRST", {}).get("2") == "/NRST", ok, fail, "R_NRST pull-up")
    check(pads.get("R_BOOT", {}).get("1") == "/SWCLK" and pads.get("R_BOOT", {}).get("2") == "GND", ok, fail, "R_BOOT PD")
    check(pads.get("R_SWDIO", {}).get("2") == "/SWDIO", ok, fail, "R_SWDIO pull-up")
    check(pads.get("SW_NRST", {}).get("1") == "/NRST", ok, fail, "SW_NRST")
    check(pads.get("SW_BOOT", {}).get("1") == "/SWCLK", ok, fail, "SW_BOOT on BOOT0/PA14")
    check("/IO0" not in text and "/DTR" not in text and "/RTS" not in text, ok, fail, "no ESP auto-boot nets")
    check("PinHeader_1x04_SWD" not in text, ok, fail, "no legacy 1x4 SWD")

    print("=== C) Protect / power nets ===")
    check(pads.get("D3", {}).get("1") == "+24V_RAW", ok, fail, "D3 series SS54")
    check(pads.get("F1", {}).get("2") == "+24V", ok, fail, "F1 fuse to +24V")
    check("T2A" in text, ok, fail, "F1 T2A time-lag")
    check("+24V" in pads.get("D1", {}).values() and "GND" in pads.get("D1", {}).values(), ok, fail, "D1 TVS SMBJ26A")
    check(pads.get("PTC_SNS", {}).get("1") == "+24V" and pads.get("PTC_SNS", {}).get("2") == "+24V_SNS_PRE", ok, fail, "PTC_SNS branch")
    check(pads.get("R10", {}).get("1") == "+24V_SNS_PRE" and pads.get("R10", {}).get("2") == "+24V_SNS", ok, fail, "R10 after PTC_SNS")
    check(pads.get("C10", {}).get("1") == "+24V_SNS", ok, fail, "C10 47u SNS")
    check(pads.get("PTC_MOT", {}).get("1") == "+24V" and pads.get("PTC_MOT", {}).get("2") == "+24V_MOT", ok, fail, "PTC_MOT to VM")
    check(pads.get("C20", {}).get("1") == "+24V_MOT", ok, fail, "C20 470u on +24V_MOT")
    check(pads.get("C21", {}).get("1") == "+24V", ok, fail, "C21 220u +24V bulk")
    check(pads.get("C5", {}).get("1") == "+5V", ok, fail, "C5 +5V bulk")
    check(pads.get("D5", {}).get("2") == "+5V" and pads.get("D5", {}).get("1") == "GND", ok, fail, "D5 SMBJ5.0A on +5V")
    check(pads.get("C3", {}).get("1") == "+3V3", ok, fail, "C3 +3V3 bulk")
    u2 = pads.get("U2", {})
    u3 = pads.get("U3", {})
    u4 = pads.get("U4", {})
    check("/STEP" in u3.values() and "/DIR" in u3.values() and "/EN_TMC" in u3.values(), ok, fail, "U3 TMC1 STEP/DIR/EN")
    check("+24V_MOT" in u3.values() and "+3V3" in u3.values(), ok, fail, "U3 VM1+VIO")
    check("/STEP2" in u4.values() and "/DIR2" in u4.values() and "/EN_TMC2" in u4.values(), ok, fail, "U4 TMC2 STEP/DIR/EN")
    check("+24V_MOT2" in u4.values() and "+3V3" in u4.values(), ok, fail, "U4 VM2+VIO")
    check(pads.get("PTC_MOT2", {}).get("2") == "+24V_MOT2", ok, fail, "PTC_MOT2 to VM2")
    check(pads.get("R2B", {}).get("2") == "/EN_TMC2", ok, fail, "R2B EN2 pull-up")
    check(u1.get("11") == "/STEP" and u1.get("12") == "/DIR" and u1.get("13") == "/EN_TMC", ok, fail, "U1 TMC1 on PA0-2")
    check(u1.get("17") == "/STEP2" and u1.get("18") == "/DIR2" and u1.get("28") == "/EN_TMC2", ok, fail, "U1 TMC2 on PA6-8")
    check(u1.get("14") == "/BUP", ok, fail, "U1 BUP PA3")
    check(u1.get("27") == "/IN2" and u1.get("43") == "/IN3", ok, fail, "U1 IN2/IN3")
    check(u1.get("33") == "/PWM_OUT1" and u1.get("34") == "/PWM_OUT2", ok, fail, "U1 PWM power outs")
    check(u1.get("44") == "/PWR_EN1" and u1.get("45") == "/PWR_EN2", ok, fail, "U1 PWR EN1/EN2")
    check(u1.get("46") == "/PWR_FAULT", ok, fail, "U1 PWR_FAULT")
    check(u1.get("47") == "/VIB_CTRL" and u1.get("48") == "/VIB_FAULT", ok, fail, "U1 VIB CTRL/FAULT")
    up1 = pads.get("U_PWR1", {})
    up2 = pads.get("U_PWR2", {})
    check(up1.get("4") == "/PWM_OUT1" and up1.get("5") == "/PWR_EN1", ok, fail, "U_PWR1 PWM/EN")
    check(up2.get("4") == "/PWM_OUT2" and up2.get("5") == "/PWR_EN2", ok, fail, "U_PWR2 PWM/EN")
    check(up1.get("1") == "+24V" and up1.get("3") == "+3V3", ok, fail, "U_PWR1 supplies")
    check(up2.get("1") == "+24V" and up2.get("6") == "/PWR_FAULT", ok, fail, "U_PWR2 +24V/FAULT")
    check("PowerMod_1CH_Sock" in text, ok, fail, "PowerMod 1CH socket footprint")
    check("PowerMod_2CH_Sock" not in text, ok, fail, "no legacy 2CH power sock")
    check("U_PWR\"" not in text.replace("U_PWR1", "").replace("U_PWR2", ""), ok, fail, "no bare U_PWR ref")
    uv = pads.get("U_VIB", {})
    check(uv.get("3") == "/VIB_CTRL" and uv.get("1") == "+24V", ok, fail, "U_VIB CTRL/+24V")
    check("VibAC_Sock" in text, ok, fail, "VibAC socket footprint")
    check(pads.get("J14", {}).get("3") == "/OPTO_IN_BUP", ok, fail, "J14 U-slot OUT")
    check(pads.get("J15", {}).get("3") == "/OPTO_IN_BUP", ok, fail, "J15 fiber OUT shared")
    check(pads.get("U44", {}).get("4") == "/BUP", ok, fail, "PC817 count to /BUP")
    check(pads.get("J_IN2", {}).get("3") == "/OPTO_IN2" and pads.get("U45", {}).get("4") == "/IN2", ok, fail, "J_IN2 opto")
    check(pads.get("J_IN3", {}).get("3") == "/OPTO_IN3" and pads.get("U46", {}).get("4") == "/IN3", ok, fail, "J_IN3 opto")
    check(pads.get("J_CNT5", {}).get("1") == "+5V" and pads.get("J_CNT5", {}).get("3") == "/OPTO_IN_5V", ok, fail, "J_CNT5 5V jack")
    check(pads.get("U47", {}).get("4") == "/CNT5" and pads.get("R47", {}).get("1") == "+5V", ok, fail, "U47/R47 5V opto")
    check(pads.get("R51", {}).get("2") == "/CNT5", ok, fail, "R51 CNT5 pull-up")
    check(u1.get("39") == "/CNT5", ok, fail, "U1 CNT5 on PD1")
    check(pads.get("J_P24N", {}).get("1") == "+24V_SNS" and pads.get("J_P24N", {}).get("2") == "GND", ok, fail, "J_P24N aux 24V")
    check(pads.get("J_P5N", {}).get("1") == "+5V" and pads.get("J_P5N", {}).get("2") == "GND", ok, fail, "J_P5N aux 5V")
    check(pads.get("J_P24S", {}).get("1") == "+24V" and pads.get("J_P24S", {}).get("2") == "GND", ok, fail, "J_P24S aux 24V")
    check(u1.get("15") == "/TM_CLK" and u1.get("16") == "/TM_DIO", ok, fail, "U1 TM1637 PA4/5")
    check(sum(1 for v in u1.values() if v.startswith("/KEY_")) >= 8, ok, fail, "U1 keypad 8")
    jd = pads.get("J_DISP", {})
    check(jd.get("1") == "/TM_CLK" and jd.get("2") == "/TM_DIO", ok, fail, "J_DISP CLK/DIO")
    check(jd.get("3") == "+5V" and jd.get("4") == "GND", ok, fail, "J_DISP +5V/GND")
    check("Disp_XH_04_Socket" in text, ok, fail, "Disp XH-4 footprint")
    check(pads.get("J_KEY", {}).get("1") == "/KEY_R0", ok, fail, "J_KEY R0")
    check("DS1" not in pads, ok, fail, "no on-board DS1 LED")
    check("BZ1" not in pads, ok, fail, "no BZ1 buzzer")
    check("SMBJ26A" in text and "SMBJ5.0A" in text, ok, fail, "TVS footprints")
    check("PTC_1812" in text, ok, fail, "PTC 1812")
    check("Diode_SMA" in text and "CP_SMD_" in text and "PC817_SOP4" in text, ok, fail, "SMT packages")
    check(u2.get("1") == "/BUCK_SW" and pads.get("L1", {}).get("2") == "+5V", ok, fail, "discrete buck")
    check(pads.get("U6", {}).get("2") == "+3V3", ok, fail, "U6 AMS1117 3V3")
    check(text.count("TMC2209_StepStick") >= 2, ok, fail, "two TMC sockets")
    check("TM1637_SOP20" not in text, ok, fail, "no on-board TM1637 IC")
    jm1 = pads.get("J_MOT1", {})
    jm2 = pads.get("J_MOT2", {})
    check(jm1.get("1") == "/MotA2" and jm1.get("4") == "/MotB2", ok, fail, "J_MOT1 phases")
    check(jm2.get("1") == "/Mot2A2" and jm2.get("4") == "/Mot2B2", ok, fail, "J_MOT2 phases")
    check(u3.get("11") == "/MotA2" and jm1.get("1") == u3.get("11"), ok, fail, "J_MOT1 tied to U3 Mot")
    check(u4.get("11") == "/Mot2A2" and jm2.get("1") == u4.get("11"), ok, fail, "J_MOT2 tied to U4 Mot")
    print("=== D) U1 STM32 placement (north / 3V3 zone) ===")
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        if '(property "Reference" "U1"' not in blk:
            continue
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", blk)
        check(at is not None, ok, fail, "U1 has position")
        if at and em:
            ux, uy = float(at.group(1)), float(at.group(2))
            rot = float(at.group(3) or 0)
            check(abs(rot) < 0.1 or abs(rot - 0) < 0.1, ok, fail, f"U1 rot=0 ({rot})")
            check("STM32G030" in blk, ok, fail, "U1 is STM32 footprint")
            check(ux > (x0 + x1) / 2, ok, fail, f"U1 east half (x={ux:.1f})")
            check(uy < y0 + 0.45 * bh, ok, fail, f"U1 north 3V3 zone (y={uy:.1f})")
        break

    print("=== D2) J1 24V on south-west edge ===")
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        if '(property "Reference" "J1"' not in blk:
            continue
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", blk)
        check(at is not None, ok, fail, "J1 has position")
        if at and em:
            jx, jy = float(at.group(1)), float(at.group(2))
            jrot = float(at.group(3) or 0)
            x0, y0, x1, y1 = map(float, em.groups())
            check(abs(jrot) < 0.1 or abs(jrot - 0) < 0.1, ok, fail, f"J1 rot=0 south ({jrot})")
            check(jx < x0 + 0.35 * bw, ok, fail, f"J1 west on south (x={jx:.1f})")
            check(jy > y1 - 18.0, ok, fail, f"J1 near south edge (y={jy:.1f})")
        break

    print("=== D2b) Inlet J1->D3->F1; 24V loads after fuse ===")
    pos = {}
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not rm:
            continue
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", blk)
        if at:
            pos[rm.group(1)] = (float(at.group(1)), float(at.group(2)), float(at.group(3) or 0))
    if all(r in pos for r in ("J1", "D3", "F1")):
        jx, jy, _ = pos["J1"]
        dx, dy, dr = pos["D3"]
        fx, fy, fr = pos["F1"]
        check(dx > jx - 2.0, ok, fail, "D3 east of / near J1")
        check(abs(fr) < 0.1, ok, fail, f"F1 rot=0 E-W ({fr})")
        check(fy > y0 + 0.55 * bh, ok, fail, f"F1 in south band (y={fy:.1f})")
        fuse_out_x = fx + 11.25
        edge_ok = {
            "J1", "D3", "F1",
            "J_MOT1", "J_MOT2", "U3", "U4",
            "U_PWR1", "U_PWR2", "U_VIB", "J_P24S",
        }
        bad = []
        for ref, nets in pads.items():
            if ref in edge_ok:
                continue
            if not any(n in ("+24V", "+24V_SNS", "+24V_SNS_PRE", "+24V_MOT", "+24V_MOT2") for n in nets.values()):
                continue
            px, py, _pr = pos.get(ref, (None, None, None))
            if px is None:
                continue
            if px + 4.0 < fuse_out_x and py > fy - 8.0:
                bad.append(f"{ref}@{px:.1f},{py:.1f}")
        check(not bad, ok, fail, f"24V loads not in pre-fuse pocket: {bad[:8]}")
    for ref, nets in pads.items():
        vals = set(nets.values())
        if ref in ("J1", "D3", "F1"):
            continue
        check("+24V_RAW" not in vals and "+24V_PRE" not in vals, ok, fail, f"{ref} not on pre-fuse nets")

    print("=== D2c) Edge jack zones (S=MOT/PWR, N=SNS/HMI; TMC inland) ===")
    if em and all(r in pos for r in ("J_MOT1", "J_MOT2", "J_P24S", "U3", "U4", "U_PWR1", "U_PWR2", "U_VIB", "J14", "J_CNT5", "J_P24N", "J_P5N", "J_KEY", "J_DISP")):
        x0, y0, x1, y1 = map(float, em.groups())
        mid_y = y0 + 0.5 * bh
        for ref in ("J_MOT1", "J_MOT2", "J_P24S", "U_PWR1", "U_PWR2", "U_VIB"):
            _mx, my, _ = pos[ref]
            check(my > mid_y, ok, fail, f"{ref} south half (y={my:.1f})")
        for ref in ("U3", "U4"):
            _tx, ty, _ = pos[ref]
            check(ty > mid_y, ok, fail, f"{ref} TMC south inland band (y={ty:.1f})")
        for ref in ("J14", "J15", "J_IN2", "J_IN3", "J_CNT5", "J_P24N", "J_P5N", "J_KEY", "J_DISP"):
            if ref not in pos:
                continue
            _nx, ny, _ = pos[ref]
            check(ny < mid_y, ok, fail, f"{ref} north half (y={ny:.1f})")
        south_seq = ("J_MOT1", "J_MOT2", "U_PWR1", "U_PWR2", "U_VIB", "J_P24S")
        for a, b in zip(south_seq, south_seq[1:]):
            check(pos[a][0] < pos[b][0], ok, fail, f"{a} left of {b}")
        check(pos["U3"][0] < pos["U4"][0], ok, fail, "U3 left of U4")
        north_seq = ("J_P24N", "J14", "J15", "J_IN2", "J_IN3", "J_P5N", "J_CNT5", "J_KEY", "J_DISP")
        for a, b in zip(north_seq, north_seq[1:]):
            check(pos[a][0] < pos[b][0], ok, fail, f"{a} left of {b}")
        check(pos["J_DISP"][0] < pos["J_USB"][0], ok, fail, "J_DISP left of J_USB")
        for ref in ("J15", "J_IN3"):
            check(abs(pos[ref][1] - pos["J14"][1]) < 3.0, ok, fail, f"{ref} flush with north jack row")
        if em:
            x0, y0, x1, y1 = map(float, em.groups())
            check(pos["J1"][0] < pos["J_MOT1"][0], ok, fail, "J1 west of motor/IO cluster")
            check(pos["J_P24S"][0] > x0 + 0.55 * bw, ok, fail, f"J_P24S on south-east (x={pos['J_P24S'][0]:.1f})")

    print("=== D3) J_USB flush north edge (with HMI) ===")
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        if '(property "Reference" "J_USB"' not in blk:
            continue
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", blk)
        check(at is not None, ok, fail, "J_USB has position")
        if at and em:
            x0, y0, x1, y1 = map(float, em.groups())
            ux, uy = float(at.group(1)), float(at.group(2))
            urot = float(at.group(3) or 0)
            check(abs(urot - 180) < 0.1, ok, fail, f"J_USB rot=180 mouth north ({urot})")
            check(uy <= y0 + 0.18 * bh, ok, fail, f"J_USB flush north edge (y={uy:.1f})")
            check(ux > (x0 + x1) / 2, ok, fail, f"J_USB east of center (x={ux:.1f})")
        break

    print("=== D3a) SW_BOOT / SW_NRST beside J_USB ===")
    if "J_USB" in pos and "SW_BOOT" in pos and "SW_NRST" in pos:
        ux, uy, _ = pos["J_USB"]
        for sref in ("SW_BOOT", "SW_NRST"):
            sx, sy, _ = pos[sref]
            dx = abs(sx - ux)
            check(dx < 18.0, ok, fail, f"{sref} near J_USB in X (dx={dx:.1f})")
            check(sy > uy, ok, fail, f"{sref} inland south of J_USB")
            check(sy < uy + 22.0, ok, fail, f"{sref} close to J_USB in Y (dy={sy - uy:.1f})")
        bx, _, _ = pos["SW_BOOT"]
        nx, _, _ = pos["SW_NRST"]
        check(bx < nx, ok, fail, "SW_BOOT west of SW_NRST")

    print("=== D3b) Field jacks only on north/south edges ===")
    field_edge = (
        "J1", "J_MOT1", "J_MOT2", "J_P24S",
        "U_PWR1", "U_PWR2", "U_VIB",
        "J_P24N", "J14", "J15", "J_IN2", "J_IN3", "J_P5N", "J_CNT5",
        "J_KEY", "J_DISP", "J_USB",
    )
    field_all = field_edge
    if em:
        x0, y0, x1, y1 = map(float, em.groups())
        n_lim = y0 + 0.22 * bh
        s_lim = y1 - 0.22 * bh
        side_band = 14.0
        mid_lo = y0 + 0.32 * bh
        mid_hi = y1 - 0.32 * bh
        for ref in field_edge:
            if ref not in pos:
                check(False, ok, fail, f"{ref} missing for edge check")
                continue
            px, py, _ = pos[ref]
            on_n = py <= n_lim
            on_s = py >= s_lim
            check(on_n or on_s, ok, fail, f"{ref} flush N or S (y={py:.1f})")
        for ref in field_all:
            if ref not in pos:
                continue
            px, py, _ = pos[ref]
            near_side = px <= x0 + side_band or px >= x1 - side_band
            in_mid_y = mid_lo < py < mid_hi
            check(not (near_side and in_mid_y), ok, fail, f"{ref} not mounted on left/right sides")

    print("=== D3c) Field jacks pin-row || N/S edge (ngang, not dọc) ===")
    # Pads along local Y → rot 90/270. Pads along local X (XH, USB, J1, TMC) → 0/180.
    row_along_y = {"J_KEY", "U_PWR1", "U_PWR2", "U_VIB"}
    row_along_x = {
        "J1": (0.0,), "J_USB": (180.0,),
        "J_P24N": (0.0,), "J14": (0.0,), "J15": (0.0,),
        "J_IN2": (0.0,), "J_IN3": (0.0,), "J_P5N": (0.0,),
        "J_CNT5": (0.0,), "J_DISP": (0.0,),
        "J_MOT1": (180.0,), "J_MOT2": (180.0,), "J_P24S": (180.0,),
    }
    if em:
        for ref in row_along_y:
            if ref not in pos:
                continue
            _, _, r = pos[ref]
            ok_r = abs(r - 90) < 1 or abs(r - 270) < 1
            check(ok_r, ok, fail, f"{ref} rot=90/270 ngang ({r})")
        for ref, allowed in row_along_x.items():
            if ref not in pos:
                continue
            _, _, r = pos[ref]
            check(any(abs(r - a) < 1 for a in allowed), ok, fail, f"{ref} rot ngang ({r})")

    print("=== E) Courtyard clearance (electronics↔jack ≥3mm, else ≥2.5mm) ===")

    def world_crt(cx, cy, rot, sx0, sy0, sx1, sy1):
        xs, ys = [], []
        r = int(round(rot)) % 360
        for x, y in ((sx0, sy0), (sx0, sy1), (sx1, sy0), (sx1, sy1)):
            if r == 90:
                rx, ry = -y, x
            elif r == 180:
                rx, ry = -x, -y
            elif r == 270:
                rx, ry = y, -x
            else:
                rx, ry = x, y
            xs.append(cx + rx)
            ys.append(cy + ry)
        return min(xs), min(ys), max(xs), max(ys)

    bodies: list[tuple[str, float, float, float, float]] = []
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        if "board_only" in blk:
            continue
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', blk)
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", blk)
        if not ref_m or not at:
            continue
        cx, cy = float(at.group(1)), float(at.group(2))
        rot = float(at.group(3) or 0)
        crt = re.search(
            r'\(fp_rect\s*\(start\s+([\d.-]+)\s+([\d.-]+)\)\s*\(end\s+([\d.-]+)\s+([\d.-]+)\)[\s\S]*?F\.CrtYd',
            blk,
        )
        if crt:
            sx0, sy0, sx1, sy1 = map(float, crt.groups())
            ax0, ay0, ax1, ay1 = world_crt(cx, cy, rot, sx0, sy0, sx1, sy1)
            hw, hh = (ax1 - ax0) / 2, (ay1 - ay0) / 2
            cx, cy = (ax0 + ax1) / 2, (ay0 + ay1) / 2
        else:
            hw, hh = 4.0, 4.0
        bodies.append((ref_m.group(1), cx, cy, hw, hh))
    edge_jacks = {
        "J1", "J_MOT1", "J_MOT2", "J_P24S",
        "U_PWR1", "U_PWR2", "U_VIB",
        "J14", "J15", "J_IN2", "J_IN3", "J_CNT5", "J_P24N", "J_P5N",
        "J_KEY", "J_DISP", "J_USB",
    }
    min_gap = 2.5
    jack_elec = 3.0
    clashes = []
    tol = 1e-3
    for i, (ra, ax, ay, aw, ah) in enumerate(bodies):
        for rb, bx, by, b_hw, b_hh in bodies[i + 1 :]:
            g = jack_elec if ((ra in edge_jacks) != (rb in edge_jacks)) else min_gap
            need_x = aw + b_hw + g
            need_y = ah + b_hh + g
            if abs(ax - bx) + tol < need_x and abs(ay - by) + tol < need_y:
                gx = need_x - abs(ax - bx)
                gy = need_y - abs(ay - by)
                clashes.append(f"{ra}/{rb}(short {min(gx, gy):.2f})")
    check(not clashes, ok, fail, f"courtyard gap inland>={min_gap} vs-jack>={jack_elec} ({len(clashes)} clashes: {clashes[:12]})")

    print("=== E2) Non-jack AABB must not cut jack h-lines; L/R keep for install ===")
    if em:
        x0, y0, x1, y1 = map(float, em.groups())
        need_edge = 8.0
        jack_side = 6.0
        hole_inset = 4.5
        hole_ns = 20.0
        bad_m = []
        for ref, cx, cy, hw, hh in bodies:
            if ref in edge_jacks or ref.startswith("H"):
                continue
            d = min(cx - hw - x0, x1 - (cx + hw))
            if d < need_edge - 0.05:
                bad_m.append(f"{ref}:{d:.2f}")
        check(not bad_m, ok, fail, f"non-jack left/right clear≥{need_edge}mm ({bad_m[:12]})")
        bad_js = []
        for ref, cx, cy, hw, hh in bodies:
            if ref not in edge_jacks:
                continue
            d = min(cx - hw - x0, x1 - (cx + hw))
            if d < jack_side - 0.05:
                bad_js.append(f"{ref}:{d:.2f}")
        check(not bad_js, ok, fail, f"jacks left/right clear≥{jack_side}mm ({bad_js[:12]})")
        n_jacks = [b for b in bodies if b[0] in (
            "J_P24N", "J14", "J15", "J_IN2", "J_IN3", "J_P5N", "J_CNT5", "J_KEY", "J_DISP", "J_USB",
        )]
        s_jacks = [b for b in bodies if b[0] in (
            "J1", "J_MOT1", "J_MOT2", "J_P24S", "U_PWR1", "U_PWR2", "U_VIB",
        )]
        row_sep = 3.0
        hole_aabb = []
        for m in re.finditer(r'\n\t\(footprint "', text):
            blk = _block(text, m.start() + 1)
            ref_m = re.search(r'\(property "Reference" "([^"]+)"', blk)
            at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", blk)
            if not ref_m or not at or not ref_m.group(1).startswith("H"):
                continue
            hx, hy = float(at.group(1)), float(at.group(2))
            hole_aabb.append((ref_m.group(1), hx, hy, 3.5, 3.5))
        extra = list(bodies) + hole_aabb
        bad_row = []
        if n_jacks:
            n_line = max(cy + hh for _, _, cy, _, hh in n_jacks)
            for ref, cx, cy, hw, hh in extra:
                if ref in edge_jacks:
                    continue
                top, bot = cy - hh, cy + hh
                if top <= n_line <= bot:
                    bad_row.append(f"{ref}:N-cut")
                elif min(abs(top - n_line), abs(bot - n_line)) < row_sep - 0.05:
                    bad_row.append(f"{ref}:N")
        if s_jacks:
            s_line = min(cy - hh for _, _, cy, _, hh in s_jacks)
            for ref, cx, cy, hw, hh in extra:
                if ref in edge_jacks:
                    continue
                top, bot = cy - hh, cy + hh
                if top <= s_line <= bot:
                    bad_row.append(f"{ref}:S-cut")
                elif min(abs(top - s_line), abs(bot - s_line)) < row_sep - 0.05:
                    bad_row.append(f"{ref}:S")
        check(not bad_row, ok, fail, f"AABB ≥{row_sep}mm from jack h-lines, no cut ({bad_row[:16]})")
        hole_clash = []
        for hr, hx, hy, hw, hh in hole_aabb:
            for jr, jx, jy, jw, jh in bodies:
                if jr not in edge_jacks:
                    continue
                g = 2.5
                if abs(hx - jx) + 1e-3 < hw + jw + g and abs(hy - jy) + 1e-3 < hh + jh + g:
                    hole_clash.append(f"{hr}/{jr}")
        check(not hole_clash, ok, fail, f"M3 holes clear of jacks ({hole_clash[:8]})")
        bad_h = []
        for hr, hx, hy, hw, hh in hole_aabb:
            dL, dR = hx - x0, x1 - hx
            on_side = min(dL, dR) <= hole_inset + 0.6
            dN, dS = hy - y0, y1 - hy
            on_ns = abs(min(dN, dS) - hole_ns) < 1.0
            if not on_side:
                bad_h.append(f"{hr}:not-LR")
            if not on_ns:
                bad_h.append(f"{hr}:y")
        check(not bad_h, ok, fail, f"M3 on L/R keep, {hole_ns:.0f}mm from N/S ({bad_h})")

    print("=== F) Removed modules ===")
    for bad in (
        "74HC595", "ULN2003", "/TFT_", "/ENC_", "/BLOWER", "ESP32_S3_DevKit",
        "ESP32_WROOM", "MP1584_5V3A", "TM1637_Module", "DSP1",
    ):
        check(bad not in text, ok, fail, f"no {bad}")

    print(f"\nPASS {len(ok)}  FAIL {len(fail)}  board={bw:.0f}x{bh:.0f}")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
