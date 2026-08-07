"""
Standalone FreeCAD: L_Flap_Divert — aperture + pin/yoke + Slider_Rail.

  Rãnh 5.5 | 12 mm — thanh đóng mở dài đúng bằng độ rộng khe.
  Gap_Slider chạy trên Slider_Rail (hành trình đủ hai khe), mấu đẩy Actuator_Cross.

Chỉnh pose: SLIDER_OPEN_MM
  1–5     → SMALL, chỉnh cửa 5.5
  transit → đóng hẹp / mở rộng
  large   → chỉnh cửa 12
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
FCSTD = OUT / "l_flap_divert.FCStd"

sys.path.insert(0, str(_HERE))
from l_flap_divert import aperture_widths, build_l_flap_divert_parts, flap_state_for_open

SLIDER_OPEN_MM = 3.0  # phase SMALL — metering 5.5 mm


def add_part(doc, name, shape, color, transparency=0):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    if Gui is not None:
        try:
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.Transparency = int(transparency)
        except Exception:
            pass
    return obj


def add_group(doc, name, children):
    grp = doc.addObject("App::Part", name)
    for c in children:
        grp.addObject(c)
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

    doc = App.newDocument("L_Flap_Divert")
    state = flap_state_for_open(SLIDER_OPEN_MM)
    parts = build_l_flap_divert_parts(slider_open_mm=SLIDER_OPEN_MM)

    objs = []
    rail_objs = []
    for n, sh, col in parts:
        if n.startswith("Lane_Fill") or n == "Inlet_Pill_Passage":
            tr = 70
        elif n == "Divert_Frame":
            tr = 40
        elif n.startswith("Slider_Rail_"):
            tr = 30
        else:
            tr = 0
        obj = add_part(doc, n, sh, col, transparency=tr)
        if n.startswith("Slider_Rail_"):
            rail_objs.append(obj)
        else:
            objs.append(obj)

    if rail_objs:
        objs.append(add_group(doc, "Slider_Rail", rail_objs))
    add_group(doc, "L_Flap_Divert", objs)
    doc.recompute()
    doc.saveAs(str(FCSTD))
    print("Saved:", FCSTD)
    aw = aperture_widths(SLIDER_OPEN_MM)
    print(
        "State=%s open=%.1f | aperture small=%.2f large=%.2f active=%.2f | Slider_Rail children=%d"
        % (state, SLIDER_OPEN_MM, aw["small_mm"], aw["large_mm"], aw["active_width_mm"], len(rail_objs))
    )

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
