# Multi-outlet Screw Feeder (CadQuery) — CountingMachine

Tham khảo form công nghiệp: [vibratory bowl / multi-outlet parts feeder](https://www.youtube.com/shorts/V1ai93n3C1I).  
Thiết kế này giữ **đĩa xoay indexing** (dễ in + dễ mô phỏng) nhưng thêm **nhiều cửa ra song song** để tăng tốc đếm — cùng ý tưởng multi-track / multi-outlet của bowl feeder công nghiệp.

## Vì sao CadQuery
- Kernel **Open CASCADE (OCP)** → STEP chuẩn cơ khí, Boolean ổn định hơn OpenSCAD
- Parametric Python, dễ gắn vào pipeline mô phỏng / firmware CountingMachine
- Xuất **STL (in Bambu P1S)** + **STEP (CAD / sim)** cùng lúc

OpenSCAD bản cũ vẫn nằm trong thư mục (tham chiếu). **Nguồn chính mới:** `multi_outlet_feeder_cq.py`.

## Tăng tốc đếm bằng nhiều cửa
| Tham số | Mặc định | Ý nghĩa |
|---------|----------|---------|
| `outlet_count` | **4** | Số cửa ra + cảm biến đếm |
| `pocket_count` | **12** | Phải là bội của `outlet_count` |
| `index_angle_deg` | 30° | Bước quay / index |
| Screws / index | **4** | Mỗi bước nhả đồng thời 1 ốc / cửa |

Throughput tương đối ≈ `outlet_count` × tốc độ 1 cửa  
(ví dụ 4 cửa ≈ **4×** so với 1 cửa cùng RPM).

Góc cửa: `0° / 90° / 180° / 270°`. Mỗi `outlet_chute` có **khe gắn sensor IR** để đếm độc lập rồi cộng tổng.

Đổi số cửa (ví dụ 6):
```python
Params(outlet_count=6, pocket_count=12)  # hoặc 18
```

## Cài đặt
```powershell
python -m pip install cadquery cadquery-ocp trimesh matplotlib numpy
```

## Build / export
```powershell
cd c:\workspace\embedded\CountingMachine\3d_model
python multi_outlet_feeder_cq.py
python render_cq_preview.py
```

## File xuất
```
3d_model/
  multi_outlet_feeder_cq.py   # nguồn CadQuery
  sim_joints_cq.json          # khớp quay + danh sách sensor
  stl_cq/                     # in 3D (Bambu P1S)
  step_cq/                    # CAD / mô phỏng
  preview_cq/                 # PNG
```

### Chi tiết in (in `outlet_chute` × `outlet_count` bản)
| STL | Vai trò | Motion sim |
|-----|---------|------------|
| `base_plate.stl` | Đế + 4 cửa sổ xả | Fixed |
| `rotary_disc.stl` | Đĩa 12 pocket | **Revolute Z** |
| `drive_hub.stl` | Hub NEMA17 Ø5 D-shaft | **Revolute Z** |
| `bowl.stl` | Phễu dạng bowl | Fixed |
| `cover.stl` | Vành giữ ốc | Fixed |
| `outlet_chute.stl` | Máng + khe sensor (in 4 cái) | Fixed |
| `brush_arm.stl` | Wiper | Fixed |

## In Bambu P1S
- Đế Ø168 mm — vừa giường 256²
- Đĩa / đế / hub: nằm phẳng, layer 0.16–0.20, infill 30–50%
- PETG/ABS cho đĩa (mòn); PLA+ OK prototype
- In **4** `outlet_chute.stl`
- Nạp vào Bambu Studio từ `stl_cq/`

## Mô phỏng
Xem `sim_joints_cq.json`:
- Joint `disc_drive`: `drive_hub` + `rotary_disc` quay quanh Z
- 4 sensor `count_ir_0..3` tại từng outlet
- Import `step_cq/*.step` vào FreeCAD / Fusion / Adam / Blender

## Phần cứng gợi ý
- NEMA17 + driver
- 4× cảm biến quang (fork / IR) trên khe chute
- MCU CountingMachine cộng 4 kênh đếm
- Vít M3 bắt đế–bowl–cover
