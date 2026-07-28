"""Render CadQuery multi-outlet feeder STL assembly to PNG."""
from pathlib import Path
import math
import numpy as np
import trimesh
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parent
STL = ROOT / "stl_cq"
OUT = ROOT / "preview_cq"
OUT.mkdir(exist_ok=True)

BASE_T = 8.0
DISC_T = 6.0
BASE_OD = 168.0
OUTLET_DEPTH = 32.0
OUTLET_W = 10.0
DISC_OD = 140.0
OUTLET_COUNT = 4
POCKET_RADIAL = 52.0


def load(name: str) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(STL / name, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        mesh = mesh.dump(concatenate=True)
    return mesh


def xf(mesh, x=0, y=0, z=0, rz=0):
    m = mesh.copy()
    T = np.eye(4)
    if rz:
        a = np.deg2rad(rz)
        c, s = np.cos(a), np.sin(a)
        T[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    T[:3, 3] = [x, y, z]
    m.apply_transform(T)
    return m


def build(disc_angle=0.0, explode=0.0):
    ez = explode * 30.0
    items = [
        (xf(load("base_plate.stl")), "#3f3f3f"),
        (xf(load("drive_hub.stl"), z=BASE_T - 2 - ez * 0.3), "#6a6a6a"),
        (xf(load("rotary_disc.stl"), z=BASE_T + 0.5 + ez, rz=disc_angle), "#2f6fed"),
        (xf(load("cover.stl"), z=BASE_T + DISC_T + 0.2 + ez), "#9aa8b8"),
        (xf(load("bowl.stl"), z=BASE_T + DISC_T + 1 + ez * 1.5), "#2f8f8a"),
    ]
    chute = load("outlet_chute.stl")
    for i in range(OUTLET_COUNT):
        a = i * 360.0 / OUTLET_COUNT
        r = BASE_OD / 2 - OUTLET_DEPTH - 4
        y_off = -(OUTLET_W + 12) / 2
        # translate then rotate about Z (same as CadQuery place)
        m = chute.copy()
        T1 = np.eye(4)
        T1[:3, 3] = [r, y_off, -2 - ez * 0.5]
        m.apply_transform(T1)
        T2 = np.eye(4)
        ar = np.deg2rad(a)
        c, s = np.cos(ar), np.sin(ar)
        T2[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
        m.apply_transform(T2)
        items.append((m, "#e87722"))
    brush_a = 180.0 / OUTLET_COUNT
    items.append(
        (
            xf(
                load("brush_arm.stl"),
                x=DISC_OD / 2 - 20,
                y=-5,
                z=BASE_T + DISC_T + 8 + ez,
                rz=brush_a,
            ),
            "#8b5a2b",
        )
    )
    return items


def plot(items, title, path, elev=28, azim=-55, max_faces=10000):
    fig = plt.figure(figsize=(11, 8.5), facecolor="#f3f3f3")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#f3f3f3")
    meshes = []
    for mesh, color in items:
        meshes.append(mesh)
        faces = mesh.faces
        if len(faces) > max_faces:
            faces = faces[np.linspace(0, len(faces) - 1, max_faces, dtype=int)]
        coll = Poly3DCollection(mesh.vertices[faces], linewidths=0.04, alpha=0.92)
        coll.set_facecolor(color)
        coll.set_edgecolor((0.1, 0.1, 0.1, 0.2))
        ax.add_collection3d(coll)
    all_v = np.vstack([m.vertices for m in meshes])
    c = all_v.mean(axis=0)
    span = (all_v.max(0) - all_v.min(0)).max() / 2 * 1.15
    ax.set_xlim(c[0] - span, c[0] + span)
    ax.set_ylim(c[1] - span, c[1] + span)
    ax.set_zlim(c[2] - span * 0.35, c[2] + span)
    ax.set_xlabel("X mm")
    ax.set_ylabel("Y mm")
    ax.set_zlabel("Z mm")
    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title)
    ax.set_box_aspect([1, 1, 0.75])
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("wrote", path)


def main():
    for name, color in [
        ("rotary_disc.stl", "#2f6fed"),
        ("base_plate.stl", "#3f3f3f"),
        ("bowl.stl", "#2f8f8a"),
        ("outlet_chute.stl", "#e87722"),
        ("drive_hub.stl", "#6a6a6a"),
        ("cover.stl", "#9aa8b8"),
    ]:
        plot([(load(name), color)], name.replace(".stl", ""), OUT / name.replace(".stl", ".png"))

    plot(build(0, 0), "Multi-outlet rotary feeder (4 exits) — CadQuery", OUT / "assembly.png")
    plot(
        build(20, 1),
        "Multi-outlet feeder — exploded (4x parallel count)",
        OUT / "exploded.png",
        elev=24,
        azim=-40,
    )

    # top view emphasizing 4 outlets
    fig_items = build(0, 0)
    fig = plt.figure(figsize=(9, 9), facecolor="#f3f3f3")
    ax = fig.add_subplot(111, projection="3d")
    for mesh, color in fig_items:
        faces = mesh.faces
        if len(faces) > 8000:
            faces = faces[np.linspace(0, len(faces) - 1, 8000, dtype=int)]
        coll = Poly3DCollection(mesh.vertices[faces], linewidths=0.03, alpha=0.9)
        coll.set_facecolor(color)
        coll.set_edgecolor((0.1, 0.1, 0.1, 0.15))
        ax.add_collection3d(coll)
    all_v = np.vstack([m.vertices for m, _ in fig_items])
    c = all_v.mean(0)
    span = (all_v.max(0) - all_v.min(0)).max() / 2 * 1.1
    ax.set_xlim(c[0] - span, c[0] + span)
    ax.set_ylim(c[1] - span, c[1] + span)
    ax.set_zlim(c[2] - 5, c[2] + span)
    ax.view_init(elev=88, azim=-90)
    ax.set_title("Top view — 4 synchronized outlets @ 0/90/180/270°")
    ax.set_box_aspect([1, 1, 0.3])
    fig.tight_layout()
    fig.savefig(OUT / "top_4_outlets.png", dpi=150)
    plt.close(fig)
    print("wrote", OUT / "top_4_outlets.png")


if __name__ == "__main__":
    main()
