# CountingMachine feeder — chỉ cơ cấu QUAY (không rung)

## Ràng buộc
- **Chỉ rotary** — motor quay liên tục (NEMA17)
- **Không** vibratory / không lò xo cộng hưởng / không cuộn điện từ rung

Video [bowl xoắn](https://www.youtube.com/shorts/V1ai93n3C1I) thường dùng **rung** — ta **không** copy cơ chế đó.  
Chỉ tham khảo ý tưởng đường xoắn + nhiều cửa ra; chuyển động thực tế = **quay**.

## Cơ chế (pure rotary)

```
        [lid]                 FIXED
    [outlet_ring ×N]          FIXED  ← đếm song song
    [bowl wall]               FIXED  ← thành phản lực
    [rotor: đĩa nón + cánh helix]  MOVING ← quay quanh Z
    [drive_hub]               MOVING
    [base + bearing]          FIXED
```

1. Rotor quay → lực ly tâm ép phôi vào thành bowl  
2. Cánh helix quay + thành đứng yên = **vít Archimedes** → đẩy phôi **lên**  
3. Vành `outlet_ring` hứng phôi ở đỉnh → chia **N cửa** (mặc định 4) để đếm  

## In 3D — tách model

| | Moving | Fixed |
|--|--------|-------|
| STL | `stl_cq/moving/` | `stl_cq/fixed/` |
| Chi tiết | `rotor_spiral`, `drive_hub` | `base`, `bowl`, `outlet_ring`, `lid` |
| Vì sao tách | Phải quay tự do, khe ~1 mm | Không in dính với rotor |

**Không in** file assembly nguyên khối.

## Build
```powershell
cd c:\workspace\embedded\CountingMachine\3d_model
python rotary_spiral_feeder_cq.py
python render_spiral_preview.py
```

Nguồn: `rotary_spiral_feeder_cq.py` · Joint: `sim_joints_spiral_cq.json`  
(Bản đĩa pocket ngang `multi_outlet_feeder_cq.py` cũng chỉ quay, không rung — nhưng không leo xoắn.)
