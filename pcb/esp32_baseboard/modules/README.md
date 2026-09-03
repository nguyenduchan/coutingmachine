# Pluggable sub-modules (JLCPCB)

## Không cắm trực tiếp (cần giắc + board rời)

| Module mua sẵn / linh kiện | Vì sao không cắm flush | Giắc carrier | Board rời |
|----------------------------|------------------------|--------------|-----------|
| ULN2003 driver Shopee | Chỉ Dupont/JST lỏng, không mate PCB | **U5–U7** 1×6 ×3 | **M3** `m3_uln2003` ×3 |

**Hàn trên carrier:** D3+F1+D1; **PC817×4 + 2k2/10k** (không còn M1/M2).

**Cắm được trực tiếp:** ESP32-S3 DevKit (U1), MP1584 (U2), TMC2209 (U3), 74HC595-24IO (J24/J25), TFT (J17+J23).

## Files

| File | Board | Size | Contents |
|------|-------|------|----------|
| `m3_uln2003.kicad_pcb` | M3 | **36×28 mm** | ULN2003AN + JST-XH 5P 28BYJ |
| `submodules_panel.kicad_pcb` | Panel | **46×48 mm** | M3 mousebite |

**U5–U7 / M3 P1 (1×6):** 1–4=`INx` · 5=`GND` · 6=`+12V`  
**M3 J1 (XH-5):** 1=`A` 2=`B` 3=`C` 4=`D` 5=`+12V` → 28BYJ-48 **12V**
