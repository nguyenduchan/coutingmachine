#!/usr/bin/env python3
"""Polarity / pin-1 / connector-mouth gate (SMT assembly).

Fails if a diode, electrolytic, IC, USB, TMC socket, or field jack is wired
or rotated so the physical part would be reversed. Writes
out/orientation_verify.json. Run via:

  python verify_orientation.py
  python verify_pre_fab.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from verify_jlcpcb import _block, parse_fps

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "esp32_baseboard.kicad_pcb"
OUT = ROOT / "out"
JSON_OUT = OUT / "orientation_verify.json"

POS = {
    "+24V_RAW", "+24V_PRE", "+24V", "+24V_SNS", "+24V_SNS_PRE",
    "+24V_MOT", "+24V_MOT2", "+5V", "+3V3", "/BUCK_SW",
}


def net_of(fp: dict, num: str) -> str:
    for p in fp["pads"]:
        if p["num"] == num:
            return p["net"] or ""
    return ""


def pad(fp: dict, num: str):
    for p in fp["pads"]:
        if p["num"] == num:
            return p
    return None


def main() -> int:
    text = PCB.read_text(encoding="utf-8")
    fps = {f["ref"]: f for f in parse_fps(text) if not f["board_only"]}
    em = re.search(
        r'\(gr_rect\s*\(start\s+([\d.]+)\s+([\d.]+)\)\s*\(end\s+([\d.]+)\s+([\d.]+)\)'
        r'[\s\S]*?layer "Edge\.Cuts"',
        text,
    )
    if not em:
        print("FAIL no Edge.Cuts rect")
        return 1
    x0, y0, x1, y1 = map(float, em.groups())
    ok: list[str] = []
    fail: list[str] = []
    warn: list[str] = []
    checks: list[dict] = []

    def check(cond: bool, msg: str, section: str, bucket: list | None = None) -> None:
        dest = bucket if bucket is not None else fail
        (ok if cond else dest).append(msg)
        print(("  OK  " if cond else (" WARN " if dest is warn else " FAIL ")) + msg)
        checks.append({"section": section, "ok": bool(cond), "warn": dest is warn, "msg": msg})

    def fp(ref: str, section: str):
        hit = fps.get(ref)
        check(hit is not None, f"ref {ref} on board", section)
        return hit

    print("=== Diodes (pad1=A, pad2=K; silk bar on K) ===")
    sec = "diode"
    d3 = fp("D3", sec)
    if d3:
        check(net_of(d3, "1") == "+24V_RAW" and net_of(d3, "2") == "+24V_PRE",
              "D3 series A=RAW K=PRE", sec)
    d4 = fp("D4", sec)
    if d4:
        check(net_of(d4, "1") == "GND" and net_of(d4, "2") == "/BUCK_SW",
              "D4 catch A=GND K=SW", sec)
    d1 = fp("D1", sec)
    if d1:
        check(net_of(d1, "1") == "GND" and net_of(d1, "2") == "+24V",
              "D1 TVS A=GND K=+24V", sec)
    d5 = fp("D5", sec)
    if d5:
        check(net_of(d5, "1") == "GND" and net_of(d5, "2") == "+5V",
              "D5 TVS A=GND K=+5V", sec)

    print("=== Electrolytic (KiCad CP pin1 = +) ===")
    sec = "cap"
    for ref in ("C3", "C5", "C10", "C20", "C20B", "C21"):
        c = fp(ref, sec)
        if not c:
            continue
        n1, n2 = net_of(c, "1"), net_of(c, "2")
        check(n1 in POS and n2 == "GND", f"{ref} +={n1} -={n2}", sec)

    print("=== STM32 U1 LQFP48 pin1 NW ===")
    sec = "mcu"
    u1 = fp("U1", sec)
    if u1:
        check(abs(u1["rot"]) < 0.5, f"U1 rot={u1['rot']} (expect 0)", sec)
        p1, p13, p25, p37 = pad(u1, "1"), pad(u1, "13"), pad(u1, "25"), pad(u1, "37")
        check(bool(p1) and p1["x"] < u1["x"] and p1["y"] < u1["y"],
              "U1 pin1 left-north of body", sec)
        check(bool(p13 and p25 and p37)
              and p13["y"] > u1["y"] and p25["x"] > u1["x"] and p37["y"] < u1["y"],
              "U1 CCW: 13 south, 25 east, 37 north", sec)
        check(net_of(u1, "6") == "+3V3" and net_of(u1, "7") == "GND", "U1 VDD/VSS", sec)
        check(net_of(u1, "4") == "+3V3" and net_of(u1, "10") == "/NRST", "U1 VBAT/NRST", sec)

    print("=== MP1584 U2 SOIC-8-EP ===")
    sec = "buck"
    u2 = fp("U2", sec)
    if u2:
        check(net_of(u2, "1") == "/BUCK_SW" and net_of(u2, "7") == "+24V",
              "U2 pin1=SW pin7=VIN", sec)
        check(net_of(u2, "5") == "GND" and net_of(u2, "4") == "/BUCK_FB", "U2 GND/FB", sec)
        check(net_of(u2, "9") == "GND", "U2 EP=GND", sec)
        check(net_of(u2, "2") in ("", "unconnected"), "U2 EN floating", sec)

    print("=== CH340C U5 SOP-16 ===")
    sec = "usb_uart"
    u5 = fp("U5", sec)
    if u5:
        check(net_of(u5, "1") == "GND" and net_of(u5, "16") == "+5V", "U5 GND/VCC", sec)
        check(net_of(u5, "2") == "/UART_RX" and net_of(u5, "3") == "/UART_TX",
              "U5 TXD to MCU RX (crossed UART)", sec)
        check(net_of(u5, "5") == "/USB_DP" and net_of(u5, "6") == "/USB_DM", "U5 UD+/UD-", sec)
        p1, p8, p9, p16 = pad(u5, "1"), pad(u5, "8"), pad(u5, "9"), pad(u5, "16")
        check(bool(p1 and p8 and p9 and p16) and p1["y"] < p8["y"] and p16["y"] < p9["y"],
              f"U5 SOIC pin1 north of pin8 (rot={u5['rot']})", sec)

    print("=== AMS1117 U6 SOT-223 ===")
    sec = "ldo"
    u6 = fp("U6", sec)
    if u6:
        check(net_of(u6, "1") == "GND" and net_of(u6, "2") == "+3V3"
              and net_of(u6, "3") == "+5V" and net_of(u6, "TAB") == "+3V3",
              "U6 1=GND 2=VOUT 3=VIN TAB=VOUT", sec)
        t, p1 = pad(u6, "TAB"), pad(u6, "1")
        check(bool(t and p1) and abs(t["x"] - p1["x"]) > 2, "U6 tab opposite 3 pins", sec)

    print("=== PC817 SOP-4  1=A 2=K 3=E 4=C ===")
    sec = "opto"
    opto = {
        "U44": ("/OPTO_IN_BUP", "/BUP"),
        "U45": ("/OPTO_IN2", "/IN2"),
        "U46": ("/OPTO_IN3", "/IN3"),
        "U47": ("/OPTO_IN_5V", "/CNT5"),
    }
    for ref, (anode, coll) in opto.items():
        u = fp(ref, sec)
        if not u:
            continue
        check(net_of(u, "1") == anode and net_of(u, "2") == "GND"
              and net_of(u, "3") == "GND" and net_of(u, "4") == coll,
              f"{ref} A/K/E/C nets", sec)
        a, k = pad(u, "1"), pad(u, "2")
        check(bool(a and k) and a["y"] < k["y"], f"{ref} anode north of cathode", sec)

    print("=== Crystal Y1 3225 ===")
    sec = "xtal"
    xtal = fp("Y1", sec)
    if xtal:
        check(net_of(xtal, "1") == "/CH340_XI" and net_of(xtal, "3") == "/CH340_XO",
              "Y1 XI/XO", sec)
        check(net_of(xtal, "2") == "GND" and net_of(xtal, "4") == "GND", "Y1 pads 2/4 GND", sec)

    print("=== USB Micro-B mouth north ===")
    sec = "usb"
    ju = fp("J_USB", sec)
    if ju:
        check(abs(ju["rot"] - 180) < 1, f"J_USB rot={ju['rot']} (180 = mouth north)", sec)
        check(net_of(ju, "1") == "+5V" and net_of(ju, "2") == "/USB_DM"
              and net_of(ju, "3") == "/USB_DP" and net_of(ju, "5") == "GND",
              "J_USB 1=VBUS 2=D- 3=D+ 5=GND", sec)
        check(ju["y"] < y0 + 0.35 * (y1 - y0), f"J_USB on north half y={ju['y']:.1f}", sec)

    print("=== J1 24V IN ===")
    sec = "inlet"
    j1 = fp("J1", sec)
    if j1:
        check(net_of(j1, "1") == "+24V_RAW" and net_of(j1, "2") == "GND", "J1 + / GND", sec)
        check(abs(j1["rot"]) < 1, f"J1 rot={j1['rot']} (0 = entry south)", sec)
        check(j1["y"] > y1 - 20, f"J1 near south edge y={j1['y']:.1f}", sec)
        p1, p2 = pad(j1, "1"), pad(j1, "2")
        check(bool(p1 and p2) and p1["x"] < p2["x"], "J1 pin1 west of pin2", sec)

    print("=== F1 5x20 holder ===")
    sec = "fuse"
    f1 = fp("F1", sec)
    if f1:
        check("Fuse_Holder_5x20" in text, "F1 is 5x20 holder (not 2410 SMT)", sec)
        check(net_of(f1, "1") in ("+24V_PRE", "+24V") and net_of(f1, "2") in ("+24V_PRE", "+24V"),
              f"F1 in fuse path {net_of(f1, '1')} / {net_of(f1, '2')}", sec)
        a, b = pad(f1, "1"), pad(f1, "2")
        check(bool(a and b) and abs(a["y"] - b["y"]) < abs(a["x"] - b["x"]),
              "F1 clips east-west", sec)

    print("=== TMC sockets (BTT pin1=EN) ===")
    sec = "tmc"
    for ref, vm, en in (("U3", "+24V_MOT", "/EN_TMC"), ("U4", "+24V_MOT2", "/EN_TMC2")):
        u = fp(ref, sec)
        if not u:
            continue
        check(net_of(u, "1") == en and net_of(u, "9") == vm, f"{ref} EN/VM", sec)
        check(net_of(u, "15") == "+3V3" and net_of(u, "10") == "GND", f"{ref} VIO/GND", sec)
        check(net_of(u, "7").startswith("/STEP") and net_of(u, "8").startswith("/DIR"),
              f"{ref} STEP/DIR", sec)
        e, vm_p = pad(u, "1"), pad(u, "9")
        check(bool(e and vm_p) and e["x"] < vm_p["x"],
              f"{ref} CTRL west, PWR east", sec)

    print("=== Tact SW poles ===")
    sec = "switch"
    boot, nrst = fp("SW_BOOT", sec), fp("SW_NRST", sec)
    if boot:
        check(net_of(boot, "1") == "/SWCLK" and net_of(boot, "2") == "/SWCLK"
              and net_of(boot, "3") == "+3V3" and net_of(boot, "4") == "+3V3",
              "SW_BOOT shorts SWCLK to +3V3", sec)
    if nrst:
        check(net_of(nrst, "1") == "/NRST" and net_of(nrst, "2") == "/NRST"
              and net_of(nrst, "3") == "GND" and net_of(nrst, "4") == "GND",
              "SW_NRST shorts NRST to GND", sec)

    print("=== North XH pin1 ===")
    sec = "jack_n"
    north = {
        "J14": ("+24V_SNS", "GND"),
        "J15": ("+24V_SNS", "GND"),
        "J_IN2": ("+24V_SNS", "GND"),
        "J_IN3": ("+24V_SNS", "GND"),
        "J_CNT5": ("+5V", "GND"),
        "J_DISP": ("/TM_CLK", "/TM_DIO"),
    }
    for ref, (a, b) in north.items():
        j = fp(ref, sec)
        if not j:
            continue
        check(net_of(j, "1") == a and net_of(j, "2") == b,
              f"{ref} p1={net_of(j, '1')} p2={net_of(j, '2')}", sec)
        check(j["y"] < y0 + 0.45 * (y1 - y0), f"{ref} on north y={j['y']:.1f}", sec)
    j14 = fp("J14", sec)
    if j14:
        check(net_of(j14, "3") == "/OPTO_IN_BUP" and net_of(j14, "4") == "+24V_SNS",
              "J14 OUT + CTRL Light ON (+V)", sec)

    print("=== South power / motor ===")
    sec = "jack_s"
    jp = fp("J_P24S", sec)
    if jp:
        check(net_of(jp, "1") == "+24V" and net_of(jp, "2") == "GND", "J_P24S +24V/GND", sec)
    m1, m2 = fp("J_MOT1", sec), fp("J_MOT2", sec)
    if m1 and m2:
        check(net_of(m1, "1") == "/MotA2" and net_of(m2, "1") == "/Mot2A2",
              "J_MOT pin1 = A2", sec)

    print("=== U_PWR / U_VIB pin1 = +24V ===")
    sec = "module"
    p1 = fp("U_PWR1", sec)
    if p1:
        check(net_of(p1, "1") == "+24V" and net_of(p1, "3") == "+3V3", "U_PWR1 +24V / 3V3", sec)
    p2 = fp("U_PWR2", sec)
    if p2:
        check(net_of(p2, "1") == "+24V", "U_PWR2 pin1 +24V", sec)
    uv = fp("U_VIB", sec)
    if uv:
        check(net_of(uv, "1") == "+24V" and net_of(uv, "3") == "/VIB_CTRL",
              "U_VIB +24V / CTRL", sec)

    print("=== L1 inductor ===")
    sec = "inductor"
    l1 = fp("L1", sec)
    if l1:
        check(net_of(l1, "1") == "/BUCK_SW" and net_of(l1, "2") == "+5V", "L1 SW to +5V", sec)

    print("=== 3D model rotate vs pads ===")
    sec = "3d"
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not rm:
            continue
        ref = rm.group(1)
        if ref not in ("U1", "U2", "U5", "U6", "D1", "D3", "D4", "D5",
                       "C3", "C5", "C10", "C20", "J_USB", "Y1"):
            continue
        rotm = re.search(
            r"\(model [\s\S]*?\(rotate\s+\(xyz\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)",
            blk,
        )
        if rotm:
            rx, ry, rz = map(float, rotm.groups())
            check(abs(rx) < 1 and abs(ry) < 1 and abs(rz) < 1,
                  f"{ref} 3D rotate ({rx},{ry},{rz})", sec, warn)

    overall = not fail
    report = {
        "overall": "PASS" if overall else "FAIL",
        "ok": len(ok),
        "fail": len(fail),
        "warn": len(warn),
        "fails": fail,
        "warns": warn,
        "checks": checks,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print()
    print(f"OK={len(ok)}  WARN={len(warn)}  FAIL={len(fail)}")
    for m in fail:
        print("  FAIL", m)
    print(f"Wrote {JSON_OUT}")
    print(f"OVERALL: {report['overall']}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
