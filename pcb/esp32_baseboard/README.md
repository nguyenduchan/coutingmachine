# ESP32 Baseboard (30-pin DevKit socket)

Board đế để cắm module ESP32 DevKit V1 **30 chân** qua 2 hàng female header.

## Thư viện

| File | Mô tả |
|------|--------|
| `libraries/ESP32_Carrier.kicad_sym` | Symbol `ESP32_DevKit_V1_30Pin` |
| `libraries/ESP32_Carrier.pretty/ESP32_DevKit_V1_30Pin_Socket.kicad_mod` | Footprint ổ cắm |

## Kích thước footprint

- Pitch: **2.54 mm**
- Số chân: **2 × 15 = 30**
- Khoảng cách 2 hàng (tâm–tâm): **25.4 mm**
- Pad: Ø1.7 mm, khoan **1.0 mm** (chuẩn female PinSocket)
- Hàn 2 thanh **female header 1×15** đứng (vertical)

## Pinout (DOIT ESP32-DevKit-V1, USB phía trên)

```
LEFT (1→15)              RIGHT (16→30)
1  3V3                   16 VIN
2  GND                   17 GND
3  IO15                  18 IO13
4  IO2                   19 IO12
5  IO4                   20 IO14
6  IO16                  21 IO27
7  IO17                  22 IO26
8  IO5                   23 IO25
9  IO18                  24 IO33
10 IO19                  25 IO32
11 IO21                  26 IO35 (input only)
12 RX0 (IO3)             27 IO34 (input only)
13 TX0 (IO1)             28 VN  (IO39)
14 IO22                  29 VP  (IO36)
15 IO23                  30 EN
```

**Quan trọng:** So khớp với chữ in trên module thật trước khi đặt hàng PCB.
Một số clone đảo cột nguồn (VIN/3V3).

## Mở project

Mở `esp32_baseboard.kicad_pro` bằng KiCad 10.

Tái tạo lib nếu sửa pinout:

```
python gen_esp32_30pin_libs.py
```
