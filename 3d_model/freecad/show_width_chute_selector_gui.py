"""
Standalone FreeCAD: Width_Chute_Selector

  Hai thanh tịnh tiến song song; thanh 2 ở +Y (trên) thanh 1.
  2 bánh: G1 (núm) ↔ thanh 1; G1↔G2 liên tục (ngược chiều); G2 ↔ thanh 2.
  Sector gián đoạn khớp tuần tự; tầng liên tục luôn truyền quay.

Chỉnh pose: DRIVE_MM
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
FCSTD = OUT / "width_chute_selector.FCStd"

sys.path.insert(0, str(_HERE))
from width_chute_selector import (  # noqa: E402
    build_width_chute_selector_parts,
    selector_state,
    write_verify_json,
    drive_phase_bounds,
    layout_ys,
    Z_GEAR,
    INLET_TOP_Z,
)

DRIVE_MM = 0.0
SLIDER_MM = DRIVE_MM


def add_part(doc, name, shape, color, transparency=0, *, visible=True):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    if Gui is not None:
        try:
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.Transparency = int(transparency)
            obj.ViewObject.Visibility = bool(visible)
        except Exception:
            pass
    return obj


def add_group(doc, name, children, *, visible=True):
    grp = doc.addObject("App::Part", name)
    for c in children:
        grp.addObject(c)
    if Gui is not None:
        try:
            grp.ViewObject.Visibility = bool(visible)
        except Exception:
            pass
    return grp


def _is_direct_launch() -> bool:
    if __name__ == "__main__":
        return True
    try:
        me = Path(__file__).resolve()
    except NameError:
        return True
    for arg in sys.argv:
        try:
            if Path(arg).resolve() == me:
                return True
        except Exception:
            continue
    return False


def main() -> None:
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)

    doc = App.newDocument("Width_Chute_Selector")
    q = float(DRIVE_MM)
    st = selector_state(q)
    parts = build_width_chute_selector_parts(slider_mm=q)
    ph = drive_phase_bounds()
    ly = layout_ys()

    root = []
    chute_objs = []
    drive_objs = []
    for n, sh, col in parts:
        if n == "Base_Plate":
            tr = 50
        elif n.startswith("Gear"):
            tr = 15
        elif n.startswith("Cassette") or n.startswith("Chute_"):
            tr = 15
        elif n.startswith("Slider2"):
            tr = 0
        else:
            tr = 0
        obj = add_part(doc, n, sh, col, transparency=tr)
        if n.startswith("Chute_") or n == "Cassette_Rails":
            chute_objs.append(obj)
        elif n.startswith("Slider") or n.startswith("Gear") or n in (
            "Knob_Shaft", "Shaft_Bearings_Both_Sides", "Upper_Bearing_Frame",
            "Width_Gate_Fixed", "Gear_Deck_On_Inlet",
        ):
            drive_objs.append(obj)
        else:
            root.append(obj)

    if chute_objs:
        root.append(add_group(doc, "Chute_Cassette", chute_objs))
    if drive_objs:
        root.append(add_group(doc, "Width_Drive_TwoGear", drive_objs))
    add_group(doc, "Width_Chute_Selector", root)

    doc.recompute()
    doc.saveAs(str(FCSTD))
    print("Saved:", FCSTD)
    print(
        "drive=%.1f | θ1=%.1f° θ2=%.1f° | ap=%.1f | chute=%s | g1=%s g2=%s"
        % (
            st["drive_mm"],
            st["gear1_angle_deg"],
            st["gear2_angle_deg"],
            st["aperture_mm"],
            st["chute_name"],
            st["gear1_active"],
            st["gear2_active"],
        )
    )
    print("layout G1(%.1f,%.1f) G2(%.1f,%.1f) Z_gear=%.1f (inlet_top=%.1f)" % (
        ly["ax1"], ly["ay1"], ly["ax2"], ly["ay2"], Z_GEAR, INLET_TOP_Z,
    ))
    print("phases:", {k: ph[k] for k in ("gear1_a", "gear2_1", "gear1_b", "gear2_2", "gear1_c")})

    v = write_verify_json(OUT / "width_chute_selector_verify.json")
    print("verify pass:", v["pass"], v["math"]["checks"])

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
        print("Shown in GUI")
    else:
        App.closeDocument(doc.Name)


if _is_direct_launch():
    main()
