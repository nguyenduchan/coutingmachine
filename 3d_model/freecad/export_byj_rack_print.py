#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export byj_rack_stage printable parts as separate STLs + one spaced print plate.

In 3D (PETG):
  Housing, Housing_Lid, Pinion, Slide_Bar,
  Guide_Rod_A, Guide_Rod_B, Guide_Rod_Cap_A, Guide_Rod_Cap_B
  (Guide_Rod_A/B: TRON O5 cat phang day -- de in may doi cu; bac Slide_Bar cung
  tron day phang, B capsule noi Y. Guide_Rod_Cap_A/B: tam phang vuong up khit vach,
  vit tu ren M3 XUYEN nap + vach vao lo moi o dau thanh -- THAO DUOC. A/B giong
  hinh, chi khac Y -- in Guide_Rod_A.stl va Guide_Rod_Cap_A.stl moi thu 2 lan.)
  LUU Y BOM: vit dai hon binh thuong mot chut vi phai xuyen QUA nap (3mm) + QUA vach
  (2.5mm) + REN VAO than thanh (~8mm) -- dung M3 dai >= 14mm (vd M3x16).

  RA SOAT DE IN 2026-09-06 (may in day tu duoi len, xac nhan bang face-normal overhang
  scan -- xem project_byj_rack_stage.md): Pinion va Guide_Rod_Cap_A/B duoc XOAY LAI
  trong STL xuat ra (khac huong lap rap) de het overhang -- xem PRINT_ROTATIONS o duoi.
  Cac phan con lai (Housing, Housing_Lid, Slide_Bar, Guide_Rod_A/B) giu nguyen huong lap
  rap, da la huong tot nhat.)

Mua san (khong export vao BOM chinh):
  BYJ_Motor (+ BYJ_Motor_Shaft), Limit_Switch_*, vit M2/M3

BONUS 2026-09-06 (khong phai BOM, chi de demo/hoc tap): BYJ_Motor + BYJ_Motor_Shaft
xuat THEM 1 file "print-in-place" (2 khoi trong 1 STL, dung vi tri lap rap, khe ho
MOT_SHAFT_CLR quanh truc) de in thu mo hinh truc quay tu do trong than -- xem
export_motor_print_in_place() va out/byj_motor_print_in_place/manifest.json.

Run:
  freecadcmd 3d_model/freecad/export_byj_rack_print.py

Output:
  3d_model/freecad/out/byj_rack_print/
    Housing.stl
    Housing_Lid.stl
    Pinion.stl
    Slide_Bar.stl
    Guide_Rod_A.stl
    Guide_Rod_B.stl            (= Guide_Rod_A.stl, xuat rieng cho tien ten trong Cura)
    Guide_Rod_Cap_A.stl
    Guide_Rod_Cap_B.stl        (= Guide_Rod_Cap_A.stl, xuat rieng cho tien ten)
    byj_rack_print_plate.stl   ← load 1 file trong Cura = in 1 luot
    manifest.json
  3d_model/freecad/out/byj_motor_print_in_place/   (BONUS, khong phai BOM)
    BYJ_Motor_PrintInPlace.stl
    manifest.json
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

import FreeCAD as App  # noqa: F401
import Part
import MeshPart

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from byj_rack_stage import build_parts  # noqa: E402
import byj_rack_stage as bm  # noqa: E402  (doc constants, vd MOT_SHAFT_CLR)

OUT = _HERE / "out" / "byj_rack_print"
OUT.mkdir(parents=True, exist_ok=True)

# Chi tiet IN 3D (tach roi). Khong gom motor / cong tac (mua san).
PRINT_PARTS = ("Housing", "Housing_Lid", "Pinion", "Slide_Bar",
               "Guide_Rod_A", "Guide_Rod_B",
               "Guide_Rod_Cap_A", "Guide_Rod_Cap_B")

# Khoang cach XY giua cac chi tiet tren plate (mm)
GAP_MM = 8.0
LINEAR_DEFLECTION = 0.25


def _to_bed(shape: Part.Shape) -> Part.Shape:
    """Dich ZMin ve 0 (dat len ban in), giu X/Y."""
    bb = shape.BoundBox
    return shape.copy().translate(App.Vector(0.0, 0.0, -bb.ZMin))


# Xoay TRUOC khi dat len ban in (_to_bed) -- xem soat "de in 3D" 2026-09-06, xac nhan
# bang face-normal overhang scan (mat phang huong xuong qua 45 deg, tru mat day).
PRINT_ROTATIONS: dict[str, tuple[float, App.Vector]] = {
    # Pinion: rang nam ban, tru+ban cau O10 huong len (khong moay-o duoi) — khong xoay.
    "Guide_Rod_Cap_A": (-90.0, App.Vector(0, 1, 0)),
    "Guide_Rod_Cap_B": (-90.0, App.Vector(0, 1, 0)),
}


def _apply_rotation(name: str, shape: Part.Shape) -> Part.Shape:
    rot = PRINT_ROTATIONS.get(name)
    if rot is None:
        return shape
    angle, axis = rot
    return shape.copy().rotate(App.Vector(0, 0, 0), axis, angle)


def _bbox_info(shape: Part.Shape) -> dict:
    bb = shape.BoundBox
    return {
        "xmin": round(bb.XMin, 3),
        "xmax": round(bb.XMax, 3),
        "ymin": round(bb.YMin, 3),
        "ymax": round(bb.YMax, 3),
        "zmin": round(bb.ZMin, 3),
        "zmax": round(bb.ZMax, 3),
        "size_mm": [
            round(bb.XLength, 2),
            round(bb.YLength, 2),
            round(bb.ZLength, 2),
        ],
    }


def shape_to_stl(shape: Part.Shape, path: Path) -> None:
    mesh = MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=LINEAR_DEFLECTION,
        AngularDeflection=0.25,
        Relative=False,
    )
    mesh.write(str(path))


def layout_on_plate(shapes: list[tuple[str, Part.Shape]]) -> Part.Shape:
    """Dat tung phan theo hang X, cach GAP_MM, tat ca ZMin=0."""
    placed: list[Part.Shape] = []
    cursor_x = 0.0
    row_y = 0.0
    max_row_h = 0.0
    # Bed ~220x220 typical; neu dai qua thi xuong hang
    BED_W = 210.0

    for name, sh in shapes:
        s = _to_bed(sh)
        bb = s.BoundBox
        w, d = bb.XLength, bb.YLength
        if cursor_x > 0 and cursor_x + w > BED_W:
            cursor_x = 0.0
            row_y += max_row_h + GAP_MM
            max_row_h = 0.0
        dx = cursor_x - bb.XMin
        dy = row_y - bb.YMin
        s = s.translate(App.Vector(dx, dy, 0.0))
        placed.append(s)
        cursor_x += w + GAP_MM
        max_row_h = max(max_row_h, d)

    compound = Part.makeCompound(placed)
    return compound


# ---------------------------------------------------------------------------
# BONUS: BYJ_Motor + BYJ_Motor_Shaft in-place (2026-09-06, theo yeu cau nguoi dung) --
# KHONG phai chi tiet trong BOM thuc te (dong co that MUA SAN nguyen khoi, xem
# PRINT_PARTS chinh). File nay chi de IN THU mo hinh truc quay tu do trong than.
# XUAT 1 FILE GOM CA 2 KHOI, GIU NGUYEN VI TRI TUONG DOI nhu trong lap rap (khong
# _to_bed() tung khoi roi ghep) -- ky thuat "print-in-place" BAT BUOC 2 khoi phai
# nam DUNG cho lien quan nhau tu dau, may in dap tung lop CA HAI CUNG LUC thi khe ho
# moi thanh hinh; xuat 2 file STL rieng roi tu ghep sau KHONG tao ra khop quay duoc.
# ---------------------------------------------------------------------------
MOTOR_DEMO_DIR = _HERE / "out" / "byj_motor_print_in_place"

EAR_GUSSET_W = 7.0     # be rong nem = het be rong tai (MOT_EAR_W) -- khong chua ho
EAR_GUSSET_EMBED = 3.0  # nem an sau vao trong than bao nhieu — mat than la mat TRU
                         # CONG, nem ve mat PHANG nen phai an sau du de fuse sach o ca
                         # 2 mep rong (khong chi dua vao dung ban kinh MOT_D/2)


def _ear_gusset(s: float) -> Part.Shape:
    """Nem tam giac do 1 tai DC khi in — CHI dung luc export (khong co trong
    make_motor_body() vi day khong phai hinh dang that cua DC, chi de in khong can
    support). Tai thi ra 7mm (MOT_EAR_TIP - MOT_D/2) ma chi day 1mm, KHONG co gi do —
    conson tran, khong phai cau — Ender-3 Pro se lam vong/xe khi in. Nem an sau
    EAR_GUSSET_EMBED vao than (dam bao fuse sach voi mat tru CONG dua vao mep rong nem)
    roi doc len toi day tai o dau mut ngoai — doc THOAI HON 45 deg (vi diem bat dau lui
    sau vao trong) nen chac chan du dieu kien in KHONG CAN SUPPORT.
    s = +1.0 (tai +Y) hoac -1.0 (tai -Y)."""
    r_body = bm.MOT_D / 2.0
    r_tip = bm.MOT_EAR_TIP
    r_back = r_body - EAR_GUSSET_EMBED
    z_top = bm.MOT_EAR_Z0                      # day tai
    # doc AN TOAN hon 45 deg dung (45 deg la bien, may re/it tuy chinh nhu Ender-3 Pro
    # in khong sach o dung bien do) -- dung ti le 1.35:1 (~54 deg tinh tu phuong ngang)
    z_bot = z_top - 1.35 * (r_tip - r_back)
    z_bot = max(z_bot, bm.MOT_Z0 + 0.5)
    x0 = bm.MOT_CX - EAR_GUSSET_W / 2.0
    pts = [
        App.Vector(0.0, s * r_back, z_bot),
        App.Vector(0.0, s * r_back, z_top),
        App.Vector(0.0, s * r_tip, z_top),
    ]
    pts.append(pts[0])
    face = Part.Face(Part.makePolygon(pts))
    prism = face.extrude(App.Vector(EAR_GUSSET_W, 0.0, 0.0))
    prism.translate(App.Vector(x0, 0.0, 0.0))
    return prism


def _conn_fill() -> Part.Shape:
    """Vá kín khe hở 1mm dưới khối nối dây — CHI dung luc export. Khối nối dây bắt
    đầu ở MOT_Z0+1.0 (hụt 1mm so với đáy thân), mà phần thò ra ngoài Ø thân
    (MOT_CONN_OUT) hoàn toàn KHÔNG có gì đỡ bên dưới trong đoạn 1mm đó -> mặt phẳng
    ~83 mm2 lơ lửng, cần support. Lấp đầy đúng đoạn hụt đó bằng 1 khối đặc."""
    return bm._box2(bm.MOT_CONN_X0, bm.MOT_CONN_X1,
                    -bm.MOT_CONN_W / 2.0, bm.MOT_CONN_W / 2.0,
                    bm.MOT_Z0, bm.MOT_Z0 + 1.0)


def export_motor_print_in_place(parts: dict) -> None:
    MOTOR_DEMO_DIR.mkdir(parents=True, exist_ok=True)
    for old in MOTOR_DEMO_DIR.glob("*.stl"):
        old.unlink()
    body = parts["BYJ_Motor"]
    # KHONG fuse nem duoi tai / vach noi day nua (2026-09-06, doi y theo yeu cau):
    # 2 hinh hoc nay FUSE CUNG vao than la VINH VIEN, khong thao sach duoc (phai
    # cua/mai, de lai vet), va lam STL LECH so voi model lap rap chinh trong FreeCAD
    # (nguoi dung phat hien: "phan hinh hop sat day hinh tru" trong STL khong co trong
    # module FreeCAD). Ca 2 la overhang o NGOAI, de tiep can — de Cura TU SINH support
    # o do la du (support co lop tiep giap yeu, thiet ke rieng de be sach, khac han
    # fuse cung). Van giu ham _ear_gusset()/_conn_fill() trong file (khong xoa) phong
    # khi can dung lai; STL xuat ra gio GIONG HET model FreeCAD (khong con hinh hoc
    # rieng chi de export).
    shaft = parts["BYJ_Motor_Shaft"]
    compound = Part.makeCompound([body, shaft])   # KHONG fuse voi shaft -- fuse co the
                                                    # xoa mat tiep xuc, compound giu 2
                                                    # khoi rieng (than co nem, truc thi khong)
    bedded = _to_bed(compound)
    path = MOTOR_DEMO_DIR / "BYJ_Motor_PrintInPlace.stl"
    shape_to_stl(bedded, path)
    info = _bbox_info(bedded)
    print(f"  OK {path.name}  {info['size_mm']} mm  (in-place, 2 khoi trong 1 file)")

    manifest = {
        "model": "byj_rack_stage - BYJ_Motor print-in-place demo",
        "note": ("KHONG phai chi tiet BOM thuc te cua may (dong co that la MUA SAN "
                 "nguyen khoi). File nay chi de in thu mo hinh truc quay tu do."),
        "file": path.name,
        "bbox": info,
        "clearance_diam_mm": bm.MOT_SHAFT_CLR,
        "retention_flange_diam_mm": bm.MOT_SHAFT_RET_D,
        "retention_chamber_diam_mm": bm.MOT_SHAFT_RET_BORE,
        "strut_count": bm.MOT_SHAFT_RET_STRUT_N,
        "strut_height_mm": bm.MOT_SHAFT_RET_STRUT_H,
        "center_pin_diam_mm": bm.MOT_SHAFT_RET_PIN_D,
        "note_2026_09_07_lan33": (
            "clearance_diam_mm = %.1fmm -- GIA TRI DA CHUNG MINH khong dinh cung tren "
            "Ender-3 Pro (xem lan 22). Co thu thu hep xuong 0.7mm o lan 32 de bot lac, "
            "nhung nguoi dung chon UU TIEN AN TOAN ('neu rui ro, tang khe ho len') nen "
            "QUAY LAI 1.0mm. Bu lai do lac bang cach KHAC: keo dai doan OM TRUC (guide "
            "length, MOT_SHAFT_BURY 3.0->5.0mm, lan 33) -- don bay dai hon lam giam goc "
            "lac o CUNG 1 khe ho, khong can danh doi rui ro dinh cung." % bm.MOT_SHAFT_CLR
        ),
        "note_2026_09_07_v3": (
            "Da doi tu 'witness layer' (go giu TUA THANG len day khoang, ban v2) sang "
            "SOI TO MANH + CHOT TAM (dung ky thuat da kiem chung o build_28byj48_"
            "reference.py, xem memory du an lan 26-31): go giu gio LO LUNG (khong cham "
            "day khoang), chi noi voi than qua %d SOI TO quanh rIa (vanh khuyen goc "
            "%.0f do, cao chi %.1fmm -- de be) VA 1 CHOT TAM O%.1fmm o giua (giai quyet "
            "gioi han hinh hoc: ho tro chi o RIA khong bao gio du de bac cau toi TAM 1 "
            "dia -- da xac nhan voi nguoi dung dung Ender-3 Pro, khong bac cau noi "
            "khoang ~3.5mm). Dien tich tiep xuc THAT (soi+chot cong lai) rat nho so voi "
            "ca mat go giu truoc day -- xoay nhe la gay, KHONG can dao/cho nguoi nhu "
            "ban v2."
        ),
        "print_settings": [
            "Layer height 0.2mm (khong lon hon) -- lop day de bit mat khe ho",
            "Quat lam mat 100% NGAY TU LOP DAU, khong tang dan -- QUAN TRONG voi soi "
            "to/chot: lam mat sai se lam chung qua deo, kho gay dut gon",
            "Flow/Extrusion 95-98% -- bu tru lo tron in luon RA NHO hon so danh nghia "
            "tren may pho thong (Ender-3 Pro)",
            "QUAN TRONG -- bat 'Horizontal Expansion' = -0.1mm (Cura: tim 'Horizontal "
            "Expansion' trong Special Modes, can bat che do Expert/Show All Settings) "
            "-- lam VACH NGOAI (truc, go giu) in NHO lai 0.1mm, giup ho khong bi day chat",
            "QUAN TRONG -- bat 'Hole Horizontal Expansion' = +0.1mm (rieng setting nay, "
            "KHAC voi Horizontal Expansion o tren) -- lam LO TRON (khoang trong than) in "
            "TO ra 0.1mm. 2 setting nay CONG DON: bu them ~0.2mm khe ho moi ben (0.4mm "
            "duong kinh) BU DAP cho sai so in that cua may pho thong, ngoai 1.0mm danh "
            "nghia da thiet ke san trong model",
            "Toc do in RAT CHAM (~15-20mm/s) rieng vung go giu (lop dau tien cua dia "
            "bac cau qua soi+chot) -- day la vung RUI RO NHAT tren Ender-3 Pro. Cac "
            "vung khac toc do binh thuong (~30-40mm/s) la du.",
        ],
        "support": [
            "BAT 'Generate Support' (Cura) — van can cho 2 CHO overhang o NGOAI (KHONG "
            "lien quan gi den khop truc, day la 2 cho khac cua than dong co):",
            "  1. 2 tai bat vit (thò ra ngoai Ø than ~7mm, day 1mm, la CONSON tran "
            "khong co gi do)",
            "  2. Khoi noi day (mat day hut 1mm so voi day than, ~83mm2 lo lung)",
            "  - Support Placement: Everywhere; Density thap (~10-15%), Z Distance mac "
            "dinh (~0.1-0.2mm)",
            "KIEM TRA LAI trong Cura preview: KHONG duoc co support sinh o BEN TRONG "
            "khoang giu/quanh truc -- day la khoang KIN (chi thong qua khe Ø9 rat nho "
            "tren dinh), support sinh o do se KHONG LAY RA DUOC sau khi in. Thiet ke "
            "soi to+chot tam da tinh de KHONG can support o vung nay -- neu Cura van tu "
            "sinh, dung 'Support Blocker' chan het vung khoang giu.",
        ],
        "after_print": [
            "CAM DOAN TRUC (phan lo ra tren dinh go O9), XOAY QUA LAI vai lan -- soi to "
            "+ chot tam se GAY GON (tiet dien nho), truc roi ra quay tu do NGAY, KHONG "
            "can dao/cho nguoi nhu ban v2 truoc.",
            "Go giu O%.1fmm o day truc to hon lo truc tron O%.1fmm phia tren -- du gay "
            "het soi to/chot, truc VAN KHONG tuot len duoc." % (bm.MOT_SHAFT_RET_D,
                                                                bm.MOT_SHAFT_BORE),
            "Neu soi/chot chua gay het: xoay tiep + keo nhe doc truc (khong day manh "
            "sang ngang de tranh gay truc O5).",
        ],
    }
    man_path = MOTOR_DEMO_DIR / "manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print("Wrote", man_path)


def main() -> None:
    for old in OUT.glob("*.stl"):
        old.unlink()
    man_path = OUT / "manifest.json"
    if man_path.exists():
        man_path.unlink()

    parts = build_parts()
    missing = [n for n in PRINT_PARTS if n not in parts]
    if missing:
        raise SystemExit(f"Missing parts: {missing}")

    bedded: list[tuple[str, Part.Shape]] = []
    files = []
    for name in PRINT_PARTS:
        sh = _to_bed(_apply_rotation(name, parts[name]))
        bedded.append((name, sh))
        path = OUT / f"{name}.stl"
        shape_to_stl(sh, path)
        info = _bbox_info(sh)
        files.append({"name": name, "file": path.name, "bbox": info})
        print(f"  OK {path.name}  {info['size_mm']} mm")

    plate = layout_on_plate(bedded)
    plate_path = OUT / "byj_rack_print_plate.stl"
    shape_to_stl(plate, plate_path)
    plate_bb = _bbox_info(plate)
    print(f"  OK {plate_path.name}  plate {plate_bb['size_mm']} mm")

    export_motor_print_in_place(parts)

    manifest = {
        "model": "byj_rack_stage",
        "print_parts": list(PRINT_PARTS),
        "buy_parts": [
            "BYJ_Motor (28BYJ-48 12V)",
            "Limit_Switch_Min (KW11)",
            "Screws M2/M3 as BOM in byj_rack_stage.py "
            "(gom 2 vit tu ren M3 DAI >= 14mm rieng cho Guide_Rod_Cap_A/B — "
            "dai hon vit thuong vi phai xuyen nap+vach roi ren vao than thanh)",
        ],
        "cura": {
            "recommended": "Open byj_rack_print_plate.stl (1 plate, 1 slice)",
            "or": ("Open Housing.stl + Housing_Lid.stl + Pinion.stl + Slide_Bar.stl "
                   "+ Guide_Rod_A.stl x2 + Guide_Rod_Cap_A.stl x2 (moi file in 2 lan, "
                   "khong can Guide_Rod_B.stl / Guide_Rod_Cap_B.stl — giong het A)"),
            "notes": [
                "TAT CA cac file duoi day da o DUNG huong in san (xoay san trong STL "
                "neu can) -- mo Cura la in duoc luon, KHONG xoay lai (xoay lai co the "
                "bien mot huong 0-overhang thanh huong co overhang, xem PRINT_ROTATIONS "
                "trong export_byj_rack_print.py va soat de-in 2026-09-06).",
                "Housing: day hop dat ban (Z=0), khong can support. 1 diem can luu y: "
                "be cong tac rong ruot co 1 'noc' day 4mm bac qua khoang rong ~14.5x22mm "
                "(4 canh co thanh do tru) -- van in duoc khong can support nhung nen bat "
                "quat lam mat 100% ngay truoc doan do.",
                "Housing_Lid: mat nap dat ban, khong can support",
                "Pinion: LIEN KHOI rang + tru/ban cau O10 (khong moay-o duoi) — "
                "rang nam ban, cau huong len; Support OFF.",
                "Slide_Bar: dat nguyen tu the (chan +Y/-Y xuong ban), cau noi tren dinh "
                "la NHIP CAU ~19 mm giua 2 chan (khong phai conson) — bat quat 100%, "
                "PETG bam ban tot la in duoc, KHONG can bat support (bat support PETG "
                "rat kho go vi PETG dinh chinh no)",
                "Guide_Rod_A/B: tron O5 day phang, da nam san mat phang xuong ban "
                "(ZMin=0 tu export), KHONG xoay lai trong Cura — xoay se mat day phang "
                "va chi cham ban theo 1 duong tiep tuyen, de bong lop dau",
                "Guide_Rod_Cap_A/B: DA XOAY -90 do so voi lap rap -- nam phang mat "
                "9.6x9.6mm xuong ban (cao 3mm), 2 lo (than vit + hoc chim mu vit) "
                "thanh DUNG (moi lop la 1 vanh tron day du, khong can support). Vit "
                "xuyen QUA CHINH GIUA nap, qua vach, roi bat THANG vao lo moi khoan "
                "san o dau thanh (M3, dai >= 14mm, vd M3x16) — THAO DUOC (thao vit la "
                "rut thanh ra lai). Khong co no thi thanh dan huong khong bi khoa, se "
                "xo lech doc truc khi may chay lau (lap rap buoc 6 trong byj_rack_stage.py).",
                "Gap giua part tren plate: 8 mm",
            ],
        },
        "files": files,
        "plate": {"file": plate_path.name, "bbox": plate_bb},
        "gap_mm": GAP_MM,
    }
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Wrote", man_path)
    print("DONE — Cura: mo", plate_path)


main()
