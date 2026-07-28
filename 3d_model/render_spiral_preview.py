"""Preview rotary spiral feeder — moving vs fixed coloring."""
from pathlib import Path
import numpy as np
import trimesh
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "preview_cq"
OUT.mkdir(exist_ok=True)
MOV = ROOT / "stl_cq" / "moving"
FIX = ROOT / "stl_cq" / "fixed"

BASE_T = 8.0
BOWL_H = 85.0


def load(path: Path) -> trimesh.Trimesh:
    m = trimesh.load_mesh(path, force="mesh")
    if not isinstance(m, trimesh.Trimesh):
        m = m.dump(concatenate=True)
    return m


def xf(m, z=0, rz=0):
    out = m.copy()
    T = np.eye(4)
    if rz:
        a = np.deg2rad(rz)
        c, s = np.cos(a), np.sin(a)
        T[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    T[2, 3] = z
    out.apply_transform(T)
    return out


def plot(items, title, path, elev=25, azim=-60, max_faces=9000):
    fig = plt.figure(figsize=(11, 8.5), facecolor="#f2f2f2")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#f2f2f2")
    meshes = []
    for mesh, color in items:
        meshes.append(mesh)
        faces = mesh.faces
        if len(faces) > max_faces:
            faces = faces[np.linspace(0, len(faces) - 1, max_faces, dtype=int)]
        coll = Poly3DCollection(mesh.vertices[faces], linewidths=0.04, alpha=0.9)
        coll.set_facecolor(color)
        coll.set_edgecolor((0.1, 0.1, 0.1, 0.18))
        ax.add_collection3d(coll)
    v = np.vstack([m.vertices for m in meshes])
    c = v.mean(0)
    span = (v.max(0) - v.min(0)).max() / 2 * 1.15
    ax.set_xlim(c[0] - span, c[0] + span)
    ax.set_ylim(c[1] - span, c[1] + span)
    ax.set_zlim(c[2] - span * 0.3, c[2] + span)
    ax.set_xlabel("X mm")
    ax.set_ylabel("Y mm")
    ax.set_zlabel("Z mm")
    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title)
    ax.set_box_aspect([1, 1, 0.85])
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("wrote", path)


def main():
    moving = [
        (xf(load(MOV / "drive_hub.stl"), z=BASE_T - 2), "#c0392b"),
        (xf(load(MOV / "rotor_spiral.stl"), z=BASE_T + 0.5, rz=15), "#e74c3c"),
    ]
    fixed = [
        (xf(load(FIX / "base.stl")), "#2c3e50"),
        (xf(load(FIX / "bowl.stl"), z=BASE_T), "#34495e"),
        (xf(load(FIX / "outlet_ring.stl"), z=BASE_T + BOWL_H - 4), "#f39c12"),
        (xf(load(FIX / "lid.stl"), z=BASE_T + BOWL_H + 14), "#7f8c8d"),
    ]
    plot(moving, "MOVING — rotor spiral + drive hub (print separately)", OUT / "spiral_moving.png")
    plot(fixed, "FIXED — base / bowl / outlet ring / lid", OUT / "spiral_fixed.png")
    plot(
        fixed + moving,
        "Assembly — red=moving, dark=fixed, orange=outlets",
        OUT / "spiral_assembly.png",
    )
    plot(
        [
            (xf(load(FIX / "base.stl")), "#2c3e50"),
            (xf(load(MOV / "drive_hub.stl"), z=BASE_T - 2 - 8), "#c0392b"),
            (xf(load(MOV / "rotor_spiral.stl"), z=BASE_T + 0.5 + 25, rz=20), "#e74c3c"),
            (xf(load(FIX / "bowl.stl"), z=BASE_T + 12), "#34495e"),
            (xf(load(FIX / "outlet_ring.stl"), z=BASE_T + BOWL_H - 4 + 40), "#f39c12"),
            (xf(load(FIX / "lid.stl"), z=BASE_T + BOWL_H + 14 + 55), "#7f8c8d"),
        ],
        "Exploded — moving vs fixed for 3D print / sim",
        OUT / "spiral_exploded.png",
        elev=20,
        azim=-45,
    )


if __name__ == "__main__":
    main()
