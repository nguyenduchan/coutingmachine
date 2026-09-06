#!/usr/bin/env python3
"""Tách BYJ_Motor (body) / BYJ_Motor_Shaft (truc) tu file tham chieu that
28BYJ-48_original.FCStd (nguoi dung tai ve, luu ban sao khong doi trong
reference/) — file goc la 1 KHOI DUY NHAT (than + go O9.1 + truc O5 + doan vat
deu FUSE cung, khong quay duoc, khong co co cau giu truc).

Ky thuat AP DUNG Y HET nhu byj_rack_stage.py (lan 22/24, xem memory du an):
  - Khoang giu (chamber) + go giu (flange) ROM RONG hon lo truc tron phia tren
    -> truc khong tuot len duoc.
  - Khe ho duong kinh 1.0mm quanh truc tron (Ø5) -- RONG HON 1 duong nhua
    (0.4mm nozzle pho thong), da CHUNG MINH THAT BAI o muc 0.6mm truoc do.
  - Go O9.1 goc CUA FILE duoc GIU LAI làm chi tiet THAN co dinh (chi khoet
    LOI O6.0 xuyen qua no) — khong bien go nay thanh 1 phan cua truc.

Cac moc Z do THAT tu file goc (freecadcmd slice(), xem hoi thoai):
  BODY_TOP=9.65  BOSS_D=9.1  BOSS_TOP=11.65  ROUND_D=5.0  FLAT_Z0=14.0
  FLAT_W=3.0  SHAFT_TOP=19.65  tam truc (CX,CY)=(0, 8.0)
"""
from pathlib import Path
import json
import math

import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
REF_FCSTD = HERE / "reference" / "28BYJ-48_original.FCStd"
OUT_FCSTD = HERE / "out" / "28byj48_reference_split.FCStd"
OUT_DIR = HERE / "out" / "byj_motor_print_in_place"

# --- so do that (Z, D) do tu file goc ---
BODY_TOP = 9.65
BOSS_D = 9.1
BOSS_TOP = 11.65
ROUND_D = 5.0
FLAT_Z0 = 14.0
FLAT_W = 3.0
SHAFT_TOP = 19.65
CX, CY = 0.0, 8.0

# --- go giu truc (retention flange), giong ky thuat lan 22 ---
RET_D = 7.0
RET_H = 1.5
RET_CLR = 1.0                       # khe ho duong kinh quanh go giu
RET_BORE_D = RET_D + RET_CLR        # 8.0
RET_TOP_CLR = 0.4                   # ho phia tren go, khong cham tran khoang
RET_BURY = 3.0                      # go cach mat than bao xa (xuong duoi)
CHAMBER_Z0 = BODY_TOP - RET_BURY    # 6.65  day khoang

# 2026-09-06 (lan 26): TRUOC DAY go giu TUA THANG len day khoang (witness layer,
# distToShape=0 -- da kiem chung THAT bang script, xem hoi thoai) -- rui ro dinh
# CHAT that (giong bai hoc khe ho 0.6mm o lan 22). Nguoi dung yeu cau: KHONG duoc co
# diem cham nao giua than/truc, thay bang cac SOI TO MANH (strut) rieng, de gay khi
# xoay. NANG go giu len, cach day khoang 1 khe ho FLOOR_GAP (khong cham).
FLOOR_GAP = 0.3                     # khe ho DUOI go giu -- KHONG cham day khoang nua
CHAMBER_H = FLOOR_GAP + RET_H + RET_TOP_CLR    # 2.2
CHAMBER_Z1 = CHAMBER_Z0 + CHAMBER_H            # 8.85
FLANGE_Z0 = CHAMBER_Z0 + FLOOR_GAP             # 6.95  day go giu (LO LUNG, khong cham)

NECK_CLR = 1.0                      # khe ho duong kinh quanh truc tron O5
NECK_D = ROUND_D + NECK_CLR         # 6.0  (long hon O9.1 cua go -> go GIU duoc)
NECK_Z0 = CHAMBER_Z1                # 8.85
NECK_Z1 = SHAFT_TOP + 0.5           # 20.15  xuyen het doan truc cu (ca doan vat)

assert RET_D > NECK_D, "go giu phai to hon lo truc tron phia tren, neu khong se tuot"

# 2026-09-06 (lan 29): NGUOI DUNG dung Ender-3 Pro (may pho thong, KHONG tan nhiet
# tot) -- xac nhan lai: du tang soi ring o RIA (lan 28) den may cung KHONG giai quyet
# duoc gioi han hinh hoc that -- TAM dia go giu LUON cach moi soi ring toi thieu ban
# kinh RET_D/2=3.5mm (them soi quanh RIA chi giam khe CUNG giua 2 soi, khong giam
# duoc khoang cach BAN KINH toi tam). Ender-3 Pro pho thong khong du tin cay bac cau
# ~3.5mm o LOP DAU TIEN (khac voi cau noi 2 tuong da co san, day la "noi khong" hoan
# toan). Fix: them 1 CHOT TAM nho, noi THANG tu day khoang len day go giu -- dien
# tich tiep xuc CUC NHO (~0.3mm2, so voi 38.5mm2 ca dia truoc do o lan 25) nen van de
# be nhu soi to, nhung giai quyet dung gioi han hinh hoc (tam gio chi con cach chot
# ~1.75mm thay vi 3.5mm toi bat ky diem do nao).
CENTER_PIN_D = 0.6                  # duong kinh chot tam -- ~1 duong nhua, de be
CENTER_PIN_Z0 = CHAMBER_Z0          # 6.65  day khoang (than)
CENTER_PIN_Z1 = FLANGE_Z0           # 6.95  day go giu (truc) -- cao dung bang FLOOR_GAP

# --- SOI TO MANH (strut) noi than <-> truc, de gay khi xoay ---
# 3 TANG, moi tang bam vao dung cho CON vat lieu than THAT gan truc nhat (chi 3 vung
# nay co vat lieu than sat truc — tren dinh go O9.1 (z>11.65) la khong khi, KHONG the
# them tang nao nua o do du muon vi khong co gi de bam):
#   (1) quanh go giu, trong khoang            z 6.95-8.45  r 3.5-4.0
#   (2) trong than chinh, ngay TREN khoang     z 8.85-9.65  r 2.5-3.0
#   (3) trong go O9.1 goc, gan dinh            z 10.65-11.65 r 2.5-3.0
# Doan truc TRON con lai (11.65-14.0) va doan VAT (14.0-19.65, dau truc) tu no da la 1
# cot TRU LIEN TUC cua chinh no (khong phai khoang ho roi) -- moi lop chi can in de len
# lop truoc CUNG mot vat the, KHONG can them soi to o do (khong co than de bam vao nua).
# 2026-09-06 (lan 27): giam goc cung (STRUT_ANGLE) 8->4 do (mong lai ~1 nua).
# 2026-09-06 (lan 28): NGUOI DUNG hoi dung "day truc lo lung nhu vay co in duoc
# khong" -- CAU HOI DUNG, phat hien 1 LO HONG THIET KE THAT: go giu la 1 DIA DAC
# O7.0 (dien tich ~38.5mm2) lo lung hoan toan (khong cham day khoang, xem lan 26),
# ma tang (1) truoc chi co 4 soi CACH NHAU 86 do -- quy doi ra CUNG ho ~5.6mm giua 2
# soi lien tiep, TAM DIA cach moi soi toi 3.5mm -- QUA RONG de lop in DAU TIEN cua 1
# dia dac bac cau an toan (dia se vong/xe khi in, hoac tho ep xuong cham luon day
# khoang -- dung cai ma FLOOR_GAP dinh tranh). Khac voi tang (2)/(3): 2 tang do CHI
# gia co them cho 1 TRU TRON DA LIEN TUC tu duoi len (round_full la 1 khoi duy nhat
# tu FLANGE_Z0), nen 4 soi la du (khong phai bac cau 1 mat dac, chi la neo them).
# CHI RIENG tang (1) -- noi CO mat dac can bac cau that -- duoc tang so soi MANH len
# nhieu de khe ho giua 2 soi lien tiep dau con < ~2mm (an toan de bac cau/in duoc).
STRUT_ANGLE = 4.0                   # do rong CUNG (goc, do) moi soi
STRUT_N_FLANGE = 10                 # tang (1) -- can bac cau 1 DIA DAC, khe ho con
                                    # ~2.1mm (xem tinh toan trong hoi thoai)
# 2026-09-06 (lan 31): NGUOI DUNG yeu cau giam CHIEU CAO soi cho DE BE hon. Truoc day
# soi cao SUOT ca chieu cao go giu (RET_H=1.5mm) -- tiet dien can be (khi xoay) ti le
# thuan voi chieu cao nay, cao = kho be hon. Giam con STRUT_HEIGHT=0.4mm (~2 lop 0.2mm)
# -- van du de dinh chac lop DAU TIEN cua dia (noi can bac cau nhat) nhung tiet dien
# can be giam ~3.75 lan so voi ban day 1.5mm -- de gay hon nhieu khi xoay. Dat o DAY go
# giu (FLANGE_Z0) vi do la vung can do lop dau tien nhat, khong can cao het go giu.
STRUT_HEIGHT = 0.4                  # cao soi (Z) -- giam tu 1.5mm (het go giu) xuong,
                                    # de be hon khi xoay
# 2026-09-06 (lan 30): NGUOI DUNG yeu cau CHI giu soi o go giu (hinh tru DAY, trong
# khoang) -- XOA soi o 2 tang quanh doan TRUC NHO hon (than_chinh, go O9.1). 2 tang do
# von chi la GIA CO THEM cho doan truc tron (khong bac cau mat dac, xem giai thich o
# tren) nen bo di KHONG anh huong kha nang in duoc -- chi mat di 1 it do vung chac
# chong lech/rung khi in doan truc cao phia tren, chap nhan duoc theo yeu cau.
_RINGS = [
    # (ten, r0, r1, z0, z1, so_soi)
    ("chamber", RET_D / 2.0, RET_BORE_D / 2.0, FLANGE_Z0, FLANGE_Z0 + STRUT_HEIGHT,
     STRUT_N_FLANGE),
]
TOTAL_STRUTS = sum(n for *_rest, n in _RINGS)


def _cyl(d: float, h: float, cx: float, cy: float, z0: float) -> Part.Shape:
    return Part.makeCylinder(d / 2.0, h, App.Vector(cx, cy, z0), App.Vector(0, 0, 1))


def _wedge_ring(r0: float, r1: float, h: float, z0: float, angle_deg: float,
                n: int, cx: float, cy: float) -> Part.Shape:
    """n mieng VANH KHUYEN GOC (pie-slice annulus) tu ban kinh r0 den r1, cao h, cach
    deu quanh tam (cx,cy) -- moi mieng rong angle_deg do. QUAN TRONG: dung CUNG TRON
    that (Part.makeCylinder co angle) chu KHONG dung box phang -- box co 2 mat DAU
    PHANG chi tiep xuc mat tru CONG theo 1 DUONG (khong phai 1 MAT), khien fuse() sau
    do KHONG gop duoc thanh 1 khoi lien thong (da gap loi nay khi thu box, xem hoi
    thoai) -- vanh khuyen goc co ca 2 mat DAU deu la mat tru CONG, khop THAT voi mat
    tru cua go/truc/vach ben canh -> fuse() gop dung thanh 1 khoi."""
    outer = Part.makeCylinder(r1, h, App.Vector(0, 0, z0), App.Vector(0, 0, 1), angle_deg)
    inner = Part.makeCylinder(r0, h, App.Vector(0, 0, z0), App.Vector(0, 0, 1), angle_deg)
    one = outer.cut(inner)
    one.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), -angle_deg / 2.0)
    parts = []
    for i in range(n):
        s = one.copy()
        s.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360.0 * i / n)
        s.translate(App.Vector(cx, cy, 0))
        parts.append(s)
    out = parts[0]
    for p in parts[1:]:
        out = out.fuse(p)
    return out


def _strut_pair(r0: float, r1: float, angle_deg: float, z0: float, z1: float,
                n: int, cx: float, cy: float) -> tuple[Part.Shape, Part.Shape]:
    """Chia soi to lam 2 NUA tai ban kinh giua (rmid): nua trong (r0..rmid) thuoc VE
    TRUC, nua ngoai (rmid..r1) thuoc VE THAN — 2 nua CHAM NHAU dung 1 MAT TRU CONG
    tai rmid (giong 1 "witness layer" nhung TIET DIEN RAT NHO, khong phai ca mat
    phang go/khoang nhu truoc)."""
    rmid = 0.5 * (r0 + r1)
    shaft_half = _wedge_ring(r0, rmid, z1 - z0, z0, angle_deg, n, cx, cy)
    body_half = _wedge_ring(rmid, r1, z1 - z0, z0, angle_deg, n, cx, cy)
    return shaft_half, body_half


def build() -> tuple[Part.Shape, Part.Shape]:
    doc = App.openDocument(str(REF_FCSTD))
    src = doc.getObject("Fillet001").Shape.copy()

    chamber = _cyl(RET_BORE_D, CHAMBER_H, CX, CY, CHAMBER_Z0)
    neck = _cyl(NECK_D, NECK_Z1 - NECK_Z0, CX, CY, NECK_Z0)
    remove_tool = chamber.fuse(neck)
    body = src.cut(remove_tool)
    body = body.removeSplitter()
    if not body.isValid():
        raise RuntimeError("body shape KHONG hop le sau khi cat")

    flange = _cyl(RET_D, RET_H, CX, CY, FLANGE_Z0)
    round_full = _cyl(ROUND_D, FLAT_Z0 - FLANGE_Z0, CX, CY, FLANGE_Z0)
    flat_h = SHAFT_TOP - FLAT_Z0
    flat_cyl = _cyl(ROUND_D, flat_h + 0.5, CX, CY, FLAT_Z0 - 0.5)
    flat_box = Part.makeBox(FLAT_W, 2.0 * ROUND_D, flat_h + 1.0,
                            App.Vector(CX - FLAT_W / 2.0, CY - ROUND_D, FLAT_Z0 - 0.5))
    flat_shape = flat_cyl.common(flat_box)
    center_pin = _cyl(CENTER_PIN_D, CENTER_PIN_Z1 - CENTER_PIN_Z0, CX, CY, CENTER_PIN_Z0)
    shaft = flange.fuse(round_full).fuse(flat_shape).fuse(center_pin)

    # soi to mang: chia doi tai ban kinh giua -- nua trong fuse vao TRUC, nua ngoai
    # fuse vao THAN, 2 nua cham nhau dung 1 mat tru cong mong (xem _strut_pair) — lap
    # qua tung tang trong _RINGS (3 tang, xem dinh nghia o tren)
    shaft_halves = []
    body_halves = []
    for _name, r0, r1, z0, z1, n in _RINGS:
        sh, bo = _strut_pair(r0, r1, STRUT_ANGLE, z0, z1, n, CX, CY)
        shaft_halves.append(sh)
        body_halves.append(bo)
    struts_shaft_side = shaft_halves[0]
    for s in shaft_halves[1:]:
        struts_shaft_side = struts_shaft_side.fuse(s)
    struts_body_side = body_halves[0]
    for s in body_halves[1:]:
        struts_body_side = struts_body_side.fuse(s)
    shaft = shaft.fuse(struts_shaft_side).removeSplitter()
    body = body.fuse(struts_body_side).removeSplitter()
    if not shaft.isValid():
        raise RuntimeError("shaft shape KHONG hop le")
    if not body.isValid():
        raise RuntimeError("body shape (sau khi fuse strut) KHONG hop le")

    # kiem tra: KHONG con diem cham nao NGOAI vung lien ket du kien (soi to + chot tam)
    struts_all = struts_shaft_side.fuse(struts_body_side)
    connectors_all = struts_all.fuse(center_pin)
    shaft_bare = shaft.cut(connectors_all)
    body_bare = body.cut(connectors_all)
    d_no_strut = shaft_bare.distToShape(body_bare)[0]
    if d_no_strut < 0.1:
        raise RuntimeError("than/truc (KHONG tinh soi to/chot tam) van cham/qua sat: "
                           "%.3f mm" % d_no_strut)
    print("Khe ho THAT giua than/truc, KHONG tinh soi to/chot tam:",
         round(d_no_strut, 3), "mm")

    # kiem tra: soi to THAT SU noi lien than va truc (khong roi rac) — hop nhat toan
    # bo (than+truc, ca 2 da fuse nua soi to cua minh) phai la 1 KHOI LIEN THONG
    whole = body.fuse(shaft)
    n_solids = len(whole.Solids)
    if n_solids != 1:
        raise RuntimeError("than+truc KHONG lien thanh 1 khoi qua soi to (ra %d khoi) "
                           "-- soi to khong thuc su bam vao ca 2 ben" % n_solids)
    print("The tich soi to (%d tang, %d soi):" % (len(_RINGS), TOTAL_STRUTS),
         round(struts_all.Volume, 4), "mm3")
    print("Than+truc qua soi to: 1 khoi lien thong (dung nhu ky vong)")

    doc_out = App.newDocument("28byj48_reference_split")
    o_body = doc_out.addObject("Part::Feature", "BYJ_Motor_Ref")
    o_body.Shape = body
    o_shaft = doc_out.addObject("Part::Feature", "BYJ_Motor_Shaft_Ref")
    o_shaft.Shape = shaft
    doc_out.recompute()
    OUT_FCSTD.parent.mkdir(parents=True, exist_ok=True)
    doc_out.saveAs(str(OUT_FCSTD))
    print("Saved", OUT_FCSTD)

    App.closeDocument(doc.Name)
    return body, shaft


def export_stl(body: Part.Shape, shaft: Part.Shape) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    compound = Part.makeCompound([body, shaft])
    path = OUT_DIR / "BYJ_Motor_PrintInPlace_v2_reference.stl"
    compound.exportStl(str(path))
    bb = compound.BoundBox
    print("Wrote", path, "bbox size",
         [round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2)])

    manifest = {
        "model": "28BYJ-48 - split tu file tham chieu THAT (nguoi dung tai ve)",
        "source": "reference/28BYJ-48_original.FCStd (ban sao, khong sua file goc)",
        "note": ("Chinh xac hon ban parametric tu truoc (byj_rack_stage.py) vi "
                "dung dung hinh hoc that: go O9.1, doan tron O5 dai 4.35mm, doan "
                "vat rong 3mm dai 5.65mm o dau truc — do THAT bang cach cat lat "
                "(slice) file goc theo Z, khong doan tu ban ve 2D."),
        "bbox_mm": [round(compound.BoundBox.XLength, 2),
                   round(compound.BoundBox.YLength, 2),
                   round(compound.BoundBox.ZLength, 2)],
        "clearance_diam_mm": NECK_CLR,
        "retention_flange_diam_mm": RET_D,
        "retention_chamber_diam_mm": RET_BORE_D,
        "note_2026_09_06_lan29": (
            "May in la Ender-3 Pro (pho thong, khong tan nhiet dac biet) -- nguoi dung "
            "xac nhan KHONG the in day nhua lo lung khoang cach dai. Gioi han hinh hoc "
            "that: du them bao nhieu soi QUANH RIA go giu, TAM dia (O7.0) VAN cach "
            "moi soi toi thieu %.1fmm (ban kinh) -- them soi RIA chi giam khe CUNG "
            "(tiep tuyen), KHONG giam duoc khoang cach BAN KINH toi tam. Da them 1 "
            "CHOT TAM O%.1fmm (`CENTER_PIN_D`), noi THANG day khoang (than) len day "
            "go giu (truc) -- dien tich tiep xuc CUC NHO (~%.2fmm2, so voi 38.5mm2 "
            "neu ca dia cham nhu ban dau) nen van de be nhu soi to (chi 1 diem, xoay "
            "nhe la gay), nhung giai quyet dung: tam gio chi con cach diem do gan nhat "
            "(chot tam HOAC soi ria) toi da ~%.2fmm thay vi 3.5mm truoc do."
            % (RET_D / 2.0, CENTER_PIN_D, math.pi * (CENTER_PIN_D / 2.0) ** 2,
              RET_D / 2.0 / 2.0)
        ),
        "strut_count": TOTAL_STRUTS,
        "strut_count_flange_ring": STRUT_N_FLANGE,
        "strut_rings": len(_RINGS),
        "strut_angle_deg": STRUT_ANGLE,
        "center_pin_diam_mm": CENTER_PIN_D,
        "print_settings": [
            "Layer height 0.2mm",
            "Quat lam mat 100% tu lop dau -- QUAN TRONG voi soi to/chot: nguoi lam "
            "mat sai lop dau se lam chung qua deo, kho gay dut gon",
            "Flow/Extrusion 95-98%",
            "QUAN TRONG -- Horizontal Expansion = -0.1mm (vach ngoai in nho lai)",
            "QUAN TRONG -- Hole Horizontal Expansion = +0.1mm (lo tron in to ra) "
            "-- 2 setting khac nhau, bat CA HAI (Cura: Special Modes, can bat "
            "Expert/Show All Settings)",
            "Toc do in RAT CHAM (~15-20mm/s) rieng vung go giu (Z 6.65-8.45, gom ca "
            "chot tam va lop dau tien cua dia bac cau qua soi+chot) -- day la vung "
            "RUI RO NHAT tren Ender-3 Pro. Tu Z 8.45 tro len (doan truc tron + doan "
            "vat) la 1 cot tru LIEN TUC tu no, khong con soi to gia co (theo yeu cau "
            "lan 30, bo soi o 2 tang tren) -- toc do binh thuong la du vi khong con "
            "bac cau, chi la in 1 tru dac tu duoi len",
        ],
        "after_print": [
            "CAM DOAN TRUC (dinh vat, tho tren dinh go O9.1), XOAY QUA LAI vai lan -- "
            "%d soi to se GAY GON (tiet dien nho), truc roi ra quay tu do NGAY, "
            "KHONG can cho nguoi/dung dao nhu kieu witness-layer truoc do." % TOTAL_STRUTS,
            "Go giu O%.1fmm o day truc to hon lo tron O%.1fmm phia tren -- du gay het "
            "soi to, truc VAN KHONG tuot len duoc." % (RET_D, NECK_D),
            "Neu soi chua gay het: xoay tiep + keo nhe doc truc (khong day manh sang "
            "ngang de tranh gay truc O5).",
            "SAU KHI IN: soi vao (qua khe O9) kiem tra ky lop DAU TIEN cua go giu -- "
            "neu thay vong/xe/thieu nhua o giua, co the can tang them so soi hoac "
            "giam FLOOR_GAP trong lan chinh sau.",
        ],
    }
    man_path = OUT_DIR / "manifest_v2_reference.json"
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print("Wrote", man_path)


b, s = build()
export_stl(b, s)
print("DONE")
