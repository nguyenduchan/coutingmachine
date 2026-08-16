"""
Standalone FreeCAD: Tube_L_Exit_Gate — chỉnh W/H bằng ray trượt chữ T.

Ref: https://www.youtube.com/shorts/ju5vIg66NNk

  Guide_System (cố định)     — xoắn hub→họng CCW
  Entry_Gate_Post            — trụ cố định trên vành bát + ray T ĐỨNG (đầu máng vào)
  Entry_Gate_Slider          — thanh trượt tịnh tiến đứng (= chỉnh cao)
  Entry_Gate_Barrier         — barrier chữ L: trần 20 mm + tấm đứng 10 mm, rộng 30 mm
  Inner_Lane_Rail + Chute_Slide + Bowl_Tube_Exit_Chute — cung Ø20 cm; máng 40° tại 9h

THAO TÁC:
  W: kéo Inner_Lane_Rail trượt trên 2 ray T (8h/10h)
  H: nới Screw_Gate_H → nâng/hạ cụm barrier trên ray T đứng; khe dưới trần = H
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import FreeCAD as App

try:
    import FreeCADGui as Gui
except ImportError:
    Gui = None

try:
    _HERE = Path(__file__).resolve().parent
except NameError:
    _HERE = Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad")

OUT = _HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
FCSTD = OUT / "tube_l_exit_gate_parts" / "tube_l_exit_gate.FCStd"

sys.path.insert(0, str(_HERE))
from tube_l_components import build_component_assembly, print_summary
from tube_l_exit_gate import (
    verify_tube_l_exit_gate,
    verify_single_file_multi,
    verify_pill_egress_multi,
    verify_size_range_egress,
    verify_disc_contact_any,
    verify_mesh_collision,
    verify_sanity_100_mechanics,
    verify_path_disc_contact,
    verify_rest_in_lane_exits,
    verify_rail_exit_seal_and_dead,
)

# Preview = medium_8x4 + 1 mm clear → máng 9×5
WIDTH_OPEN = 9.0
HEIGHT_OPEN = 5.0


def main() -> None:
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)

    # Assembly = App::Link tới cùng thư mục tube_l_exit_gate_parts/*.FCStd — không nhúng
    # solid ở đây nữa, nếu không mỗi lần chạy script này sẽ xoá mất phần sửa tay
    # trong các file component. rebuild=False = giữ file component đang có;
    # muốn dựng lại từ code thì chạy tube_l_components.py --rebuild.
    doc, info = build_component_assembly(WIDTH_OPEN, HEIGHT_OPEN, rebuild=True)
    print("Saved:", FCSTD)
    print_summary(info)

    v = verify_tube_l_exit_gate(WIDTH_OPEN, HEIGHT_OPEN, OUT / "tube_l_exit_gate_verify.json")
    m, p = v["math"], v["pose"]
    print(
        "Verify pass=%s | W×H=%.1f×%.1f | s=%.2f | z=%.2f | jam=%s | "
        "slide W/H map1:1=%s/%s"
        % (
            v["pass"],
            v["width_open_mm"],
            v["height_open_mm"],
            p["s_mm"],
            p["z_gate_roof_mm"],
            v["collision"]["jam_hits"],
            m["map_width_1to1_mm"],
            m["map_height_1to1_mm"],
        )
    )
    print(
        "ADJUST SLIDE: Inner_Lane_Rail on Chute_Slide T-rails | "
        "Entry_Gate_Slider on vertical T-rail | 1mm = 1mm W/H"
    )
    if v["collision"]["jam_hits"]:
        print("JAM DETAIL:", v["collision"]["detail"])
    sf = verify_single_file_multi(out_path=OUT / "tube_l_single_file_verify.json")
    print("Single-file pass=%s | %s/%s" % (sf["pass"], sf["n_pass"], sf["n_datasets"]))
    eg = verify_pill_egress_multi(out_path=OUT / "tube_l_pill_egress_verify.json")
    print("Egress pass=%s | %s/%s" % (eg["pass"], eg["n_pass"], eg["n_datasets"]))
    sr = verify_size_range_egress(out_path=OUT / "tube_l_size_range_egress_verify.json")
    print(
        "Size 2–26 mm any-start pass=%s | %s/%s"
        % (sr["pass"], sr["n_pass"], sr["n_datasets"])
    )
    dc = verify_disc_contact_any(out_path=OUT / "tube_l_disc_contact_verify.json")
    print(
        "Disc contact any-pos pass=%s | %s/%s | open_bottom=%s floor_hits=%s"
        % (
            dc["pass"],
            dc["n_contact_ok"],
            dc["n_contact_trials"],
            dc["open_bottom_ok"],
            dc["floor_hits"],
        )
    )
    mc = verify_mesh_collision(
        WIDTH_OPEN, HEIGHT_OPEN, out_path=OUT / "tube_l_mesh_collision_verify.json"
    )
    print(
        "Mesh collision pass=%s | jam=%s | disc_rot=%s | static=%s | W=%s | H=%s"
        % (
            mc["pass"],
            mc["jam_hits"],
            mc["checks"]["disc_rotate_free"],
            mc["checks"]["no_surface_interpenetration"],
            mc["checks"]["width_adjust_2_26_clear"],
            mc["checks"]["height_adjust_2_26_clear"],
        )
    )
    if mc["jam_hits"]:
        print("MESH HITS:", mc["hits"][:12])
    s100 = verify_sanity_100_mechanics(out_path=OUT / "tube_l_sanity_100_verify.json")
    print(
        "Sanity 100 mechanics pass=%s | %s/%s exit=%s noslip=%s multi_rev=%s"
        % (
            s100["pass"],
            s100["n_pass"],
            s100["n_cases"],
            s100["n_exit"],
            s100["n_noslip"],
            s100["n_multi_rev"],
        )
    )
    if s100["failures"]:
        print("SANITY FAIL sample:", s100["failures"][:6])
    pd = verify_path_disc_contact(out_path=OUT / "tube_l_path_disc_contact_verify.json")
    print(
        "Path disc contact pass=%s | %s/%s math=%s cad=%s steps=%s floor=%s"
        % (
            pd["pass"],
            pd["n_case_pass"],
            pd["n_cases"],
            pd["n_math_path_ok"],
            pd["n_cad_path_ok"],
            pd["n_disc_steps_total"],
            pd["floor_hits"],
        )
    )
    if pd["failures"]:
        print("PATH-DISC FAIL sample:", pd["failures"][:6])
    rest = verify_rest_in_lane_exits(out_path=OUT / "tube_l_rest_in_lane_verify.json")
    print(
        "Rest-in-lane exit pass=%s | %s/%s cad_hits=%s join_turn=%.2fdeg"
        % (
            rest["pass"],
            rest["n_pass"],
            rest["n_cases"],
            rest["cad_join_hits"],
            rest["join"]["max_turn_deg"],
        )
    )
    if rest["failures"]:
        print("REST-LANE FAIL sample:", rest["failures"][:6])
    sd = verify_rail_exit_seal_and_dead(out_path=OUT / "tube_l_seal_dead_verify.json")
    print(
        "Seal+dead pass=%s | gaps=%s | geo_dead=%s | mech_dead=%s | grid_exit=%s/%s"
        % (
            sd["pass"],
            sd["seal"]["n_gap"],
            len(sd["dead_corners"]["geometric"]),
            len(sd["dead_corners"]["mechanics"]),
            sd["dead_corners"]["n_exit"],
            sd["dead_corners"]["n_grid"],
        )
    )
    if sd["seal"]["n_gap"]:
        print("GAP W:", [r for r in sd["seal"]["rows"] if not r["sealed"]][:8])
    if sd["dead_corners"]["mechanics"]:
        print("DEAD MECH:", sd["dead_corners"]["mechanics"][:8])
    if sd["dead_corners"]["geometric"]:
        print("DEAD GEO:", sd["dead_corners"]["geometric"][:8])

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
    else:
        App.closeDocument(doc.Name)


main()
