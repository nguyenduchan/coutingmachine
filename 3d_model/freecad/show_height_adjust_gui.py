"""
Standalone FreeCAD: Height_Adjust Z — print-split rack & pinion.

Active:
  HA_Pinion_Shaft (pinion+shaft fused print)
  HA_Bearing_Rail_S/N + HA_Bearing_Cap_S/N (M3 clamp)
  HA_Rail_Bridge (flat // follower, joins S–N)
  HA_Knob (blind seat + short M3) + HA_Friction_Washer
  HA_Follower

Assembly: drop pinion-shaft into saddles → bolt caps M3 → washer/knob (blind).
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
import Part

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
FCSTD = OUT / "height_adjust_z.FCStd"

sys.path.insert(0, str(_HERE))
import box_settings as BX
from height_adjust_z import ACTIVE_HA_PARTS, build_height_adjust_z_parts


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


def main() -> None:
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)

    doc = App.newDocument("Height_Adjust_Z")
    drv = dict(BX.LID.get("height_bar", {}).get("drive", {}))
    hb = BX.LID.get("height_bar", {})
    drv["bar_length_y"] = float(drv.get("bar_length_y", 24.0))
    drv["bar_thickness"] = float(drv.get("bar_thickness", hb.get("thickness", 6.0)))
    drv["bar_height"] = float(drv.get("bar_height", hb.get("height", 12.0)))
    drv["include_bottom_stop"] = False
    drv["include_scale"] = False

    parts = build_height_adjust_z_parts(
        cx=0.0,
        cy=0.0,
        z_zero=0.0,
        cfg=drv,
        include_demo_wall=False,
    )
    objs = []
    for n, sh, col in parts:
        if n not in ACTIVE_HA_PARTS:
            print("skip (not in active model):", n)
            continue
        if n == "HA_Follower":
            tr = 50
        elif n.startswith("HA_Bearing_Cap"):
            tr = 35
            col = (0.40, 0.60, 0.85)
        elif n.startswith("HA_Bearing"):
            tr = 40
        elif n == "HA_Rail_Bridge":
            tr = 25
        elif n == "HA_Pinion_Shaft":
            tr = 0
            col = (1.0, 0.45, 0.05)
        elif n == "HA_Friction_Washer":
            tr = 30
        else:
            tr = 15
        objs.append(add_part(doc, n, sh, col, transparency=tr))
    add_group(doc, "Height_Adjust_Drive", objs)

    doc.recompute()
    doc.saveAs(str(FCSTD))
    print("Saved:", FCSTD)
    print("Active:", ", ".join(sorted(ACTIVE_HA_PARTS)))
    print("Assembly: drop HA_Pinion_Shaft → M3 caps → blind HA_Knob")

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
        print("Shown in GUI")
    else:
        App.closeDocument(doc.Name)


main()
