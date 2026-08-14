"""
Mo phong dia quay Rotor_Disc trong FreeCAD GUI (thoi gian thuc).

Chay bang FreeCAD GUI (khong phai freecadcmd), vi du:
  "C:\\Users\\Admin\\AppData\\Local\\Programs\\FreeCAD 1.1\\bin\\freecad.exe" ^
    "3d_model\\freecad\\out\\tube_l_exit_gate_parts\\tube_l_exit_gate.FCStd" ^
    "3d_model\\freecad\\animate_rotor_disc.py"

FreeCAD tu dong mo file .FCStd truoc, roi thuc thi script .py nay trong
cung mot session -> script lay ActiveDocument va bat dau quay Rotor_Disc.

De dung animation tu Python console cua FreeCAD:
  _rotor_anim_timer.stop()
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

RPM = 40.0
DEG_PER_SEC = RPM * 360.0 / 60.0  # 240 deg/s
TICK_MS = 33  # ~30 fps

doc = App.ActiveDocument
if doc is None:
    raise RuntimeError("Khong co document nao dang mo — hay mo tube_l_exit_gate.FCStd truoc.")

disc = doc.getObject("Rotor_Disc")
if disc is None:
    raise RuntimeError("Khong tim thay object 'Rotor_Disc' trong document.")

_axis = App.Vector(0, 0, 1)
_center = App.Vector(0, 0, 0)
_clock = QtCore.QElapsedTimer()
_clock.start()


def _tick():
    t = _clock.elapsed() / 1000.0
    angle_deg = (DEG_PER_SEC * t) % 360.0
    disc.Placement = App.Placement(_center, App.Rotation(_axis, angle_deg))
    doc.recompute()


_rotor_anim_timer = QtCore.QTimer()
_rotor_anim_timer.timeout.connect(_tick)
_rotor_anim_timer.start(TICK_MS)

try:
    import __main__
    __main__._rotor_anim_timer = _rotor_anim_timer  # giu tham chieu, tranh bi garbage-collect
except Exception:
    pass

Gui.SendMsgToActiveView("ViewFit")
print(f"[animate_rotor_disc] Dia quay {RPM:.0f} vong/phut ({DEG_PER_SEC:.1f} do/giay). "
      f"Dung bang: _rotor_anim_timer.stop()")
