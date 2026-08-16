"""
Chup anh 3D view hien tai (FreeCAD GUI) ra file PNG — dung de kiem tra vi tri
cac phan (VD: Entry_Gate_Barrier so voi Rotor_Disc/Bowl_Tube) ma khong can mo GUI
tuong tac.

Chay (giong animate_rotor_disc.py — FreeCAD tu mo FCStd truoc, roi thuc thi script nay):
  "C:\\Users\\Admin\\AppData\\Local\\Programs\\FreeCAD 1.1\\bin\\freecad.exe" ^
    "3d_model\\freecad\\out\\tube_l_exit_gate_parts\\tube_l_exit_gate.FCStd" ^
    "3d_model\\freecad\\snapshot_view.py"
"""
import os
import FreeCAD as App
import FreeCADGui as Gui

OUT_PATH = os.environ.get("SNAPSHOT_OUT", r"C:\workspace\embedded\CountingMachine\3d_model\freecad\out\_snapshot.png")
VIEW = os.environ.get("SNAPSHOT_VIEW", "iso")  # iso | front | top | right

doc = App.ActiveDocument
if doc is None:
    raise RuntimeError("Khong co document dang mo.")

view = Gui.activeDocument().activeView()
{
    "iso": view.viewIsometric,
    "front": view.viewFront,
    "top": view.viewTop,
    "right": view.viewRight,
}.get(VIEW, view.viewIsometric)()
Gui.SendMsgToActiveView("ViewFit")
view.saveImage(OUT_PATH, 1200, 900, "White")
print(f"[snapshot_view] Da luu anh: {OUT_PATH}")

App.closeDocument(doc.Name)
