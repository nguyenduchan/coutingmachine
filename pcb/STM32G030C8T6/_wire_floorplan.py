#!/usr/bin/env python3
from pathlib import Path

p = Path(__file__).resolve().parent / "gen_power_carrier.py"
t = p.read_text(encoding="utf-8")

if "placement_floorplan" not in t:
    t = t.replace(
        "from s3_pinmap import (",
        "from placement_floorplan import balanced_placement\nfrom s3_pinmap import (",
        1,
    )

old = """    # --- Placement: ALL parts TOP; edge/MCU/cluster clearances ---
    # 12V star west of MCU: POWER + TMC + OPTO + BLOWER + BUP + AXIS
    # 3V3/5V east: MCU + HMI (TFT/buzzer)
    # N: BUP|BLOWER …… HMI
    # Mid: POWER|OPTO|TMC …… MCU
    # S: A1→A3 (HOME+ULN+BYJ) packed toward POWER
    ix0, iy0 = ox + MODULE_EDGE_CLEAR, oy + MODULE_EDGE_CLEAR
    ix1, iy1 = ox + bw - MODULE_EDGE_CLEAR, oy + bh - MODULE_EDGE_CLEAR
    # MCU courtyard flush to Eco box at rot=0 (world = at + local)
    _u1_lx0, _u1_ly0 = -1.8, -8.0
    _u1_lx1, _u1_ly1 = ROW_SPACING + 1.8, y_last + 3.0
    # MCU east — frees west band for 12V loads next to POWER
    mcu_wx0, mcu_wy0 = ox + 130.0, oy + 48.0
    fx = mcu_wx0 - _u1_lx0
    fy = mcu_wy0 - _u1_ly0
    mcu_wx1 = mcu_wx0 + (_u1_lx1 - _u1_lx0)
    mcu_wy1 = mcu_wy0 + (_u1_ly1 - _u1_ly0)
    # Power west — J1 screw axis || left Edge (nearest); wire entry faces west
    jx, jy = ix0 + 5.0, oy + 118.0
    f1x, f1y = ix0 + 18.0, oy + 78.0
    d1x, d1y = ix0 + 16.0, oy + 146.0
    mx, my = ix0 + 22.0, oy + 96.0
    # TMC east of POWER / between OPTO and AXIS (12V VM), west of MCU
    tx, ty = ox + 92.0, oy + 96.0
    # HMI NE — pack against east usable edge; ≥10 mm east of MCU
    j3x, j3y = ix1 - 23.0, iy0 + 6.0  # TFT LCD; 1×09 span ≤ usable
    j18x, j18y = max(mcu_wx1 + MODULE_MCU_CLEAR + 3.0, j3x - 26.0), iy0 + 10.0
    j15x, j15y = (j18x + j3x) / 2.0, iy0 + 6.0  # buzzer between ENC and TFT
    # Blower NW — next to BUP / above POWER (12V pump)
    j16x, j16y = ox + 52.0, iy0 + 8.0
    # BUP NW (12V_SNS)
    j14x, j14y = ix0 + 8.0, iy0 + 4.0
    # Opto: east of POWER (≥8 mm Eco gap), north of TMC (LED = +12V_SNS)
    opto_origin = (ox + 62.0, oy + 55.0)
"""

new = """    # --- Placement: force-directed + SA floorplan (placement_floorplan.py) ---
    # Traditional: spring-electrical layout, anneal for COM/quadrant balance,
    # then even pack within POWER / AXIS / HMI / OPTO / SHIFT.
    ix0, iy0 = ox + MODULE_EDGE_CLEAR, oy + MODULE_EDGE_CLEAR
    ix1, iy1 = ox + bw - MODULE_EDGE_CLEAR, oy + bh - MODULE_EDGE_CLEAR
    _u1_lx0, _u1_ly0 = -1.8, -8.0
    _u1_lx1, _u1_ly1 = ROW_SPACING + 1.8, y_last + 3.0
    FP = balanced_placement(
        ox, oy, bw, bh,
        edge_clear=MODULE_EDGE_CLEAR,
        cluster_gap=MODULE_CLUSTER_GAP,
        mcu_clear=MODULE_MCU_CLEAR,
        seed=42,
    )
    print(f"Floorplan cost={FP['cost']:.0f}")
    mcu_wx0, mcu_wy0 = FP["mcu_wx0"], FP["mcu_wy0"]
    fx = mcu_wx0 - _u1_lx0
    fy = mcu_wy0 - _u1_ly0
    mcu_wx1 = mcu_wx0 + (_u1_lx1 - _u1_lx0)
    mcu_wy1 = mcu_wy0 + (_u1_ly1 - _u1_ly0)
    jx, jy = FP["jx"], FP["jy"]
    f1x, f1y = FP["f1x"], FP["f1y"]
    d1x, d1y = FP["d1x"], FP["d1y"]
    mx, my = FP["mx"], FP["my"]
    tx, ty = FP["tx"], FP["ty"]
    j3x, j3y = FP["j3x"], FP["j3y"]
    j18x, j18y = FP["j18x"], FP["j18y"]
    j15x, j15y = FP["j15x"], FP["j15y"]
    j16x, j16y = FP["j16x"], FP["j16y"]
    j14x, j14y = FP["j14x"], FP["j14y"]
    opto_origin = FP["opto_origin"]
"""

if old not in t:
    raise SystemExit("placement block not found")
t = t.replace(old, new, 1)

old2 = """    # South: AXIS1→3 (ULN). SHIFT module U10 = 74HC595-24IO east of ESP32.
    # Pack AXIS to south usable edge so 24-pin module fits between HMI and AXIS.
    _dip_y = min(iy1 - 12.0, oy + bh - MODULE_EDGE_CLEAR - 14.0)
    u5x, u5y = ox + 72.0, _dip_y
    u6x, u6y = ox + 107.0, _dip_y
    u7x, u7y = ox + 142.0, _dip_y  # keep A3 west of SHIFT (no Y-gap fight)
"""
new2 = """    # South: AXIS1→3 (ULN). SHIFT module U10 from floorplan (east of ESP32).
    _dip_y = FP["_dip_y"]
    u5x, u5y = FP["u5x"], FP["u5y"]
    u6x, u6y = FP["u6x"], FP["u6y"]
    u7x, u7y = FP["u7x"], FP["u7y"]
"""
if old2 not in t:
    raise SystemExit("AXIS block not found")
t = t.replace(old2, new2, 1)

old3 = """    MOD_CTRL_TO_Q = 17.0
    u10_ctrl_x = mcu_wx1 + MODULE_MCU_CLEAR + 4.0
    u10_q_x = u10_ctrl_x + MOD_CTRL_TO_Q
    # Vertical 24-pin between HMI (north) and AXIS (south); ≥8 mm Eco gaps
    _mod_span = 23 * PITCH + 5.0
    u10_y0 = (_dip_y - 10.0) - _mod_span
    if u10_y0 < mcu_wy0 + 14.0:
        u10_y0 = mcu_wy0 + 14.0
    # If R4 is east of Q, expand courtyard east — keep inside board
    if u10_q_x + 12.0 > ix1:
        u10_ctrl_x = ix1 - 12.0 - MOD_CTRL_TO_Q
        u10_q_x = u10_ctrl_x + MOD_CTRL_TO_Q
"""
new3 = """    MOD_CTRL_TO_Q = FP["MOD_CTRL_TO_Q"]
    u10_ctrl_x = FP["u10_ctrl_x"]
    u10_q_x = FP["u10_q_x"]
    u10_y0 = FP["u10_y0"]
"""
if old3 not in t:
    raise SystemExit("SHIFT coords not found")
t = t.replace(old3, new3, 1)

t = t.replace(
    "r4x, r4y = u10_q_x + 8.0, u10_y0 + 1.5 * PITCH  # east of Q (clear MCU)",
    'r4x, r4y = FP["r4x"], FP["r4y"]',
    1,
)

old_sns = """    r10x, r10y = ix0 + 24.0, oy + 126.0  # east of J1, clear D1
    c10x, c10y = ix0 + 24.0, oy + 132.0
    c11x, c11y = ix0 + 32.0, oy + 132.0"""
new_sns = """    r10x, r10y = FP["r10x"], FP["r10y"]
    c10x, c10y = FP["c10x"], FP["c10y"]
    c11x, c11y = FP["c10x"] + 8.0, FP["c10y"]"""
if old_sns not in t:
    raise SystemExit("SNS coords not found")
t = t.replace(old_sns, new_sns, 1)

t = t.replace(
    '("C21", "CP_Radial_D6_100u_25V", "100u/25V", u5x - 14.0, _dip_y - 2.0, "ULN"),',
    '("C21", "CP_Radial_D6_100u_25V", "100u/25V", FP["c21x"], FP["c21y"], "ULN"),',
    1,
)
t = t.replace(
    "c21x, c21y = u5x - 14.0, _dip_y - 2.0",
    'c21x, c21y = FP["c21x"], FP["c21y"]',
    1,
)

p.write_text(t, encoding="utf-8")
print("OK patched", p)
