"""
Standalone FreeCAD: mở Tube_L_Exit_Gate để XEM (không còn bộ verify).

Ref: https://www.youtube.com/shorts/ju5vIg66NNk

  Guide_System (cố định)     — xoắn hub→họng CCW; họng ra 20 mm tính từ mép đĩa
  Entry_Gate_Post            — trụ cố định trên vành bát + ray T ĐỨNG (đầu máng vào)
  Entry_Gate_Slider          — thanh trượt tịnh tiến đứng (= chỉnh cao)
  Entry_Gate_Barrier         — barrier chữ L: trần 20 mm + tấm đứng 10 mm, rộng 30 mm
  Exit_Inner_Wall            — vách trong tại 9h, lùi 2 cm vào tâm, chạy tới vành đĩa
  Bowl_Tube_Exit_Chute       — máng 40° rộng 2 cm, hứng ngay dưới kênh hai vách exit

THAO TÁC:
  W: cố định = họng ra Guide_System (ENTRANCE_W) — không còn cơ cấu trượt
  H: nới Screw_Gate_H → nâng/hạ cụm barrier trên ray T đứng; khe dưới trần = H

CHẠY: phải dùng freecad.exe (KHÔNG phải freecadcmd) — save headless mất
GuiDocument.xml nên model mở ra bị ẩn sạch, không màu.
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
from mech_common import ENTRANCE_W, GATE_TH_DEG, H_MIN, H_MAX

# Preview = medium_8x4 + 1 mm clear → khe cửa H = 5
WIDTH_OPEN = 9.0
HEIGHT_OPEN = 5.0


def main() -> None:
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)

    # rebuild=False: GIỮ nguyên các file component (kể cả sửa tay trong FreeCAD).
    # Muốn dựng lại từ code thì chạy: freecad.exe tube_l_components.py --rebuild
    doc, info = build_component_assembly(WIDTH_OPEN, HEIGHT_OPEN, rebuild=False)
    print("Saved:", FCSTD)
    print_summary(info)
    print(
        "LANE: W cố định %.1f mm (họng Guide, đo từ mép đĩa) | "
        "H chỉnh %.0f–%.0f mm tại cửa %.1f°"
        % (ENTRANCE_W, H_MIN, H_MAX, GATE_TH_DEG)
    )

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
    else:
        print("!! Dang chay headless — model se bi an. Hay mo bang freecad.exe.")
        App.closeDocument(doc.Name)


main()
