# Mô phỏng chuyển động + vật lý (miễn phí)

## Target videos

| Role | Link |
|------|------|
| Cơ khí (Huibao centrifugal) | https://www.youtube.com/shorts/jGgILsgO2yY |
| Hành vi hướng/reject (EcoType — **không** dùng rung) | https://www.youtube.com/shorts/oszvi08exHI |

Chi tiết checklist: `../VERIFICATION.md`

## Phần mềm

| Ưu tiên | Phần mềm | Vai trò |
|--------|----------|---------|
| **1 — vật lý** | **PyBullet** | Rigid-body — script này |
| **2 — render** | Blender 4.5 LTS | Video đẹp |

## Acceptance

`SUCCESS=True` khi:
- `exited_any >= 3` (ốc đúng tư thế xếp hàng trên máng)
- `wrong_still_in_bowl >= 1` (tư thế sai còn trong đĩa / reject)

## Chạy

```powershell
cd c:\workspace\embedded\CountingMachine\3d_model\sim
python screw_feeder_pybullet.py --headless --steps 2000
python screw_feeder_pybullet.py --gui
python screw_feeder_pybullet.py --until-success --steps 2000
```

Kết quả: `out/sim_report.txt`, `preview_still.png`, `screw_feeder_sim.mp4`
