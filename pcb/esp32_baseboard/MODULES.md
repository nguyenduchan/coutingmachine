# Counting machine — danh sách module (ghi nhớ)

**Cập nhật:** 2026-09-04 (**chưa mua** linh kiện; giỏ Shopee = dự định)  
**PCB:** `esp32_baseboard` (generator: `gen_power_carrier.py`)  
**BOM audit:** [`BOM.md`](BOM.md)  
**Mục tiêu:** văn phòng ~20 cm, **ổn định >3 năm**, **tổng giá kinh tế**.

> ✅ **Generator đã đồng bộ.** Carrier: **D3/F1/D1 + PC817×4 trên board**, **U5–U7→M3**.
> Field I/O = **JST-XH keyed** (HOME XH-2, BUP/BLW/ENC XH-4, BZ XH-3). Daughter ULN = **pin header 2.54**.
> Snap panel: [`modules/`](modules/) (`gen_submodules.py`, JLCPCB 2L mousebite) — **M3 only**.
> **U10** 74HC595-24IO bên phải ESP32; **M3 ULN2003 ×3**; board ~**180×145**.
> Motor kick: C21=220µ, C24/C25 100n, D2=SS24 @ blower (TVS rail = D1 — không D4 trùng).
> Đã bỏ: J2, J5–J7, J19–J22, D4, **J30/M1**, **J31A/B/M2**.

### Không cắm trực tiếp → giắc + board rời

| Không cắm flush | Lý do | Giắc carrier | Board rời |
|-----------------|-------|--------------|-----------|
| D3+F1+D1 | Hàn trên carrier | — | **trên PCB chính** |
| PC817 ×4 | Hàn trên carrier (layout 4 cột) | — | **trên PCB chính** |
| ULN2003 Shopee | Chỉ Dupont, không mate PCB | **U5–U7** 1×6 | **M3** ×3 |

Cắm được trực tiếp: U1 ESP32, U2 MP1584, U3 TMC2209, U10 595-24IO, TFT J17+J23.  
Ngoài board qua cáp: AOD4184→J16, BUP→J14, HOME→J8/10/12, BZ→J15, ENC→J18.

Nguồn 12V ngoài → J1 → **D3 → F1 → D1** → `+12V`. Field/HOME → **PC817×4 trên carrier**.

```
PSU 12V ──J1── D3+F1+D1 ── +12V ──┬── U2 MP1584 ── +5V ── U1 / TFT / buzzer
                                      ├── J16 AOD4184 + D2 ── bơm 370 12V
                                      ├── U3 TMC2209 + C20/C24 ── NEMA17
                                      ├── U5–U7 ULN + C21/C25 ── 28BYJ
                                      └── R10/C10/C11 ── +12V_SNS ── limit + BUP
Field ── PC817×4 (U41–U44) ── GPIO
```

---

## A) Trên baseboard (hàn / cắm socket)

| Ref | Module / linh kiện | Size typ. | SL | Vai trò | Pin / net chính |
|-----|-------------------|-----------|----|---------|-----------------|
| **J1** | Terminal 2P pitch 5.0 mm | ~10×8 | 1 | Vào 12V PSU | `+12V_RAW`, GND |
| **D3** | **SS54** Schottky | DO-41 | 1 | Series chống ngược | A←RAW K→PRE |
| **F1** | Đế 5×20 + ống **T3.15A** | PCB clips | 1 | Cầu chì rút ống | PRE→+12V |
| **D1** | **P6KE15A** TVS | DO-41 | 1 | Clamp +12V | K=+12V A=GND |
| ~~**J30/M1**~~ | — | — | **XOÁ** | Bảo vệ hàn carrier | — |
| ~~**J31A/B / M2**~~ | — | — | **XOÁ** | Opto hàn carrier | — |
| **U41–U44** | **PC817** DIP-4 | ~6×7 | **4** | HOME1–3 + BUP opto | 4 cột như layout M2 cũ |
| **R41–R44 / R45–R48** | 2k2 / 10k axial | — | 4+4 | LED / collector PU | |
| **C26** | 100n 0805 | — | 1 | HF `+12V_SNS` @ opto | |
| **U1** | **ESP32-S3-DevKitC-1 N16R8** (bản `v1.1`, **không** hậu tố `V`) | ~63×25 | 1 | MCU | Socket 2×22 @2.54, row 25.4; cấp **5V** từ U2 |
| **U2** | **MP1584EN** fixed **5V** ([Shopee 41383641614](https://shopee.vn/MP1584EN-Mini-DC-Buck-41383641614)) | ~22×17 | 1 | Buck logic **duy nhất** | `+12V` → `+5V`; pad 18.54×10.67 mm |
| **U3** | **TMC2209** stepstick **BTT** + heatsink | ~15×20 | 1 | Driver NEMA17 | VM=12V, VIO=3V3; STEP/DIR/EN |
| **D3/F1/D1** | trên carrier | — | 1 | Bảo vệ nguồn | sau J1 |
| ~~**U4/U9**~~ | ~~PC817 4CH module~~ | — | **BỎ** | Module Shopee không có hàng chân | — |

> ⚠️ **Không phải cách ly galvanic.** `GND` chung (một PSU). Vai trò: **hạ 12 V → 3.3 V + chắn xung field**.
| **U5** | Socket **1×6** → **M3** | pitch 2.54 | 1 | Stepper trục 1; 28BYJ trên **M3 JST** | IN ← SR_Q0–3; VCC=`+12V` |
| **U6** | Socket **1×6** → **M3** | pitch 2.54 | 1 | Stepper trục 2 | IN ← SR_Q4–7; VCC=`+12V` |
| **U7** | Socket **1×6** → **M3** | pitch 2.54 | 1 | Stepper trục 3 | IN ← SR_Q8–11; VCC=`+12V` |
| **M3** / ULN Shopee | Module ULN+JST **hoặc** `m3_uln2003` | ~35×32 | **3** | Gần 28BYJ; cáp từ U5–U7 | Ưu tiên combo Shopee trong giỏ |
| **U10** | **74HC595-24IO** module (3×595) | ~66×20 | **1** | [Shopee thegioimodule](https://shopee.vn/-C%C3%B3-s%E1%BA%B5n-M%E1%BA%A1ch-m%E1%BB%9F-r%E1%BB%99ng-I-O-24-ch%C3%A2n-74HC595-thegioimodule-i.951399259.42633627766) — **bên phải ESP32** | J24 CTRL + J25 Q; 12/24 → ULN |
| **J24** | Header cái **1×06** | pitch 2.54 | 1 | Cắm CTRL module | LDEN GND VCC LDSI LDSTR LDSCK |
| **J25** | Header cái **1×24** | pitch 2.54 | 1 | Cắm Q module | 1_Q0…3_Q7; Q0–11 → ULN |
| **R4** | Điện trở axial **10k** | pitch ~7.5 | 1 | Pull-up LDEN/`OE` (boot Hi-Z) | `OE_595` → `+3V3` |
| **R1** | Điện trở axial **4k7** | pitch ~7.5 | 1 | Pull-up BUP NPN | `+12V_SNS` → OUT |
| **R2** | Điện trở axial **10k** | pitch ~7.5 | 1 | Pull-up EN của TMC2209 | `/EN_TMC` → `+3V3` |
| **R3** | Điện trở axial **10k** | pitch ~7.5 | 1 | Pull-down PWM bơm | `/BLOWER` → GND |
| **D2** | **SS24** (DO-41) | axial | 1 | Freewheel bơm 370 12V | `+12V` ↔ `/BLW_RET` |
| **R10** | 10Ω 1206 | — | 1 | Lọc star SNS | `+12V` → `+12V_SNS` |
| **C10** | 47µF radial 25V (105°C) | Ø~6 | 1 | Bulk SNS | `+12V_SNS`–GND |
| **C11** | 100nF 0805 | — | 1 | HF SNS | `+12V_SNS`–GND |
| **C20** | 470µF 25V radial (105°C) | Ø~8 | 1 | Bulk @ TMC2209 VM | `+12V`–GND |
| **C21** | **220µF** 25V radial (105°C) | Ø~6 | 1 | Bulk **dùng chung** cho COM của U5–U7 | `+12V`–GND |
| ~~**C22–C23**~~ | ~~470µF~~ | — | **BỎ** | 3 ULN2003 chỉ hút ~74 mA/trục (N20 stall là 1,5–2 A) — một tụ chung là đủ | — |

### Jack trên board (chỉ chân cắm — không gắn sensor/motor lên PCB)

| Ref | Header | SL | Cắm ra ngoài |
|-----|--------|----|--------------|
| **J2** | ~~1×04~~ | **XOÁ** | Trùng Mot trên U3 TMC2209 — NEMA17 hàn/cắm thẳng chân Mot module |
| ~~**J4**~~ | ~~1×06~~ | **XOÁ** | Trùng hoàn toàn J8/J10/J12/J14 (`OPTO_IN1…IN4` từng chân). Phía vào của U4 nay lấy **`+12V_SNS`** — cùng rail các giắc limit đã mang — thay cho chân `OPTO_VCC_I` riêng |
| ~~**J5**~~ | ~~1×05~~ | **XOÁ** | 28BYJ cắm thẳng JST trên **ULN2003 module** (U5) — không giắc thừa trên carrier |
| ~~**J6**~~ | ~~1×05~~ | **XOÁ** | như J5 → U6 |
| ~~**J7**~~ | ~~1×05~~ | **XOÁ** | như J5 → U7 |
| **J8** | **JST-XH 2P** keyed | 1 | HOME trục 1 — **công tắc hành trình dry NC** + dây XH-2 (SIG/`+12V_SNS`); **không** module CNC 1×04 |
| **J10** | **JST-XH 2P** keyed | 1 | HOME trục 2 (như J8 → OPTO_IN2) |
| **J12** | **JST-XH 2P** keyed | 1 | HOME trục 3 (như J8 → OPTO_IN3) |
| ~~**J19–J22**~~ | ~~1×02~~ | **XOÁ** | Field IN5–8 bỏ (GPIO reclaim) |
| **J14** | **JST-XH 4P** keyed | 1 | BUP-30S (+12 / GND / OUT / CTRL) |
| **J15** | **JST-XH 3P** keyed | 1 | Buzzer 5V (VCC / GND / SIG) |
| **J16** | **JST-XH 4P** keyed | 1 | AOD4184 (PWM / GND / **+12V** / FAN−) |
| **J17** | **1×09** LCD | 1 | MSP3520 pins 1–9: VCC…SDO; SDO **NC** |
| **J23** | **1×05** touch | 1 | MSP3520 pins 10–14: T_CLK…T_IRQ — **liền dưới J17**, cùng cột, đúng thứ tự module |

**J3:** không dùng.

---

## B) Trạng thái mua — **CHƯA MUA gì** (cập nhật 2026-09-04)

> Người dùng xác nhận: **chưa có linh kiện nào trong tay.**  
> Bảng dưới = **giỏ Shopee dự định** (đã mapping BOM). Phần còn thiếu = §B2.

### B1) Giỏ dự định — khớp BOM (nên giữ)

| # | Linh kiện (giỏ) | SL | Giá giỏ | BOM | Ghi chú |
|---|-----------------|----|---------|-----|---------|
| 1 | Mean Well **LRS-50-12** | 1 | 304.000 | J1 | PSU |
| 2 | **ESP32-S3 N16R8** Type-C | 1 | 200.316 | U1 | Chọn đúng **N16R8**; kiểm **v1.1** (không hậu tố V) |
| 3 | **MP1584EN** phân loại **5V** | 1 | 21.000 | U2 | ⚠️ R-2: có thể vẫn ADJ — khoá biến trở |
| 4 | **AOD4184** module | 1 | 25.000 | J16 | |
| 5 | **MKS TMC2209 V2.0** | 1 | 115.548 | U3 | Thêm **heatsink** (§B2) |
| 6 | **NEMA17** ~40 mm 2A | 1 | 213.270 | U3 Mot | |
| 7 | **28BYJ(12V) + ULN2003** | **3** | 177.000 | Motor + driver gần motor | Thay fab M3; nối 6 dây → U5–U7 |
| 8 | **74HC595-24IO** | 1 | 55.000 | J24+J25 | |
| 9 | TFT **ILI9488 3.5"** SPI | 1 | 395.000 | J17+J23 | |
| 10 | Autonics **BUP-30S** | 1 | 480.000 | J14 | |
| 11 | **OMRON SS-5GL2** | **3** | 96.000 | HOME J8/10/12 | Thêm giắc/dây XH-2 (§B2) |
| 12 | **PC817** ×50 | 1 gói | 90.000 | M2 ×4 | Dư OK |
| 13 | Điện trở **10k** ×100 | 1 | 5.545 | R2/R3/R4 + M2 PU | |
| 14 | Điện trở **2.2k** ×100 | 1 | 5.545 | M2 LED | |
| 15 | Bơm **370 12V** | 1 | 50.700 | qua AOD4184 | Nên +1 dự phòng (§B2) |
| 16 | **EC11** encoder | 1 | 19.600 | J18 | |

**Tạm tính giỏ B1 (điện chính):** ~**2.253.524₫** (chưa voucher / chưa §B2).

### B1b) Giỏ — dụng cụ / cơ khí / tùy chọn

| Linh kiện | SL | Giá | Ghi chú |
|-----------|----|-----|---------|
| Gen co nhiệt 560 PCS | 1 | 58.000 | Tùy chọn bọc dây |
| Thiếc 0.8 100g | 1 | 59.000 | Dụng cụ |
| Mũi hàn 900M T-K | 1 | 31.900 | Dụng cụ |
| Núm WH148 ×10 | 1 | 63.000 | Thừa — EC11 chỉ cần **1** núm |
| Tay quay taro M3–M8 | 1 | 129.999 | Cơ khí |
| Thanh trượt Ø8×100 | 1 | 17.000 | Trục NEMA (không thay Ø5 slide) |
| Khớp mềm 5–8 mm ×2 | 1 | 66.800 | NEMA |
| Khớp mặt bích 8 mm ×2 | 1 | 80.800 | NEMA |
| Gối KFL08 ×5 | 1 | 113.000 | NEMA |

### B2) Còn thiếu — bắt buộc trước khi fab/lắp board

| Nhóm | Linh kiện | SL | Ghi chú |
|------|-----------|----|---------|
| Bảo vệ **M1** | **SS54** + đế 5×20 + ống **T3.15A** + **P6KE15A** | 1 bộ | Daughter M1 (rút ống khi chảy) |
| Passive | **SS24** DO-41 | 1 | D2 flyback |
| Passive | **4k7** axial (gói) | ≥1 | R1 |
| Passive | **10Ω 1206** | ≥1 | R10 |
| Passive | **100n 0805** | ≥7 | C11/C24/C25 + M2/M3 |
| Passive | **47µF** / **220µF** / **470µF** 25V | 1+1+1 | C10 / C21 / C20 |
| Nhiệt | **Heatsink** TMC2209 | 1 | |
| Báo hiệu | **Buzzer active 5V** | 1 | J15 |
| Khí | Bơm 370 **dự phòng** | +1 | khuyến nghị |
| Khí | Ống silicone 4×6 + tee Y + vòi | 1 bộ | |
| Đầu nối | Terminal 2P 5.0 | 1 | J1 |
| Đầu nối | Socket 2×22 ESP32 | 1 | U1 |
| Đầu nối | Header cái 1×4/5/6/9/24 | theo [`BOM.md`](BOM.md) §D | |
| Đầu nối | JST-XH cái 2P×3 · 3P×1 · 4P×3 | field | |
| Đầu nối | Cáp 6 lõi U5–U7 ↔ ULN module | 3 | |
| PCB | Carrier + panel M1\|M2 (M3 optional nếu dùng ULN Shopee) | — | JLCPCB |
| Cơ khí slide | Trục Ø5 ×115 mm | **6** | Không dùng Ø8 |

**Không mua:** bơm 280 3.7V · DRV8871 · GA12-N20 · PC817 module 4CH · 1N5819 (dùng SS24).

---

## B3) Rủi ro thiết kế / khi nhận hàng

### ✅ R-5 — PC817: **trên M2** (DIP-4 ×4) — không còn trên carrier

**M2** mang **PC817 ×4** + LED **2k2** + PU **10k** (HOME×3 + BUP).  
Không còn U41–U48 / field IN5–8 trên carrier.

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
| D2 | **SS24** song song bơm; cathode → **+12V** |

**Mã mua (Shopee VN):** `bơm khí 370 12V` / `động cơ 370 12V máy bơm khí` /
`370 air pump 12V`. Định mức **12V DC** (không 5V/3.7V). Cổ hơi Ø4–4,8 mm.

**Lý do bỏ 5V + U8:** bơm 370 **12V** áp cao hơn, mạnh hơn trên cùng kích thước;
gỡ **U8** giảm BOM, nhiệt và diện tích PCB. Chỉ mua **1× MP1584** (không cần con thứ 2 trừ khi muốn dự phòng).

**❌ Không mua / không lắp:** bơm 280 3.7V; quạt 5015.

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
| MP1584 ×1 | **OK** | Chỉ 1 con; kiểm cố định 5V (R-2) | baseline |
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
| **PSU** | **Mean Well LRS-50-12** | `Mean Well LRS-50-12` | 12 V / 4,2 A; MTBF typ. >500k h (MIL-HDBK); nhiệt độ 0–70 °C | Tem Mean Well, đo 12,0 V không tải | 🔴 **chưa mua** (trong giỏ) |
| **D3** | **SS54** trên **M1** | `SS54 DO-41` | Series sau J1; A←RAW K→F1 | Vạch cathode đúng chiều | 🔴 **chưa mua** |
| **F1** | Đế PCB 5×20 + ống **T3.15A** trên **M1** | `Fuse_Holder_5x20` | Chảy → rút ống, cắm ống mới | Mua thêm ống dự phòng | 🔴 **chưa mua** |
| **D1** | **P6KE15A** trên **M1** | `P6KE15A DO-41` | Clamp 12 V rail | Vạch cathode đúng chiều | 🔴 **chưa mua** |
| **U1** | **ESP32-S3-DevKitC-1-N16R8** rev **v1.1** | `DevKitC-1 N16R8 Type-C` | Không hậu tố `V`; USB-C; đủ GPIO | WS2812 onboard ở IO38 = ENC_A (v1.1) | 🔴 **chưa mua** (trong giỏ) |
| **U2** | **MP1584EN** module **5 V cố định** | `MP1584 5V cố định` | **1 module**; derate ≤1,5 A; không ADJ | Không potentiometer; đo 5,00 V | 🔴 **chưa mua** (trong giỏ — ⚠️ R-2) |
| **U3** | **TMC2209** Makerbase **V2.0** + heatsink | `MKS TMC2209 V2.0` | R_sense MKS; I_run vừa; có tản | Heatsink gắn; tra Vref V2.0 | 🔴 **chưa mua** (TMC trong giỏ; heatsink thiếu) |
| **M2** | **PC817** DIP-4 ×4 + 2k2/10k | `PC817 DIP` | LED **2,2 k**; PU **10k**; cắm J31A/B | — | 🔴 PC817+R trong giỏ; tụ 100n thiếu |
| **U5–U7** | Module **ULN2003+28BYJ 12V** (Shopee) | `28BYJ(12V) + ULN2003` | **Gần motor**; cáp từ socket 1×6 | COM=+12V; đo Ω đỏ↔pha ~150–300 | 🔴 **chưa mua** (trong giỏ ×3) |
| **U10** | **74HC595-24IO** module | [Shopee 42633627766](https://shopee.vn/-C%C3%B3-s%E1%BA%B5n-M%E1%BA%A1ch-m%E1%BB%9F-r%E1%BB%99ng-I-O-24-ch%C3%A2n-74HC595-thegioimodule-i.951399259.42633627766) | 3×595; hàn header rồi cắm J24/J25; VCC=3V3 | Tem thegioimodule | 🔴 **chưa mua** (trong giỏ) |
| **Motor 3 trục** | *(kèm combo ULN ở trên)* | — | Firmware **cắt 4 pha khi dừng** | — | cùng dòng U5–U7 |
| **NEMA17** | 40–42 mm + **TMC2209** | `NEMA17 42` | I_run hợp lý; không stall lâu | — | 🔴 **chưa mua** (trong giỏ) |
| **Limit ×3** | **OMRON SS-5GL2** | `SS-5GL2` | NC fail-safe; ≥10⁶ chu kỳ cơ | Chân NC vào opto | 🔴 **chưa mua** (trong giỏ) |
| **BUP** | **Autonics BUP-30S** | `BUP-30S Autonics` | U-slot 30 mm; NPN; 12–24 V; IP66 | Tem Autonics; thổi TX+RX | 🔴 **chưa mua** (trong giỏ) |
| **Bơm khí** | **370 micro khí 12V DC** | `bơm khí 370 12V` | Định mức **12V**; I≤300 mA; cổ Ø4–4,8 mm | Ghi 12V trên motor | 🔴 **1 trong giỏ** — thiếu dự phòng |
| **J16** | Module **AOD4184** | `AOD4184 MOSFET` | Full ON 3 s; tải ≤2 A @12V; **D2 SS24** | MOSFET AOD4184A | 🔴 **chưa mua** (trong giỏ) |
| **D2** | **SS24** DO-41 | `SS24` | Freewheel; cathode→**+12V** | Vạch→+12V | 🔴 **chưa mua** |
| **R3** | **10k** axial | *(gói 10k trong giỏ)* | Pull-down `/BLOWER` | — | 🔴 gói trong giỏ |
| **Ống khí** | Silicone **4×6 mm** + tee Y + 2 nozzle | `ống silicone 4mm` | Lỗ vòi **0,8–1,2 mm** | — | 🔴 **chưa mua** |
| **Buzzer** | Active **5 V** | `buzzer 5V active` | Logic 3V3-compatible | — | 🔴 **chưa mua** |
| **TFT** | ILI9488 + XPT2046 J17+J23 | `MSP3520` | VCC=3V3; LCD SDO NC | Cắm đúng pin1 VCC | 🔴 **chưa mua** (trong giỏ) |
| **ENC** | EC11 | `EC11` | A/B → J18 | — | 🔴 **chưa mua** (trong giỏ) |

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
