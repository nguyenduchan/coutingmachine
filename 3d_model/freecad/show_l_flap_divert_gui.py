"""
Standalone FreeCAD: L_Flap_Divert — Geneva + rack/pinion stack.

  Two arms @ 90° (L = groove widths). Closed across groove; open inward
  into divider pocket (sát thành máng). 1-slot Geneva → 90° once/dir.
  SHOW_SLIDER_GEAR = True → Gap_Slider + rails visible.

Chỉnh pose: SLIDER_OPEN_MM
  0      → default: che hết khe nhỏ
  0–5.5  → SMALL metering
  transit → Geneva index 90°
  17.5   → LARGE full (max travel)
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

SLIDER_OPEN_MM = 0.0  # default: aperture covers small groove fully (0 mm open)
SHOW_SLIDER_GEAR = True

# Optional hide set (unused when SHOW_SLIDER_GEAR True)
_HIDE_SLIDER_GEAR = frozenset({
    "Gap_Slider",
    "Drive_Knob",
    "Gear_Drive_Disc",
    "Knob_Shaft",
    "Slider_Rail_Base",
    "Slider_Rail_Wall_NegY",
    "Slider_Rail_Wall_PosY",
    "Slider_Rail_Stop_L",
    "Slider_Rail_Stop_R",
})


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

    doc = App.newDocument("L_Flap_Divert")
    state = flap_state_for_open(SLIDER_OPEN_MM)
    parts = build_l_flap_divert_parts(
        slider_open_mm=SLIDER_OPEN_MM,
        include_slider_gear=SHOW_SLIDER_GEAR,
    )

    objs = []
    rail_objs = []
    malta_objs = []
    chute_objs = []
    hide_gear = not SHOW_SLIDER_GEAR
    for n, sh, col in parts:
        if n.startswith("Lane_Fill") or n == "Inlet_Pill_Passage":
            tr = 70
        elif n == "Divert_Frame":
            tr = 40
        elif n.startswith("Slider_Rail_"):
            tr = 30
        elif n.startswith("Guide_Chute_"):
            tr = 35
        else:
            tr = 0
        visible = True
        if hide_gear and n in _HIDE_SLIDER_GEAR:
            visible = False
        obj = add_part(doc, n, sh, col, transparency=tr, visible=visible)
        if n.startswith("Slider_Rail_"):
            rail_objs.append(obj)
        elif n.startswith("Guide_Chute_"):
            chute_objs.append(obj)
        elif n in ("Malta_Cross", "Geneva_Driver", "Pivot_Pin", "Gear_Drive_Disc", "Drive_Knob", "Knob_Shaft"):
            malta_objs.append(obj)
        else:
            objs.append(obj)

    if chute_objs:
        objs.append(add_group(doc, "Groove_Guide_Chutes", chute_objs))
    if rail_objs:
        objs.append(add_group(doc, "Slider_Rail", rail_objs, visible=not hide_gear))
    if malta_objs:
        objs.append(add_group(doc, "Malta_Geneva_Drive", malta_objs))
    add_group(doc, "L_Flap_Divert", objs)
    doc.recompute()
    doc.saveAs(str(FCSTD))
    print("Saved:", FCSTD)
    aw = aperture_widths(SLIDER_OPEN_MM)
    print(
        "State=%s open=%.1f | SHOW_SLIDER_GEAR=%s | aperture small=%.2f large=%.2f | "
        "visible: Malta+Geneva+Frame"
        % (state, SLIDER_OPEN_MM, SHOW_SLIDER_GEAR, aw["small_mm"], aw["large_mm"])
    )

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
        print("Shown in GUI (Malta gate focus)")
    else:
        App.closeDocument(doc.Name)


if _is_direct_launch():
    main()
