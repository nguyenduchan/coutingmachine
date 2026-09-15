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
        check(bw <= 180.01 and bh <= 180.01, ok, fail, f"size {bw:.0f}x{bh:.0f} <= 180")
        check(bw >= bh - 0.01, ok, fail, f"wide board for DIN N/S edges ({bw:.0f}x{bh:.0f})")
    check("gen_compact_carrier" in text, ok, fail, "generator gen_compact_carrier")
    check("U_PWR" in text and "U_VIB" in text, ok, fail, "power/vib socket silk or refs")
    check("J_MOT1" in text and "J_MOT2" in text, ok, fail, "edge motor jacks J_MOT1/2")
    check("Mot_XH_04_Socket" in text, ok, fail, "Mot_XH_04 footprint")
    check("ANT KEEPOUT" not in text, ok, fail, "no ESP antenna keepout")
    check("ESP32_WROOM" not in text, ok, fail, "no WROOM footprint")

    print("=== B) Required refs ===")
    pads = pad_table(text)
    for ref in (
        "U1", "U2", "U3", "U4", "U5", "U6", "U7", "U44", "U45", "U46", "U_PWR", "U_VIB",
        "J1", "J_MOT1", "J_MOT2", "J14", "J15", "J_IN2", "J_IN3", "J_USB", "J_KEY", "J_DISP", "J_DBG",
        "D3", "D1", "D4", "D5", "F1", "L1", "R2", "R2B", "R10", "R44", "R48", "Rfb1", "Rfb2",
        "PTC_SNS", "PTC_MOT", "PTC_MOT2",
        "C10", "C11", "C20", "C20B", "C21", "C24", "C24B", "C26", "Cbst", "Cc",
        "C5", "C51", "C3", "C31", "C_MCU", "C_MCU2",
        "Y1", "C_XI", "C_XO", "C52", "C53",
        "R_NRST", "C_NRST", "R_BOOT", "R_SWDIO", "SW_BOOT", "SW_NRST",
        "R45", "R49", "R46", "R50", "R_PWR_FLT", "R_VIB_FLT",
    ):
        check(ref in pads, ok, fail, f"ref {ref}")
    for gone in ("Q1", "Q2", "R_DTR", "R_RTS", "C_DTR", "C_RTS", "R_EN", "R_IO0", "R_IO2", "SW_EN", "J_SWD"):
        check(gone not in pads, ok, fail, f"removed legacy part {gone}")

    print("=== B2) STM32 + USB-UART + Cortex Debug-10 ===")
    u1 = pads.get("U1", {})
    u5 = pads.get("U5", {})
    jdbg = pads.get("J_DBG", {})
    check("STM32G030C8T6_LQFP48" in text, ok, fail, "STM32 LQFP48 footprint")
    check("Cortex_Debug_10" in text, ok, fail, "Cortex Debug-10 footprint")
    check(u1.get("6") == "+3V3" and u1.get("7") == "GND", ok, fail, "U1 VDD/VSS")
    check(u1.get("4") == "+3V3" and u1.get("5") == "+3V3", ok, fail, "U1 VBAT/VREF+")
    check(u1.get("10") == "/NRST", ok, fail, "U1 NRST")
    check(u1.get("29") == "/UART_TX" and u1.get("32") == "/UART_RX", ok, fail, "U1 USART1 PA9/PA10")
    check(u1.get("35") == "/SWDIO" and u1.get("36") == "/SWCLK", ok, fail, "U1 SWD PA13/PA14")
    check(u1.get("42") == "/SWO", ok, fail, "U1 SWO PB3")
    check(u5.get("7") == "/CH340_XI" and u5.get("8") == "/CH340_XO", ok, fail, "U5 XI/XO crystal")
    check("10" not in u5 and "15" not in u5, ok, fail, "U5 DTR/RTS not wired")
    check(u5.get("2") == "/UART_RX" and u5.get("3") == "/UART_TX", ok, fail, "CH340-USART cross nets")
    check(jdbg.get("1") == "+3V3", ok, fail, "J_DBG VTREF=+3V3")
    check(jdbg.get("2") == "/SWDIO" and jdbg.get("4") == "/SWCLK", ok, fail, "J_DBG SWDIO/SWCLK")
    check(jdbg.get("3") == "GND" and jdbg.get("5") == "GND" and jdbg.get("9") == "GND", ok, fail, "J_DBG GNDs")
    check(jdbg.get("6") == "/SWO", ok, fail, "J_DBG SWO")
    check(jdbg.get("10") == "/NRST", ok, fail, "J_DBG nSRST")
    check("7" not in jdbg, ok, fail, "J_DBG pin7 KEY no net")
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
    u7 = pads.get("U7", {})
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
    check(u1.get("44") == "/PWR_EN" and u1.get("45") == "/PWR_DIR", ok, fail, "U1 PWR EN/DIR")
    check(u1.get("46") == "/PWR_FAULT", ok, fail, "U1 PWR_FAULT")
    check(u1.get("47") == "/VIB_CTRL" and u1.get("48") == "/VIB_FAULT", ok, fail, "U1 VIB CTRL/FAULT")
    up = pads.get("U_PWR", {})
    check(up.get("7") == "/PWM_OUT1" and up.get("8") == "/PWM_OUT2", ok, fail, "U_PWR PWM pads")
    check(up.get("1") == "+24V" and up.get("5") == "+3V3", ok, fail, "U_PWR supplies")
    check("PowerMod_2CH_Sock" in text, ok, fail, "PowerMod socket footprint")
    uv = pads.get("U_VIB", {})
    check(uv.get("3") == "/VIB_CTRL" and uv.get("1") == "+24V", ok, fail, "U_VIB CTRL/+24V")
    check("VibAC_Sock" in text, ok, fail, "VibAC socket footprint")
    check(pads.get("J14", {}).get("3") == "/OPTO_IN_BUP", ok, fail, "J14 U-slot OUT")
    check(pads.get("J15", {}).get("3") == "/OPTO_IN_BUP", ok, fail, "J15 fiber OUT shared")
    check(pads.get("U44", {}).get("4") == "/BUP", ok, fail, "PC817 count to /BUP")
    check(pads.get("J_IN2", {}).get("3") == "/OPTO_IN2" and pads.get("U45", {}).get("4") == "/IN2", ok, fail, "J_IN2 opto")
    check(pads.get("J_IN3", {}).get("3") == "/OPTO_IN3" and pads.get("U46", {}).get("4") == "/IN3", ok, fail, "J_IN3 opto")
    check(u1.get("15") == "/TM_CLK" and u1.get("16") == "/TM_DIO", ok, fail, "U1 TM1637 PA4/5")
    check(sum(1 for v in u1.values() if v.startswith("/KEY_")) >= 8, ok, fail, "U1 keypad 8")
    check(u7.get("18") == "/TM_CLK" and u7.get("17") == "/TM_DIO", ok, fail, "U7 CLK/DIO")
    check(pads.get("J_DISP", {}).get("1") == "/TM_G1", ok, fail, "J_DISP GRID1")
    check(pads.get("J_KEY", {}).get("1") == "/KEY_R0", ok, fail, "J_KEY R0")
    check("DS1" not in pads, ok, fail, "no on-board DS1 LED")
    check("BZ1" not in pads, ok, fail, "no BZ1 buzzer")
    check("SMBJ26A" in text and "SMBJ5.0A" in text, ok, fail, "TVS footprints")
    check("PTC_1812" in text, ok, fail, "PTC 1812")
    check("Diode_SMA" in text and "CP_SMD_" in text and "PC817_SOP4" in text, ok, fail, "SMT packages")
    check(u2.get("1") == "/BUCK_SW" and pads.get("L1", {}).get("2") == "+5V", ok, fail, "discrete buck")
    check(pads.get("U6", {}).get("2") == "+3V3", ok, fail, "U6 AMS1117 3V3")
    check(text.count("TMC2209_StepStick") >= 2, ok, fail, "two TMC sockets")
    check("TM1637_SOP20" in text, ok, fail, "TM1637 SOP20")
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
        bad = []
        for ref, nets in pads.items():
            if ref in ("J1", "D3", "F1"):
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

    print("=== D2c) Edge jack zones (S=MOT, N=SNS/HMI) ===")
    if em and all(r in pos for r in ("J_MOT1", "J_MOT2", "J14", "J_KEY", "J_DISP")):
        x0, y0, x1, y1 = map(float, em.groups())
        mid_y = y0 + 0.5 * bh
        for ref in ("J_MOT1", "J_MOT2"):
            _mx, my, _ = pos[ref]
            check(my > mid_y, ok, fail, f"{ref} south half (y={my:.1f})")
        for ref in ("J14", "J15", "J_IN2", "J_IN3", "J_KEY", "J_DISP"):
            if ref not in pos:
                continue
            _nx, ny, _ = pos[ref]
            check(ny < mid_y, ok, fail, f"{ref} north half (y={ny:.1f})")
        check(pos["J_MOT1"][0] < pos["J_MOT2"][0], ok, fail, "J_MOT1 left of J_MOT2")
        check(pos["J14"][0] < pos["J_DISP"][0], ok, fail, "J14 left of J_DISP")
        check(pos["J_KEY"][0] < pos["J_DISP"][0], ok, fail, "J_KEY left of J_DISP")
        check(pos["U3"][1] < pos["J_MOT1"][1], ok, fail, "U3 north of J_MOT1")
        check(pos["U4"][1] < pos["J_MOT2"][1], ok, fail, "U4 north of J_MOT2")

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

    print("=== D3b) Field jacks only on north/south edges ===")
    field_edge = (
        "J1", "J_MOT1", "J_MOT2", "J14", "J_IN2",
        "J_KEY", "J_DISP", "J_USB", "J_DBG",
    )
    field_all = field_edge + ("J15", "J_IN3")
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
    # Native pad-row along local Y → must be rot 90/270 on N/S edges
    row_along_y = {
        "J_MOT1", "J_MOT2", "J14", "J15", "J_IN2", "J_IN3",
        "J_KEY", "J_DISP", "J_DBG",
    }
    # Native pad-row along local X (already ngang at 0/180)
    row_along_x = {"J1": (0.0,), "J_USB": (180.0,)}
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

    print("=== E) Courtyard clearance (gap >= 2.0mm) ===")
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
            hw, hh = abs(sx1 - sx0) / 2, abs(sy1 - sy0) / 2
        else:
            hw, hh = 4.0, 4.0
        if abs(rot - 90) < 1 or abs(rot - 270) < 1:
            hw, hh = hh, hw
        bodies.append((ref_m.group(1), cx, cy, hw, hh))
    min_gap = 2.0
    clashes = []
    for i, (ra, ax, ay, aw, ah) in enumerate(bodies):
        for rb, bx, by, b_hw, b_hh in bodies[i + 1 :]:
            need_x = aw + b_hw + min_gap
            need_y = ah + b_hh + min_gap
            if abs(ax - bx) < need_x and abs(ay - by) < need_y:
                gx = need_x - abs(ax - bx)
                gy = need_y - abs(ay - by)
                clashes.append(f"{ra}/{rb}(short {min(gx, gy):.2f})")
    check(not clashes, ok, fail, f"courtyard gap>={min_gap}mm ({len(clashes)} clashes: {clashes[:12]})")

    print("=== E2) Non-jack parts ≥4mm from Edge.Cuts ===")
    edge_jacks = {
        "J1", "J_MOT1", "J_MOT2", "J14", "J15", "J_IN2", "J_IN3",
        "J_KEY", "J_DISP", "J_USB", "J_DBG",
    }
    if em:
        x0, y0, x1, y1 = map(float, em.groups())
        need = 4.0
        bad_m = []
        for ref, cx, cy, hw, hh in bodies:
            if ref in edge_jacks:
                continue
            d = min(cx - hw - x0, x1 - (cx + hw), cy - hh - y0, y1 - (cy + hh))
            if d < need - 0.05:
                bad_m.append(f"{ref}:{d:.2f}")
        check(not bad_m, ok, fail, f"non-jack edge clear≥{need}mm ({bad_m[:12]})")

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
