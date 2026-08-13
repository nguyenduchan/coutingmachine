"""
Standalone FreeCAD: Disc_Access_Lid (nắp mở đĩa).

Cùng geometry makers với máy đếm (show_jgb37_gui.py + box_settings.LID).
Lỗ M3 (assembly_bolts) — chỉ khoét lỗ, không vẽ bu-lông.
Sửa LID / make_lid_* rồi chạy lại script này HOẶC show_jgb37_gui.py
→ cả model nắp và hộp đều nhận shape mới đầy đủ.

Launch:
  freecad.exe 3d_model/freecad/show_disc_access_lid_gui.py
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
FCSTD = OUT / "disc_access_lid.FCStd"

sys.path.insert(0, str(_HERE))

# Import makers without running show_jgb37 main (guarded by __name__).
import show_jgb37_gui as JGB  # noqa: E402
from disc_access_lid import (  # noqa: E402
    assemble_disc_access_lid,
    enforce_lid_parent_pz0,
    force_show_lid_top,
)


def add_part(doc, name, shape, color, transparency=0):
    return JGB.add_part(doc, name, shape, color, transparency=transparency)


def add_group(doc, name, children, use_part=True):
    return JGB.add_group(doc, name, children, use_part=use_part)


def main() -> None:
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)

    doc = App.newDocument("Disc_Access_Lid")

    # Same world Z as counting-machine assembly so coords match 1:1.
    z_disc = JGB.TOP_Z + JGB.BOX_T + 1.0

    result = assemble_disc_access_lid(
        doc,
        z_disc,
        add_part=add_part,
        add_group=add_group,
        make_lid_top_parts=JGB.make_lid_top_parts,
        make_lid_bottom_parts=JGB.make_lid_bottom_parts,
        make_lid_fill_parts=JGB.make_lid_fill_parts,
        make_disc_access_lid_parts=JGB.make_disc_access_lid_parts,
        make_width_adjust_drive_parts=JGB.make_width_adjust_drive_parts,
        make_height_adjust_drive_parts=JGB.make_height_adjust_drive_parts,
        lid_cfg=JGB._LID_CFG,
        keep_assembly=None,
    )
    if result.get("count_msg"):
        print(result["count_msg"])

    enforce_lid_parent_pz0(doc, JGB.LID_DISC_CLEAR)
    if result.get("lid_top_grp") is not None:
        force_show_lid_top(doc, result["lid_top_objs"], result["lid_top_grp"])

    doc.recompute()
    doc.saveAs(str(FCSTD))
    print("Saved:", FCSTD)
    print(
        "Shared with box: edit box_settings.LID / make_lid_* then rebuild "
        "this file OR show_jgb37_gui.py — both update fully."
    )
    print(
        "Lid clearance: wall bottoms at disc_top+%.1f mm (Disc_Access_Lid Pz=0)"
        % JGB.LID_DISC_CLEAR
    )

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
        print("Shown in GUI")
    else:
        App.closeDocument(doc.Name)


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


if _is_direct_launch():
    main()
