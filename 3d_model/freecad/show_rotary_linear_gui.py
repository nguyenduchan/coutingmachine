"""
Standalone FreeCAD: Rotary_Linear — rack & pinion (travel horizontal).

Active:
  RL_Pinion_Shaft (pinion+shaft fused print)
  RL_Bearing_Rail_S/N + RL_Bearing_Cap_S/N (M3 clamp)
  RL_Rail_Bridge (flat // follower, joins S–N; bore for ball detent)
  RL_Knob (blind seat + short M3) + RL_Friction_Washer
  RL_Follower (tịnh tiến ngang + rãnh cầu detent)
  RL_Detent (bi + lò xo + ốc siết — hãm khi dừng xoay)

Assembly: drop pinion-shaft → M3 caps → washer/knob; ball plunger in bridge.
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
FCSTD = OUT / "rotary_linear.FCStd"

sys.path.insert(0, str(_HERE))
import box_settings as BX
from rotary_linear import ACTIVE_RL_PARTS, build_rotary_linear_parts


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

    doc = App.newDocument("Rotary_Linear")
    drv = dict(BX.LID.get("height_bar", {}).get("drive", {}))
    hb = BX.LID.get("height_bar", {})
    drv["bar_length_y"] = float(drv.get("bar_length_y", 24.0))
    drv["bar_thickness"] = float(drv.get("bar_thickness", hb.get("thickness", 6.0)))
    drv["bar_height"] = float(drv.get("bar_height", hb.get("height", 12.0)))
    drv["include_bottom_stop"] = False
    drv["include_scale"] = False
    # Ball detent: răng m=2 dễ in; nấc bi 0.5 mm độc lập (độ phân giải mịn)
    drv["include_ball_detent"] = True
    drv["include_active_cam"] = True
    drv["detent_pitch"] = 0.5
    drv["detent_ball_r"] = 0.75  # bi Ø1.5 — hợp nấc 0.5 mm
    # detent_off / pocket_r: để rotary_linear tự tính dimple nông (còn gờ giữa nấc)
    drv.pop("detent_off", None)
    # Giữ module lớn (đã có trong box_settings ≈ 2.0) — không hạ xuống 0.5 mm/răng
    drv["gear_module"] = 2.0
    drv.setdefault("rack", {})
    if isinstance(drv["rack"], dict):
        drv["rack"] = dict(drv["rack"])
        drv["rack"]["module"] = 2.0
        drv["rack"]["tooth_clear"] = float(drv["rack"].get("tooth_clear", 0.55))

    parts = build_rotary_linear_parts(
        cx=0.0,
        cy=0.0,
        z_zero=0.0,
        cfg=drv,
        include_demo_wall=False,
    )
    objs = []
    for n, sh, col in parts:
        if n not in ACTIVE_RL_PARTS:
            print("skip (not in active model):", n)
            continue
        elif n == "RL_Detent":
            tr = 0
            col = (0.95, 0.78, 0.08)  # vàng — đầu ốc + bi/lò xo
        elif n == "RL_Cam_Sleeve":
            tr = 0
            col = (0.98, 0.45, 0.08)
        elif n == "RL_Cam_StopPin":
            tr = 0
            col = (0.2, 0.2, 0.2)
        elif n.startswith("RL_Bearing_Cap"):
            tr = 35
            col = (0.40, 0.60, 0.85)
        elif n.startswith("RL_Bearing"):
            tr = 45
        elif n == "RL_Rail_Bridge":
            tr = 75  # cửa sổ + trong suốt: thấy bi tì rãnh thanh
        elif n == "RL_Follower":
            tr = 35  # bớt đục để thấy track rãnh trên lưng
            # keep green from builder
        elif n == "RL_Pinion_Shaft":
            tr = 0
            col = (1.0, 0.45, 0.05)
        elif n == "RL_Friction_Washer":
            tr = 30
        else:
            tr = 15
        objs.append(add_part(doc, n, sh, col, transparency=tr))
    add_group(doc, "Rotary_Linear_Drive", objs)

    doc.recompute()
    doc.saveAs(str(FCSTD))
    print("Saved:", FCSTD)
    print("Active:", ", ".join(sorted(ACTIVE_RL_PARTS)))
    det_obj = next((o for o in objs if o.Name == "RL_Detent"), None)
    print(
        "KINEMATICS: xoay núm → ramp trong núm → RL_Cam_Sleeve trượt → "
        "tay đẩy RL_Detent rút bi lên trước. Hết free-play thì stop pin "
        "mới kéo trục/pinion. Nhìn cụm cam màu cam gần núm."
    )
    if det_obj is not None:
        print("RL_Detent selected — look at bridge side window mid-travel")

    if App.GuiUp and Gui is not None:
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        if det_obj is not None:
            try:
                Gui.Selection.clearSelection()
                Gui.Selection.addSelection(doc.Name, det_obj.Name)
            except Exception:
                pass
        Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
        print("Shown in GUI")
    else:
        App.closeDocument(doc.Name)


main()
