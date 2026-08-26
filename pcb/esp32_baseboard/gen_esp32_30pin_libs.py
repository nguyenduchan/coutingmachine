#!/usr/bin/env python3
"""Generate KiCad symbol + footprint for ESP32 DevKit V1 30-pin carrier socket."""

from __future__ import annotations

import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIB = ROOT / "libraries"
PRETTY = LIB / "ESP32_Carrier.pretty"

# DOIT ESP32-DevKit-V1 30-pin (USB at top). Verify against silk on your module.
# Left column: top → bottom (pads 1..15). Right column: top → bottom (pads 16..30).
LEFT_PINS = [
    (1, "3V3", "power_in"),
    (2, "GND", "power_in"),
    (3, "IO15", "bidirectional"),
    (4, "IO2", "bidirectional"),
    (5, "IO4", "bidirectional"),
    (6, "IO16", "bidirectional"),
    (7, "IO17", "bidirectional"),
    (8, "IO5", "bidirectional"),
    (9, "IO18", "bidirectional"),
    (10, "IO19", "bidirectional"),
    (11, "IO21", "bidirectional"),
    (12, "RX0", "input"),  # GPIO3
    (13, "TX0", "output"),  # GPIO1
    (14, "IO22", "bidirectional"),
    (15, "IO23", "bidirectional"),
]

RIGHT_PINS = [
    (16, "VIN", "power_in"),
    (17, "GND", "power_in"),
    (18, "IO13", "bidirectional"),
    (19, "IO12", "bidirectional"),
    (20, "IO14", "bidirectional"),
    (21, "IO27", "bidirectional"),
    (22, "IO26", "bidirectional"),
    (23, "IO25", "bidirectional"),
    (24, "IO33", "bidirectional"),
    (25, "IO32", "bidirectional"),
    (26, "IO35", "input"),  # input-only
    (27, "IO34", "input"),  # input-only
    (28, "VN", "input"),  # GPIO39 input-only
    (29, "VP", "input"),  # GPIO36 input-only
    (30, "EN", "input"),
]

PITCH = 2.54
ROW_SPACING = 25.4  # center-to-center between header rows
PAD_SIZE = 1.7
PAD_DRILL = 1.0


def uid() -> str:
    return str(uuid.uuid4())


def write_footprint() -> Path:
    y_last = (15 - 1) * PITCH  # 35.56
    # Module outline approx (USB above pin 1)
    x0, x1 = -1.8, ROW_SPACING + 1.8
    y0, y1 = -8.0, y_last + 3.0

    lines: list[str] = []
    a = lines.append
    a('(footprint "ESP32_DevKit_V1_30Pin_Socket"')
    a('\t(version 20260206)')
    a('\t(generator "gen_esp32_30pin_libs.py")')
    a('\t(generator_version "1.0")')
    a('\t(layer "F.Cu")')
    a('\t(descr "Female header socket for ESP32 DevKit V1 30-pin (2x15, P2.54, row 25.4mm). Carrier/base board.")')
    a('\t(tags "ESP32 DevKit socket 30-pin female header carrier")')
    a('\t(property "Reference" "U**"')
    a('\t\t(at 12.7 -10.5 0)')
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 1 1) (thickness 0.15)))')
    a("\t)")
    a('\t(property "Value" "ESP32_DevKit_V1_30Pin_Socket"')
    a(f'\t\t(at 12.7 {y_last + 5.0} 0)')
    a('\t\t(layer "F.Fab")')
    a('\t\t(effects (font (size 1 1) (thickness 0.15)))')
    a("\t)")
    a('\t(property "Datasheet" "~"')
    a('\t\t(at 0 0 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(hide yes)")
    a('\t\t(effects (font (size 1 1) (thickness 0.15)))')
    a("\t)")
    a('\t(property "Description" "ESP32 DevKit V1 30-pin female socket for carrier board"')
    a('\t\t(at 0 0 0)')
    a('\t\t(layer "F.Fab")')
    a("\t\t(hide yes)")
    a('\t\t(effects (font (size 1 1) (thickness 0.15)))')
    a("\t)")
    a("\t(attr through_hole)")

    # Courtyard / fab / silk outline
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t(fp_rect")
        a(f"\t\t(start {x0} {y0})")
        a(f"\t\t(end {x1} {y1})")
        a(f"\t\t(stroke (width {w}) (type solid))")
        a('\t\t(fill none)')
        a(f'\t\t(layer "{layer}")')
        a("\t)")

    # USB end marker on silk
    a("\t(fp_line")
    a(f"\t\t(start {x0 + 4} {y0})")
    a(f"\t\t(end {x1 - 4} {y0})")
    a("\t\t(stroke (width 0.2) (type solid))")
    a('\t\t(layer "F.SilkS")')
    a("\t)")
    a('\t(fp_text user "USB"')
    a(f"\t\t(at {ROW_SPACING / 2} {y0 + 2.5} 0)")
    a('\t\t(layer "F.SilkS")')
    a('\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))')
    a("\t)")

    # Pin name silk (outside pads)
    for num, name, _etype in LEFT_PINS:
        y = (num - 1) * PITCH
        a(f'\t(fp_text user "{name}"')
        a(f"\t\t(at -3.2 {y} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.6 0.6) (thickness 0.1)) (justify right))')
        a("\t)")
    for num, name, _etype in RIGHT_PINS:
        y = (num - 16) * PITCH
        a(f'\t(fp_text user "{name}"')
        a(f"\t\t(at {ROW_SPACING + 3.2} {y} 0)")
        a('\t\t(layer "F.SilkS")')
        a('\t\t(effects (font (size 0.6 0.6) (thickness 0.1)) (justify left))')
        a("\t)")

    # Pads — pin 1 rectangular
    for num, _name, _etype in LEFT_PINS:
        y = (num - 1) * PITCH
        shape = "rect" if num == 1 else "circle"
        a(f'\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t(at 0 {y})")
        a(f"\t\t(size {PAD_SIZE} {PAD_SIZE})")
        a(f"\t\t(drill {PAD_DRILL})")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t\t(remove_unused_layers no)")
        a("\t)")
    for num, _name, _etype in RIGHT_PINS:
        y = (num - 16) * PITCH
        a(f'\t(pad "{num}" thru_hole circle')
        a(f"\t\t(at {ROW_SPACING} {y})")
        a(f"\t\t(size {PAD_SIZE} {PAD_SIZE})")
        a(f"\t\t(drill {PAD_DRILL})")
        a('\t\t(layers "*.Cu" "*.Mask")')
        a("\t\t(remove_unused_layers no)")
        a("\t)")

    # Optional 3D: two vertical sockets (approximate placement)
    a('\t(model "${KICAD10_3DMODEL_DIR}/Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x15_P2.54mm_Vertical.step"')
    a("\t\t(offset (xyz 0 17.78 0))")
    a("\t\t(scale (xyz 1 1 1))")
    a("\t\t(rotate (xyz -90 0 0))")
    a("\t)")
    a('\t(model "${KICAD10_3DMODEL_DIR}/Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x15_P2.54mm_Vertical.step"')
    a(f"\t\t(offset (xyz {ROW_SPACING} 17.78 0))")
    a("\t\t(scale (xyz 1 1 1))")
    a("\t\t(rotate (xyz -90 0 0))")
    a("\t)")
    a(")")

    out = PRETTY / "ESP32_DevKit_V1_30Pin_Socket.kicad_mod"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_symbol() -> Path:
    # Symbol body height for 15 pins: pin pitch 2.54, center at 0
    # Top pin at +17.78, bottom at -17.78
    pin_ys = [17.78 - i * 2.54 for i in range(15)]
    body_x = 12.7
    body_top = pin_ys[0] + 2.54
    body_bot = pin_ys[-1] - 2.54

    lines: list[str] = []
    a = lines.append
    a("(kicad_symbol_lib")
    a("\t(version 20251024)")
    a('\t(generator "gen_esp32_30pin_libs.py")')
    a('\t(generator_version "1.0")')
    a('\t(symbol "ESP32_DevKit_V1_30Pin"')
    a("\t\t(exclude_from_sim no)")
    a("\t\t(in_bom yes)")
    a("\t\t(on_board yes)")
    a("\t\t(in_pos_files yes)")
    a("\t\t(duplicate_pin_numbers_are_jumpers no)")
    a('\t\t(property "Reference" "U"')
    a(f"\t\t\t(at 0 {body_top + 2.54} 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Value" "ESP32_DevKit_V1_30Pin"')
    a(f"\t\t\t(at 0 {body_bot - 2.54} 0)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Footprint" "ESP32_Carrier:ESP32_DevKit_V1_30Pin_Socket"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "Datasheet" "~"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a(
        '\t\t(property "Description" '
        '"ESP32 DevKit V1 30-pin module socket (DOIT pinout, USB top)"'
    )
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "ki_keywords" "ESP32 DevKit carrier socket 30pin"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")
    a('\t\t(property "ki_fp_filters" "ESP32_DevKit_V1_30Pin*"')
    a("\t\t\t(at 0 0 0)")
    a("\t\t\t(hide yes)")
    a("\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t)")

    # Drawing unit
    a('\t\t(symbol "ESP32_DevKit_V1_30Pin_0_1"')
    a("\t\t\t(rectangle")
    a(f"\t\t\t\t(start {-body_x} {body_top})")
    a(f"\t\t\t\t(end {body_x} {body_bot})")
    a("\t\t\t\t(stroke (width 0.254) (type default))")
    a("\t\t\t\t(fill (type background))")
    a("\t\t\t)")
    a('\t\t\t(text "USB ↑"')
    a(f"\t\t\t\t(at 0 {body_top - 1.5} 0)")
    a("\t\t\t\t(effects (font (size 1.27 1.27)))")
    a("\t\t\t)")
    a("\t\t)")

    a('\t\t(symbol "ESP32_DevKit_V1_30Pin_1_1"')
    for (num, name, etype), y in zip(LEFT_PINS, pin_ys):
        a(f"\t\t\t(pin {etype} line")
        a(f"\t\t\t\t(at {-body_x - 5.08} {y} 0)")
        a("\t\t\t\t(length 5.08)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
        a("\t\t\t)")
    for (num, name, etype), y in zip(RIGHT_PINS, pin_ys):
        a(f"\t\t\t(pin {etype} line")
        a(f"\t\t\t\t(at {body_x + 5.08} {y} 180)")
        a("\t\t\t\t(length 5.08)")
        a(f'\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
        a(f'\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
        a("\t\t\t)")
    a("\t\t)")
    a("\t)")
    a(")")

    out = LIB / "ESP32_Carrier.kicad_sym"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_lib_tables() -> None:
    (ROOT / "fp-lib-table").write_text(
        '(fp_lib_table\n'
        '  (version 7)\n'
        '  (lib (name "ESP32_Carrier")(type "KiCad")'
        '(uri "${KIPRJMOD}/libraries/ESP32_Carrier.pretty")'
        '(options "")(descr "ESP32 carrier footprints"))\n'
        ")\n",
        encoding="utf-8",
    )
    (ROOT / "sym-lib-table").write_text(
        '(sym_lib_table\n'
        '  (version 7)\n'
        '  (lib (name "ESP32_Carrier")(type "KiCad")'
        '(uri "${KIPRJMOD}/libraries/ESP32_Carrier.kicad_sym")'
        '(options "")(descr "ESP32 carrier symbols"))\n'
        ")\n",
        encoding="utf-8",
    )


def write_schematic() -> Path:
    """Minimal schematic with one ESP32 socket symbol."""
    # Embed a simplified copy of the symbol for standalone open,
    # and also reference the project lib via symbol instance.
    # For KiCad, placing requires lib_symbols embedded. We'll embed a compact version
    # by reading the library symbol body after generation.

    sym_path = LIB / "ESP32_Carrier.kicad_sym"
    sym_text = sym_path.read_text(encoding="utf-8")
    # Extract the symbol block (without outer kicad_symbol_lib wrapper)
    start = sym_text.index('(symbol "ESP32_DevKit_V1_30Pin"')
    # find matching close — last ")\n)" of file; strip outer lib close
    # Naive: from start to second-to-last closing paren of file
    body = sym_text[start:]
    # Remove trailing ")\n" that closes kicad_symbol_lib — body ends with symbol's ")"
    # File ends with: )\n)\n  → symbol close then lib close
    body = body.rstrip()
    if body.endswith(")"):
        # remove lib-closing paren already not in body if we sliced from symbol
        pass
    # body currently includes symbol and possibly leftover ")". Trim one trailing ")"
    # if it belongs to lib: count — our write_symbol ends with symbol )\n)\n
    # After index, we have symbol...)\n)\n — strip final )
    while body.endswith("\n"):
        body = body[:-1]
    if body.endswith(")"):
        # check if there's an extra lib closer
        # Find: the last line should be ")" of symbol; if previous structure has two at end
        parts = body.rsplit("\n", 1)
        # Keep as-is: start at symbol means we have "...symbol...\n)\n)" with lib closer
        if body.count('(symbol "ESP32_DevKit_V1_30Pin"') == 1:
            # remove final lone ")" belonging to lib
            idx = body.rfind("\n)")
            if idx > 0 and body[idx + 2 :].strip() == "":
                # There's content after last newline-paren
                pass
            # Explicit: remove trailing "\n)" once if file had lib wrapper
            if sym_text.strip().endswith(")"):
                # body = symbol ... )\n)
                if body.endswith(")\n)"):
                    body = body[:-2]
                elif body.endswith(")"):
                    # count closing at end
                    stripped = body.rstrip(")")
                    # one ) was symbol, one was lib — if ends with )\n)\n originally
                    pass

    # Simpler approach: rebuild embedded symbol from LEFT/RIGHT data
    pin_ys = [17.78 - i * 2.54 for i in range(15)]
    body_x = 12.7
    body_top = pin_ys[0] + 2.54
    body_bot = pin_ys[-1] - 2.54

    emb: list[str] = []
    e = emb.append
    e('\t\t(symbol "ESP32_Carrier:ESP32_DevKit_V1_30Pin"')
    e("\t\t\t(exclude_from_sim no)")
    e("\t\t\t(in_bom yes)")
    e("\t\t\t(on_board yes)")
    e('\t\t\t(property "Reference" "U"')
    e(f"\t\t\t\t(at 0 {body_top + 2.54} 0)")
    e("\t\t\t\t(effects (font (size 1.27 1.27)))")
    e("\t\t\t)")
    e('\t\t\t(property "Value" "ESP32_DevKit_V1_30Pin"')
    e(f"\t\t\t\t(at 0 {body_bot - 2.54} 0)")
    e("\t\t\t\t(effects (font (size 1.27 1.27)))")
    e("\t\t\t)")
    e('\t\t\t(property "Footprint" "ESP32_Carrier:ESP32_DevKit_V1_30Pin_Socket"')
    e("\t\t\t\t(at 0 0 0)")
    e("\t\t\t\t(hide yes)")
    e("\t\t\t\t(effects (font (size 1.27 1.27)))")
    e("\t\t\t)")
    e('\t\t\t(property "Datasheet" "~"')
    e("\t\t\t\t(at 0 0 0)")
    e("\t\t\t\t(hide yes)")
    e("\t\t\t\t(effects (font (size 1.27 1.27)))")
    e("\t\t\t)")
    e('\t\t\t(property "Description" "ESP32 DevKit V1 30-pin socket"')
    e("\t\t\t\t(at 0 0 0)")
    e("\t\t\t\t(hide yes)")
    e("\t\t\t\t(effects (font (size 1.27 1.27)))")
    e("\t\t\t)")
    e('\t\t\t(symbol "ESP32_DevKit_V1_30Pin_0_1"')
    e("\t\t\t\t(rectangle")
    e(f"\t\t\t\t\t(start {-body_x} {body_top})")
    e(f"\t\t\t\t\t(end {body_x} {body_bot})")
    e("\t\t\t\t\t(stroke (width 0.254) (type default))")
    e("\t\t\t\t\t(fill (type background))")
    e("\t\t\t\t)")
    e("\t\t\t)")
    e('\t\t\t(symbol "ESP32_DevKit_V1_30Pin_1_1"')
    for (num, name, etype), y in zip(LEFT_PINS, pin_ys):
        e(f"\t\t\t\t(pin {etype} line")
        e(f"\t\t\t\t\t(at {-body_x - 5.08} {y} 0)")
        e("\t\t\t\t\t(length 5.08)")
        e(f'\t\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
        e(f'\t\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
        e("\t\t\t\t)")
    for (num, name, etype), y in zip(RIGHT_PINS, pin_ys):
        e(f"\t\t\t\t(pin {etype} line")
        e(f"\t\t\t\t\t(at {body_x + 5.08} {y} 180)")
        e("\t\t\t\t\t(length 5.08)")
        e(f'\t\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))')
        e(f'\t\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))')
        e("\t\t\t\t)")
    e("\t\t\t)")
    e("\t\t)")

    sch_uuid = uid()
    sym_uuid = uid()
    lines = [
        "(kicad_sch",
        "\t(version 20250114)",
        '\t(generator "gen_esp32_30pin_libs.py")',
        '\t(generator_version "1.0")',
        f'\t(uuid "{sch_uuid}")',
        '\t(paper "A4")',
        "\t(title_block",
        '\t\t(title "ESP32 Baseboard")',
        '\t\t(comment 1 "30-pin DevKit V1 socket + expansion headers TBD")',
        "\t)",
        "\t(lib_symbols",
        *emb,
        "\t)",
        f'\t(symbol (lib_id "ESP32_Carrier:ESP32_DevKit_V1_30Pin") (at 127 101.6 0) (unit 1)',
        f'\t\t(uuid "{sym_uuid}")',
        '\t\t(property "Reference" "U1" (at 127 76.2 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        '\t\t(property "Value" "ESP32_DevKit_V1_30Pin" (at 127 127 0)',
        "\t\t\t(effects (font (size 1.27 1.27)))",
        "\t\t)",
        '\t\t(property "Footprint" "ESP32_Carrier:ESP32_DevKit_V1_30Pin_Socket" (at 127 101.6 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        '\t\t(property "Datasheet" "~" (at 127 101.6 0)',
        "\t\t\t(effects (font (size 1.27 1.27)) (hide yes))",
        "\t\t)",
        "\t\t(instances",
        f'\t\t\t(project "esp32_baseboard" (path "/{sch_uuid}" (reference "U1") (unit 1)))',
        "\t\t)",
        "\t)",
        f'\t(sheet_instances (path "/" (page "1")))',
        ")",
    ]
    out = ROOT / "esp32_baseboard.kicad_sch"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_pcb() -> Path:
    """PCB with ESP32 socket footprint already placed."""
    y_last = 14 * PITCH
    lines: list[str] = []
    a = lines.append
    a("(kicad_pcb")
    a("\t(version 20241229)")
    a('\t(generator "gen_esp32_30pin_libs.py")')
    a('\t(generator_version "1.0")')
    a('\t(general (thickness 1.6) (legacy_teardrops no))')
    a('\t(paper "A4")')
    a("\t(layers")
    a('\t\t(0 "F.Cu" signal)')
    a('\t\t(2 "B.Cu" signal)')
    a('\t\t(9 "F.Adhes" user "F.Adhesive")')
    a('\t\t(11 "B.Adhes" user "B.Adhesive")')
    a('\t\t(13 "F.Paste" user)')
    a('\t\t(15 "B.Paste" user)')
    a('\t\t(17 "F.SilkS" user "F.Silkscreen")')
    a('\t\t(19 "B.SilkS" user "B.Silkscreen")')
    a('\t\t(21 "F.Mask" user)')
    a('\t\t(23 "B.Mask" user)')
    a('\t\t(25 "Dwgs.User" user "User.Drawings")')
    a('\t\t(27 "Cmts.User" user "User.Comments")')
    a('\t\t(29 "Eco1.User" user "User.Eco1")')
    a('\t\t(31 "Eco2.User" user "User.Eco2")')
    a('\t\t(33 "Edge.Cuts" user)')
    a('\t\t(35 "Margin" user)')
    a('\t\t(37 "F.CrtYd" user "F.Courtyard")')
    a('\t\t(39 "B.CrtYd" user "B.Courtyard")')
    a('\t\t(41 "F.Fab" user "F.Fabrication")')
    a('\t\t(43 "B.Fab" user "B.Fabrication")')
    a("\t)")
    a("\t(setup")
    a("\t\t(pad_to_mask_clearance 0)")
    a('\t\t(allow_soldermask_bridges_in_footprints no)')
    a("\t\t(pcbplotparams")
    a("\t\t\t(layerselection 0x00010fc_ffffffff)")
    a("\t\t\t(plot_on_all_layers_selection 0x0000000_00000000)")
    a("\t\t\t(disableapertmacros no)")
    a("\t\t\t(usegerberextensions no)")
    a("\t\t\t(usegerberattributes yes)")
    a("\t\t\t(usegerberadvancedattributes yes)")
    a("\t\t\t(creategerberjobfile yes)")
    a("\t\t\t(dashed_line_dash_ratio 12.000000)")
    a("\t\t\t(dashed_line_gap_ratio 3.000000)")
    a("\t\t\t(svgprecision 4)")
    a("\t\t\t(plotframeref no)")
    a("\t\t\t(mode 1)")
    a("\t\t\t(useauxorigin no)")
    a("\t\t\t(hpglpennumber 1)")
    a("\t\t\t(hpglpenspeed 20)")
    a("\t\t\t(hpglpendiameter 15.000000)")
    a('\t\t\t(pdf_front_fp_property_popups yes)')
    a('\t\t\t(pdf_back_fp_property_popups yes)')
    a("\t\t\t(dxfpolygonmode yes)")
    a("\t\t\t(dxfimperialunits yes)")
    a('\t\t\t(dxfusepcbnewfont yes)')
    a("\t\t\t(psnegative no)")
    a("\t\t\t(psa4output no)")
    a("\t\t\t(plotreference yes)")
    a("\t\t\t(plotvalue yes)")
    a("\t\t\t(plotfptext yes)")
    a("\t\t\t(plotinvisibletext no)")
    a("\t\t\t(sketchpadsonfab no)")
    a("\t\t\t(subtractmaskfromsilk no)")
    a("\t\t\t(outputformat 1)")
    a("\t\t\t(mirror no)")
    a("\t\t\t(drillshape 1)")
    a("\t\t\t(scaleselection 1)")
    a('\t\t\t(outputdirectory "")')
    a("\t\t)")
    a("\t)")
    a('\t(net 0 "")')

    # Board outline (placeholder rectangular carrier)
    ox, oy = 50.0, 50.0
    bw, bh = 70.0, 60.0
    a("\t(gr_rect")
    a(f"\t\t(start {ox} {oy})")
    a(f"\t\t(end {ox + bw} {oy + bh})")
    a("\t\t(stroke (width 0.1) (type default))")
    a("\t\t(fill none)")
    a('\t\t(layer "Edge.Cuts")')
    a(f'\t\t(uuid "{uid()}")')
    a("\t)")

    # Place footprint: pin1 at (ox+20, oy+15)
    fx, fy = ox + 22.3, oy + 15.0
    a('\t(footprint "ESP32_Carrier:ESP32_DevKit_V1_30Pin_Socket"')
    a('\t\t(layer "F.Cu")')
    a(f'\t\t(uuid "{uid()}")')
    a(f"\t\t(at {fx} {fy})")
    a('\t\t(property "Reference" "U1"')
    a('\t\t\t(at 12.7 -10.5 0)')
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a('\t\t(property "Value" "ESP32_DevKit_V1_30Pin"')
    a(f"\t\t\t(at 12.7 {y_last + 5.0} 0)")
    a('\t\t\t(layer "F.Fab")')
    a("\t\t\t(effects (font (size 1 1) (thickness 0.15)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")
    a("\t\t(attr through_hole)")

    x0, x1 = -1.8, ROW_SPACING + 1.8
    y0, y1 = -8.0, y_last + 3.0
    for layer, w in (("F.CrtYd", 0.05), ("F.Fab", 0.1), ("F.SilkS", 0.12)):
        a("\t\t(fp_rect")
        a(f"\t\t\t(start {x0} {y0})")
        a(f"\t\t\t(end {x1} {y1})")
        a(f"\t\t\t(stroke (width {w}) (type solid))")
        a("\t\t\t(fill none)")
        a(f'\t\t\t(layer "{layer}")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")

    a('\t\t(fp_text user "USB"')
    a(f"\t\t\t(at {ROW_SPACING / 2} {y0 + 2.5} 0)")
    a('\t\t\t(layer "F.SilkS")')
    a("\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))")
    a(f'\t\t\t(uuid "{uid()}")')
    a("\t\t)")

    for num, name, _ in LEFT_PINS:
        y = (num - 1) * PITCH
        a(f'\t\t(fp_text user "{name}"')
        a(f"\t\t\t(at -3.2 {y} 0)")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.6 0.6) (thickness 0.1)) (justify right))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        shape = "rect" if num == 1 else "circle"
        a(f'\t\t(pad "{num}" thru_hole {shape}')
        a(f"\t\t\t(at 0 {y})")
        a(f"\t\t\t(size {PAD_SIZE} {PAD_SIZE})")
        a(f"\t\t\t(drill {PAD_DRILL})")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")

    for num, name, _ in RIGHT_PINS:
        y = (num - 16) * PITCH
        a(f'\t\t(fp_text user "{name}"')
        a(f"\t\t\t(at {ROW_SPACING + 3.2} {y} 0)")
        a('\t\t\t(layer "F.SilkS")')
        a("\t\t\t(effects (font (size 0.6 0.6) (thickness 0.1)) (justify left))")
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")
        a(f'\t\t(pad "{num}" thru_hole circle')
        a(f"\t\t\t(at {ROW_SPACING} {y})")
        a(f"\t\t\t(size {PAD_SIZE} {PAD_SIZE})")
        a(f"\t\t\t(drill {PAD_DRILL})")
        a('\t\t\t(layers "*.Cu" "*.Mask")')
        a(f'\t\t\t(uuid "{uid()}")')
        a("\t\t)")

    a("\t)")
    a(")")

    out = ROOT / "esp32_baseboard.kicad_pcb"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_project() -> Path:
    # Minimal .kicad_pro — KiCad will fill defaults on open
    pro = {
        "board": {
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.1,
                    "copper_line_width": 0.2,
                    "copper_text_size_h": 1.5,
                    "copper_text_size_v": 1.5,
                    "copper_text_thickness": 0.3,
                    "other_line_width": 0.15,
                    "pads": {"drill": 1.0, "height": 1.7, "width": 1.7},
                    "silk_line_width": 0.15,
                    "silk_text_size_h": 1.0,
                    "silk_text_size_v": 1.0,
                    "silk_text_thickness": 0.15,
                }
            }
        },
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "erc": {
            "erc_exclusions": [],
            "meta": {"version": 0},
            "pin_map": [[0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2], [0] * 12] * 11,
            "rule_severities": {},
        },
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": "esp32_baseboard.kicad_pro", "version": 3},
        "net_settings": {
            "classes": [
                {
                    "bus_width": 12,
                    "clearance": 0.2,
                    "diff_pair_gap": 0.25,
                    "diff_pair_via_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "name": "Default",
                    "pcb_color": "rgba(0, 0, 0, 0.000)",
                    "schematic_color": "rgba(0, 0, 0, 0.000)",
                    "track_width": 0.25,
                    "via_diameter": 0.6,
                    "via_drill": 0.3,
                    "wire_width": 6,
                }
            ],
            "meta": {"version": 3},
        },
        "pcbnew": {
            "last_paths": {
                "gencad": "",
                "idf": "",
                "netlist": "",
                "plot": "",
                "pos_files": "",
                "specctra_dsn": "",
                "step": "",
                "svg": "",
                "vrml": "",
            },
            "page_layout_descr_file": "",
        },
        "schematic": {
            "annotate_start_num": 0,
            "drawing": {
                "dashed_lines_dash_length_ratio": 12.0,
                "dashed_lines_gap_length_ratio": 3.0,
                "default_line_thickness": 6.0,
                "default_text_size": 50.0,
                "field_names": [],
                "intersheets_ref_own_page": False,
                "intersheets_ref_prefix": "",
                "intersheets_ref_short": False,
                "intersheets_ref_show": False,
                "intersheets_ref_suffix": "",
                "junction_size_choice": 3,
                "label_size_ratio": 0.375,
                "operating_point_overlay_i_precision": 3,
                "operating_point_overlay_i_range": "~A",
                "operating_point_overlay_v_precision": 3,
                "operating_point_overlay_v_range": "~V",
                "overbar_offset_ratio": 1.27,
                "pin_symbol_size": 25.0,
                "text_offset_ratio": 0.15,
            },
            "legacy_lib_dir": "",
            "legacy_lib_list": [],
            "meta": {"version": 1},
            "net_format_name": "",
            "page_layout_descr_file": "",
            "plot_directory": "",
            "spice_current_sheet_as_root": False,
            "spice_external_command": 'spice "%I"',
            "spice_model_current_sheet_as_root": True,
            "spice_save_all_currents": False,
            "spice_save_all_dissipations": False,
            "spice_save_all_voltages": False,
            "subsheet_field_names": [],
            "text_variables": {},
        },
        "sheets": [["esp32_baseboard.kicad_sch", "Root"]],
        "text_variables": {},
    }
    import json

    out = ROOT / "esp32_baseboard.kicad_pro"
    out.write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")
    return out


def write_readme() -> Path:
    text = """# ESP32 Baseboard (30-pin DevKit socket)

Board đế để cắm module ESP32 DevKit V1 **30 chân** qua 2 hàng female header.

## Thư viện

| File | Mô tả |
|------|--------|
| `libraries/ESP32_Carrier.kicad_sym` | Symbol `ESP32_DevKit_V1_30Pin` |
| `libraries/ESP32_Carrier.pretty/ESP32_DevKit_V1_30Pin_Socket.kicad_mod` | Footprint ổ cắm |

## Kích thước footprint

- Pitch: **2.54 mm**
- Số chân: **2 × 15 = 30**
- Khoảng cách 2 hàng (tâm–tâm): **25.4 mm**
- Pad: Ø1.7 mm, khoan **1.0 mm** (chuẩn female PinSocket)
- Hàn 2 thanh **female header 1×15** đứng (vertical)

## Pinout (DOIT ESP32-DevKit-V1, USB phía trên)

```
LEFT (1→15)              RIGHT (16→30)
1  3V3                   16 VIN
2  GND                   17 GND
3  IO15                  18 IO13
4  IO2                   19 IO12
5  IO4                   20 IO14
6  IO16                  21 IO27
7  IO17                  22 IO26
8  IO5                   23 IO25
9  IO18                  24 IO33
10 IO19                  25 IO32
11 IO21                  26 IO35 (input only)
12 RX0 (IO3)             27 IO34 (input only)
13 TX0 (IO1)             28 VN  (IO39)
14 IO22                  29 VP  (IO36)
15 IO23                  30 EN
```

**Quan trọng:** So khớp với chữ in trên module thật trước khi đặt hàng PCB.
Một số clone đảo cột nguồn (VIN/3V3).

## Mở project

Mở `esp32_baseboard.kicad_pro` bằng KiCad 10.

Tái tạo lib nếu sửa pinout:

```
python gen_esp32_30pin_libs.py
```
"""
    out = ROOT / "README.md"
    out.write_text(text, encoding="utf-8")
    return out


def main() -> None:
    PRETTY.mkdir(parents=True, exist_ok=True)
    fp = write_footprint()
    sym = write_symbol()
    write_lib_tables()
    sch = write_schematic()
    pcb = write_pcb()
    pro = write_project()
    readme = write_readme()
    print("Wrote:")
    for p in (fp, sym, sch, pcb, pro, readme):
        print(" ", p)


if __name__ == "__main__":
    main()
