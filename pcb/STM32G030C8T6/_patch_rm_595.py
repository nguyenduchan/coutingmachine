"""One-shot: remove 74HC595; direct-drive ULN; shrink opto to HOME+BUP."""
from __future__ import annotations

import re
from pathlib import Path

p = Path(__file__).resolve().parent / "gen_power_carrier.py"
t = p.read_text(encoding="utf-8")

t = t.replace(
    '"""Generate MP1584EN + TMC2209 + PC817 DIP-4 + ULN2003/74HC595 + ESP32-S3 carrier.',
    '"""Generate MP1584EN + TMC2209 + PC817 DIP-4 + ULN2003 + ESP32-S3 carrier.',
)
t = t.replace(
    "       --> ULN2003 x3 (U5-U7) COM=+12V via 74HC595 (U10/U11) -> J5-J7 28BYJ-48",
    "       --> ULN2003 x3 (U5-U7) COM=+12V, IN from GPIO direct -> J5-J7 28BYJ-48",
)

# imports
t = t.replace(
    "    SHIFT_GPIO,\n",
    "    BYJ_GPIO,\n",
)
if "from s3_pinmap import" in t and "BYJ_GPIO" not in t.split("from s3_pinmap import")[1][:800]:
    pass  # already replaced SHIFT with BYJ

# OPTO_CH — keep only HOME×3 + BUP
old_opto = """OPTO_CH = [
    # (uref, r_led, r_pu, in_id, in_net, out_id, out_net, anode_id, anode_net, tag)
    # Required field 12V→3V3: HOME×3 + BUP. Extra: ESTOP/HOPPER/DOOR/SPARE (was U9).
    ("U41", "R41", "R45", 25, "/OPTO_IN1", 16, "/OPTO_OUT1", 80, "/OPTO_A1", "HOME1"),
    ("U42", "R42", "R46", 26, "/OPTO_IN2", 17, "/OPTO_OUT2", 81, "/OPTO_A2", "HOME2"),
    ("U43", "R43", "R47", 27, "/OPTO_IN3", 18, "/OPTO_OUT3", 82, "/OPTO_A3", "HOME3"),
    ("U44", "R44", "R48", 28, "/OPTO_IN4", 19, "/OPTO_OUT4", 83, "/OPTO_A4", "BUP"),
    ("U45", "R49", "R53", 29, "/OPTO_IN5", 21, "/OPTO_OUT5", 84, "/OPTO_A5", "ESTOP"),
    ("U46", "R50", "R54", 30, "/OPTO_IN6", 22, "/OPTO_OUT6", 85, "/OPTO_A6", "HOPPER"),
    ("U47", "R51", "R55", 31, "/OPTO_IN7", 23, "/OPTO_OUT7", 86, "/OPTO_A7", "DOOR"),
    ("U48", "R52", "R56", 32, "/OPTO_IN8", 24, "/OPTO_OUT8", 87, "/OPTO_A8", "SPARE"),
]"""
new_opto = """OPTO_CH = [
    # (uref, r_led, r_pu, in_id, in_net, out_id, out_net, anode_id, anode_net, tag)
    # Just enough: HOME×3 + BUP (field IN5–8 removed with 74HC595 GPIO reclaim).
    ("U41", "R41", "R45", 25, "/OPTO_IN1", 16, "/OPTO_OUT1", 80, "/OPTO_A1", "HOME1"),
    ("U42", "R42", "R46", 26, "/OPTO_IN2", 17, "/OPTO_OUT2", 81, "/OPTO_A2", "HOME2"),
    ("U43", "R43", "R47", 27, "/OPTO_IN3", 18, "/OPTO_OUT3", 82, "/OPTO_A3", "HOME3"),
    ("U44", "R44", "R48", 28, "/OPTO_IN4", 19, "/OPTO_OUT4", 83, "/OPTO_A4", "BUP"),
]"""
if old_opto not in t:
    raise SystemExit("OPTO_CH block not found")
t = t.replace(old_opto, new_opto, 1)

# nets dict — replace shift / field / enc / touch extras
old_nets_tail = """        19: "/OPTO_OUT4",
        21: "/OPTO_OUT5",
        22: "/OPTO_OUT6",
        23: "/OPTO_OUT7",
        24: "/OPTO_OUT8",
        25: "/OPTO_IN1",
        26: "/OPTO_IN2",
        27: "/OPTO_IN3",
        28: "/OPTO_IN4",  # BUP
        29: "/OPTO_IN5",
        30: "/OPTO_IN6",
        31: "/OPTO_IN7",
        32: "/OPTO_IN8",
        80: "/OPTO_A1",
        81: "/OPTO_A2",
        82: "/OPTO_A3",
        83: "/OPTO_A4",
        84: "/OPTO_A5",
        85: "/OPTO_A6",
        86: "/OPTO_A7",
        87: "/OPTO_A8",
        33: "/OPTO_GND_I",
        # 74HC595 control (IO10-13) + cascade
        34: "SER",
        35: "SRCLK",
        36: "RCLK",
        37: "OE_595",
        38: "QH_U10",
        # Shift Q -> ULN IN
        39: "SR_Q0",
        40: "SR_Q1",
        41: "SR_Q2",
        42: "SR_Q3",
        43: "SR_Q4",
        44: "SR_Q5",
        45: "SR_Q6",
        63: "SR_Q7",
        64: "SR_Q8",
        65: "SR_Q9",
        66: "SR_Q10",
        67: "SR_Q11",
        # ULN OUT -> 28BYJ phases
        68: "BYJ1_A",
        69: "BYJ1_B",
        70: "BYJ1_C",
        71: "BYJ1_D",
        72: "BYJ2_A",
        73: "BYJ2_B",
        74: "BYJ2_C",
        75: "BYJ2_D",
        76: "BYJ3_A",
        77: "BYJ3_B",
        78: "BYJ3_C",
        79: "BYJ3_D",
        46: "+12V_SNS",
        47: "/TFT_SCK",
        48: "/TFT_MOSI",
        50: "/TFT_CS",
        51: "/TFT_DC",
        52: "/TFT_MISO",
        53: "/T_CS",
        20: "/T_IRQ",
        54: "/BUZZER",
        55: "/BLOWER",
        57: "+12V_RAW",
        58: "/TFT_RST",
        59: "/TFT_BL",
        60: "/ENC_B",
        61: "/BLW_RET",
        62: "/ENC_A",
    }"""
new_nets_tail = """        19: "/OPTO_OUT4",
        25: "/OPTO_IN1",
        26: "/OPTO_IN2",
        27: "/OPTO_IN3",
        28: "/OPTO_IN4",  # BUP
        80: "/OPTO_A1",
        81: "/OPTO_A2",
        82: "/OPTO_A3",
        83: "/OPTO_A4",
        33: "/OPTO_GND_I",
        # GPIO → ULN2003 IN (direct; was 74HC595 Q)
        34: "BYJ1_IN_A",
        35: "BYJ1_IN_B",
        36: "BYJ1_IN_C",
        37: "BYJ1_IN_D",
        38: "BYJ2_IN_A",
        39: "BYJ2_IN_B",
        40: "BYJ2_IN_C",
        41: "BYJ2_IN_D",
        42: "BYJ3_IN_A",
        43: "BYJ3_IN_B",
        44: "BYJ3_IN_C",
        45: "BYJ3_IN_D",
        # ULN OUT -> 28BYJ phases
        68: "BYJ1_A",
        69: "BYJ1_B",
        70: "BYJ1_C",
        71: "BYJ1_D",
        72: "BYJ2_A",
        73: "BYJ2_B",
        74: "BYJ2_C",
        75: "BYJ2_D",
        76: "BYJ3_A",
        77: "BYJ3_B",
        78: "BYJ3_C",
        79: "BYJ3_D",
        46: "+12V_SNS",
        47: "/TFT_SCK",
        48: "/TFT_MOSI",
        50: "/TFT_CS",
        51: "/TFT_DC",
        54: "/BUZZER",
        55: "/BLOWER",
        57: "+12V_RAW",
        58: "/TFT_RST",
        59: "/TFT_BL",
        61: "/BLW_RET",
    }"""
if old_nets_tail not in t:
    raise SystemExit("nets tail not found")
t = t.replace(old_nets_tail, new_nets_tail, 1)

old_esp = """            "IO1": (16, "/OPTO_OUT1"),
            "IO2": (17, "/OPTO_OUT2"),
            "IO4": (18, "/OPTO_OUT3"),
            "IO5": (19, "/OPTO_OUT4"),
            "IO7": (21, "/OPTO_OUT5"),
            "IO8": (22, "/OPTO_OUT6"),
            "IO14": (23, "/OPTO_OUT7"),
            "IO15": (24, "/OPTO_OUT8"),
            "IO9": (54, "/BUZZER"),
            "IO10": (34, "SER"),
            "IO11": (35, "SRCLK"),
            "IO12": (36, "RCLK"),
            "IO13": (37, "OE_595"),
            "IO6": (20, "/T_IRQ"),
            "IO39": (47, "/TFT_SCK"),
            "IO40": (48, "/TFT_MOSI"),
            "IO42": (50, "/TFT_CS"),
            "IO21": (51, "/TFT_DC"),
            "IO47": (52, "/TFT_MISO"),
            "IO48": (53, "/T_CS"),
            "IO38": (62, "/ENC_A"),
            "IO3": (55, "/BLOWER"),
            "IO46": (58, "/TFT_RST"),
            "IO45": (59, "/TFT_BL"),
            "IO41": (60, "/ENC_B"),
        }"""
new_esp = """            "IO1": (16, "/OPTO_OUT1"),
            "IO2": (17, "/OPTO_OUT2"),
            "IO4": (18, "/OPTO_OUT3"),
            "IO5": (19, "/OPTO_OUT4"),
            "IO9": (54, "/BUZZER"),
            "IO10": (34, "BYJ1_IN_A"),
            "IO11": (35, "BYJ1_IN_B"),
            "IO12": (36, "BYJ1_IN_C"),
            "IO13": (37, "BYJ1_IN_D"),
            "IO7": (38, "BYJ2_IN_A"),
            "IO8": (39, "BYJ2_IN_B"),
            "IO14": (40, "BYJ2_IN_C"),
            "IO15": (41, "BYJ2_IN_D"),
            "IO38": (42, "BYJ3_IN_A"),
            "IO41": (43, "BYJ3_IN_B"),
            "IO6": (44, "BYJ3_IN_C"),
            "IO48": (45, "BYJ3_IN_D"),
            "IO39": (47, "/TFT_SCK"),
            "IO40": (48, "/TFT_MOSI"),
            "IO42": (50, "/TFT_CS"),
            "IO21": (51, "/TFT_DC"),
            "IO3": (55, "/BLOWER"),
            "IO46": (58, "/TFT_RST"),
            "IO45": (59, "/TFT_BL"),
            # IO47 spare
        }"""
if old_esp not in t:
    raise SystemExit("esp_net map not found")
t = t.replace(old_esp, new_esp, 1)

p.write_text(t, encoding="utf-8")
print("patched nets/OPTO/esp_net OK", p)
