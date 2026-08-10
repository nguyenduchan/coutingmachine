"""Verify Width_Chute_Selector dual-gear drive (math + collision sweep)."""
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

try:
    _HERE = Path(__file__).resolve().parent
except NameError:
    _HERE = Path(r"c:\workspace\embedded\CountingMachine\3d_model\freecad")

sys.path.insert(0, str(_HERE))
from width_chute_selector import write_verify_json  # noqa: E402


def main() -> None:
    out = _HERE / "out" / "width_chute_selector_verify.json"
    data = write_verify_json(out)
    print("pass:", data.get("pass"))
    print("math:", data.get("math", {}).get("checks"))
    cs = data.get("collision_sweep", {})
    print("jam_hits:", cs.get("jam_hits"), "worst:", cs.get("worst"))
    print(
        "mesh_s0:", cs.get("mesh_s0", {}).get("pass"),
        "mesh_s10:", cs.get("mesh_s10", {}).get("pass"),
    )
    fl = data.get("flow_path_geometry", {})
    print(
        "flow_pass:", fl.get("pass"),
        "flush:", fl.get("bottom_flush_ok"),
        "outer:", fl.get("outer_edge_flush_ok"),
        "path_jams:", fl.get("flow_jam_hits"),
        "worst:", fl.get("worst"),
    )
    seal = data.get("gate_seal_no_gaps", {})
    print(
        "seal_pass:", seal.get("pass"),
        "gap_poses:", seal.get("gap_pose_hits"),
        "x_flush:", seal.get("bar_x_flush_inlet_cassette"),
        "worst:", seal.get("worst"),
    )
    if not data.get("pass"):
        raise SystemExit(1)


main()
