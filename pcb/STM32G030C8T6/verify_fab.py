#!/usr/bin/env python3
"""Fab-readiness: schematic is the source of truth; the PCB must match it.

Algorithm (run before sending Gerbers to a fab):

  1. SCH     — kicad-cli sch export netlist (kicadxml) + sch erc
  2. PCB     — pad→net and footprints on STM32G030C8T6.kicad_pcb
  3. MATCH   — every schematic pin net equals the PCB pad net (and vice versa)
  4. LOGIC   — ERC clean + electrical sanity on the schematic netlist
  5. COPPER  — KiCad unconnected / clearance (routing, not assignment)
  6. PARITY  — pcb drc --schematic-parity (ignore KiCad 10 {slash} alias)

The generator P() dict is logged as extra info. It is not the want-list.
A PCB that matches a wrong schematic still fails ERC / sanity.

  python verify_fab.py

Exit 0 only if schematic logic and SCH↔PCB assignment/footprints pass *and*
copper is joined. Writes out/fab_verify.json.
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from pcb_parse import NetTable, pad_net
from stm32_pinmap import (
    BOOT_PINS,
    BUP_PIN,
    CNT5_PIN,
    IN2_PIN,
    IN3_PIN,
    KEYPAD_PINS,
    LQFP48_PINS,
    PWR_PINS,
    TMC2_PINS,
    TMC_PINS,
    TM1637_PINS,
    USART1_PINS,
    VIB_PINS,
)

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "STM32G030C8T6.kicad_pcb"
SCH = ROOT / "STM32G030C8T6.kicad_sch"
GEN = ROOT / "gen_compact_carrier.py"
OUT = ROOT / "out"
JSON_OUT = OUT / "fab_verify.json"

POWER_NETS = frozenset({
    "GND", "+3V3", "+5V", "+24V", "+24V_RAW", "+24V_PRE",
    "+24V_SNS", "+24V_SNS_PRE", "+24V_MOT", "+24V_MOT2",
    "/BUCK_SW", "/BUCK_FB", "/BUCK_COMP", "/BUCK_BS",
})
POWER_RAILS = ("GND", "+3V3", "+5V", "+24V", "+24V_RAW", "+24V_MOT", "+24V_MOT2", "+24V_SNS")

NET_FN: dict[str, tuple[str, str]] = {
    "GND": ("POWER", "Common return"),
    "+3V3": ("POWER", "STM32 / TMC logic / opto collector pull-up"),
    "+5V": ("POWER", "USB / CH340 / TM1637 / 5V count jack"),
    "+24V": ("POWER", "Fused 24 V after D3+F1 (motors, MOSFET modules)"),
    "+24V_RAW": ("POWER", "Terminal J1 incoming 24 V (before reverse diode)"),
    "+24V_PRE": ("POWER", "After D3, before fuse F1"),
    "+24V_SNS": ("POWER", "PTC+R10 branch for 24 V sensors"),
    "+24V_SNS_PRE": ("POWER", "After PTC_SNS, before R10"),
    "+24V_MOT": ("POWER", "TMC1 VM after PTC_MOT"),
    "+24V_MOT2": ("POWER", "TMC2 VM after PTC_MOT2"),
    "/BUCK_SW": ("POWER", "MP1584 switch node → L1 → +5V"),
    "/BUCK_FB": ("POWER", "MP1584 feedback (Rfb1/Rfb2)"),
    "/BUCK_COMP": ("POWER", "MP1584 compensation Cc"),
    "/BUCK_BS": ("POWER", "MP1584 bootstrap Cbst"),
    "/STEP": ("TMC1", "STM32 PA0 → TMC2209 U3 STEP"),
    "/DIR": ("TMC1", "STM32 PA1 → TMC2209 U3 DIR"),
    "/EN_TMC": ("TMC1", "STM32 PA2 → TMC2209 U3 EN (R2 pull-up 3V3)"),
    "/MotA1": ("TMC1", "U3 coil A1 → J_MOT1.2"),
    "/MotA2": ("TMC1", "U3 coil A2 → J_MOT1.1"),
    "/MotB1": ("TMC1", "U3 coil B1 → J_MOT1.3"),
    "/MotB2": ("TMC1", "U3 coil B2 → J_MOT1.4"),
    "/STEP2": ("TMC2", "STM32 PA6 → TMC2209 U4 STEP"),
    "/DIR2": ("TMC2", "STM32 PA7 → TMC2209 U4 DIR"),
    "/EN_TMC2": ("TMC2", "STM32 PA8 → TMC2209 U4 EN (R2B pull-up 3V3)"),
    "/Mot2A1": ("TMC2", "U4 coil A1 → J_MOT2.2"),
    "/Mot2A2": ("TMC2", "U4 coil A2 → J_MOT2.1"),
    "/Mot2B1": ("TMC2", "U4 coil B1 → J_MOT2.3"),
    "/Mot2B2": ("TMC2", "U4 coil B2 → J_MOT2.4"),
    "/BUP": ("COUNT", "PC817 U44 collector → STM32 PA3 count input"),
    "/OPTO_IN_BUP": ("COUNT", "J14/J15 NPN LED → U44 anode (24 V slot/fiber)"),
    "/IN2": ("IN", "PC817 U45 collector → STM32 PB15"),
    "/OPTO_IN2": ("IN", "J_IN2 NPN LED → U45 anode"),
    "/IN3": ("IN", "PC817 U46 collector → STM32 PB4"),
    "/OPTO_IN3": ("IN", "J_IN3 NPN LED → U46 anode"),
    "/CNT5": ("COUNT", "PC817 U47 collector → STM32 PD1 (5 V through-beam)"),
    "/OPTO_IN_5V": ("COUNT", "J_CNT5 NPN LED → U47 anode"),
    "/PWM_OUT1": ("PWRMOD", "STM32 PA11 PWM → MOSFET module U_PWR1.4"),
    "/PWM_OUT2": ("PWRMOD", "STM32 PA12 PWM → MOSFET module U_PWR2.4"),
    "/PWR_EN1": ("PWRMOD", "STM32 PB5 enable → U_PWR1.5"),
    "/PWR_EN2": ("PWRMOD", "STM32 PB6 enable → U_PWR2.5"),
    "/PWR_FAULT": ("PWRMOD", "Shared OD fault U_PWR1/2.6 → STM32 PB7, R_PWR_FLT PU"),
    "/VIB_CTRL": ("VIB", "STM32 PB8 → SSR socket U_VIB.3"),
    "/VIB_FAULT": ("VIB", "U_VIB.4 → STM32 PB9, R_VIB_FLT PU"),
    "/TM_CLK": ("HMI", "STM32 PA4 → J_DISP.1 TM1637 CLK"),
    "/TM_DIO": ("HMI", "STM32 PA5 → J_DISP.2 TM1637 DIO"),
    "/KEY_R0": ("HMI", "STM32 PB0 → keypad row 0 J_KEY.1"),
    "/KEY_R1": ("HMI", "STM32 PB1 → keypad row 1 J_KEY.2"),
    "/KEY_R2": ("HMI", "STM32 PB2 → keypad row 2 J_KEY.3"),
    "/KEY_R3": ("HMI", "STM32 PB10 → keypad row 3 J_KEY.4"),
    "/KEY_C0": ("HMI", "STM32 PB11 → keypad col 0 J_KEY.5"),
    "/KEY_C1": ("HMI", "STM32 PB12 → keypad col 1 J_KEY.6"),
    "/KEY_C2": ("HMI", "STM32 PB13 → keypad col 2 J_KEY.7"),
    "/KEY_C3": ("HMI", "STM32 PB14 → keypad col 3 J_KEY.8"),
    "/UART_TX": ("MCU", "STM32 PA9 USART1_TX → CH340C U5.3 (MCU TX / CH340 RX)"),
    "/UART_RX": ("MCU", "STM32 PA10 USART1_RX → CH340C U5.2 (MCU RX / CH340 TX)"),
    "/USB_DM": ("MCU", "USB D− J_USB.2 ↔ CH340C U5.6"),
    "/USB_DP": ("MCU", "USB D+ J_USB.3 ↔ CH340C U5.5"),
    "/CH340_XI": ("MCU", "CH340 crystal XI + C_XI"),
    "/CH340_XO": ("MCU", "CH340 crystal XO + C_XO"),
    "/CH340_V3": ("MCU", "CH340C V3 LDO out + C_V3; not tied to AMS1117"),
    "/NRST": ("MCU", "STM32 NRST + SW_NRST + R_NRST PU + C_NRST"),
    "/SWDIO": ("MCU", "STM32 PA13 SWDIO + R_SWDIO PU"),
    "/SWCLK": ("MCU", "STM32 PA14 SWCLK/BOOT0 + SW_BOOT + R_BOOT PD"),
    "/LED_RUN": ("LED", "STM32 PB2 → R_LEDRUN → D_LEDRUN → GND (heartbeat)"),
    "/LED_ERR": ("LED", "STM32 PC6 → R_LEDERR → D_LEDERR → GND (fault)"),
    "/LED24_A": ("LED", "R_LED24 ↔ D_LED24 anode (+24V status)"),
    "/LED33_A": ("LED", "R_LED33 ↔ D_LED3V3 anode (+3V3 status)"),
    "/LEDRUN_A": ("LED", "R_LEDRUN ↔ D_LEDRUN anode"),
    "/LEDERR_A": ("LED", "R_LEDERR ↔ D_LEDERR anode"),
    "/LEDBUP_A": ("LED", "R_LEDBUP ↔ D_LEDBUP anode (count BUP activity)"),
    "/LEDCNT5_A": ("LED", "R_LEDCNT5 ↔ D_LEDCNT5 anode (count 5V activity)"),
    "/LEDIN2_A": ("LED", "R_LEDIN2 ↔ D_LEDIN2 anode"),
    "/LEDIN3_A": ("LED", "R_LEDIN3 ↔ D_LEDIN3 anode"),
}

FATAL_DRC = {
    "unconnected_items", "shorting_items", "tracks_crossing", "clearance",
    "copper_edge_clearance", "hole_clearance", "hole_to_hole", "track_dangling",
    "via_dangling", "annular_width", "drill_out_of_range", "track_width",
    "invalid_outline", "footprint_type_mismatch", "duplicate_footprints",
    "missing_footprint", "extra_footprint", "net_conflict", "schematic_parity",
}
SKIP_DRC = {"lib_footprint_mismatch", "lib_footprint_issues"}
FATAL_ERC = {
    "pin_to_pin", "hier_label_mismatch", "confliction", "different_unit",
    "duplicate_reference", "power_pin_not_driven", "pin_not_connected",
    "similar_labels", "label_dangling", "global_label_dangling",
}


def _canon(n: str | None) -> str | None:
    if not n:
        return None
    if n.startswith("unconnected-") or n.startswith("unconnected"):
        return None
    return n.replace("{slash}", "/")


def _is_nc_alias_noise(desc: str) -> bool:
    """KiCad 10 names NC pads unconnected-(U1-1-Pad1) on PCB vs unconnected-(U1-Pad1) on SCH."""
    m = re.search(
        r"Pad net \(unconnected-\(([^)]+)\)\).*schematic \(unconnected-\(([^)]+)\)\)",
        desc,
    )
    if not m:
        return False

    def norm(s: str) -> str:
        return re.sub(r"-(\d+)-Pad", "-Pad", s)

    return norm(m.group(1)) == norm(m.group(2))


def _norm(n: str | None) -> str | None:
    return _canon(n)


def _fp_short(fp: str | None) -> str:
    return (fp or "").split(":")[-1]


def find_cli() -> str | None:
    if (cli := shutil.which("kicad-cli")):
        return cli
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiCad"
    hits = sorted(base.glob("*/bin/kicad-cli.exe"), reverse=True) if base.is_dir() else []
    return str(hits[0]) if hits else None


def _block(text: str, start: int) -> str:
    d, i = 0, start
    while i < len(text):
        if text[i] == "(":
            d += 1
        elif text[i] == ")":
            d -= 1
            if d == 0:
                return text[start : i + 1]
        i += 1
    raise ValueError("unbalanced")


def parse_pcb_pads(text: str) -> dict[str, dict[str, str | None]]:
    table = NetTable(text)
    out: dict[str, dict[str, str | None]] = {}
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = _block(text, m.start() + 1)
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not rm:
            continue
        ref = rm.group(1)
        pads: dict[str, str | None] = {}
        starts = [p.start() for p in re.finditer(r'\(pad\s+"', blk)]
        for k, ps in enumerate(starts):
            chunk = blk[ps : (starts[k + 1] if k + 1 < len(starts) else len(blk))]
            num = re.match(r'\(pad\s+"([^"]*)"', chunk)
            if not num or not num.group(1):
                continue
            _nid, name = pad_net(chunk, table)
            pads[num.group(1)] = _norm(name)
        out[ref] = pads
    return out


def _u1_intent() -> dict[str, str]:
    gpio_net = {
        TMC_PINS["STEP"]: "/STEP", TMC_PINS["DIR"]: "/DIR", TMC_PINS["EN"]: "/EN_TMC",
        TMC2_PINS["STEP"]: "/STEP2", TMC2_PINS["DIR"]: "/DIR2", TMC2_PINS["EN"]: "/EN_TMC2",
        BUP_PIN: "/BUP", IN2_PIN: "/IN2", IN3_PIN: "/IN3", CNT5_PIN: "/CNT5",
        PWR_PINS["PWM1"]: "/PWM_OUT1", PWR_PINS["PWM2"]: "/PWM_OUT2",
        PWR_PINS["EN1"]: "/PWR_EN1", PWR_PINS["EN2"]: "/PWR_EN2",
        PWR_PINS["FAULT"]: "/PWR_FAULT",
        VIB_PINS["CTRL"]: "/VIB_CTRL", VIB_PINS["FAULT"]: "/VIB_FAULT",
        TM1637_PINS["CLK"]: "/TM_CLK", TM1637_PINS["DIO"]: "/TM_DIO",
        KEYPAD_PINS["ROW0"]: "/KEY_R0", KEYPAD_PINS["ROW1"]: "/KEY_R1",
        KEYPAD_PINS["ROW2"]: "/KEY_R2", KEYPAD_PINS["ROW3"]: "/KEY_R3",
        KEYPAD_PINS["COL0"]: "/KEY_C0", KEYPAD_PINS["COL1"]: "/KEY_C1",
        KEYPAD_PINS["COL2"]: "/KEY_C2", KEYPAD_PINS["COL3"]: "/KEY_C3",
        USART1_PINS["TX"]: "/UART_TX", USART1_PINS["RX"]: "/UART_RX",
        BOOT_PINS["SWDIO"]: "/SWDIO", BOOT_PINS["SWCLK"]: "/SWCLK",
        "NRST": "/NRST", "VBAT": "+3V3", "VREF+": "+3V3", "VDD": "+3V3", "VSS": "GND",
    }
    return {str(num): gpio_net[name] for num, name in LQFP48_PINS if name in gpio_net}


def intent_from_generator() -> dict[str, dict[str, str]]:
    """P() pad_nets in gen_compact_carrier.build_parts — without rewriting libs."""
    tree = ast.parse(GEN.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_parts")
    parts: dict[str, dict[str, str]] = {"U1": _u1_intent()}
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "P"):
            continue
        if len(node.args) < 1 or not isinstance(node.args[0], ast.Constant):
            continue
        ref = str(node.args[0].value)
        pad_arg = node.args[4] if len(node.args) >= 5 else None
        for kw in node.keywords:
            if kw.arg == "pad_nets":
                pad_arg = kw.value
        if isinstance(pad_arg, ast.Dict):
            parts[ref] = {str(k): str(v) for k, v in ast.literal_eval(pad_arg).items()}
    return parts


def parse_sch_xml(path: Path) -> dict[str, dict[str, str | None]]:
    tree = ET.parse(path)
    out: dict[str, dict[str, str | None]] = defaultdict(dict)
    for net in tree.getroot().findall(".//net"):
        name = _norm(net.attrib.get("name") or net.attrib.get("Name"))
        for node in net.findall("node"):
            ref = node.attrib.get("ref") or node.attrib.get("Ref")
            pin = node.attrib.get("pin") or node.attrib.get("Pin")
            if ref and pin:
                out[ref][pin] = name
    return dict(out)


def pin_name(ref: str, pad: str) -> str:
    if ref == "U1":
        for num, name in LQFP48_PINS:
            if str(num) == pad:
                return f"U1.{pad}({name})"
    return f"{ref}.{pad}"


def parse_sch_footprints(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in re.finditer(r"\n\t\(symbol \(lib_id ", text):
        blk = _block(text, m.start() + 1)
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        fm = re.search(r'\(property "Footprint" "([^"]+)"', blk)
        if rm and fm:
            out[rm.group(1)] = fm.group(1)
    return out


def parse_pcb_footprints(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in re.finditer(r'\n\t\(footprint "([^"]+)"', text):
        blk = _block(text, m.start() + 1)
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if rm:
            out[rm.group(1)] = m.group(1)
    return out


def compare_sch_pcb(sch, pcb) -> list[dict]:
    """Want = schematic pin nets. PCB must equal SCH on every pin/pad."""
    rows = []
    refs = sorted({r for r in set(sch) | set(pcb) if not str(r).startswith("H")})
    for ref in refs:
        sp = sch.get(ref) or {}
        pp = pcb.get(ref) or {}
        pads = sorted(set(sp) | set(pp), key=lambda x: (len(x), x))
        for pad in pads:
            in_s = pad in sp
            in_p = pad in pp
            snet = _canon(sp.get(pad)) if in_s else None
            pnet = _canon(pp.get(pad)) if in_p else None
            if not in_s and not pnet:
                continue
            if in_s and not in_p:
                status, why = "FAIL", f"SCH={snet!r} missing on PCB"
            elif in_p and not in_s and pnet:
                status, why = "FAIL", f"PCB extra pad net={pnet!r} not on schematic"
            elif snet == pnet:
                status, why = "OK", ""
            else:
                status, why = "FAIL", f"PCB={pnet!r} SCH={snet!r}"
            wnet = snet if snet is not None else pnet
            rows.append({
                "ref": ref, "pad": pad, "pin": pin_name(ref, pad),
                "want": snet, "pcb": pnet, "sch": snet,
                "status": status, "why": why,
                "cluster": (NET_FN.get(wnet or "") or ("?", ""))[0],
                "fn": (NET_FN.get(wnet or "") or ("", "Assigned net"))[1],
            })
    return rows


def compare_intent_info(intent, sch) -> list[dict]:
    """Generator vs schematic — informational only, not a fab gate."""
    rows = []
    for ref, want in sorted(intent.items()):
        if ref.startswith("H"):
            continue
        sp = sch.get(ref) or {}
        for pad, wnet in sorted(want.items(), key=lambda kv: (len(kv[0]), kv[0])):
            snet = _canon(sp.get(pad))
            if snet == _canon(wnet):
                continue
            rows.append({
                "ref": ref, "pad": pad, "pin": pin_name(ref, pad),
                "intent": wnet, "sch": snet,
                "why": f"generator={wnet!r} SCH={snet!r}",
            })
    return rows


def compare_footprints(sch_fp: dict[str, str], pcb_fp: dict[str, str]) -> list[str]:
    fails = []
    for ref, sfp in sorted(sch_fp.items()):
        pfp = pcb_fp.get(ref)
        if not pfp:
            fails.append(f"{ref} on schematic, missing PCB footprint")
        elif _fp_short(sfp) != _fp_short(pfp):
            fails.append(f"{ref} SCH={sfp} PCB={pfp}")
    for ref, pfp in sorted(pcb_fp.items()):
        if ref.startswith("H"):
            continue
        if ref not in sch_fp:
            fails.append(f"{ref} on PCB, missing schematic")
    return fails


def pin_pairs(pcb: dict[str, dict[str, str | None]]) -> list[dict]:
    by_net: dict[str, list[str]] = defaultdict(list)
    for ref, pads in pcb.items():
        if ref.startswith("H"):
            continue
        for pad, net in pads.items():
            if net:
                by_net[net].append(pin_name(ref, pad))
    pairs = []
    for net, pins in sorted(by_net.items()):
        pins = sorted(set(pins))
        cluster, fn = NET_FN.get(net, ("OTHER", "Net on PCB"))
        hub = next((p for p in pins if p.startswith("U1.")), pins[0])
        others = [p for p in pins if p != hub]
        if net in POWER_NETS:
            pairs.append({
                "net": net, "cluster": cluster, "fn": fn, "kind": "power",
                "hub": hub, "count": len(pins),
                "members": ", ".join(pins[:8]) + (f" … +{len(pins)-8}" if len(pins) > 8 else ""),
                "pair": f"{len(pins)} pins on {net}",
                "ok": True,
            })
            continue
        if not others:
            pairs.append({
                "net": net, "cluster": cluster, "fn": fn, "kind": "orphan",
                "hub": hub, "count": 1, "members": hub,
                "pair": f"{hub} (no mate)", "ok": False,
            })
            continue
        pairs.append({
            "net": net, "cluster": cluster, "fn": fn, "kind": "signal",
            "hub": hub, "count": len(pins),
            "members": ", ".join(pins),
            "pair": f"{hub} ↔ " + ", ".join(others),
            "ok": True,
        })
    return pairs


def _get(table, ref: str, pad: str) -> str | None:
    return _canon((table.get(ref) or {}).get(pad))


def sanity(table, src: str, *, pcb_text: str | None = None) -> list[str]:
    """Electrical logic on a pin→net table (schematic netlist or PCB pads)."""
    fails = []
    u1 = table.get("U1") or {}
    checks = [
        (_canon(u1.get("6")) == "+3V3" and _canon(u1.get("7")) == "GND",
         f"{src} U1 VDD/VSS"),
        (_canon(u1.get("4")) == "+3V3" and _canon(u1.get("5")) == "+3V3",
         f"{src} U1 VBAT/VREF+"),
        (_canon(u1.get("10")) == "/NRST", f"{src} U1 NRST"),
        (_canon(u1.get("29")) == "/UART_TX" and _canon(u1.get("32")) == "/UART_RX",
         f"{src} U1 USART1"),
        (_canon(u1.get("35")) == "/SWDIO" and _canon(u1.get("36")) == "/SWCLK",
         f"{src} U1 SWDIO/SWCLK"),
        (_get(table, "U5", "2") == "/UART_RX", f"{src} CH340 TX → MCU RX"),
        (_get(table, "U5", "3") == "/UART_TX", f"{src} CH340 RX ← MCU TX"),
        (_get(table, "U5", "4") == "/CH340_V3", f"{src} CH340 V3 isolated"),
        (_get(table, "C_V3", "1") == "/CH340_V3" and _get(table, "C_V3", "2") == "GND",
         f"{src} C_V3"),
        (_get(table, "R_PD_PWM1", "1") == "/PWM_OUT1"
         and _get(table, "R_PD_EN1", "1") == "/PWR_EN1"
         and _get(table, "R_PD_VIB", "1") == "/VIB_CTRL", f"{src} P4.5 PD"),
        (_get(table, "J1", "1") == "+24V_RAW", f"{src} J1 +24V_RAW"),
        (_get(table, "J1", "2") == "GND", f"{src} J1 GND"),
        (_get(table, "J_USB", "1") == "+5V"
         and _get(table, "J_USB", "2") == "/USB_DM"
         and _get(table, "J_USB", "3") == "/USB_DP", f"{src} USB VBUS/D−/D+"),
        (_get(table, "J_USB", "5") == "GND"
         and _get(table, "J_USB", "MH1") == "GND"
         and _get(table, "J_USB", "MH2") == "GND", f"{src} USB GND+shield"),
        (_get(table, "U6", "1") == "GND"
         and _get(table, "U6", "2") == "+3V3"
         and _get(table, "U6", "3") == "+5V"
         and _get(table, "U6", "TAB") == "+3V3", f"{src} AMS1117 GND/VOUT/VIN/TAB"),
        (_get(table, "F1", "1") == "+24V_PRE" and _get(table, "F1", "2") == "+24V",
         f"{src} F1 fuse +24V_PRE→+24V"),
        (_get(table, "U3", "9") == "+24V_MOT" and _get(table, "U3", "15") == "+3V3",
         f"{src} TMC1 VM/VIO"),
        (_get(table, "U4", "9") == "+24V_MOT2" and _get(table, "U4", "15") == "+3V3",
         f"{src} TMC2 VM/VIO"),
    ]
    if pcb_text is not None:
        checks.append(("np_thru_hole" in pcb_text, f"{src} 4× M3 NPTH present"))
    for ok, msg in checks:
        if not ok:
            fails.append(msg)
    gpio_nets = {n for n in (_canon(v) for v in u1.values()) if n and n.startswith("/")}
    for n in gpio_nets:
        if n.lstrip("/") in {r.lstrip("/") for r in POWER_RAILS}:
            fails.append(f"{src} GPIO net collided with rail {n}")
    return fails


def run_kicad(cli: str | None) -> dict:
    out: dict = {"cli": bool(cli), "erc": {}, "drc": {}, "sch_xml": None}
    if not cli:
        return out
    OUT.mkdir(parents=True, exist_ok=True)
    xml_path = OUT / "sch_netlist.xml"
    erc_path = OUT / "erc_fab.json"
    drc_path = OUT / "drc_fab.json"
    subprocess.run(
        [cli, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(xml_path), str(SCH)],
        cwd=ROOT, capture_output=True, text=True,
    )
    if xml_path.exists():
        out["sch_xml"] = str(xml_path)
    subprocess.run(
        [cli, "sch", "erc", "--format", "json", "--severity-error", "-o", str(erc_path), str(SCH)],
        cwd=ROOT, capture_output=True, text=True,
    )
    subprocess.run(
        [cli, "pcb", "drc", "--format", "json", "--schematic-parity",
         "--severity-error", "--severity-warning", "-o", str(drc_path), str(PCB)],
        cwd=ROOT, capture_output=True, text=True,
    )

    def counts(path: Path, key: str) -> dict[str, int]:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        c: dict[str, int] = defaultdict(int)
        for v in data.get(key) or data.get("violations") or []:
            t = v.get("type") or v.get("severity") or "other"
            c[t] += 1
        # KiCad 10 json: { "sheets": [ { "violations": [...] } ] } or top violations
        if not c:
            for sheet in data.get("sheets") or []:
                for v in sheet.get("violations") or []:
                    c[v.get("type", "other")] += 1
        if not c:
            for v in data.get("violations") or []:
                c[v.get("type", "other")] += 1
        return dict(c)

    out["erc"] = counts(erc_path, "violations")
    out["drc"] = counts(drc_path, "violations")
    # KiCad 10 pcb drc json often { "violations": [ {"type": ...} ], "schematic_parity": [...] }
    if drc_path.exists():
        data = json.loads(drc_path.read_text(encoding="utf-8"))
        for extra in ("schematic_parity", "unconnected_items"):
            items = data.get(extra)
            if isinstance(items, list) and items:
                out["drc"][extra] = out["drc"].get(extra, 0) + len(items)
        if not out["drc"]:
            for v in data.get("violations") or []:
                out["drc"][v.get("type", "other")] = out["drc"].get(v.get("type", "other"), 0) + 1
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pcb_text = PCB.read_text(encoding="utf-8")
    pcb = parse_pcb_pads(pcb_text)
    intent = intent_from_generator()
    kicad = run_kicad(find_cli())
    sch: dict[str, dict[str, str | None]] = {}
    if kicad.get("sch_xml") and Path(kicad["sch_xml"]).exists():
        sch = parse_sch_xml(Path(kicad["sch_xml"]))

    rows = compare_sch_pcb(sch, pcb)
    mismatches = [r for r in rows if r["status"] == "FAIL"]
    warns = [r for r in rows if r["status"] == "WARN"]
    intent_drift = compare_intent_info(intent, sch) if sch else []
    sch_fp = parse_sch_footprints(SCH.read_text(encoding="utf-8")) if SCH.exists() else {}
    pcb_fp = parse_pcb_footprints(pcb_text)
    fp_fail = compare_footprints(sch_fp, pcb_fp)
    pairs = pin_pairs(sch if sch else pcb)
    orphans = [p for p in pairs if not p["ok"]]
    sanity_fail = sanity(sch, "SCH") + sanity(pcb, "PCB", pcb_text=pcb_text)
    erc_fatal = {t: n for t, n in kicad["erc"].items() if t in FATAL_ERC and n}
    erc_ok = bool(kicad.get("cli")) and bool(sch) and not erc_fatal

    drc_path = OUT / "drc_fab.json"
    unconnected_by_net: dict[str, int] = {}
    parity_real = 0
    parity_slash = 0
    clearance_n = 0
    unconnected_n = 0
    if drc_path.exists():
        drc_j = json.loads(drc_path.read_text(encoding="utf-8"))
        for v in drc_j.get("violations") or []:
            if v.get("type") != "clearance":
                continue
            m = re.search(r"actual\s+([\d.]+)\s*mm", v.get("description") or "", re.I)
            actual = float(m.group(1)) if m else 0.0
            if actual + 1e-9 < 0.10:  # below JLCPCB house min
                clearance_n += 1
        for v in drc_j.get("schematic_parity") or []:
            desc = v.get("description") or ""
            if "{slash}" in desc:
                parity_slash += 1
            elif _is_nc_alias_noise(desc):
                parity_slash += 1  # count with ignored aliases
            elif desc.startswith("Value (") and "doesn't match symbol value" in desc:
                parity_real += 1
            else:
                parity_real += 1
        for v in drc_j.get("unconnected_items") or []:
            unconnected_n += 1
            for it in v.get("items") or []:
                m = re.search(r"\[([^\]]+)\]", it.get("description") or "")
                if m:
                    unconnected_by_net[m.group(1)] = unconnected_by_net.get(m.group(1), 0) + 1
    else:
        clearance_n = kicad["drc"].get("clearance", 0)

    pcb_net_ok = bool(sch) and not mismatches
    fp_ok = bool(sch_fp) and not fp_fail
    copper_ok = unconnected_n == 0
    clear_ok = clearance_n == 0
    parity_ok = parity_real == 0

    gates = [
        {"id": "1", "name": "Schematic netlist exported", "ok": bool(sch)},
        {"id": "2", "name": "Schematic ERC (logic: unconnected / power / pin-to-pin)", "ok": erc_ok},
        {"id": "3", "name": "Schematic ↔ PCB pin nets (SCH is source of truth)", "ok": pcb_net_ok},
        {"id": "4", "name": "Schematic ↔ PCB footprints", "ok": fp_ok},
        {"id": "5", "name": "Electrical sanity on schematic + PCB", "ok": not sanity_fail},
        {"id": "6", "name": "Signal nets have ≥2 schematic pins", "ok": not orphans},
        {"id": "7", "name": "KiCad schematic_parity (ignore {slash} alias)", "ok": parity_ok},
        {"id": "8", "name": "Copper joins pads on each net (KiCad unconnected)", "ok": copper_ok},
        {"id": "9", "name": "DRC clearance (fab copper spacing)", "ok": clear_ok},
    ]
    overall = all(g["ok"] for g in gates)

    sch_pcb_ok = all(g["ok"] for g in gates if g["id"] in {"1", "2", "3", "4", "5", "6", "7"})
    report = {
        "overall": "PASS" if overall else "FAIL",
        "fab_ready": overall,
        "sch_pcb_ok": sch_pcb_ok,
        "source_of_truth": "schematic",
        "sch_pins": len(rows),
        "mismatch": len(mismatches),
        "warn": len(warns),
        "intent_vs_sch": intent_drift[:40],
        "footprint_fail": fp_fail,
        "signal_nets": sum(1 for p in pairs if p["kind"] == "signal"),
        "power_nets": sum(1 for p in pairs if p["kind"] == "power"),
        "gates": gates,
        "sanity_fail": sanity_fail,
        "erc": kicad["erc"],
        "erc_fatal": erc_fatal,
        "drc": kicad["drc"],
        "parity_real": parity_real,
        "parity_slash_alias": parity_slash,
        "unconnected": unconnected_n,
        "unconnected_by_net": dict(sorted(unconnected_by_net.items(), key=lambda kv: -kv[1])),
        "clearance": clearance_n,
        "mismatches": mismatches[:80],
        "warns": warns[:20],
        "pairs": pairs,
        "rows_ok": sum(1 for r in rows if r["status"] == "OK"),
    }
    JSON_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=== Fab verify (schematic is source of truth; PCB must match) ===")
    for g in gates:
        print(f"  {'PASS' if g['ok'] else 'FAIL'}  G{g['id']} {g['name']}")
    print(f"\nSCH pins checked: {len(rows)}  OK {report['rows_ok']}  mismatch {len(mismatches)}")
    for r in mismatches[:40]:
        print(f"  FAIL {r['pin']}: {r['why']}")
    if len(mismatches) > 40:
        print(f"  … {len(mismatches) - 40} more")
    if fp_fail:
        print("Footprints:")
        for s in fp_fail[:20]:
            print(f"  FAIL {s}")
    if sanity_fail:
        print("Sanity:")
        for s in sanity_fail:
            print(f"  FAIL {s}")
    if erc_fatal:
        print("ERC fatal:", erc_fatal)
    elif kicad["erc"]:
        print("ERC (non-fatal):", kicad["erc"])
    if kicad["drc"]:
        print("DRC:", {k: v for k, v in kicad["drc"].items() if k not in SKIP_DRC})
    print(f"schematic_parity real={parity_real}  {{slash}} alias ignored={parity_slash}")
    if intent_drift:
        print(f"Note: generator P() differs from schematic on {len(intent_drift)} pin(s) (not a fab gate)")
    print(f"\nSCH↔PCB (G1–G7): {'PASS' if sch_pcb_ok else 'FAIL'}")
    print(f"OVERALL: {report['overall']}")
    print(f"Wrote {JSON_OUT}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
