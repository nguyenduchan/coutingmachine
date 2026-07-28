# Động cơ DC giảm tốc 24V + cụm lắp đĩa / khung

## Motor đã chọn (đồng bộ PLC FX3U-24MT)

| Mục | Giá trị |
|-----|---------|
| Loại | **GB37 / JGB37-520** (hộp số kim loại Ø37 mm) |
| Điện áp | **24 V DC** — cùng rail nguồn với **FX3U-24MT** |
| Tốc độ | **~30 RPM** (dải 20–60 RPM OK) |
| Trục | **Ø6 mm D-shaft, tâm (CENTER)** |
| Mặt bích | **6× M3**, PCD **31 mm** |
| Ghi chú | **Không** mua bản trục lệch tâm (eccentric) |

Gợi ý mua: `GB37 24V 30RPM center shaft` / `JGY370 24V 30RPM trục giữa`.

Cơ khí (trục, lỗ M3, bạc) **giống bản 12V** — chỉ đổi điện áp motor.

## Đấu với FX3U-24MT

```
[PSU 24VDC] ──► FX3U-24MT (CPU / I/O)
            └─► Relay coil / MOSFET module ◄── Y□ (transistor out)
                         │
                         └─► Motor GB37 24V (+ qua tiếp điểm / FET)
```

- **Không** cấp trực tiếp motor từ cổng Y (dòng / cảm ứng quá lớn).  
- Dùng **relay 24V** (ví dụ G2R) hoặc module MOSFET; PLC chỉ kích coil/input.  
- Chung một PSU 24V đủ công suất (PLC + motor stall ~1–2 A tùy model).  
- Chiều quay: đảo cực motor hoặc dùng H-bridge nếu cần CW/CCW.

## Chuỗi lắp (dưới → trên)

```
[khung máy] --M5-- [frame_riser ×4 tùy chọn]
                 --M5-- [base feet]
[motor GB37 24V] --M3≤3mm-- [motor_clamp] + [base]
                 trục Ø6 xuyên bạc [626ZZ] trong base
[shaft_collar]  set-screw trên trục
[drive_hub]     D-bore + set-screw, khóa vào rotor
[rotor_spiral]
[bowl / outlet_ring / lid]
```

- Bạc **626ZZ** (6×19×6) chịu tải hướng kính  
- Vít M3 vào mặt gearbox **≤ 3 mm**

## Chi tiết in 3D

### Moving — `stl_cq/moving/`
| File | Chức năng |
|------|-----------|
| `drive_hub.stl` | Khớp D-shaft Ø6 mm khóa vào rotor |
| `shaft_collar.stl` | Khóa trục dưới / gần bạc |
| `rotor_spiral.stl` | Đĩa xoắn quay |

### Fixed — `stl_cq/fixed/`
| File | Chức năng |
|------|-----------|
| `base.stl` | Ổ 626ZZ + lỗ M3 motor + chân M5 khung |
| `motor_clamp.stl` | Vành kẹp mặt motor (phía dưới đế) |
| `frame_riser.stl` | Cột cao — in **4** cái nếu cần khoảng motor |
| `bowl`, `outlet_ring`, `lid` | Bowl + cửa ra + nắp |

### Reference
- `stl_cq/reference/geared_motor_GB37_24V.stl` (preview kích thước)

## Lắp vào khung máy

1. Tấm máy: **4 lỗ M5**, hình vuông ~**130 mm** (góc 45°)  
2. Bắt `base` trực tiếp hoặc qua `frame_riser` ×4  
3. Slot chân đế chỉnh tâm vài mm  

## Build
```powershell
cd c:\workspace\embedded\CountingMachine\3d_model
python rotary_spiral_feeder_cq.py
```
