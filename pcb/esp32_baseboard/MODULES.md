# Counting machine — danh sách module (ghi nhớ)

**Cập nhật:** 2026-08-28 (bơm **370 12V**; **1× MP1584** 5V; thổi **3 s / 5 phút**)  
**PCB:** `esp32_baseboard` (generator: `gen_power_carrier.py`)  
**Mục tiêu:** văn phòng ~20 cm, **ổn định >3 năm**, **tổng giá kinh tế** (chỉ nâng cấp khi chênh ít).

> ✅ **Generator đã đồng bộ.** `gen_power_carrier.py` sinh
> **U10 = module 74HC595-24IO** ([Shopee](https://shopee.vn/-C%C3%B3-s%E1%BA%B5n-M%E1%BA%A1ch-m%E1%BB%9F-r%E1%BB%99ng-I-O-24-ch%C3%A2n-74HC595-thegioimodule-i.951399259.42633627766))
> **bên phải ESP32** (J24 CTRL + J25 Q) → **ULN2003AN ×3** + 28BYJ J5–J7,
> HOME endstop J8/J10/J12 **1×04**, **U41–U44 PC817 ×4**, TFT **có touch**, J18 ENC,
> board **220×160 mm**. Spare GPIO: IO7/8/14/15. Firmware: **shiftOut 3 byte**.
> Vẫn cần FreeRouting + DRC trước fab.

Nguồn 12V ngoài → J1 → F1 PTC → `+12V` (+ D1 TVS) → các rail / driver.

```
PSU 12V ──J1── F1 ── +12V ──┬── U2 MP1584 ── +5V ── U1 / TFT / buzzer  (buck duy nhat)
                            ├── J16 AOD4184 ── bơm khí 370 12V
                            ├── U3 TMC2209 Mot ── NEMA17 (không J2)
                            ├── U5–U7 ULN2003 ── J5–J7 28BYJ-48 (bản 12V)
                            └── R10/C10/C11 ── +12V_SNS ── limit + BUP
```

---

## A) Trên baseboard (hàn / cắm socket)

| Ref | Module / linh kiện | Size typ. | SL | Vai trò | Pin / net chính |
|-----|-------------------|-----------|----|---------|-----------------|
| **J1** | Terminal 2P pitch 5.0 mm | ~10×8 | 1 | Vào 12V PSU | `+12V_RAW`, GND |
| **F1** | PTC radial ~3A / 30V (RXE030 / MF-R300 class) | Ø~9–11 | 1 | Bảo vệ ngắn mạch | RAW → `+12V` |
| **D1** | TVS P6KE15A (DO-41) | axial | 1 | Clamp surge 12V | `+12V`–GND |
| **U1** | **ESP32-S3-DevKitC-1 N16R8** (bản `v1.1`, **không** hậu tố `V`) | ~63×25 | 1 | MCU | Socket 2×22 @2.54, row 25.4; cấp **5V** từ U2 |
| **U2** | **MP1584EN** fixed **5V** ([Shopee 41383641614](https://shopee.vn/MP1584EN-Mini-DC-Buck-41383641614)) | ~22×17 | 1 | Buck logic **duy nhất** | `+12V` → `+5V`; pad 18.54×10.67 mm |
| **U3** | **TMC2209** stepstick **BTT** + heatsink | ~15×20 | 1 | Driver NEMA17 | VM=12V, VIO=3V3; STEP/DIR/EN |
| **U41–U44** | **PC817** DIP-4 | ~5×7 | **4** | Level-shift → 3V3 | IN1–3 **HOME**, IN4 **BUP** → IO1,2,4,5 |
| **R41–R44** | Điện trở axial **2k2** | pitch ~7.5 | 4 | LED series PC817 (~5 mA @12V) | `OPTO_INx` → anode |
| **R45–R48** | Điện trở axial **10k** | pitch ~7.5 | 4 | Pull-up collector → GPIO | `+3V3` → `OPTO_OUTx` |
| ~~**U4/U9**~~ | ~~PC817 4CH module~~ | — | **BỎ** | Module Shopee không có hàng chân; thay bằng chip rời | — |

> ⚠️ **Không phải cách ly galvanic.** `GND` chung (một PSU). Vai trò: **hạ 12 V → 3.3 V + chắn xung field**.
| **U5** | **ULN2003AN** DIP-16 | ~20×7 | 1 | Đệm 4 pha stepper trục 1 | IN ← SR_Q0–3 → J5; **COM(9) → `+12V`** |
| **U6** | **ULN2003AN** DIP-16 | ~20×7 | 1 | Đệm 4 pha stepper trục 2 | IN ← SR_Q4–7 → J6; **COM(9) → `+12V`** |
| **U7** | **ULN2003AN** DIP-16 | ~20×7 | 1 | Đệm 4 pha stepper trục 3 | IN ← SR_Q8–11 → J7; **COM(9) → `+12V`** |
| **U10** | **74HC595-24IO** module (3×595) | ~66×20 | **1** | [Shopee thegioimodule](https://shopee.vn/-C%C3%B3-s%E1%BA%B5n-M%E1%BA%A1ch-m%E1%BB%9F-r%E1%BB%99ng-I-O-24-ch%C3%A2n-74HC595-thegioimodule-i.951399259.42633627766) — **bên phải ESP32** | J24 CTRL + J25 Q; 12/24 → ULN |
| **J24** | Header cái **1×06** | pitch 2.54 | 1 | Cắm CTRL module | LDEN GND VCC LDSI LDSTR LDSCK |
| **J25** | Header cái **1×24** | pitch 2.54 | 1 | Cắm Q module | 1_Q0…3_Q7; Q0–11 → ULN |
| **R4** | Điện trở axial **10k** | pitch ~7.5 | 1 | Pull-up LDEN/`OE` (boot Hi-Z) | `OE_595` → `+3V3` |
| **R1** | Điện trở axial **4k7** | pitch ~7.5 | 1 | Pull-up BUP NPN | `+12V_SNS` → OUT |
| **R2** | Điện trở axial **10k** | pitch ~7.5 | 1 | Pull-up EN của TMC2209 | `/EN_TMC` → `+3V3` |
| **R3** | Điện trở axial **10k** | pitch ~7.5 | 1 | Pull-down PWM bơm | `/BLOWER` → GND |
| **D2** | **1N5819** (DO-41) | axial | 1 | Freewheel bơm 370 12V | `+12V` ↔ `/BLW_RET` |
| **R10** | 10Ω 1206 | — | 1 | Lọc star SNS | `+12V` → `+12V_SNS` |
| **C10** | 47µF radial 25V (105°C) | Ø~6 | 1 | Bulk SNS | `+12V_SNS`–GND |
| **C11** | 100nF 0805 | — | 1 | HF SNS | `+12V_SNS`–GND |
| **C20** | 470µF 25V radial (105°C) | Ø~8 | 1 | Bulk @ TMC2209 VM | `+12V`–GND |
| **C21** | 100µF 25V radial (105°C) | Ø~6 | 1 | Bulk **dùng chung** cho COM của U5–U7 | `+12V`–GND |
| ~~**C22–C23**~~ | ~~470µF~~ | — | **BỎ** | 3 ULN2003 chỉ hút ~74 mA/trục (N20 stall là 1,5–2 A) — một tụ chung là đủ | — |

### Jack trên board (chỉ chân cắm — không gắn sensor/motor lên PCB)

| Ref | Header | SL | Cắm ra ngoài |
|-----|--------|----|--------------|
| **J2** | ~~1×04~~ | **XOÁ** | Trùng Mot trên U3 TMC2209 — NEMA17 hàn/cắm thẳng chân Mot module |
| ~~**J4**~~ | ~~1×06~~ | **XOÁ** | Trùng hoàn toàn J8/J10/J12/J14 (`OPTO_IN1…IN4` từng chân). Phía vào của U4 nay lấy **`+12V_SNS`** — cùng rail các giắc limit đã mang — thay cho chân `OPTO_VCC_I` riêng |
| **J5** | **1×05** | 1 | **28BYJ-48 trục 1** — JST-XH 5P (ULN2003 chip rời không có giắc sẵn) |
| **J6** | **1×05** | 1 | **28BYJ-48 trục 2** |
| **J7** | **1×05** | 1 | **28BYJ-48 trục 3** |
| **J8** | **1×04** endstop | 1 | HOME trục 1 — [module CNC/3D](https://shopee.vn/Module-c%C3%B4ng-t%E1%BA%AFc-h%C3%A0nh-tr%C3%ACnh-Endstop-CNC-Printer-3D-i.951399259.23532922598); **VCC+GND NC**; SIG+SNS = dry NC → `+12V_SNS` / OPTO_IN1 |
| **J10** | **1×04** endstop | 1 | HOME trục 2 (như J8 → OPTO_IN2) |
| **J12** | **1×04** endstop | 1 | HOME trục 3 (như J8 → OPTO_IN3) |
| **J19** | 1×02 | 1 | Field **ESTOP** (dry contact → OPTO_IN5) |
| **J20** | 1×02 | 1 | Field **HOPPER** level (→ OPTO_IN6) |
| **J21** | 1×02 | 1 | Field **DOOR** (→ OPTO_IN7) |
| **J22** | 1×02 | 1 | Field **SPARE** (→ OPTO_IN8) |
| **J14** | 1×04 | 1 | BUP-30S (+12 / GND / OUT / CTRL) |
| **J15** | 1×03 | 1 | Buzzer 5V (VCC / GND / SIG) |
| **J16** | 1×04 | 1 | AOD4184 (PWM / GND / **+12V** / FAN−) |
| **J17** | **1×09** LCD | 1 | MSP3520 pins 1–9: VCC…SDO; SDO **NC** |
| **J23** | **1×05** touch | 1 | MSP3520 pins 10–14: T_CLK…T_IRQ — **liền dưới J17**, cùng cột, đúng thứ tự module |

**J3:** không dùng.

---

## B) Ngoài board — đã đặt mua (Shopee, 2026-08-27)

| # | Linh kiện đã mua | SL | Giá | Cắm / nối | Trạng thái |
|---|------------------|----|-----|-----------|------------|
| 1 | **Mean Well LRS-50-12** (+ nắp che TBC-09 tặng kèm) | 1 | 304.000 | → J1 | ✅ đúng |
| 2 | **ESP32-S3-DevKitC N16R8** Type-C (Lập Trình Nhúng A-Z G182) | 1 | 210.000 | socket U1 | ✅ đúng — **kiểm tra rev v1.1** |
| 3 | **MP1584EN** 3A, phân loại 5V | **1**/2 | 42.000 | **U2** (con thứ 2 = dự phòng) | ⚠️ xem R-2 |
| 5 | **AOD4184** MOSFET cách ly | 1 | 25.000 | → J16 | ✅ đúng |
| 6 | **MKS TMC2209 V2.0** (Makerbase, hàng đặt trước) | 1 | 160.313 | U3 | ⚠️ xem R-4 |
| 7 | **NEMA 17** 42×34 mm | 1 | 225.000 | → U3 Mot | ✅ đúng |
| 9 | **Module endstop CNC/3D** (giắc 1×04) | **3** | — | → J8, J10, J12 | ✅ VCC/GND **không dùng** trên carrier; SIG+SNS dry NC qua PC817. Thay OMRON SS-5GL2 + dây rời |
| 10 | **PC817 DIP-4** (chip rời) | **8**/50 | — | U41–U48 | ✅ gói 50; 4 bắt buộc + 4 field dự phòng |
| 11 | Autonics **BUP-30S** | 1 | 480.000 | → J14 | ✅ đúng |
| 12 | **TFT 3.5" 320×480 SPI ILI9488** | 1 | 395.000 | → J17 1×9 + J23 1×5 | ✅ khớp MSP3520 (R-1) |
| 13 | Bơm khí mini, phân loại **"BƠM 280 3.7V"** | 1 | 44.000 | — | ❌ **không lắp** — mua **370 khí 12V** (§G) |

**Tổng phần điện CÒN DÙNG: 2.028.313₫** · cơ khí còn dùng ~617.000₫ *(665.000 trừ ~48.000 ty ren/đai ốc/khớp nối 4–3 đã bỏ)*

> 💰 **Đã chi nhưng không dùng nữa — 653.000₫.** Ghi lại ở đây để không mua lại nhầm
> và không mất dấu vết chi tiêu: DRV8871 ×3 (255.000) · GA12-N20 ×3 (207.000) ·
> OMRON SS-5GL2 ×3 dư (96.000) · PC817 4CH ×1 dư (47.000) · ty ren M4×40 + đai ốc M4
> + khớp nối 4–3 (~48.000). **Tất cả còn nguyên — giữ dự phòng, không phải lỗ.**

### Cơ khí / dụng cụ trong cùng đơn

Khớp mềm D19 L25 (5–8 mm) ×2 · khớp mặt bích 8 mm ×2 · gối đỡ KFL08 ×5 · thanh
trượt Ø8 L100 · gen co nhiệt Ø2 · tay quay taro M3–M8. *(Cho trục NEMA17 + vít me
T8 — vẫn dùng.)*

> ⚠️ **Trục trơn Ø5 chưa có trong đơn.** Ba cụm tịnh tiến mới cần **6 cây Ø5 × 115 mm**
> (bạc trong `Slide_Bar` là Ø5,4). Cây Ø8 L100 đã mua là của trục NEMA17, không thay được.

---

## B2) CHƯA MUA — thiếu là không lắp được board

| Nhóm | Linh kiện | SL | Ghi chú |
|------|-----------|----|---------|
| **Động cơ** | **28BYJ-48 bản 12V** (KHÔNG phải bản 5V) | **3** | **Bắt buộc bản 12V** — xem R-8. Giắc zin JST-XH 5P cắm thẳng J5–J7 |
| **Driver** | **ULN2003AN** DIP-16 — **U5–U7** | **3** | Mua con IC rời, KHÔNG mua bo breakout (bo có 4 LED, tốn chỗ, không cần) |
| **Driver** | **74HC595-24IO** module — **U10** | **1** | [Shopee](https://shopee.vn/-C%C3%B3-s%E1%BA%B5n-M%E1%BA%A1ch-m%E1%BB%9F-r%E1%BB%99ng-I-O-24-ch%C3%A2n-74HC595-thegioimodule-i.951399259.42633627766) — **không** LED-thanh 8 LED |
| **Passive** | Điện trở axial **10k** — **R4** | 1 | Pull-up `/OE`, **bắt buộc** (boot-state) |
| **Đầu nối** | Cáp nối dài **JST-XH 5P** đực–cái | 3 | Cáp zin của 28BYJ-48 chỉ ~20 cm, không tới được mạch đế |
| Bảo vệ | PTC radial ~3A/30V (RXE030 / MF-R300) — **F1** | 1 | |
| Bảo vệ | TVS **P6KE15A** DO-41 — **D1** | 1 | |
| Passive | Điện trở axial **4k7** — **R1** | 1 | pull-up BUP |
| Passive | Điện trở axial **10k** — **R2**, **R3** | 2 | boot-state, **bắt buộc** |
| Passive | Diode **1N5819** DO-41 — **D2** | 1 | freewheel bơm |
| Passive | Tụ **470µF 25V 105°C** — C20 | **1** | *(was 4 — bỏ C22/C23, C21 đổi sang 100µF)* |
| Passive | Tụ **100µF 25V 105°C** — C21 | 1 | bulk chung cho 3 ULN2003 |
| Passive | Tụ 47µF 25V 105°C (C10) · 100nF 0805 (C11) · R 10Ω 1206 (R10) | 1 mỗi loại | star SNS |
| Nhiệt | **Heatsink** cho TMC2209 | 1 | MKS không kèm sẵn |
| Báo hiệu | **Buzzer active 5V** | 1 | → J15 |
| Đầu nối | Terminal block 2P pitch 5.0 mm — **J1** | 1 | |
| Đầu nối | Socket cái 2×22 pitch 2.54 (cho U1) — **mạ vàng** | 1 bộ | |
| Đầu nối | Socket DIP-16 cho U5–U7 | 3 | Cắm ULN |
| Đầu nối | Header cái 1×06 + 1×24 (J24/J25) | 1+1 | Cắm module 595-24IO |
| Đầu nối | Socket DIP-4 cho U41–U44 (tuỳ chọn) | 4 | |
| Đầu nối | Header đực 2.54: **1×2 ×4** (J19–J22), **1×4 endstop ×3** (J8/J10/J12), 1×3 ×1 (J15), **1×4 ×3** (J14/J16/J18), **1×5 ×4** (J5–J7 + J23), **1×9 ×1** (J17 LCD) | — | mạ vàng |
| **Driver** | **PC817** DIP-4 — **U41–U48** | **8** | Chip rời |
| **Passive** | Điện trở axial **2k2** — LED R41–R44, R49–R52 | 8 | LED series |
| **Passive** | Điện trở axial **10k** — PU R45–R48, R53–R56 | 8 | Pull-up collector |
| **Khí** | **Bơm khí 370 định mức 12V** | **1 + 1 dự phòng** | J16 từ `+12V`; xem §G |
| Khí | Ống silicone **4×6 mm** + tee Y + 2 vòi Ø0,8–1,2 mm | 1 bộ | Cổ bơm typ. Ø4,3 mm |
| PCB | Fab 2 lớp **220×160 mm** | — | route xong R2/R3/D2 + DRC rồi hãy đặt |

---

## B3) Rủi ro đã nhận diện trên đơn hàng

### ✅ R-5 — PC817: **đã đổi sang chip rời DIP-4** (không còn module 4CH)

Board dùng **U41–U48 PC817 DIP-4 ×8** + LED **2k2** + PU **10k**.
IN1–4 = HOME×3 + BUP (bắt buộc). IN5–8 = ESTOP / HOPPER / DOOR / SPARE
(giắc J19–J22) — thay footprint U9 module cũ.

Mạch mỗi kênh: `OPTO_INx —[2k2]— A`, `K→GND`, `+3V3 —[10k]— C=OPTO_OUTx`, `E→GND`.

### ✅ R-1 — TFT ILI9488 3.5" thegioimodule: **XPT2046**, giắc **J17 1×9 + J23 1×5**

Module Shopee: hai hàng đực **9 chân display + 5 chân touch** liền nhau thẳng hàng
→ PCB tách **J17 (LCD)** rồi **J23 (touch)** ngay dưới, cùng cột 2.54 mm — thứ tự giống
[MSP3520 / lcdwiki](https://www.lcdwiki.com/3.5inch_SPI_Module_ILI9488_SKU:MSP3520).

| Jack.pin | Module pin | Silk module | Net board |
|----------|------------|-------------|-----------|
| J17.1–2 | 1–2 | VCC, GND | +3V3, GND |
| J17.3–8 | 3–8 | CS, RST, DC, SDI, SCK, LED | TFT_CS/RST/DC/MOSI/SCK/BL |
| J17.9 | 9 | SDO (MISO LCD) | **NC** (ILI9488 SDO thường không Hi-Z) |
| J23.1–5 | 10–14 | T_CLK, T_CS, T_DIN, T_DO, T_IRQ | SCK, T_CS, MOSI, MISO, T_IRQ(IO6) |

SPI dùng chung: `SCK↔T_CLK`, `MOSI↔T_DIN`; MISO chỉ từ `T_DO`.

**Lưu ý phụ ILI9488** (không đổi chân):

- **SPI của ILI9488 chỉ nhận màu 18-bit (3 byte/pixel)**, không có RGB565.
  480×320×3 = 460 KB/khung → ở SPI 40 MHz là ~92 ms/khung ≈ **11 FPS** khi vẽ
  full màn. LVGL partial refresh vẫn mượt cho HMI tĩnh, nhưng vuốt/kéo sẽ thấy
  chậm. (ST7796 cùng kích thước hỗ trợ RGB565 → nhanh gần gấp đôi.)
- **LCD SDO có thể không tri-state** khi LCD_CS ở mức cao → đọc XPT2046 bị
  nhiễu. Nhiều module đã có trở nối tiếp sẵn; nếu không thì chèn **1k nối
  tiếp trên đường SDO của LCD**, hoặc dùng đệm 74HC125.

### 🔴 R-3 — Bơm thổi BUP: **370 khí 12V** (đã chốt; bỏ buck U8)

**Chốt (2026-08-28):** bơm **370 micro khí 12V** cấp trực tiếp từ rail `+12V` qua
**AOD4184 (J16)**. Chỉ **1 buck MP1584 (U2)** → `+5V` cho ESP32 / TFT / buzzer.

| Tham số | Giá trị |
|---------|---------|
| Chu kỳ | **5 phút** |
| Thời gian ON | **3 giây** |
| Điều khiển | GPIO3 full ON (không PWM) |
| D2 | **1N5819** song song bơm; cathode → **+12V** |

**Mã mua (Shopee VN):** `bơm khí 370 12V` / `động cơ 370 12V máy bơm khí` /
`370 air pump 12V`. Định mức **12V DC** (không 5V/3.7V). Cổ hơi Ø4–4,8 mm.

**Lý do bỏ 5V + U8:** bơm 370 **12V** áp cao hơn, mạnh hơn trên cùng kích thước;
gỡ **U8** giảm BOM, nhiệt và diện tích PCB. MP1584 thứ 2 đã mua → **giữ dự phòng**.

**❌ Không lắp:** bơm 280 3.7V (đã mua); quạt 5015.

### ⚠️ R-2 — MP1584 "phân loại 5V" chưa chắc là bản cố định

Tiêu đề listing ghi "Ra 3.3V 5V 9V 12V **tùy chọn**" → nhiều khả năng vẫn là
module có **biến trở**, chỉ được set sẵn 5 V. Khi hàng về: nhìn có biến trở
không. Nếu có → chỉnh đúng 5,00 V, đo lại, rồi **khoá biến trở bằng keo /
sơn móng tay**. MP1584 không có OVP ngõ ra: biến trở trôi là 12 V thẳng vào
DevKit.

### ⚠️ R-4 — MKS TMC2209 V2.0

- Makerbase là hãng thật, chất lượng chấp nhận được — **không phải clone vô danh**.
- **R_sense của MKS khác BTT** (MKS thường 0,1 Ω). Công thức Vref → dòng khác
  → **phải tra đúng bản V2.0**, đừng dùng công thức của BTT.
- **Không kèm heatsink** → phải mua rời.
- **"Hàng đặt trước"** → có thể về chậm, đừng để chặn tiến độ lắp.

### ✅ R-7 — GPIO: ULN2003 ×3 qua **module 74HC595-24IO** (4 chân ESP)

**U10** = [module Shopee 24 chân / 3×595](https://shopee.vn/-C%C3%B3-s%E1%BA%B5n-M%E1%BA%A1ch-m%E1%BB%9F-r%E1%BB%99ng-I-O-24-ch%C3%A2n-74HC595-thegioimodule-i.951399259.42633627766)
cắm **bên phải ESP32** (J24 CTRL + J25 Q) + R4 LDEN PU. 12 pha đầu → U5–U7; ESP **IO10–13**.

| Phương án | Chân ESP | Ghi chú |
|-----------|----------|---------|
| **Module 3×595 → ULN×3** | **4** | 1_Q0–3→U5; 1_Q4–7→U6; 2_Q0–3→U7 |
| ~~2× DIP trên board~~ | ~~4~~ | đổi sang module cho dễ hàn |

Firmware: **shiftOut 3 byte** (24 bit) mỗi lần latch; spare **IO7/8/14/15**.

### 🔴 R-8 — PHẢI mua đúng bản 28BYJ-48 **12V**

ULN2003 **không có mạch giới hạn dòng** — dòng do đúng điện trở cuộn quyết định.

| Bản | R/pha | Dòng ở 12V | Kết quả |
|-----|-------|-----------|---------|
| 28BYJ-48-**12V** | ~300 Ω | 37 mA | ✅ đúng |
| 28BYJ-48-**5V** | 50 Ω | **240 mA, ~2,9 W** | 🔴 **cháy** |

Tin đăng thường ghi "5V 12V" nghĩa là bán cả hai biến thể. Khi hàng về, **đo điện
trở giữa dây đỏ và một dây bất kỳ**: ~50 Ω là bản 5V (trả lại), ~150–300 Ω là 12V.

### ✅ Điểm tốt trong đơn

- **LRS-50-12** đúng theo khuyến nghị nâng cấp, lại có nắp che cầu đấu tặng kèm.
- **OMRON SS-5GL2** là loại tốt, có sẵn chân NC → đấu fail-safe được ngay.
  *Lưu ý ngược chiều:* việc đổi trở LED opto 1k → 2,2 k (~5 mA) vẫn **trên
  ngưỡng wetting current** của tiếp điểm bạc — đừng hạ thấp hơn 2,2 k, nếu
  không tiếp điểm dễ oxy hoá ở dòng quá nhỏ.
- **AOD4184 / PC817 / BUP-30S / NEMA17** đều đúng loại đã chốt.

---

## C) GPIO map (nhớ nhanh)

| Chức năng | GPIO |
|-----------|------|
| Limit **HOME** trục 1/2/3 (opto OUT1–3) | IO1, 2, 4 |
| BUP (opto OUT4) | IO5 |
| ESTOP / HOPPER / DOOR / SPARE (opto OUT5–8) | IO7, 8, 14, 15 |
| Stepper SER / SRCLK / RCLK / `/OE` | IO10 / 11 / 12 / 13 |
| *(giải phóng khi bỏ DRV8871)* | **IO14, IO15 dự phòng** |
| TMC STEP / DIR / EN | IO16 / 17 / 18 |
| TFT SCK / MOSI / CS / DC | IO39 / 40 / 42 / 21 |
| TFT RST (chung LCD + touch) | IO46 |
| TFT BL (PWM, LEDC) | IO45 |
| Touch SDA / SCL | IO47 / 48 |
| Touch INT | IO41 *(chỗ của MISO cũ)* |
| Buzzer | IO9 |
| EC11 ENC_A / ENC_B | IO38 / IO41 |
| Bơm (AOD4184) | IO3 |
| USB | IO19/20 (để trống) |
| UART0 console | IO43/44 (để trống) |
| BOOT button | IO0 (để trống) |
| **Octal PSRAM chiếm — CẤM dùng** | **IO35 / IO36 / IO37** |

### Ngân sách GPIO (N16R8)

| | Số chân |
|---|---|
| GPIO trên header | 36 |
| Octal PSRAM chiếm | −3 (IO35/36/37) |
| **Dùng được** | **33** |
| Thiết kế dùng | **22** *(was 28)* |
| Để trống bắt buộc (IO0, IO19, IO20, IO43, IO44) | 5 |
| **Dự phòng** | **0** — IO7/8/14/15 lấy cho opto IN5–8; IO6 = T_IRQ |

Đợt đổi sang stepper (2026-08-28) **cởi được nút thắt GPIO**, dù ULN2003 tốn 4
chân/trục thay vì 2: 74HC595 gom 12 pha về 4 chân (−2), và quyết định **chỉ 1 công
tắc HOME mỗi trục** bỏ được 3 limit MAX (−3), và chỉ 4 kênh opto (3 HOME + BUP)
thay vì 8 (−4 GPIO). Từ 0 dự phòng lên **6**.

Cả 6 chân dự phòng đều là **GPIO tự do thật** (vào, ra, PWM, bus phụ — tuỳ ý):

| Chân | Được giải phóng nhờ |
|------|--------------------|
| **IO14, IO15** | Bỏ 3× DRV8871 (mỗi con ăn 2 chân), thay bằng 4 chân qua 74HC595 |
| **IO6, 7, 8** (+ IO9 dùng buzzer) | Chỉ 4 kênh opto rời (U41–U44), không còn 4 kênh module thứ 2 |

**Muốn thêm ngõ vào cách mức 12 V** (E-stop, cảm biến mức phễu, công tắc cửa): thêm
PC817 DIP-4 + 2k2/10k trên rev PCB sau (GPIO dự phòng IO6–8,14,15). Không còn footprint U9.

Hai đánh đổi cũ vẫn giữ (nay đã có đường lùi nhờ 6 chân dự phòng):

1. **Bỏ TFT MISO.** SPI chạy write-only — ILI9341 / ST7796 + LVGL không cần đọc
   thanh ghi. Đặt `TFT_MISO = -1` trong TFT_eSPI / driver panel của LVGL.
   IO41 được giải phóng để nhận `T_INT`.
2. **Bỏ TMC `PDN_UART`.** Cần IO36, đã bị octal PSRAM lấy. Chỉnh dòng bằng biến
   trở Vref trên module; không đọc được `DRV_STATUS` (quá nhiệt / hở pha).

**Đường thoát nếu sau này bí một chân:** hy sinh `T_INT` — poll FT6336 qua I2C ở
50–100 Hz (chỉ tốn ~1% băng thông bus) và **J23.2 / IO41 thành chân dự phòng**.
Ngoài ra đã có sẵn **6 chân dự phòng** (IO6, 7, 8, 9, 14, 15) nên đường thoát này gần
như không bao giờ phải dùng tới.

### Trạng thái chân lúc power-on (trước khi firmware chạy)

ESP32 thả toàn bộ GPIO về high-Z khi reset, nên mọi ngõ vào cơ cấu chấp hành
phải có mức an toàn xác định bằng phần cứng:

| Net | GPIO | Mức an toàn | Cách đảm bảo |
|-----|------|-------------|--------------|
| `/EN_TMC` | IO18 | HIGH = driver tắt | ✅ **R2** 10k pull-up → 3V3 |
| `/BLOWER` | IO3 | LOW = bơm tắt | ✅ **R3** 10k pull-down → GND |
| `/TFT_BL` | IO45 | LOW = đèn nền tắt | ✅ pull-down nội bộ của strapping pin |
| `/TFT_RST` | IO46 | LOW = giữ trong reset | ✅ pull-down nội bộ của strapping pin |
| `/OE_595` | IO13 | HIGH = ngõ 595 Hi-Z ⇒ ULN2003 tắt ⇒ **cả 3 stepper mất điện** | ✅ **R4** 10k pull-up → 3V3. **Bắt buộc** — nội dung thanh ghi 595 lúc boot là ngẫu nhiên, xem R-7 |
| `SER/SRCLK/RCLK` | IO10–12 | bất kỳ (bị `/OE` chặn) | ✅ `/OE` lo |
| `/BUZZER` | IO9 | LOW = im | ✅ module buzzer active có trở kéo base |

### Cảnh báo mua module

- **Chốt DevKitC-1 v1.1.** v1.1 để WS2812 onboard ở GPIO38 → trùng **ENC_A**,
  vô hại (WS2812 chỉ là tải DIN; LED có thể nháy khi xoay núm). v1.0 để ở
  GPIO48 → **trùng T_CS của touch**.
- **Tuyệt đối không route IO35 / IO36 / IO37.** Octal PSRAM của N16R8 dùng
  chúng làm SPIIO4–7 + SPIDQS; chạm vào là chip không boot.
- **Không mua bản hậu tố `V`** (N16R8V / N32R16V): VDD_SPI = 1.8 V kéo
  GPIO47/48 xuống mức logic 1.8 V → hỏng bus touch.
- **TFT phải là loại 3.3 V-native.** J17 chỉ cấp 3V3, không có 5V. Nhiều
  module 2.8" rẻ có LDO + level shifter onboard và cần 5 V ở chân VCC —
  loại đó không dùng được với J17 hiện tại.
- **MP1584 bản ADJ**: chỉnh 5.0 V, đo lại, rồi **khoá biến trở bằng keo /
  sơn móng tay**. MP1584 không có OVP ngõ ra — biến trở trôi là 12 V thẳng
  vào DevKit.
- **PC817 DIP-4**: R LED **2.2k** (R41–R44); pull-up collector **10k** (R45–R48).
  CTR suy giảm theo thời gian dẫn — 2.2k (~5 mA) bền hơn 1k trên module.
- **28BYJ-48**: **BẮT BUỘC bản 12V** — xem R-8. Nhận hàng đo điện trở đỏ↔dây bất kỳ:
  ~50 Ω là bản 5V (trả lại), ~150–300 Ω là 12V.
- **ULN2003AN**: nhớ nối **COM (chân 9) lên `+12V`** — đó là đường về của diode dập
  ngược. Bo breakout bán sẵn đã đấu sẵn, tự làm PCB mà quên là hỏng IC. Chỉ dùng 4/7
  kênh mỗi con.
- **74HC595**: `/OE` (chân 13) **phải** có pull-up 10k (R4) + do IO13 điều khiển;
  `/SRCLR` (chân 10) nối thẳng `+3V3`. Cấp **VCC = 3V3** (không phải 5V) để mức logic
  khớp ESP32 — ở 3,3 V ngõ vào ULN2003 vẫn nhận 667 µA dòng base, gấp 2,7 lần mức
  datasheet cần cho 100 mA, dư thoải mái.
- **TMC2209**: MS1/MS2 không route → thả nổi → mặc định 1/8 microstep +
  MicroPlyer. Hàn jumper xuống GND/3V3 cho xác định thay vì dựa vào mặc định.

---

## D) Review độ bền >3 năm + kinh tế

Thang: **OK** = giữ | **CHỌN KỸ** = cùng giá nhưng đúng SKU | **DỰ PHÒNG** = wear item | **KHÔNG ĐỔI** = quá đắt so với lợi ích.

| Hạng mục | Verdict | Lý do / hành động mua | Ước giá chênh |
|----------|---------|----------------------|---------------|
| PSU Mean Well 12V/**4.2A** | **CHỌN KỸ** | LRS-50-12 thay LRS-35-12 — tránh hiccup OCP khi nhiều motor kẹt cùng lúc | +~50k |
| F1 + D1 | **OK** | Đã trên PCB; bảo vệ rẻ | +5–15k |
| ESP32-S3 DevKitC **N16R8** | **CHỌN KỸ** | Phổ biến ở VN. Vừa đủ GPIO (28/33, dư 0) — bản `v1.1`, **không** hậu tố `V` | baseline |
| MP1584 ×2 | **CHỌN KỸ** | Bản **5V cố định**, derate ≤1.5A; không ADJ / không buck công nghiệp | ~0 |
| TMC2209 | **CHỌN KỸ** | **BTT thật** + heatsink; I_run vừa | +20–40k vs clone |
| PC817 DIP-4 ×4 + R | **OK** | 2k2 LED trên board; bỏ module không chân | −module |
| ~~DRV8871 ×3~~ → **ULN2003 ×3 + 74HC595 ×2** | **OK** | ~15k tổng thay vì 255k; không có gì phải chỉnh dòng; giải luôn bài toán GPIO | **−240k** |
| Capacitor 105°C | **CHỌN KỸ** | 470µ / 47µ long-life | +5–15k |
| Header mạ vàng | **CHỌN KỸ** | Field + socket U1 | +10–20k |
| Limit cơ khí | **CHỌN KỸ** | Omron-class nếu giá gần KW12 thường | +0–30k |
| BUP-30S Autonics | **OK** | Cảm biến chính; thổi bụi giúp tuổi thọ quang | baseline |
| ~~GA12-N20~~ → **28BYJ-48 12V** | **OK** | **Không chổi than**, datasheet >10.000 h vs 81 h thực dùng trong 3 năm. Điều kiện: firmware **cắt cả 4 pha khi dừng** (giữ dòng 24/7 mới là thứ giết nó) | −40k/trục so với N20 |
| Bơm **370 khí 12V** | **CHỌN KỸ** | Duty 3s/5min; +1 dự phòng; **không** buck U8 | +50–90k |
| MP1584 ×1 | **OK** | Con thứ 2 đã mua = dự phòng | 0 |
| TFT 2.8" IPS | **CHỌN KỸ** | Cùng phân khúc, tránh siêu rẻ | +0–30k |
| AOD4184 module | **OK** | Burst dòng thấp | baseline |
| Buck Recom / HMI công nghiệp / JST toàn bộ | **KHÔNG ĐỔI** | Giá nhảy nhiều, lợi ích biên với máy VP | — |

### Ước chi phí module điện (Shopee VN, tham khảo)

| Nhóm | Khoảng (VND) |
|------|----------------|
| PCB carrier + fab nhỏ | tùy qty |
| MCU + 2× buck + TMC BTT + 3× DRV + 2× opto + AOD + F1/D1 | ~800k–1.4tr |
| PSU Mean Well | ~250–400k |
| 3× 28BYJ-48 + NEMA17 + **3 limit** + BUP + buzzer + bơm + ống | ~450k–900k |
| TFT 2.8" touch | ~150–350k |
| **Tổng điện + cơ điện điển hình (1 máy)** | **~2–3.5tr** (chưa cơ khí khung / in 3D) |

→ Tối ưu kinh tế: **giữ kiến trúc hiện tại**; chỉ “chọn đúng SKU” (BTT, MP1584 fixed 5V, cap 105°C, pin vàng, limit tốt) thay vì đổi sang linh kiện công nghiệp đắt.

---

## E) Việc cần đo trước khi fab PCB

1. **PC817 DIP-4** ×4 + R 2k2/10k — chuẩn JEDEC, không đo module.  
2. **MP1584** Shopee [41383641614](https://shopee.vn/MP1584EN-Mini-DC-Buck-41383641614) fixed 5V — pad span **18.54 × 10.67 mm** (8 lỗ, 2 lỗ/chân).  
3. ~~DRV8871 footprint~~ → **giắc JST-XH 5P** (J5–J7): đo pitch/pad thực tế của cáp
   nối dài mua kèm. U5–U7 / U10 / U11 là DIP-16 tiêu chuẩn, không cần đo.  
4. **ESP32-S3-DevKitC** row 25.4 / 44 pin.  
5. **AOD4184** jack J16 khớp dây.

```
python gen_power_carrier.py
```

---

## G) Yêu cầu độ bền >3 năm — từng module (chốt 2026-08-28)

**Mục tiêu:** máy văn phòng ~20 cm, chạy ổn định **≥3 năm** với chu kỳ thổi BUP:

| Tham số | Giá trị |
|---------|---------|
| Chu kỳ | **5 phút** (300 s) |
| Thời gian thổi | **3 giây** / lần |
| Chu kỳ / giờ | 12 |
| Thời gian ON / giờ | 36 s (= 0,01 h) |
| Giả định VP | 8 h/ngày × 250 ngày/năm × 3 năm |
| Chu kỳ 3 năm (VP) | **72.000** |
| Giờ ON tích lũy 3 năm (VP) | **~60 h** |
| Worst-case 24/7 × 3 năm | **216.000 chu kỳ / ~180 h ON** |

Thang đánh giá: **✅ đạt** | **⚠️ chọn đúng SKU** | **🔴 wear / thay định kỳ** | **❌ không dùng**

### G.1 Bảng mã sản phẩm + yêu cầu

| Ref | Mã / SKU chốt | Từ khóa Shopee (VN) | Yêu cầu kỹ thuật (>3 năm) | Kiểm tra khi nhận hàng | Verdict |
|-----|---------------|---------------------|---------------------------|------------------------|---------|
| **PSU** | **Mean Well LRS-50-12** | `Mean Well LRS-50-12` | 12 V / 4,2 A; MTBF typ. >500k h (MIL-HDBK); nhiệt độ 0–70 °C | Tem Mean Well, đo 12,0 V không tải | ✅ đã mua |
| **F1** | **RXE030** hoặc MF-R300 | `PTC 3A 30V` | I_hold ~3 A; khôi phục sau ngắn mạch | — | ✅ |
| **D1** | **P6KE15A** | `P6KE15A DO-41` | Clamp 12 V rail | Vạch cathode đúng chiều | ✅ |
| **U1** | **ESP32-S3-DevKitC-1-N16R8** rev **v1.1** | `DevKitC-1 N16R8 Type-C` | Không hậu tố `V`; USB-C; đủ GPIO | WS2812 onboard ở IO38 = ENC_A (v1.1) | ✅ đã mua — ⚠️ kiểm rev |
| **U2** | **MP1584EN** module **5 V cố định** | `MP1584 5V cố định` | **1 module**; derate ≤1,5 A; không ADJ | Không potentiometer; đo 5,00 V | ⚠️ đã mua ×2 — lắp **1**, 1 dự phòng |
| **U3** | **TMC2209** Makerbase **V2.0** + heatsink | `MKS TMC2209 V2.0` | R_sense MKS; I_run vừa; có tản | Heatsink gắn; tra Vref V2.0 | ⚠️ đã mua |
| **U41–U44** | **PC817** DIP-4 | `PC817 DIP` | LED **2,2 k** (R41–R44); PU **10k** (R45–R48) | Socket tùy chọn | ✅ |
| **U5–U7** | **ULN2003AN** DIP-16 | `ULN2003AN DIP` | COM(9)→`+12V`; chỉ 4/7 kênh dùng | IC rời, không bo LED | ⚠️ chưa mua |
| **U10** | **74HC595-24IO** module | [Shopee 42633627766](https://shopee.vn/-C%C3%B3-s%E1%BA%B5n-M%E1%BA%A1ch-m%E1%BB%9F-r%E1%BB%99ng-I-O-24-ch%C3%A2n-74HC595-thegioimodule-i.951399259.42633627766) | 3×595; hàn header rồi cắm J24/J25; VCC=3V3; đo khớp lỗ trước fab | Tem thegioimodule; LDSI/LDSCK/LDSTR/LDEN | 🔴 **MUA** ×1 |
| **Motor 3 trục** | **28BYJ-48-12V** | `28BYJ-48 12V` (không ghi 5V12V chung) | R đỏ↔pha ~150–300 Ω; firmware **cắt 4 pha khi dừng** | Đo Ω: ~50 Ω = bản 5V → trả | ⚠️ chưa mua |
| **NEMA17** | 42×34 mm + **TMC2209** | `NEMA17 42` | I_run hợp lý; không stall lâu | — | ✅ |
| **Limit ×3** | **OMRON SS-5GL2** | `SS-5GL2` / `SS-5GL2T` | NC fail-safe; ≥10⁶ chu kỳ cơ | Chân NC vào opto | ✅ |
| **BUP** | **Autonics BUP-30S** | `BUP-30S Autonics` | U-slot 30 mm; NPN; 12–24 V; IP66 | Tem Autonics; thổi TX+RX | ✅ đã mua |
| **Bơm khí** | **370 micro khí 12V DC** | `bơm khí 370 12V` / `370 air pump 12V` | Định mức **12V**; I≤300 mA; cổ Ø4–4,8 mm; ≥500 h liên tục (brushed typ.) | Ghi 12V trên motor; thử áp trên kính BUP 3s | 🔴 **MUA** ×2 |
| ~~Bơm cũ~~ | ~~280 3.7V~~ | — | Không lắp | — | ❌ |
| **J16** | Module **AOD4184** | `AOD4184 MOSFET` | Full ON 3 s; tải ≤2 A @12V; **D2** freewheel | MOSFET AOD4184A; có opto | ✅ đã mua |
| **D2** | **1N5819** DO-41 | `1N5819` | Freewheel song song bơm; cathode→**+12V** | Vạch→+12V | ⚠️ chưa hàn |
| **R3** | **10k** axial | `điện trở 10k` | Pull-down `/BLOWER` (IO3 strapping) | — | ⚠️ chưa hàn |
| **Ống khí** | Silicone **4×6 mm** + tee Y + 2 nozzle | `ống silicone 4mm` `tee Y 4mm` | Lỗ vòi **0,8–1,2 mm**; thổi TX/RX, không thổi vào máng viên | Thử áp trên kính BUP | ⚠️ chưa mua |
| **Buzzer** | Active **5 V** | `buzzer 5V active` | Logic 3V3-compatible | — | ⚠️ chưa mua |
| **TFT** | ILI9488 + XPT2046 J17+J23 | `MSP3520` | VCC=3V3; LCD SDO NC | Cắm đúng pin1 VCC | ✅ |

### G.2 Bơm khí — chốt mua

**Mã chốt:** **370 micro diaphragm air pump, 12 V DC** (motor 370, đầu bơm màng).

| Hạng mục | Thông số |
|----------|----------|
| Điện áp | **12 V DC** (cùng rail PSU / J16 pin 3) |
| Loại | Brushed 370 phổ biến VN; BLDC 12V nếu listing rõ |
| Dòng | ≤300 mA @ 12V (AOD4184 + LRS-50 dư) |
| Áp / lưu lượng | ≥50 kPa khí; đủ thổi BUP TX+RX qua tee |
| Cổ hơi | Ø **4,0–4,8 mm** (ống silicone 4×6) |
| Tuổi thọ | ≥**500 h** liên tục (datasheet brushed) >> 60 h ON / 3 năm VP |
| Số lượng | **1 lắp + 1 dự phòng** |
| Giá tham khảo VN | ~50–90k/con |

**Từ khóa Shopee:**

1. `bơm khí 370 12V`
2. `động cơ 370 12V máy bơm khí hút chân không`
3. `370 air pump 12V diaphragm`

**Đấu nối J16 + module AOD4184:**

```
+12V (J16-3) → V+ module → MOSFET → bơm (+)
GND (J16-2)  → module GND; bơm (−) → FAN− (J16-4) / BLW_RET + D2
PWM (J16-1)  → IO3
```

**❌ Không dùng:** bơm 5V/3.7V; buck U8; quạt 5015.

### G.3 Firmware thổi BUP (tham số lưu code)

```c
#define BLOW_INTERVAL_MS   (5 * 60 * 1000)   // 5 phút
#define BLOW_DURATION_MS   3000              // 3 giây
// Điều kiện: chute_empty && !motor_moving; mask BUP_IN trong BLOW_DURATION_MS
// Điều khiển: digitalWrite(BLOWER, HIGH) — không PWM
```

Nếu sau thử tải áp yếu: giảm `BLOW_DURATION_MS` → **2000** trước khi đổi bơm.

### G.4 Margin độ bền (tóm tắt)

| Module | VP 8h×3y | 24/7×3y | Ghi chú |
|--------|----------|---------|---------|
| LRS-50-12 | ✅ dư | ✅ | Bơm 12V ~3 W thêm vào budget |
| MP1584 ×1 (U2) | ✅ | ✅ | Bỏ U8 |
| 370 khí 12V | ✅ >>500 h rating | ✅ | ~60 h ON / 3y VP |
| BUP-30S + thổi | ✅ | ✅ | Autonics + khô, không nước |
| 28BYJ-48 12V | ✅ >>10k h | ✅ | Cắt pha khi dừng |
| SS-5GL2 | ✅ 30M ops | ✅ | — |
| AOD4184 + D2 | ✅ | ✅ | ON/OFF 3s, MOSFET mát |

---

## F) Lịch sử quyết định (tóm tắt)

| Đã bỏ / không dùng | Đã chọn thay |
|--------------------|--------------|
| ESP32 DevKit V1 + MCP23017 | ESP32-S3 DevKitC |
| Mini560 | MP1584EN ×**1** (logic 5V) |
| U8 buck +5V_BLW | Bơm **370 12V** từ rail +12V |
| Quạt 5015 | Bơm **370 12V** (3 s / 5 phút) |
| Bơm 5V / 280 3.7V | Bơm **370 12V** |
| Limit quang hành trình | Limit **cơ khí** (chỉ jack trên board) |
| **DRV8871 ×3 + GA12-N20 ×3** (chổi than) | **ULN2003 ×3 + 28BYJ-48 12V ×3** (2026-08-28) |
| **6 limit (MIN+MAX × 3 trục)** | **3 limit HOME** — stepper đếm bước lo giới hạn, cữ cứng lo va chạm |
| Nối thẳng 12 pha vào GPIO (tràn 1 chân) | **2× 74HC595** nối tiếp — 12 pha còn 4 chân |
| PSU DIN DDR quá to | Mean Well 12V/3A |
| Buck / HMI công nghiệp đắt | Không (ràng buộc giá) |
