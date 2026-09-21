"""JLCPCB capability limits (rigid 2-layer FR-4, 1 oz) — 2026.

Source: https://jlcpcb.com/capabilities/pcb-capabilities
Assembly: https://jlcpcb.com/help/article/how-to-add-edge-rails-fiducials-for-pcb-assembly-order
           https://jlcpcb.com/help/article/terms-and-conditions-of-jlcpcb-assembly-service

Values are the published *minimums*. HOUSE_* are tighter so a cheap 2-layer
lot still yields if the drill wanders ±0.05 mm.
"""
from __future__ import annotations

# --- Fabrication (bare PCB) ---
LAYERS_OK = (1, 2, 4)
THICKNESS_MM = (0.4, 0.6, 0.8, 1.0, 1.2, 1.6, 2.0)
THICKNESS_USED = 1.6
COPPER_OZ = 1
BOARD_MIN_MM = 3.0
BOARD_MAX_2L_MM = (670.0, 600.0)
BOARD_MAX_4L_MM = (400.0, 500.0)

TRACK_MIN_MM = 0.10
SPACE_MIN_MM = 0.10
TRACK_HOUSE_MM = 0.15
SPACE_HOUSE_MM = 0.15

DRILL_MIN_2L_MM = 0.15
DRILL_MAX_MM = 6.3
NPTH_MIN_MM = 0.50
VIA_HOLE_MIN_MM = 0.15
VIA_DIA_MIN_MM = 0.25
VIA_HOLE_PREF_MM = 0.30
VIA_PAD_PREF_MM = 0.60
VIA_HOUSE = (0.40, 0.80)  # drill, pad — this project's A8
NO_BLIND_BURIED = True

PTH_ANNULAR_ABS_MM = 0.18
PTH_ANNULAR_REC_MM = 0.20
NPTH_ANNULAR_REC_MM = 0.45  # only if a copper pad exists around the hole
HOLE_TO_HOLE_VIA_MM = 0.20
HOLE_TO_HOLE_PAD_MM = 0.45
PTH_TO_TRACK_MM = 0.28
NPTH_TO_TRACK_MM = 0.20
VIA_TO_TRACK_MM = 0.20
PAD_TO_TRACK_MM = 0.10
SMD_PAD_TO_PAD_MM = 0.15
SMD_PAD_MIN_MM = 0.25

COPPER_TO_ROUTED_EDGE_MM = 0.20
COPPER_TO_EDGE_HOUSE_MM = 0.30
SILK_TO_PAD_MM = 0.15
SILK_LINE_MIN_MM = 0.15
SILK_HEIGHT_MIN_MM = 1.00
MASK_DAM_1OZ_GREEN_MM = 0.10
MASK_TO_TRACE_MM = 0.09

# --- Assembly (SMT) ---
ASSY_BODY_TO_EDGE_MM = 2.50
ASSY_RAIL_MM = 5.00
ASSY_FIDUCIAL_CU_MM = 1.00
ASSY_FIDUCIAL_MASK_MM = 2.00
ASSY_FIDUCIAL_EDGE_MM = 3.35
ASSY_TOOLING_HOLE_MM = 2.00
ASSY_COURTYARD_GAP_MM = 0.30  # IPC-7351B medium density / JLC body gap
EDGE_CONNECTOR_REFS = ("J1", "J_")  # field jacks may sit on N/S edge

# Electrical (not JLC min — JLC 0.10 mm will etch +24V next to 3V3)
HV_NET_PREFIXES = ("+24V", "+12V")
HV_PAD_CLEAR_MM = 0.40  # 24 V DC external uncoated, house
JACK_PLUG_GAP_MM = 5.00  # two field plugs must not touch
NPTH_M3_MM = 3.20
NPTH_M3_COUNT = 4

NORTH_JACKS = (
    "J14", "J15", "J_IN2", "J_IN3",
    "J_CNT5", "J_KEY", "J_DISP", "J_USB",
)
SOUTH_JACKS = ("J1", "J_MOT1", "J_MOT2", "U_PWR1", "U_PWR2", "U_VIB", "J_P24S")
POLARIZED_REFS = (
    "U1", "U2", "U5", "U6", "J_USB",
    "D1", "D3", "D4", "D5",
    "Y1", "F1",
    "U44", "U45", "U46", "U47",
    "C3", "C5", "C10", "C20", "C20B", "C21",
)
