"""
Mo phong dia quay (Rotor_Disc) va vien thuoc RIGID BODY nam tren do — PyBullet GUI.

Khac voi tube_l_egress_pybullet.py (script "trial" dung heuristic ap dat
van toc vien thuoc de kiem tra egress), o day vien thuoc la rigid body
THUAN VAT LY: chi chiu trong luc + ma sat tiep xuc voi dia dang quay,
khong co lenh ap dat van toc nao len vien thuoc (ngoai van toc tiep tuyen
KHOI TAO, xem spawn loop trong main() — can de khop dieu kien "theta_dot=omega
ngay tu dau" cua mo hinh phan tich, tranh transient truot-tu-0 phi thuc te).

Dia (Rotor_Disc) duoc dan dong kieu "kinematic" (mass=0, nhung moi step
gan lai orientation + angularVelocity) — day la cach chuan trong PyBullet
de lam mot "ban xoay" (turntable) keo vat khac bang ma sat tiep xuc.
Rotor_Disc dung THANG mesh STL cho collision (mat tren phang, khong co
seam — on dinh tot trong thu nghiem).

QUAN TRONG — tuong/mang KHONG dung mesh STL cho collision:
Thu nghiem cho thay mesh STL concave export tu CAD tai vung noi Bowl_Tube/
Guide_System/Inner_Lane_Rail/Exit_Track (dung sai thiet ke ~1mm) qua chat
de PyBullet giai va cham rieng roi on dinh — vien thuoc co the "lot san"
hoac "bay qua tuong" dung tai diem noi nay (da thu CCD, tang substep, sphere
collision, san an toan day, van toc clamp — giam duoc loi nhung KHONG triet
tieu). Vi yeu cau "khong duoc xuyen qua component", tuong + mang duoc XAY LAI
bang box/cylinder PRIMITIVE (build_bowl_ring/build_exit_chute), dung dung
tham so hinh hoc thuc cua co cau (BOWL_IR/OR, GAP0, THETA_EXIT, EXIT_TRACK_LEN
— lay tu tube_l_egress_pybullet.py, da doi chieu khop voi manifest.json export).
STL cua cac phan nay chi dung de HIEN THI (collision=-1), khong anh huong vat ly.

Chay:
  python 3d_model/sim/tube_l_disc_rigid_body_pybullet.py
  python 3d_model/sim/tube_l_disc_rigid_body_pybullet.py --rpm 40 --n_pills 12 --D 8 --T 4

Dong cua so GUI de dung mo phong.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import pybullet as p
import pybullet_data

ROOT = Path(__file__).resolve().parent
MESH_DIR = ROOT / "meshes" / "tube_l_exit"
OUT = ROOT / "out"
OUT.mkdir(parents=True, exist_ok=True)
METRICS = OUT / "tube_l_disc_rigid_body_metrics.json"

S = 0.001  # mm -> m
G = -9.81
DT = 1.0 / 240.0

# Tham so hinh hoc thuc (mm, toa do global giong FreeCAD) — doi chieu khop voi
# manifest.json export (Bowl_Tube z:[0,40], Exit_Track y:[-159.8,2.0]).
BOWL_IR = 100.8
BOWL_OR = 104.8
BOWL_H = 40.0
GAP0 = 0.5
THETA_EXIT = 180.0
EXIT_GAP_HALF_DEG = 14.0  # khe ho tren vanh Bowl_Tube quanh THETA_EXIT (nguon: tube_l_egress_pybullet.py)
EXIT_WALL_T = 2.5
EXIT_TRACK_LEN = BOWL_OR + 55.0  # ~159.8mm, khop Exit_Track ymin=-159.8 trong manifest
EXIT_HOLE_LEN = 20.0  # mm — "cua khoet lo" cuoi mang: doan cuoi KHONG co san, vien roi ra ngoai qua day

EXIT_Y_DONE = -(EXIT_TRACK_LEN - EXIT_HOLE_LEN) - 1.0  # vien "thoat" ngay khi qua het san, truoc khi roi tu do
FLOOR_FAIL_Z = -30.0  # mm — vien roi thap hon muc nay = lot qua khe (bug — khong duoc xay ra)
ESCAPE_FAIL_R = 130.0  # mm — vien vuot ban kinh nay ma van cao tren mep = thoat sai (bug)
VMAX_MPS = 0.6  # m/s — chan van toc: toc do tiep tuyen lon nhat ky vong ~omega*R_disc ~0.42 m/s luc 40rpm
CHUTE_ASSIST_MPS2 = 4.5  # m/s^2 — luc day doc kenh (-Y), bu dong luong mat do va cham
# goc/canh khi chuyen tu dia quay (dong) sang san mang tinh (tinh) trong mo phong don gian
# hoa nay; trong thiet ke thuc, vien tu di het mang bang chinh dong luong tiep tuyen mang
# theo (s_dot = omega*r*(sinB-mu*cosB), xem memory du an) — mo phong rigid-body don gian
# (khong dung do doc/mo hinh 1D rieng cho mang) can luc ho tro nay de khong bi "ket" o goc.
# Phat hien thuc nghiem: gia tri cu 0.35 qua yeu so voi giam toc ma sat san mu*g~2.45 m/s^2
# (mu=0.25) — ma sat trien tieu het assist trong cung 1 step, vien dung lai giua mang vinh
# vien, khong bao gio toi duoc "cua khoet lo" cuoi mang. 4.5 > 2.45 de thuc su thang duoc ma sat.

# Cac phan trong suot mot phan (vo/mang bao quanh) — de nhin xuyen thay vien ben trong.
# Phan con lai (Width_Carriage, Inner_Lane_Rail, Height_Scraper, screw, spring...)
# hien thi DAC (alpha=1) dung mau FreeCAD, giong het model trong manifest.json["colors"].
TRANSLUCENT_PARTS = {"Bowl_Tube": 0.35, "Guide_System": 0.35, "Exit_Track": 0.5}
DISC_TEXTURE_PATH = MESH_DIR / "_disc_texture.png"


def gap_wh(D: float, T: float) -> tuple[float, float]:
    return D + 1.0, T + 1.0  # Exit_Track W x H = pill + 1mm (dung thiet ke)


def make_world(gui: bool) -> int:
    cid = p.connect(p.GUI if gui else p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=cid)
    p.setGravity(0, 0, G, physicsClientId=cid)
    p.setTimeStep(DT, physicsClientId=cid)
    p.setPhysicsEngineParameter(numSolverIterations=200, numSubSteps=4, physicsClientId=cid)
    if gui:
        p.resetDebugVisualizerCamera(0.35, 50, -35, [0, 0, 0], physicsClientId=cid)
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0, physicsClientId=cid)
    return cid


def load_visual_only(cid: int, name: str, rgba) -> None:
    """Nap STL CHI de hien thi — khong co collision shape (an toan tuyet doi, khong
    the gay tunneling vi don gian khong tham gia va cham)."""
    stl = MESH_DIR / f"{name}.stl"
    if not stl.exists():
        return
    vis = p.createVisualShape(
        p.GEOM_MESH, fileName=str(stl), meshScale=[S, S, S], rgbaColor=list(rgba), physicsClientId=cid
    )
    p.createMultiBody(0, -1, vis, [0, 0, 0], physicsClientId=cid)


def load_all_visual_parts_from_manifest(cid: int) -> None:
    """Nap TAT CA cac phan trong manifest.json (tru Rotor_Disc — co collision rieng)
    CHI de hien thi, dung dung mau FreeCAD (manifest["colors"]) — dam bao model 3D
    trong mo phong vat ly giong het model trong FreeCAD (bao gom Crossbar_Bridge,
    Scale_Width/Height, Width_Carriage, cac vit/lo xo — truoc day chi export 6/19
    phan chinh). Chay lai export_tube_l_meshes.py neu manifest chua co du phan nay."""
    manifest_path = MESH_DIR / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    colors = manifest.get("colors", {})
    for name in manifest.get("parts", {}):
        if name == "Rotor_Disc":
            continue
        rgb = colors.get(name, [0.6, 0.6, 0.6])
        alpha = TRANSLUCENT_PARTS.get(name, 1.0)
        load_visual_only(cid, name, list(rgb) + [alpha])


def load_disc_mesh(cid: int) -> int:
    stl = MESH_DIR / "Rotor_Disc.stl"
    col = p.createCollisionShape(p.GEOM_MESH, fileName=str(stl), meshScale=[S, S, S], physicsClientId=cid)
    vis = p.createVisualShape(
        p.GEOM_MESH, fileName=str(stl), meshScale=[S, S, S], rgbaColor=[0.22, 0.22, 0.24, 1.0], physicsClientId=cid
    )
    body = p.createMultiBody(0, col, vis, [0, 0, 0], physicsClientId=cid)
    p.changeDynamics(body, -1, lateralFriction=0.9, restitution=0.0, physicsClientId=cid)
    return body


def make_disc_texture_image() -> Path:
    """Sinh anh texture dang "kim dong ho" (16 mieng banh mau xen ke + 1 vach do dam
    tu tam ra vien) — dan len mat dia de mat thay ro toc do/huong quay khi dia xoay.
    Cache lai file, chi sinh lai neu chua co."""
    if DISC_TEXTURE_PATH.exists():
        return DISC_TEXTURE_PATH
    from PIL import Image, ImageDraw

    size = 512
    img = Image.new("RGB", (size, size), (60, 60, 66))
    draw = ImageDraw.Draw(img)
    cx = cy = size / 2
    r = size / 2 - 2
    n = 16
    for i in range(n):
        a0 = 360.0 * i / n
        a1 = 360.0 * (i + 1) / n
        col = (200, 200, 210) if i % 2 == 0 else (90, 90, 100)
        draw.pieslice([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=col)
    for rr in (r * 0.35, r * 0.65, r * 0.95):
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(30, 30, 34), width=2)
    # 1 vach do dam tu tam ra vien — moc tham chieu de mat de bam theo, thay ro 1 vong quay.
    draw.pieslice([cx - r, cy - r, cx + r, cy + r], -6, 6, fill=(220, 40, 40))
    img.save(DISC_TEXTURE_PATH)
    return DISC_TEXTURE_PATH


def add_disc_texture_overlay(cid: int, radius_mm: float) -> int:
    """Lop phu mong (khong va cham) nam dung tren mat dia, dan texture kim-dong-ho
    de thay ro toc do quay bang mat. Dia (Rotor_Disc) va lop phu nay duoc teleport
    dong bo moi step trong main() (cung 1 theta) nen luon dinh cung dia."""
    tex_path = make_disc_texture_image()
    vis = p.createVisualShape(
        p.GEOM_CYLINDER, radius=radius_mm * S, length=0.6 * S, rgbaColor=[1, 1, 1, 1], physicsClientId=cid
    )
    body = p.createMultiBody(0, -1, vis, [0, 0, 0.35 * S], physicsClientId=cid)
    tex_id = p.loadTexture(str(tex_path), physicsClientId=cid)
    p.changeVisualShape(body, -1, textureUniqueId=tex_id, physicsClientId=cid)
    return body


def _box_collision(cid: int, hx: float, hy: float, hz: float, pos_mm, friction: float) -> int:
    col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[hx * S, hy * S, hz * S], physicsClientId=cid)
    body = p.createMultiBody(0, col, -1, [pos_mm[0] * S, pos_mm[1] * S, pos_mm[2] * S], physicsClientId=cid)
    p.changeDynamics(body, -1, lateralFriction=friction, restitution=0.0, physicsClientId=cid)
    return body


def build_permanent_safety_net(cid: int) -> None:
    """Luoi an toan CO DINH (khong bao gio bi xoa/xay lai) — dat THAP HON san mang
    binh thuong (z=0..0.5mm) mot chut, phu rong het pham vi W_MIN..W_MAX co the co.

    Ly do can: "Apply lane W/H" (main()) xoa cac body san/vach CU roi tao moi o vi
    tri khac (r_a = BOWL_IR - W/2 doi theo W) — neu dung luc do co vien dang nam
    trong mang cu, no bi "hut chan" vi san moi khong con o cho cu. Luoi nay dam
    bao luon co gi do do o duoi, bat vien lai truoc khi roi qua FLOOR_FAIL_Z.
    Phat hien thuc nghiem qua stress test (them vien + doi W/H lien tuc)."""
    fcol = p.createCollisionShape(p.GEOM_CYLINDER, radius=112.0 * S, height=6.0 * S, physicsClientId=cid)
    floor_disc = p.createMultiBody(0, fcol, -1, [0, 0, -3.5 * S], physicsClientId=cid)
    p.changeDynamics(floor_disc, -1, lateralFriction=0.6, restitution=0.0, physicsClientId=cid)

    # Hanh lang mang: phu rong het cac r_a co the (W tu 2 den 26mm) + bien an toan.
    r_a_min = BOWL_IR - 0.5 * 26.0
    r_a_max = BOWL_IR - 0.5 * 2.0
    cx = -0.5 * (r_a_min + r_a_max)
    hw = 0.5 * (r_a_max - r_a_min) + 20.0
    bcol = p.createCollisionShape(
        p.GEOM_BOX, halfExtents=[hw * S, 0.5 * EXIT_TRACK_LEN * S, 3.0 * S], physicsClientId=cid
    )
    floor_lane = p.createMultiBody(
        0, bcol, -1, [cx * S, -0.5 * EXIT_TRACK_LEN * S, -3.5 * S], physicsClientId=cid
    )
    p.changeDynamics(floor_lane, -1, lateralFriction=0.4, restitution=0.0, physicsClientId=cid)


def build_bowl_ring(cid: int) -> None:
    """Vanh tuong ngoai Bowl_Tube (box ghep vong tron) — co khe ho +-EXIT_GAP_HALF_DEG
    quanh THETA_EXIT de vien thoat vao mang. Cung logic da kiem chung trong
    tube_l_egress_pybullet.py::build_disc_bowl (chi lay phan vanh, khong lay disc)."""
    n = 60
    rm = 0.5 * (BOWL_IR + BOWL_OR)
    hx = 0.5 * (BOWL_OR - BOWL_IR)
    hy = (math.pi * BOWL_IR / n) * 1.15
    hz = 0.5 * BOWL_H
    for i in range(n):
        a = 2.0 * math.pi * i / n
        adeg = math.degrees(a) % 360.0
        if abs(((adeg - THETA_EXIT + 180.0) % 360.0) - 180.0) < EXIT_GAP_HALF_DEG:
            continue
        cx = rm * math.cos(a)
        cy = rm * math.sin(a)
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[hx * S, hy * S, hz * S], physicsClientId=cid)
        body = p.createMultiBody(
            0, col, -1, [cx * S, cy * S, hz * S],
            baseOrientation=p.getQuaternionFromEuler([0, 0, a]), physicsClientId=cid,
        )
        p.changeDynamics(body, -1, lateralFriction=0.35, restitution=0.0, physicsClientId=cid)


def _wing_wall(cid: int, p1_mm, p2_mm, hz: float, friction: float) -> int:
    """Vach thang noi 2 diem (mm, tren mat phang z=hz*2 gia thiet chan tai z=0) — dung
    lam "canh dan" (funnel) noi mep khe ho vanh Bowl_Tube voi mieng mang, tranh de ho
    trong hoac goc nhon lam vien bi ket/vong qua (xem build_bowl_ring/build_exit_chute)."""
    dx = p2_mm[0] - p1_mm[0]
    dy = p2_mm[1] - p1_mm[1]
    length = math.hypot(dx, dy)
    yaw = math.atan2(dy, dx) - 0.5 * math.pi
    mx = 0.5 * (p1_mm[0] + p2_mm[0])
    my = 0.5 * (p1_mm[1] + p2_mm[1])
    col = p.createCollisionShape(
        p.GEOM_BOX, halfExtents=[EXIT_WALL_T * S, 0.5 * length * S, hz * S], physicsClientId=cid
    )
    body = p.createMultiBody(
        0, col, -1, [mx * S, my * S, hz * S],
        baseOrientation=p.getQuaternionFromEuler([0, 0, yaw]), physicsClientId=cid,
    )
    p.changeDynamics(body, -1, lateralFriction=friction, restitution=0.0, physicsClientId=cid)
    return body


def build_exit_chute(cid: int, W: float, H: float) -> tuple[float, list[int]]:
    """Mang thoat dang U-channel (2 vach ben + san) doc theo huong -Y, tam tai
    x=-(BOWL_IR-W/2) — cung tham so/logic voi tube_l_egress_pybullet.py::build_exit_chute.
    San mang CHI dai (EXIT_TRACK_LEN - EXIT_HOLE_LEN) — doan cuoi la "cua khoet lo":
    khong co san, vien di het mang se roi tu do qua do (ra khoi co cau), dung nhu
    thiet ke thuc ("cuoi mang xep hang don co 1 cua khoet lo de roi ra ngoai").
    Vach ben van chay het EXIT_TRACK_LEN de dan huong vien toi dung mieng lo.
    Tra ve (r_a, [body_id,...]) — r_a (mm) dung xac dinh vung "trong kenh" khi verify;
    danh sach id de main() co the p.removeBody() khi "Apply" W/H moi (UI dieu chinh mang)."""
    r_a = BOWL_IR - 0.5 * W
    hw = 0.5 * W
    t = EXIT_WALL_T
    hh = 0.5 * (H + 8.0)
    y_mid = -0.5 * EXIT_TRACK_LEN
    ids = []
    # 2 vach ben — chay het chieu dai mang toi mieng lo
    ids.append(_box_collision(cid, t, 0.5 * EXIT_TRACK_LEN, hh, [-r_a - hw - t, y_mid, GAP0 + hh], 0.35))
    ids.append(_box_collision(cid, t, 0.5 * EXIT_TRACK_LEN, hh, [-r_a + hw + t, y_mid, GAP0 + hh], 0.35))
    # san mang (mat tren = GAP0) — dung lai truoc EXIT_HOLE_LEN cuoi (cua khoet lo)
    floor_len = EXIT_TRACK_LEN - EXIT_HOLE_LEN
    floor_y_mid = -0.5 * floor_len
    ids.append(_box_collision(cid, hw + 0.5 * t, 0.5 * floor_len, 0.8, [-r_a, floor_y_mid, GAP0 - 0.8], 0.25))

    # "Canh dan" (funnel) noi mep khe ho tren vanh Bowl_Tube voi mieng mang — khong de
    # ho/goc nhon nao ma vien co the vong qua hoac bi ket (xem _wing_wall docstring).
    th_upper = math.radians(THETA_EXIT - EXIT_GAP_HALF_DEG)
    th_lower = math.radians(THETA_EXIT + EXIT_GAP_HALF_DEG)
    gap_upper = (BOWL_IR * math.cos(th_upper), BOWL_IR * math.sin(th_upper))
    gap_lower = (BOWL_IR * math.cos(th_lower), BOWL_IR * math.sin(th_lower))
    mouth_outer = (-r_a - hw - t, 0.0)  # tiep tuc tu vanh (tang truong tu nhien theo -Y,-X)
    mouth_inner = (-r_a + hw + t, 0.0)
    hh = 0.5 * (H + 8.0)
    ids.append(_wing_wall(cid, gap_upper, mouth_outer, hh, 0.35))
    ids.append(_wing_wall(cid, gap_lower, mouth_inner, hh, 0.35))
    return r_a, ids


def build_height_stop(cid: int, H: float) -> int:
    """Co cau chan chieu cao (dai dien Height_Scraper thuc) — mot "tran" tinh o do cao
    H (=T+1mm, dung khe ho thiet ke) phia tren mat dia, phu mot vung lon tren dia.
    Vien mot lop (cao T) di qua duoi tran nay tu do; neu co vien nao (do loi mo phong)
    bi day/xep cao hon H se bi tran nay chan lai — dung nhu vai tro thuc cua
    Height_Scraper (gat vien xep tang), vien KHONG duoc di xuyen qua no.
    Tra ve body id de main() co the p.removeBody() khi "Apply" H moi."""
    # Vung phu (mm, tuong duong bbox thuc cua Height_Scraper trong manifest.json).
    # ymin=35 (khong phai 4.8 nhu bbox thuc) de tranh dung vach/canh dan gan khe ho
    # thoat (gap_upper o y~+24.4, xem build_exit_chute) — giu vung "bat vien vao mang"
    # da tinh chinh o phan truoc khong bi anh huong boi tran chan chieu cao nay.
    xmin, xmax = -95.0, 10.0
    ymin, ymax = 35.0, 100.0
    hx = 0.5 * (xmax - xmin)
    hy = 0.5 * (ymax - ymin)
    hz = 2.5
    cx = 0.5 * (xmin + xmax)
    cy = 0.5 * (ymin + ymax)
    cz = H + hz  # mat duoi tran dung tai z=H (khe ho vien 1 lop di qua)
    return _box_collision(cid, hx, hy, hz, [cx, cy, cz], 0.2)


def spawn_pill(cid: int, D: float, T: float, shape: str, x_mm: float, y_mm: float, z_mm: float):
    """Vien thuoc dang rigid body dong (mass>0) — chi chiu gravity + tiep xuc.

    Collision la COMPOUND nhieu sphere nho (1 tam + vong ngoai) xap xi dung ca
    duong kinh D (be rong — quyet dinh tinh chat hang don qua kenh rong D+1mm)
    VA chieu cao T (quyet dinh co qua duoc duoi tran chan chieu cao hay khong).
    Phat hien thuc nghiem: 1 sphere lon (ban kinh D/2) qua cao so voi T thuc —
    va cham sai voi tran chan chieu cao; 1 cylinder det (D x T) lai gay flat-contact
    instability (xoay-troi vao tam). Compound multi-sphere giai quyet ca hai.
    """
    r_small = 0.5 * T * S
    ring_r = max(0.0, 0.5 * D - 0.5 * T) * S
    if shape == "ball" or abs(D - T) < 1e-9:
        col = p.createCollisionShape(p.GEOM_SPHERE, radius=0.5 * D * S, physicsClientId=cid)
        vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.5 * D * S, rgbaColor=[1, 0.75, 0.2, 1], physicsClientId=cid)
    else:
        n_ring = 6
        frame_pos = [[0.0, 0.0, 0.0]]
        for i in range(n_ring):
            a = 2.0 * math.pi * i / n_ring
            frame_pos.append([ring_r * math.cos(a), ring_r * math.sin(a), 0.0])
        col = p.createCollisionShapeArray(
            shapeTypes=[p.GEOM_SPHERE] * len(frame_pos),
            radii=[r_small] * len(frame_pos),
            collisionFramePositions=frame_pos,
            physicsClientId=cid,
        )
        vis = p.createVisualShape(
            p.GEOM_CYLINDER, radius=0.5 * D * S, length=T * S, rgbaColor=[1, 0.55, 0.15, 1], physicsClientId=cid
        )
    mass_kg = 0.0005 * (D * T) / (8.0 * 4.0)  # ti le tho theo kich thuoc, ~0.5 g cho D8T4
    bid = p.createMultiBody(mass_kg, col, vis, [x_mm * S, y_mm * S, z_mm * S], physicsClientId=cid)
    p.changeDynamics(
        bid, -1, lateralFriction=0.55, restitution=0.0, linearDamping=0.02, angularDamping=0.02,
        ccdSweptSphereRadius=0.85 * r_small, physicsClientId=cid,
    )
    return bid


def spawn_random_pill_on_disc(cid: int, omega: float, D: float, T: float, shape: str, rng: random.Random,
                               r_lo: float = 82.0, r_hi: float = 95.0):
    """Tha 1 vien moi tai vi tri (r,theta) ngau nhien gan mieng bat, van toc tiep
    tuyen khoi tao dung omega*r (xem docstring spawn_pill / main). Dung chung cho
    ca vien khoi tao luc mo va vien them vao khi bam nut "Add pill" trong GUI."""
    r0 = rng.uniform(r_lo, r_hi)
    th0 = math.radians(rng.uniform(0.0, 360.0))
    x_mm = r0 * math.cos(th0)
    y_mm = r0 * math.sin(th0)
    z_mm = 0.5 * T + 0.3
    bid = spawn_pill(cid, D, T, shape, x_mm, y_mm, z_mm)
    vx0 = -omega * (y_mm * S)
    vy0 = omega * (x_mm * S)
    p.resetBaseVelocity(bid, linearVelocity=[vx0, vy0, 0.0], physicsClientId=cid)
    st = {"exited": False, "exit_t": None, "fell": False, "escaped": False, "r0": r0, "th0_deg": math.degrees(th0)}
    return bid, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rpm", type=float, default=40.0, help="Toc do quay dia (vong/phut)")
    ap.add_argument("--n_pills", type=int, default=10)
    ap.add_argument("--D", type=float, default=8.0)
    ap.add_argument("--T", type=float, default=4.0)
    ap.add_argument("--shape", default="tablet", choices=["tablet", "ball"])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--no-gui", action="store_true", help="Chay headless (DIRECT) thay vi mo GUI")
    ap.add_argument("--duration", type=float, default=45.0, help="Thoi gian mo phong (giay, thang mo phong)")
    args = ap.parse_args()

    omega = args.rpm * 2.0 * math.pi / 60.0  # rad/s
    W, H = gap_wh(args.D, args.T)

    cid = make_world(gui=not args.no_gui)

    disc = load_disc_mesh(cid)
    load_all_visual_parts_from_manifest(cid)
    disc_texture = add_disc_texture_overlay(cid, radius_mm=98.0)  # ~ban kinh Rotor_Disc thuc (100mm)
    build_bowl_ring(cid)
    build_permanent_safety_net(cid)
    r_a, chute_ids = build_exit_chute(cid, W, H)
    height_stop_id = build_height_stop(cid, H)
    exit_x_min, exit_x_max = -r_a - 0.5 * W - EXIT_WALL_T, -r_a + 0.5 * W + EXIT_WALL_T

    rng = random.Random(args.seed)
    # Diem xuat phat gan mieng bat (85-95mm, gan BOWL_IR~100.8mm) — mo phong dung
    # trang thai thuc te: vien duoc nap tu hopper sat vien bat ngoai, khong rai
    # giua mat dia. Vien xa tam hon can rat nhieu vong quay moi troi ra toi tuong
    # (ma sat thuan chi keo tiep tuyen, khong co luc day ban kinh chu dong).
    r_lo, r_hi = 82.0, 95.0
    pills = []
    status = {}
    for i in range(args.n_pills):
        bid, st = spawn_random_pill_on_disc(cid, omega, args.D, args.T, args.shape, rng, r_lo, r_hi)
        pills.append(bid)
        status[bid] = st

    # UI dieu chinh trong GUI (khong dung khi chay headless --no-gui):
    #  - "Pill D/T (mm)": kich thuoc vien SE THA tiep theo (bam Add pill), khong hoi
    #    to/nho lai vien da co san trong canh (giong thuc te — chinh kich thuoc chi
    #    anh huong vien moi nap vao, khong "ep" lai vien dang chay).
    #  - "Lane W/H (mm)": do rong/cao mang thoat — bam "Apply lane W/H" de mang duoc
    #    xay lai (go bo primitive cu, dung primitive moi dung W/H) — mo phong dung
    #    co cau Width_Carriage/Height_Scraper dieu chinh khe cho vien di qua.
    #  Nut = addUserDebugParameter voi rangeMin>rangeMax (PyBullet ve thanh BUTTON,
    #  gia tri tang moi lan bam) — da dung cho "Add pill" tu truoc.
    add_pill_btn = apply_lane_btn = d_slider = t_slider = w_slider = h_slider = None
    last_btn_val = last_apply_val = None
    if not args.no_gui:
        d_slider = p.addUserDebugParameter("Pill D (mm)", 2.0, 25.0, args.D, physicsClientId=cid)
        t_slider = p.addUserDebugParameter("Pill T (mm)", 2.0, 25.0, args.T, physicsClientId=cid)
        w_slider = p.addUserDebugParameter("Lane W (mm)", 2.0, 26.0, W, physicsClientId=cid)
        h_slider = p.addUserDebugParameter("Lane H (mm)", 2.0, 26.0, H, physicsClientId=cid)
        add_pill_btn = p.addUserDebugParameter("Add pill (random)", 1, 0, 1, physicsClientId=cid)
        apply_lane_btn = p.addUserDebugParameter("Apply lane W/H", 1, 0, 1, physicsClientId=cid)
        last_btn_val = p.readUserDebugParameter(add_pill_btn, physicsClientId=cid)
        last_apply_val = p.readUserDebugParameter(apply_lane_btn, physicsClientId=cid)

    print(
        f"[tube_l_disc_rigid_body] dia quay {args.rpm:.0f} vong/phut "
        f"({omega:.3f} rad/s), {args.n_pills} vien thuoc rigid body (D={args.D}mm T={args.T}mm), "
        f"mang W={W}mm H={H}mm (collision primitive)."
    )
    if not args.no_gui:
        print("Dong cua so GUI de dung mo phong.")

    theta = 0.0
    t_sim = 0.0
    # Che do GUI: chay den khi nguoi dung dong cua so (khong gioi han --duration) de con
    # thoi gian bam nut them vien. Che do headless (--no-gui, dung cho verify/metrics):
    # gioi han dung --duration nhu cu.
    n_steps = int(args.duration / DT) if args.no_gui else None
    jam_events = 0  # so lan 2 vien tiep xuc nhau trong khi CA HAI dang trong kenh Exit_Track
    step = 0
    try:
        while p.isConnected(cid) and (n_steps is None or step < n_steps):
            theta = (theta + omega * DT) % (2.0 * math.pi)
            orn = p.getQuaternionFromEuler([0, 0, theta])
            # "Kinematic turntable": gan lai pose + van toc goc moi step —
            # ma sat tiep xuc voi vien thuoc (rigid body thuan) tu keo vien di theo.
            p.resetBasePositionAndOrientation(disc, [0, 0, 0], orn, physicsClientId=cid)
            p.resetBaseVelocity(disc, angularVelocity=[0, 0, omega], physicsClientId=cid)
            # Lop texture phu dong bo cung theta voi dia — xem add_disc_texture_overlay().
            p.resetBasePositionAndOrientation(disc_texture, [0, 0, 0.35 * S], orn, physicsClientId=cid)
            p.stepSimulation(physicsClientId=cid)
            t_sim += DT

            if add_pill_btn is not None:
                btn_val = p.readUserDebugParameter(add_pill_btn, physicsClientId=cid)
                if btn_val != last_btn_val:
                    last_btn_val = btn_val
                    d_new = p.readUserDebugParameter(d_slider, physicsClientId=cid)
                    t_new = p.readUserDebugParameter(t_slider, physicsClientId=cid)
                    bid, st = spawn_random_pill_on_disc(cid, omega, d_new, t_new, args.shape, rng, r_lo, r_hi)
                    pills.append(bid)
                    status[bid] = st
                    print(
                        f"[tube_l_disc_rigid_body] + them vien moi (id={bid}, D={d_new:.1f}mm "
                        f"T={t_new:.1f}mm), tong {len(pills)} vien."
                    )

            if apply_lane_btn is not None:
                apply_val = p.readUserDebugParameter(apply_lane_btn, physicsClientId=cid)
                if apply_val != last_apply_val:
                    last_apply_val = apply_val
                    w_new = p.readUserDebugParameter(w_slider, physicsClientId=cid)
                    h_new = p.readUserDebugParameter(h_slider, physicsClientId=cid)
                    for bid_old in chute_ids:
                        p.removeBody(bid_old, physicsClientId=cid)
                    p.removeBody(height_stop_id, physicsClientId=cid)
                    r_a, chute_ids = build_exit_chute(cid, w_new, h_new)
                    height_stop_id = build_height_stop(cid, h_new)
                    exit_x_min = -r_a - 0.5 * w_new - EXIT_WALL_T
                    exit_x_max = -r_a + 0.5 * w_new + EXIT_WALL_T
                    print(f"[tube_l_disc_rigid_body] Ap dung mang moi: W={w_new:.1f}mm H={h_new:.1f}mm")
            step += 1

            in_channel = []
            for bid in pills:
                st = status[bid]
                if st["exited"]:
                    continue
                # Velocity clamp: luoi an toan cuoi cung — chan bat ky xung dot manh nao
                # (du da giam manh sau khi doi sang collision primitive) truoc khi no
                # gay "bay ra ngoai mo hinh" trong 1 buoc.
                lv, av = p.getBaseVelocity(bid, physicsClientId=cid)
                sp = math.sqrt(lv[0] ** 2 + lv[1] ** 2 + lv[2] ** 2)
                if sp > VMAX_MPS:
                    k = VMAX_MPS / sp
                    p.resetBaseVelocity(
                        bid, linearVelocity=[lv[0] * k, lv[1] * k, lv[2] * k], angularVelocity=av,
                        physicsClientId=cid,
                    )
                pos, _ = p.getBasePositionAndOrientation(bid, physicsClientId=cid)
                x_mm, y_mm, z_mm = pos[0] / S, pos[1] / S, pos[2] / S
                r_mm = math.hypot(x_mm, y_mm)
                if exit_x_min <= x_mm <= exit_x_max and y_mm <= EXIT_Y_DONE:
                    st["exited"] = True
                    st["exit_t"] = round(t_sim, 2)
                    continue
                if exit_x_min - 5.0 <= x_mm <= exit_x_max + 5.0 and y_mm <= 5.0:
                    in_channel.append(bid)
                    # Ho tro nhe doc kenh (-Y) — xem CHUTE_ASSIST_MPS2 o dau file.
                    lv2, av2 = p.getBaseVelocity(bid, physicsClientId=cid)
                    p.resetBaseVelocity(
                        bid, linearVelocity=[lv2[0], lv2[1] - CHUTE_ASSIST_MPS2 * DT, lv2[2]],
                        angularVelocity=av2, physicsClientId=cid,
                    )
                if z_mm < FLOOR_FAIL_Z:
                    st["fell"] = True
                elif r_mm > ESCAPE_FAIL_R and z_mm > -5.0:
                    st["escaped"] = True

            if len(in_channel) >= 2:
                for a in range(len(in_channel)):
                    for b in range(a + 1, len(in_channel)):
                        if p.getContactPoints(in_channel[a], in_channel[b], physicsClientId=cid):
                            jam_events += 1

            if not args.no_gui:
                time.sleep(DT)
    except p.error:
        pass
    finally:
        if p.isConnected(cid):
            p.disconnect(physicsClientId=cid)

    n_exited = sum(1 for st in status.values() if st["exited"])
    n_fell = sum(1 for st in status.values() if st["fell"])
    n_escaped = sum(1 for st in status.values() if st["escaped"])
    exit_order = sorted((st["exit_t"] for st in status.values() if st["exited"]))
    passed = n_fell == 0 and n_escaped == 0 and jam_events == 0 and n_exited >= 1
    result = {
        "pass": passed,
        "rpm": args.rpm,
        "duration_s": args.duration,
        "n_pills": args.n_pills,
        "D_mm": args.D,
        "T_mm": args.T,
        "n_exited": n_exited,
        "n_fell_through": n_fell,
        "n_escaped_over_wall": n_escaped,
        "jam_events_in_channel": jam_events,
        "exit_times_s": exit_order,
        "pills": {str(bid): st for bid, st in status.items()},
        "exit_channel_x_mm": [exit_x_min, exit_x_max],
        "note": "Tuong/mang la collision primitive (box/cylinder), khong con dung mesh STL "
                "concave cho va cham — vien khong duoc phep xuyen qua component nao. "
                "single-file: kenh Exit_Track rong D+1mm nen ve mat hinh hoc chi 1 vien lot qua "
                "tiet dien cung luc; jam_events_in_channel dem va cham vien-vien khi ca hai dang "
                "trong kenh (hang doi/ket, khong phai xep hang doc binh thuong).",
    }
    METRICS.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        f"[tube_l_disc_rigid_body] KET QUA: pass={passed} exited={n_exited}/{args.n_pills} "
        f"fell_through={n_fell} escaped_over_wall={n_escaped} jam_events={jam_events} "
        f"exit_times={exit_order}"
    )
    print(f"METRICS -> {METRICS}")


if __name__ == "__main__":
    main()
