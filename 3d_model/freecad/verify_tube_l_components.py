# -*- coding: utf-8 -*-
"""
Verify việc tách Tube_L_Exit_Gate ra component rời (tube_l_components.py).

Kiểm 2 điều thật sự quan trọng:
  A. KÍCH THƯỚC GIỮ NGUYÊN — solid trong mỗi file component phải trùng khít
     solid dựng từ code: cùng Volume, cùng Area, cùng CenterOfMass (global).
  B. SỬA COMPONENT → ASSEMBLY CẬP NHẬT — dời Placement trong 1 file component,
     lưu, mở lại assembly thì hình phải dời theo đúng lượng đó. Sau đó trả lại
     nguyên trạng.

KHÔNG dùng Shape.BoundBox làm tiêu chí: OCC tính BoundBox xấp xỉ từ lưới tam
giác nên với mặt cong nó nới rộng ra, và mức nới phụ thuộc shape đã được
tessellate hay chưa — hình dựng thẳng trong RAM và hình đọc lại từ BRep đã lưu
cho ra bbox lệch tới ~0.13 mm dù khối y hệt nhau (Volume lệch ~1e-15). Volume +
Area + CenterOfMass là bất biến hình học chính xác: CoM bắt được mọi phép dời/
xoay, Volume+Area bắt được mọi thay đổi kích thước. BoundBox vẫn được ghi ra
JSON nhưng chỉ để tham khảo.

Run:
  "…\\freecad.exe" -c "import runpy; runpy.run_path(r'…\\verify_tube_l_components.py', run_name='__main__')"
  hoặc: freecadcmd 3d_model\\freecad\\verify_tube_l_components.py
"""
from __future__ import annotations

import json
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
    _HERE = Path(__file__).resolve().parent
except NameError:
    _HERE = Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad")

sys.path.insert(0, str(_HERE))

from tube_l_components import (  # noqa: E402
    FCSTD,
    HEIGHT_OPEN,
    PARTS_DIR,
    WIDTH_OPEN,
    all_source_parts,
    component_path,
)

OUT = _HERE / "out"
VOL_RTOL = 1e-9
AREA_RTOL = 1e-9
COM_ATOL = 1e-6  # mm — bắt mọi phép dời/xoay
PROBE_PART = "Scale_Width"
PROBE_DZ = 7.0


def _bbox(shape) -> dict:
    bb = shape.BoundBox
    return {
        "xmin": float(bb.XMin), "xmax": float(bb.XMax),
        "ymin": float(bb.YMin), "ymax": float(bb.YMax),
        "zmin": float(bb.ZMin), "zmax": float(bb.ZMax),
    }


def _com(shape) -> tuple[float, float, float]:
    """Trọng tâm khối. Part.Compound không có .CenterOfMass → tự cộng theo
    thể tích từng solid (kết quả y hệt, và đúng cho cả compound lẫn solid)."""
    solids = shape.Solids
    if solids:
        total = sum(s.Volume for s in solids)
        if total > 1e-12:
            return (
                sum(s.CenterOfMass.x * s.Volume for s in solids) / total,
                sum(s.CenterOfMass.y * s.Volume for s in solids) / total,
                sum(s.CenterOfMass.z * s.Volume for s in solids) / total,
            )
    try:
        c = shape.CenterOfMass
        return (float(c.x), float(c.y), float(c.z))
    except Exception:
        c = shape.BoundBox.Center
        return (float(c.x), float(c.y), float(c.z))


def _metrics(shape) -> dict:
    return {
        "volume": float(shape.Volume),
        "area": float(shape.Area),
        "com": _com(shape),
        "bbox": _bbox(shape),
        "n_solid": len(shape.Solids),
    }


def _com_delta(a: dict, b: dict) -> float:
    return max(abs(x - y) for x, y in zip(a["com"], b["com"]))


def _rel(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1e-12)


def _bbox_delta(a: dict, b: dict) -> float:
    return max(abs(a[k] - b[k]) for k in a)


def _close_all() -> None:
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)


def _linked_shape(doc, name):
    """Shape global của một App::Link trong assembly."""
    lnk = doc.getObject(name)
    if lnk is None:
        return None
    src = lnk.getLinkedObject(True)
    if src is None:
        return None
    sh = getattr(src, "Shape", None)
    try:
        if sh is not None and not sh.isNull() and float(getattr(sh, "Volume", 0) or 0) > 1e-6:
            return sh
    except Exception:
        pass
    kids = list(getattr(src, "Group", []) or [])
    shapes = []
    for k in kids:
        ks = getattr(k, "Shape", None)
        try:
            if ks is not None and not ks.isNull() and float(getattr(ks, "Volume", 0) or 0) > 1e-9:
                shapes.append(ks)
        except Exception:
            continue
    if not shapes:
        return None
    body = shapes[0]
    for extra in shapes[1:]:
        try:
            body = body.fuse(extra)
        except Exception:
            continue
    return body


def check_dimensions_preserved() -> dict:
    """A. component + link phải trùng khít solid dựng từ code."""
    ref = {}
    for name, shape, _color in all_source_parts(WIDTH_OPEN, HEIGHT_OPEN):
        if shape is None or shape.isNull():
            continue
        ref[name] = _metrics(shape)

    _close_all()
    doc = App.openDocument(str(FCSTD))

    rows = []
    for name, r in ref.items():
        path = component_path(name)
        got = _linked_shape(doc, name)
        if got is None:
            rows.append({"part": name, "pass": False, "why": "link không resolve"})
            continue
        m = _metrics(got)
        rel_vol = _rel(m["volume"], r["volume"])
        rel_area = _rel(m["area"], r["area"])
        d_com = _com_delta(m, r)
        ok = rel_vol <= VOL_RTOL and rel_area <= AREA_RTOL and d_com <= COM_ATOL
        rows.append({
            "part": name,
            "file": path.name,
            "file_exists": path.exists(),
            "volume_mm3": m["volume"],
            "volume_rel_err": rel_vol,
            "area_rel_err": rel_area,
            "com_max_err_mm": d_com,
            # tham khảo: bbox xấp xỉ theo lưới, lệch trên mặt cong là bình thường
            "bbox_max_err_mm_informational": _bbox_delta(m["bbox"], r["bbox"]),
            "pass": bool(ok),
        })

    _close_all()
    n_pass = sum(1 for r in rows if r.get("pass"))
    return {
        "pass": n_pass == len(rows) and len(rows) > 0,
        "n_pass": n_pass,
        "n_parts": len(rows),
        "vol_rtol": VOL_RTOL,
        "area_rtol": AREA_RTOL,
        "com_atol_mm": COM_ATOL,
        "rows": rows,
    }


def check_edit_propagates() -> dict:
    """B. sửa file component → mở lại assembly thấy đổi. Xong trả nguyên trạng."""
    path = component_path(PROBE_PART)
    if not path.exists():
        return {"pass": False, "why": f"thiếu {path.name}"}

    _close_all()
    doc = App.openDocument(str(FCSTD))
    before = _metrics(_linked_shape(doc, PROBE_PART))
    _close_all()

    # --- sửa trong file component ---
    cdoc = App.openDocument(str(path))
    obj = cdoc.getObject(PROBE_PART)
    orig = App.Placement(obj.Placement)
    moved = App.Placement(orig)
    moved.Base.z = orig.Base.z + PROBE_DZ
    obj.Placement = moved
    cdoc.recompute()
    cdoc.save()
    _close_all()

    # --- mở lại assembly, không đụng gì tới nó ---
    doc = App.openDocument(str(FCSTD))
    after = _metrics(_linked_shape(doc, PROBE_PART))
    _close_all()

    dz = after["com"][2] - before["com"][2]
    dxy = max(
        abs(after["com"][0] - before["com"][0]),
        abs(after["com"][1] - before["com"][1]),
    )
    # dời chứ không biến dạng: thể tích phải y nguyên
    vol_kept = _rel(after["volume"], before["volume"]) <= VOL_RTOL
    ok = abs(dz - PROBE_DZ) <= COM_ATOL and dxy <= COM_ATOL and vol_kept

    # --- trả nguyên trạng ---
    cdoc = App.openDocument(str(path))
    cdoc.getObject(PROBE_PART).Placement = orig
    cdoc.recompute()
    cdoc.save()
    _close_all()

    doc = App.openDocument(str(FCSTD))
    restored = _metrics(_linked_shape(doc, PROBE_PART))
    _close_all()
    restored_ok = _com_delta(restored, before) <= COM_ATOL

    return {
        "pass": bool(ok and restored_ok),
        "probe_part": PROBE_PART,
        "probe_dz_mm": PROBE_DZ,
        "observed_dz_mm": dz,
        "xy_drift_mm": dxy,
        "volume_unchanged": bool(vol_kept),
        "restored_ok": bool(restored_ok),
    }


def main() -> None:
    dims = check_dimensions_preserved()
    prop = check_edit_propagates()
    result = {
        "pass": bool(dims["pass"] and prop["pass"]),
        "assembly": str(FCSTD),
        "parts_dir": str(PARTS_DIR),
        "W_mm": WIDTH_OPEN,
        "H_mm": HEIGHT_OPEN,
        "dimensions_preserved": dims,
        "edit_propagates": prop,
    }
    out_path = OUT / "tube_l_components_verify.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(
        "A. Kích thước giữ nguyên: pass=%s | %s/%s part | "
        "vol_rel<=%.0e area_rel<=%.0e CoM<=%.0e mm"
        % (dims["pass"], dims["n_pass"], dims["n_parts"], VOL_RTOL, AREA_RTOL, COM_ATOL)
    )
    for r in dims["rows"]:
        if not r.get("pass"):
            print("   FAIL:", r)
    print(
        "B. Sửa component → assembly cập nhật: pass=%s | dời %s +%.1f mm → "
        "CoM assembly dời %.9f mm, xy_drift=%.2e, vol_giu_nguyen=%s, restored=%s"
        % (
            prop["pass"], prop.get("probe_part"), prop.get("probe_dz_mm", 0.0),
            prop.get("observed_dz_mm", 0.0), prop.get("xy_drift_mm", 0.0),
            prop.get("volume_unchanged"), prop.get("restored_ok"),
        )
    )
    print("OVERALL pass=%s → %s" % (result["pass"], out_path))


if __name__ == "__main__" or True:
    main()
