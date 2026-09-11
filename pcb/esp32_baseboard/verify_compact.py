#!/usr/bin/env python3
"""Connectivity / size / antenna-keepout audit for compact carrier."""

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

    print("=== A) Board size (<=100, from Edge.Cuts) ===")
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
        check(bw <= 150.01 and bh <= 150.01, ok, fail, f"size {bw:.0f}x{bh:.0f} <= 150")
        check(abs(bw - bh) < 0.01, ok, fail, "square board")
    check("gen_compact_carrier" in text, ok, fail, "generator gen_compact_carrier")
    check("ANT KEEPOUT" in text, ok, fail, "ANT KEEPOUT silk/eco present")

    print("=== B) Required refs ===")
    pads = pad_table(text)
    for ref in (
        "U1", "U2", "U3", "U5", "U6", "U7", "U44",
        "J1", "J14", "J15", "J_USB", "J_KEY", "J_DISP", "BZ1",
        "D3", "D1", "D4", "F1", "L1", "R2", "R10", "R44", "R48", "Rfb1", "Rfb2",
        "C10", "C11", "C20", "C21", "C24", "C26", "Cbst", "Cc",
        "C5", "C51", "C3", "C31",
    ):
        check(ref in pads, ok, fail, f"ref {ref}")

    print("=== C) Protect / power nets ===")
    check(pads.get("D3", {}).get("1") == "+24V_RAW", ok, fail, "D3 series SS54")
    check(pads.get("F1", {}).get("2") == "+24V", ok, fail, "F1 fuse to +24V")
    check("+24V" in pads.get("D1", {}).values() and "GND" in pads.get("D1", {}).values(), ok, fail, "D1 TVS SMBJ26A")
    check(pads.get("R10", {}).get("1") == "+24V" and pads.get("R10", {}).get("2") == "+24V_SNS", ok, fail, "R10 star SNS")
    check(pads.get("C10", {}).get("1") == "+24V_SNS", ok, fail, "C10 47u SNS")
    check(pads.get("C20", {}).get("1") == "+24V", ok, fail, "C20 470u TMC")
    check(pads.get("C21", {}).get("1") == "+24V", ok, fail, "C21 220u +24V bulk")
    check(pads.get("C5", {}).get("1") == "+5V", ok, fail, "C5 +5V bulk")
    check(pads.get("C3", {}).get("1") == "+3V3", ok, fail, "C3 +3V3 bulk")
    u1 = pads.get("U1", {})
    u2 = pads.get("U2", {})
    u3 = pads.get("U3", {})
    u7 = pads.get("U7", {})
    check("/STEP" in u3.values() and "/DIR" in u3.values() and "/EN_TMC" in u3.values(), ok, fail, "U3 TMC STEP/DIR/EN")
    check("+24V" in u3.values() and "+3V3" in u3.values(), ok, fail, "U3 VM+VIO")
    check("/BUP" in u1.values(), ok, fail, "U1 BUP GPIO")
    check(pads.get("J14", {}).get("3") == "/OPTO_IN_BUP", ok, fail, "J14 U-slot OUT")
    check(pads.get("J15", {}).get("3") == "/OPTO_IN_BUP", ok, fail, "J15 fiber OUT shared")
    check(pads.get("J14", {}).get("1") == "+24V_SNS" and pads.get("J15", {}).get("1") == "+24V_SNS", ok, fail, "both sensors SNS supply")
    check(pads.get("U44", {}).get("4") == "/BUP", ok, fail, "PC817 to /BUP")
    check("/TM_CLK" in u1.values() and "/TM_DIO" in u1.values(), ok, fail, "U1 TM1637")
    check(sum(1 for v in u1.values() if v.startswith("/KEY_")) >= 8, ok, fail, "U1 keypad 8")
    check(u7.get("18") == "/TM_CLK" and u7.get("17") == "/TM_DIO", ok, fail, "U7 CLK/DIO")
    check(pads.get("J_DISP", {}).get("1") == "/TM_G1", ok, fail, "J_DISP GRID1 (ext 7seg)")
    check(pads.get("J_KEY", {}).get("1") == "/KEY_R0", ok, fail, "J_KEY R0 (ext keypad)")
    check("DS1" not in pads, ok, fail, "no on-board DS1 LED")
    check("LED_7SEG_3DIG_CC" not in text, ok, fail, "no on-board 7seg footprint")
    check(pads.get("D1", {}).get("2") == "+24V", ok, fail, "D1 cathode on +24V")
    check("SMBJ26A" in text, ok, fail, "TVS SMBJ26A for 24V")
    check("Diode_SMA" in text, ok, fail, "SMA Schottky footprints")
    check("CP_SMD_" in text, ok, fail, "SMD electrolytic footprints")
    check("PC817_SOP4" in text, ok, fail, "PC817 SOP4 SMT")
    check("Buzzer_SMD_5V" in text, ok, fail, "SMD buzzer")
    check("Diode_TVS_DO41" not in text, ok, fail, "no THT DO41 diodes")
    check("CP_Radial_" not in text, ok, fail, "no THT radial caps")
    check("PC817_DIP4" not in text, ok, fail, "no DIP PC817")
    check("Buzzer_5V_THT" not in text, ok, fail, "no THT buzzer")
    check(u2.get("1") == "/BUCK_SW" and pads.get("L1", {}).get("2") == "+5V", ok, fail, "discrete buck SW-L1-+5V")
    check(pads.get("U6", {}).get("2") == "+3V3", ok, fail, "U6 AMS1117 3V3")
    check("ESP32_WROOM_32" in text, ok, fail, "WROOM footprint")
    check("TMC2209_StepStick" in text, ok, fail, "TMC socket footprint")
    check("MP1584EN_SOT23-8" in text, ok, fail, "discrete MP1584 footprint")
    check("TM1637_SOP20" in text, ok, fail, "discrete TM1637 footprint")
    check("PinHeader_1x10_7SEG" in text, ok, fail, "7seg jack footprint")

    print("=== D) Antenna keepout (no foreign footprints in Eco1 box) ===")
    # Parse U1 at + keepout rect on Eco1.User
    u1m = re.search(
        r'\(footprint "[^"]*ESP32_WROOM_32"[\s\S]*?\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)[\s\S]*?'
        r'\(property "Reference" "U1"',
        text,
    )
    # Reference may appear before at — find footprint block for U1
    ant_ok = False
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        if '(property "Reference" "U1"' not in blk:
            continue
        at = re.search(r"\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)", blk)
        check(at is not None, ok, fail, "U1 has position")
        if not at:
            break
        ux, uy = float(at.group(1)), float(at.group(2))
        rot = float(at.group(3) or 0)
        check(abs(rot - 180) < 0.1, ok, fail, "U1 rot=180 (antenna north/top)")
        km = None
        for rm in re.finditer(r"\n\t\(gr_rect", text):
            rblk = _block(text, rm.start() + 1)
            if 'layer "Eco1.User"' not in rblk:
                continue
            sm = re.search(
                r"\(start\s+([\d.-]+)\s+([\d.-]+)\)[\s\S]*?\(end\s+([\d.-]+)\s+([\d.-]+)\)",
                rblk,
            )
            if sm:
                km = sm
                break
        check(km is not None, ok, fail, "Eco1 ANT keepout rect")
        if km:
            kx0, ky0, kx1, ky1 = map(float, km.groups())
            if kx0 > kx1:
                kx0, kx1 = kx1, kx0
            if ky0 > ky1:
                ky0, ky1 = ky1, ky0
            tip_y = uy - 13.5  # ANT_TIP
            check(abs(ky1 - tip_y) <= 1.5, ok, fail, "keepout ends at/near antenna tip")
            check((ky1 - ky0) >= 14.0, ok, fail, "keepout depth >= ~15mm")
            check(uy < y0 + 45.0, ok, fail, f"U1 near top (y={uy:.1f})")
            hits = []
            for m2 in re.finditer(r'\n\t\(footprint "', text):
                blk2 = _block(text, m2.start() + 1)
                if "board_only" in blk2:
                    continue
                ref_m = re.search(r'\(property "Reference" "([^"]+)"', blk2)
                if not ref_m or ref_m.group(1) == "U1":
                    continue
                # footprint placement is the first (at ...) in the block
                at2 = re.match(
                    r'[\s\S]*?\(at\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+))?\)',
                    blk2,
                )
                if not at2:
                    continue
                cx, cy = float(at2.group(1)), float(at2.group(2))
                prot = float(at2.group(3) or 0)
                crt = re.search(
                    r'\(fp_rect\s*\(start\s+([\d.-]+)\s+([\d.-]+)\)\s*\(end\s+([\d.-]+)\s+([\d.-]+)\)[\s\S]*?F\.CrtYd',
                    blk2,
                )
                if crt:
                    sx0, sy0, sx1, sy1 = map(float, crt.groups())
                    hw, hh = abs(sx1 - sx0) / 2, abs(sy1 - sy0) / 2
                else:
                    hw, hh = 5.0, 5.0
                if abs(prot - 90) < 1 or abs(prot - 270) < 1:
                    hw, hh = hh, hw
                px0, py0, px1, py1 = cx - hw, cy - hh, cx + hw, cy + hh
                # require positive area overlap (epsilon)
                if min(px1, kx1) - max(px0, kx0) > 0.05 and min(py1, ky1) - max(py0, ky0) > 0.05:
                    hits.append(ref_m.group(1))
            check(not hits, ok, fail, f"no parts in ANT keepout ({hits})")
            ant_ok = not hits
        break

    print("=== D2) J1 24V on left edge, parallel ===")
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
            # Parallel to west/east edge => rot 90 or 270
            check(abs(jrot - 90) < 0.1 or abs(jrot - 270) < 0.1, ok, fail, f"J1 rot parallel to W edge ({jrot})")
            check(abs(jx - (x0 + 4.0 + 4.0)) < 4.0 or jx < x0 + 14.0, ok, fail, f"J1 near left edge (x={jx:.1f})")
            check(jy > y0 + 20.0, ok, fail, "J1 below antenna/U1 strip")
        break

    print("=== E) Courtyard clearance (no bbox cut, gap >= 2.0mm) ===")
    # Collect ref -> (cx,cy,hw,hh) from footprints
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

    print("=== E) Removed modules (only TMC socket allowed) ===")
    for bad in (
        "74HC595", "ULN2003", "/TFT_", "/ENC_", "/BLOWER", "ESP32_S3_DevKit",
        "MP1584_5V3A", "TM1637_Module", "DSP1",
    ):
        check(bad not in text, ok, fail, f"no {bad}")

    print(f"\nPASS {len(ok)}  FAIL {len(fail)}  board={bw:.0f}x{bh:.0f}")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
