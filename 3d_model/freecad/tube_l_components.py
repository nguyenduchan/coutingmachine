# -*- coding: utf-8 -*-
"""
Tách Tube_L_Exit_Gate thành từng component FCStd rời + assembly bằng App::Link.

  out/tube_l_exit_gate_parts/<Component>.FCStd   ← file rời, SỬA Ở ĐÂY
  out/tube_l_exit_gate_parts/tube_l_exit_gate.FCStd ← assembly, App::Link tới các file trên

Sửa 1 component rồi save → mở lại (hoặc reload) assembly là thấy cập nhật ngay,
vì assembly chỉ giữ link ngoài tài liệu chứ không copy hình khối.

KÍCH THƯỚC GIỮ NGUYÊN: mỗi component được cắt ra ở đúng toạ độ global của
assembly (Placement = identity), nên tách/ghép lại không đổi kích thước lẫn vị
trí lắp. Muốn dời một chi tiết thì sửa Placement trong chính file component —
link dùng LinkTransform=True nên assembly đi theo.

Run:
  "…\\freecad.exe" 3d_model\\freecad\\tube_l_components.py
      → giữ nguyên các file component đã sửa tay, chỉ tạo file còn thiếu
        rồi dựng lại assembly.

  "…\\freecad.exe" 3d_model\\freecad\\tube_l_components.py --rebuild
      → dựng lại TẤT CẢ component từ code (ghi đè sửa tay).

  "…\\freecad.exe" 3d_model\\freecad\\tube_l_components.py --W 9 --H 5
"""
from __future__ import annotations

import argparse
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
PARTS_DIR = OUT / "tube_l_exit_gate_parts"
# Assembly nằm cùng thư mục với component → XLink relative = "Name.FCStd"
# (không còn "tube_l_exit_gate_parts/…"), tránh gãy khi mở từ folder parts.
FCSTD = PARTS_DIR / "tube_l_exit_gate.FCStd"

sys.path.insert(0, str(_HERE))
from part_exit_camera import build_exit_camera_parts  # noqa: E402
from part_chute_slide import write_chute_slide_component  # noqa: E402
from part_bowl_tube import write_bowl_tube_component  # noqa: E402
from tube_l_exit_gate import build_tube_l_exit_gate_parts  # noqa: E402


def all_source_parts(width_open: float, height_open: float) -> list[tuple]:
    """Cơ khí + cụm camera đếm. Cố ý KHÔNG gộp vào
    build_tube_l_exit_gate_parts() vì hàm đó còn nuôi export_tube_l_meshes.py
    → thêm camera vào đó là nhét khối tĩnh vô ích vào mô phỏng PyBullet."""
    return list(build_tube_l_exit_gate_parts(width_open, height_open)) + \
        list(build_exit_camera_parts())

# Preview = medium_8x4 + 1 mm clear → máng 9×5 (giống show_tube_l_exit_gate_gui)
WIDTH_OPEN = 9.0
HEIGHT_OPEN = 5.0

TRANSPARENCY = {"Bowl_Tube": 55, "Rotor_Disc": 15}

GROUPS = (
    ("Rotor", ("Rotor_Disc", "Hub_Body")),
    ("Bowl", ("Bowl_Tube",)),
    ("Guide", ("Guide_System",)),
    (
        "Adjust_Slide",
        (
            "Crossbar_Bridge",
            "Scale_Width",
            "Width_Carriage",
            "Scale_Height",
            "Height_Scraper",
        ),
    ),
    ("Lane_And_Exit", ("Inner_Lane_Rail", "Chute_Slide")),
    (
        "Vision_Count",
        (
            "Exit_Camera",
            "Camera_Mount",
            "Backlight_Panel",
            "Backlight_Mount",
            "Collection_Funnel",
        ),
    ),
)


def component_path(name: str) -> Path:
    return PARTS_DIR / f"{name}.FCStd"


def _gui_up() -> bool:
    return Gui is not None and bool(getattr(App, "GuiUp", False))


def _style(obj, color, transparency: int = 0) -> None:
    if not _gui_up():
        return
    try:
        vo = obj.ViewObject
        vo.ShapeColor = tuple(color)
        vo.Transparency = int(transparency)
        vo.Visibility = True
    except Exception:
        pass


def _same_file(doc, path: Path) -> bool:
    try:
        return bool(doc.FileName) and Path(doc.FileName).resolve() == path.resolve()
    except Exception:
        return False


def _close_doc_for(path: Path) -> None:
    for doc in list(App.listDocuments().values()):
        if _same_file(doc, path):
            App.closeDocument(doc.Name)


def _open_doc(path: Path):
    for doc in App.listDocuments().values():
        if _same_file(doc, path):
            return doc
    return App.openDocument(str(path))


def _source_object(doc, name: str):
    obj = doc.getObject(name)
    if obj is not None:
        return obj
    for cand in doc.Objects:
        if cand.isDerivedFrom("Part::Feature"):
            return cand
    return None


def export_components(
    width_open: float = WIDTH_OPEN,
    height_open: float = HEIGHT_OPEN,
    rebuild: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    """Ghi mỗi solid ra 1 FCStd riêng. Mặc định KHÔNG đè file đã có."""
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    written: list[str] = []
    kept: list[str] = []

    for name, shape, color in all_source_parts(width_open, height_open):
        names.append(name)
        path = component_path(name)
        if path.exists() and not rebuild:
            kept.append(name)
            continue
        if name == "Chute_Slide":
            _close_doc_for(path)
            write_chute_slide_component(path, color, style_fn=_style)
            written.append(name)
            continue
        if name == "Bowl_Tube":
            _close_doc_for(path)
            write_bowl_tube_component(path, color, style_fn=_style)
            written.append(name)
            continue
        if shape is None or shape.isNull():
            continue
        _close_doc_for(path)
        doc = App.newDocument(name)
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = shape
        obj.Label = name
        _style(obj, color, TRANSPARENCY.get(name, 0))
        doc.recompute()
        doc.saveAs(str(path))
        App.closeDocument(doc.Name)
        written.append(name)

    return names, written, kept


def build_component_assembly(
    width_open: float = WIDTH_OPEN,
    height_open: float = HEIGHT_OPEN,
    rebuild: bool = False,
    save: bool = True,
):
    """Tạo assembly App::Link trỏ tới các file component. Trả (doc, info)."""
    names, written, kept = export_components(width_open, height_open, rebuild)

    _close_doc_for(FCSTD)
    doc = App.newDocument("Tube_L_Exit_Gate")
    # App::Link ra ngoài tài liệu đòi owner phải có sẵn FileName, nếu không
    # setLink() ném "Owner document not saved" → lưu rỗng trước rồi mới link.
    doc.saveAs(str(FCSTD))

    links: dict[str, object] = {}
    missing: list[str] = []
    for name in names:
        path = component_path(name)
        if not path.exists():
            missing.append(name)
            continue
        src_doc = _open_doc(path)
        src = _source_object(src_doc, name)
        if src is None:
            missing.append(name)
            continue
        lnk = doc.addObject("App::Link", name)
        lnk.setLink(src)
        lnk.Label = name
        try:
            # Placement của component được tôn trọng → dời trong file rời là
            # assembly đi theo.
            lnk.LinkTransform = True
        except Exception:
            pass
        if _gui_up():
            try:
                lnk.ViewObject.Visibility = True
            except Exception:
                pass
        links[name] = lnk

    for group_name, members in GROUPS:
        kids = [links[m] for m in members if m in links]
        if not kids:
            continue
        # Dùng DocumentObjectGroup (không phải App::Part): App::Part gắn Origin
        # với axes/planes bbox ±1e100 → ViewFit zoom vô cực = màn hình trống.
        grp = doc.addObject("App::DocumentObjectGroup", group_name)
        grp.Label = group_name
        for kid in kids:
            grp.addObject(kid)

    doc.recompute()
    if save:
        doc.save()

    info = {
        "names": names,
        "written": written,
        "kept": kept,
        "missing": missing,
        "n_link": len(links),
        "parts_dir": PARTS_DIR,
        "assembly": FCSTD,
    }
    return doc, info


def print_summary(info: dict) -> None:
    print("Components dir:", info["parts_dir"])
    print("Assembly      :", info["assembly"])
    print(
        "Linked=%s | rebuilt=%s | kept=%s"
        % (info["n_link"], len(info["written"]), len(info["kept"]))
    )
    if info["written"]:
        print("  rebuilt:", ", ".join(info["written"]))
    if info["kept"]:
        print("  kept (sửa tay được giữ nguyên):", ", ".join(info["kept"]))
    if info["missing"]:
        print("  MISSING:", ", ".join(info["missing"]))
    print(
        "Sửa 1 component → save → mở lại tube_l_exit_gate.FCStd là cập nhật "
        "(App::Link ngoài tài liệu)."
    )


def main() -> None:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--W", type=float, default=WIDTH_OPEN)
    ap.add_argument("--H", type=float, default=HEIGHT_OPEN)
    ap.add_argument("--rebuild", action="store_true")
    args, _unknown = ap.parse_known_args(sys.argv[1:])

    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)

    doc, info = build_component_assembly(args.W, args.H, rebuild=args.rebuild)
    print_summary(info)

    if _gui_up():
        Gui.ActiveDocument = Gui.getDocument(doc.Name)
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.updateGui()
        print("Shown in GUI")
    else:
        for name in list(App.listDocuments().keys()):
            App.closeDocument(name)


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
