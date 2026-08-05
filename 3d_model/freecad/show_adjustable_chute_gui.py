"""
Standalone FreeCAD: Adjustable_Chute — máng chữ nhật chỉnh rộng + cao.

  Truyền động bánh răng + thanh răng (không vít me), 2 núm ĐỘC LẬP:
    Width_Knob_Pinion  (trục đứng, tím)  — pinion + 2 thanh răng đối diện
                        → 2 vách xanh tịnh tiến đối xứng = BỀ RỘNG
    Height_Knob_Pinion (trục ngang, tím) — pinion + thanh răng đứng
                        → tấm trần cam tịnh tiến lên/xuống = CHIỀU CAO
  Đáy máng rỗng — vách đứng luôn sát mặt đĩa quay (không hạ vách).
  Đường hầm dài cố định; cửa chỉnh 0×0 → 25×25 mm.
  Hãm bi lò xo (Detent_WN/WS/H): vặn núm → bi nén lên cho tịnh tiến;
  nhả tay → bi sập vào lỗ lõm khóa cứng từng nấc 2 mm.

Chỉnh nominal opening: sửa WIDTH_OPEN / HEIGHT_OPEN rồi chạy lại script
(chọn giá trị đúng nấc: width bội số 4, height bội số 2).
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
    _HERE = Path(r"d:\Project\coutingmachine\3d_model\freecad")

OUT = _HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
FCSTD = OUT / "adjustable_chute.FCStd"

sys.path.insert(0, str(_HERE))
from adjustable_chute import build_adjustable_chute_parts

WIDTH_OPEN = 20.0   # bề rộng lòng máng (mm), 0..25, nấc 4 mm
HEIGHT_OPEN = 14.0  # chiều cao cửa dưới tấm trần (mm), 0..25, nấc 2 mm


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

    doc = App.newDocument("Adjustable_Chute")
    parts = build_adjustable_chute_parts(
        width_open=WIDTH_OPEN, height_open=HEIGHT_OPEN
    )
    objs = []
    for n, sh, col in parts:
        if n == "Rotor_Disc":
            tr = 20
        elif n.startswith("Frame"):
            tr = 30
        elif n == "Height_Gate":
            tr = 10
        else:
            tr = 0
        objs.append(add_part(doc, n, sh, col, transparency=tr))
    add_group(doc, "Adjustable_Chute", objs)

    doc.recompute()
    doc.saveAs(str(FCSTD))
    print("Saved:", FCSTD)
    print("Knobs: Width_Knob_Pinion (trục Z, chỉnh rộng) | "
          "Height_Knob_Pinion (trục Y, chỉnh cao) — rack & pinion")

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
        print("Shown in GUI")
    else:
        App.closeDocument(doc.Name)


main()
