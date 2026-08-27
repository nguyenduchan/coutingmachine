# Counting machine — danh sách module (ghi nhớ)

**Cập nhật:** 2026-08-28  
**PCB:** `esp32_baseboard` (generator: `gen_power_carrier.py`)  
**Mục tiêu:** văn phòng ~20 cm, **ổn định >3 năm**, **tổng giá kinh tế** (chỉ nâng cấp khi chênh ít).

> 🔴 **CHƯA ĐỒNG BỘ — CHẶN FAB (2026-08-28).** Tài liệu này đã cập nhật sang
> **28BYJ-48 + ULN2003 + 74HC595**, **1 công tắc HOME mỗi trục**. Nhưng
> `gen_power_carrier.py` **vẫn đang sinh 3× DRV8871 + 6 jack limit + J5–J7 loại 1×02**.
> Phải sửa generator rồi chạy lại DRC trước khi đặt PCB. Việc còn phải làm ở generator:
> footprint/symbol ULN2003AN + 74HC595 (DIP-16) thay `DRV8871_Module`; J5–J7 đổi
> 1×02 → 1×05; thêm R4; đấu COM(9) của U5–U7 lên `+12V`; **xoá J9/J11/J13 và U9**;
> J4 1×10 → 1×06; bỏ C22/C23.

Nguồn 12V ngoài → J1 → F1 PTC → `+12V` (+ D1 TVS) → các rail / driver.

```
PSU 12V ──J1── F1 ── +12V ──┬── U2 MP1584 ── +5V ── U1 / TFT / buzzer
                            ├── U8 MP1584 ── +5V_BLW ── J16 AOD4184 ── bơm màng
                            ├── U3 TMC2209 ── J2 NEMA17
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
| **U2** | **MP1584EN** fixed **5V** | ~22×17 | 1 | Buck logic | `+12V` → `+5V` |
| **U8** | **MP1584EN** fixed **5V** | ~22×17 | 1 | Buck riêng bơm | `+12V` → `+5V_BLW` |
| **U3** | **TMC2209** stepstick **BTT** + heatsink | ~15×20 | 1 | Driver NEMA17 | VM=12V, VIO=3V3; STEP/DIR/EN |
| **U4** | **PC817 4CH** | ~48×38 | 1 | Level-shift 4 ngõ vào field | IN1–3 = **limit HOME trục 1/2/3**, IN4 = **BUP** → IO1, 2, 4, 5 |
| ~~**U9**~~ | ~~PC817 4CH~~ | ~48×38 | **DNP** | **KHÔNG HÀN** — sau khi bỏ 3 limit MAX chỉ còn 4 ngõ vào field, vừa đúng một con U4. Giữ footprint, giải phóng **IO6, 7, 8, 9** | — |

> ⚠️ **Không phải cách ly galvanic.** `GND_I` nối thẳng vào `GND` (một PSU
> duy nhất thì không cách ly được). Vai trò thật của U4/U9 là **hạ mức
> 12 V → 3.3 V + chắn xung trên dây field**, đừng kỳ vọng khả năng chống
> nhiễu của opto cách ly thật.
| **U5** | **ULN2003AN** DIP-16 | ~20×7 | 1 | Đệm 4 pha stepper trục 1 | IN từ U10 Q1–Q4 → J5; **COM(9) → `+12V`** |
| **U6** | **ULN2003AN** DIP-16 | ~20×7 | 1 | Đệm 4 pha stepper trục 2 | IN từ U10 Q5–Q8 → J6; **COM(9) → `+12V`** |
| **U7** | **ULN2003AN** DIP-16 | ~20×7 | 1 | Đệm 4 pha stepper trục 3 | IN từ U11 Q1–Q4 → J7; **COM(9) → `+12V`** |
| **U10** | **74HC595** DIP-16 | ~20×7 | 1 | Shift reg 1 (8 pha) | SER IO10, SRCLK IO11, RCLK IO12, `/OE` IO13 |
| **U11** | **74HC595** DIP-16 | ~20×7 | 1 | Shift reg 2, nối tiếp U10 | `QH'` của U10 → SER; dùng 4/8 ngõ |
| **R4** | Điện trở axial **10k** | pitch ~7.5 | 1 | Pull-up `/OE` — giữ ngõ 595 Hi-Z lúc boot | `/OE` → `+3V3` |
| **R1** | Điện trở axial **4k7** | pitch ~7.5 | 1 | Pull-up BUP NPN | `+12V_SNS` → OUT |
| **R2** | Điện trở axial **10k** | pitch ~7.5 | 1 | Pull-up EN của TMC2209 | `/EN_TMC` → `+3V3` |
| **R3** | Điện trở axial **10k** | pitch ~7.5 | 1 | Pull-down PWM bơm | `/BLOWER` → GND |
| **D2** | **1N5819** (DO-41) | axial | 1 | Freewheel bơm màng | `+5V_BLW` ↔ `/BLW_RET` |
| **R10** | 10Ω 1206 | — | 1 | Lọc star SNS | `+12V` → `+12V_SNS` |
| **C10** | 47µF radial 25V (105°C) | Ø~6 | 1 | Bulk SNS | `+12V_SNS`–GND |
| **C11** | 100nF 0805 | — | 1 | HF SNS | `+12V_SNS`–GND |
| **C20** | 470µF 25V radial (105°C) | Ø~8 | 1 | Bulk @ TMC2209 VM | `+12V`–GND |
| **C21** | 100µF 25V radial (105°C) | Ø~6 | 1 | Bulk **dùng chung** cho COM của U5–U7 | `+12V`–GND |
| ~~**C22–C23**~~ | ~~470µF~~ | — | **BỎ** | 3 ULN2003 chỉ hút ~74 mA/trục (N20 stall là 1,5–2 A) — một tụ chung là đủ | — |

### Jack trên board (chỉ chân cắm — không gắn sensor/motor lên PCB)

| Ref | Header | SL | Cắm ra ngoài |
|-----|--------|----|--------------|
| **J2** | 1×04 | 1 | NEMA17 A2/A1/B1/B2 |
| **J4** | **1×06** | 1 | Opto field (GND_I, VCC_I, **IN1…IN4**) — song song với J8/J10/J12/J14. *(was 1×10: U9 không hàn nên IN5–IN8 không tồn tại)* |
| **J5** | **1×05** | 1 | **28BYJ-48 trục 1** — JST-XH 5P, trùng giắc zin của động cơ |
| **J6** | **1×05** | 1 | **28BYJ-48 trục 2** |
| **J7** | **1×05** | 1 | **28BYJ-48 trục 3** |
| **J8** | 1×02 | 1 | Limit **HOME** trục 1 (cơ khí, chân NC) |
| **J10** | 1×02 | 1 | Limit **HOME** trục 2 |
| **J12** | 1×02 | 1 | Limit **HOME** trục 3 |
| **J14** | 1×04 | 1 | BUP-30S (+12 / GND / OUT / CTRL) |
| **J15** | 1×03 | 1 | Buzzer 5V (VCC / GND / SIG) |
| **J16** | 1×04 | 1 | AOD4184 (PWM / GND / +5V_BLW / FAN−) |
| **J17** | 1×11 | 1 | TFT SPI + touch I2C (+ RST / BL / T_INT) — **không có MISO** |

**J3:** không dùng.

---

## B) Ngoài board — đã đặt mua (Shopee, 2026-08-27)

| # | Linh kiện đã mua | SL | Giá | Cắm / nối | Trạng thái |
|---|------------------|----|-----|-----------|------------|
| 1 | **Mean Well LRS-50-12** (+ nắp che TBC-09 tặng kèm) | 1 | 304.000 | → J1 | ✅ đúng |
| 2 | **ESP32-S3-DevKitC N16R8** Type-C (Lập Trình Nhúng A-Z G182) | 1 | 210.000 | socket U1 | ✅ đúng — **kiểm tra rev v1.1** |
| 3 | **MP1584EN** 3A, phân loại 5V | 2 | 42.000 | U2 / U8 | ⚠️ xem R-2 |
| 5 | **AOD4184** MOSFET cách ly | 1 | 25.000 | → J16 | ✅ đúng |
| 6 | **MKS TMC2209 V2.0** (Makerbase, hàng đặt trước) | 1 | 160.313 | U3 | ⚠️ xem R-4 |
| 7 | **NEMA 17** 42×34 mm | 1 | 225.000 | → J2 | ✅ đúng |
| 9 | **OMRON SS-5GL2** (SPDT, cần gạt bản lề) | **3**/6 | 96.000 | → J8, J10, J12 | ✅ dùng chân **NC**. Thân 19,8×10,2×6,4 khớp hốc trong `byj_rack_stage.py`; 30 triệu lần tác động |
| 10 | **PC817 opto 4 kênh** | **1**/2 | 47.000 | U4 | ✅ đúng — đo footprint trước fab. Con thứ 2 không hàn (U9 = DNP) |
| 11 | Autonics **BUP-30S** | 1 | 480.000 | → J14 | ✅ đúng |
| 12 | **TFT 3.5" 320×480 SPI ILI9488** | 1 | 395.000 | → J17 | 🔴 **xem R-1 — chặn fab** |
| 13 | Bơm khí mini, phân loại **"BƠM 280 3.7V"** | 1 | 44.000 | tải AOD4184 | 🔴 xem R-3 |

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
| **Driver** | **74HC595** DIP-16 — **U10, U11** | **2** | Mở rộng ngõ ra, giải bài toán GPIO — xem R-7 |
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
| Đầu nối | Socket DIP-16 cho U5–U7, U10, U11 | 5 | Cắm IC, thay được khi hỏng |
| Đầu nối | Header đực 2.54: **1×2 ×6**, 1×3, 1×4 ×3, **1×5 ×3**, **1×6**, 1×11 | — | mạ vàng. *(J5–J7: 1×02 → 1×05. **XOÁ J9/J11/J13** — U9 không hàn nên không còn kênh opto phía sau. J4: 1×10 → 1×06)* |
| Khí | Ống silicone Ø4 + tee + 2 vòi phun | 1 bộ | |
| PCB | Fab 2 lớp 175×175 mm | — | route xong R2/R3/D2 + DRC rồi hãy đặt |

---

## B3) Rủi ro đã nhận diện trên đơn hàng

### 🔴 R-1 — TFT ILI9488 3.5": nhiều khả năng là touch **điện trở XPT2046**, không phải điện dung I2C

**Chặn fab. Phải xác nhận trước khi đặt PCB.**

Đại đa số module "3.5 inch 320×480 SPI ILI9488" trên thị trường đi kèm
**XPT2046 (điện trở, giao tiếp SPI)** chứ không phải FT6336/GT911 (điện dung,
I2C). Nếu đúng vậy thì J17 hiện tại **sai hoàn toàn ở khối touch**: 3 chân
SDA / SCL / T_INT vô dụng, và XPT2046 lại cần đúng đường **MISO** vừa bị bỏ.

**Cách xác nhận:** nhìn mặt sau module — có IC nhỏ ghi `XPT2046` và hàng chân
ghi `T_CLK / T_CS / T_DIN / T_DO / T_IRQ` là điện trở. Nếu chỉ có 2 chân
`SDA / SCL` cạnh chân nguồn thì là điện dung.

**Tin tốt: vẫn vừa đúng 11 chân, chỉ đổi nhãn — không phải đổi số chân J17.**

| J17 | Bản điện dung (hiện tại) | GPIO | → Bản XPT2046 | GPIO |
|-----|--------------------------|------|---------------|------|
| 1 | GND | — | GND | — |
| 2 | 3V3 | — | 3V3 | — |
| 3 | SCK | 39 | SCK *(dùng chung)* | 39 |
| 4 | MOSI | 40 | MOSI *(dùng chung)* | 40 |
| 5 | CS | 42 | **MISO** *(dùng chung)* | **41** |
| 6 | DC | 21 | LCD_CS | 42 |
| 7 | RST | 46 | DC | 21 |
| 8 | BL | 45 | RST | 46 |
| 9 | SDA | 47 | BL | 45 |
| 10 | SCL | 48 | **T_CS** | **47** |
| 11 | T_INT | 41 | **T_IRQ** | **48** |

Vẫn 11 chân, vẫn 28 GPIO, vẫn 0 dự phòng. Chỉ cần sửa `TFT_HEADER` +
`TFT_GPIO` rồi regenerate.

**Kèm theo 2 vấn đề phụ của ILI9488:**

- **SPI của ILI9488 chỉ nhận màu 18-bit (3 byte/pixel)**, không có RGB565.
  480×320×3 = 460 KB/khung → ở SPI 40 MHz là ~92 ms/khung ≈ **11 FPS** khi vẽ
  full màn. LVGL partial refresh vẫn mượt cho HMI tĩnh, nhưng vuốt/kéo sẽ thấy
  chậm. (ST7796 cùng kích thước hỗ trợ RGB565 → nhanh gần gấp đôi.)
- **LCD SDO có thể không tri-state** khi LCD_CS ở mức cao → đọc XPT2046 bị
  nhiễu. Nhiều module đã có trở nối tiếp sẵn; nếu không thì chèn **1k nối
  tiếp trên đường SDO của LCD**, hoặc dùng đệm 74HC125.

### 🔴 R-3 — Bơm "280 3.7V" chạy trên rail 5 V

Phân loại đã chọn là **motor 280, định mức 3,7 V**, trong khi U8 cấp **5 V** →
**quá áp ~35 %**. Chổi than và màng cao su mòn nhanh hơn hẳn.

Vì đã có sẵn AOD4184 PWM, cách chữa rẻ nhất là **giới hạn duty ~70 %** ở tần số
**≥ 20 kHz** (dưới 20 kHz bơm màng rít). Burst 100–300 ms nên nhiệt không phải
vấn đề chính — mòn cơ khí mới là.

Rủi ro thứ hai: **motor 280 yếu hơn 370**. Chia sang 2 vòi phun là mỗi vòi chỉ
còn nửa lưu lượng — cần thử thực tế xem có đủ áp thổi sạch mặt kính BUP-30S
không. Nếu không đủ: bỏ tee, dùng 1 vòi thổi thẳng mặt thu.

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

### 🔴 R-7 — GPIO: ULN2003 tốn 4 chân/trục, KHÔNG nối thẳng được

**Đây là lý do có U10/U11 74HC595. Đừng bỏ chúng đi.**

DRV8871 chỉ cần 2 chân/trục, ULN2003 cần **4**. Ngân sách GPIO của board vốn đã
**0 dự phòng**:

| Phương án | Chân motor | Chân limit | Chênh so với hiện tại |
|-----------|-----------|-----------|----------------------|
| Hiện tại (3× DRV8871 + 6 limit) | 6 | 6 | baseline, dùng 28/28 |
| 3× ULN2003 nối THẲNG + 3 limit home | 12 | 3 | **+3 → tràn**, kể cả sau khi hy sinh Touch INT (IO41) và spare OUT8 (IO9) vẫn **thiếu 1 chân** |
| **3× ULN2003 qua 2× 74HC595 + 3 limit home** | **4** | **3** | **−5 → dùng 23/28, dư 5** ✅ |

74HC595 nối tiếp nhau: 16 ngõ ra, dùng 12 cho 3 con ULN2003. Ở 800 Hz × 3 trục,
mỗi lần cập nhật chỉ tốn 16 bit — dưới 4 % CPU kể cả bit-bang.

**`/OE` phải có pull-up 10k (R4) và do IO13 điều khiển.** Nội dung thanh ghi 595
lúc cấp nguồn là **ngẫu nhiên**; nếu `/OE` nối thẳng xuống GND thì có thể cả 4 pha
cùng đóng ngay lúc boot. Pull-up giữ ngõ ra Hi-Z → ngõ vào ULN2003 tự bị mạng trở
nội kéo xuống → động cơ tắt. Firmware kéo `/OE` xuống sau lần latch đầu tiên.

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
| *(U9 không hàn — 4 kênh opto biến mất)* | **IO6, 7, 8, 9 — GPIO TỰ DO** |
| Stepper SER / SRCLK / RCLK / `/OE` | IO10 / 11 / 12 / 13 |
| *(giải phóng khi bỏ DRV8871)* | **IO14, IO15 dự phòng** |
| TMC STEP / DIR / EN | IO16 / 17 / 18 |
| TFT SCK / MOSI / CS / DC | IO39 / 40 / 42 / 21 |
| TFT RST (chung LCD + touch) | IO46 |
| TFT BL (PWM, LEDC) | IO45 |
| Touch SDA / SCL | IO47 / 48 |
| Touch INT | IO41 *(chỗ của MISO cũ)* |
| Buzzer | IO38 |
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
| **Dự phòng** | **6** *(was 0)* — IO6, 7, 8, 9, 14, 15 |

Đợt đổi sang stepper (2026-08-28) **cởi được nút thắt GPIO**, dù ULN2003 tốn 4
chân/trục thay vì 2: 74HC595 gom 12 pha về 4 chân (−2), và quyết định **chỉ 1 công
tắc HOME mỗi trục** bỏ được 3 limit MAX (−3), và U9 không hàn bỏ thêm 4 kênh opto
(−4). Từ 0 dự phòng lên **6**.

Cả 6 chân dự phòng đều là **GPIO tự do thật** (vào, ra, PWM, bus phụ — tuỳ ý):

| Chân | Được giải phóng nhờ |
|------|--------------------|
| **IO14, IO15** | Bỏ 3× DRV8871 (mỗi con ăn 2 chân), thay bằng 4 chân qua 74HC595 |
| **IO6, 7, 8, 9** | **U9 không hàn** — chỉ còn 4 ngõ vào field (3 limit + BUP), vừa đúng một con U4 |

**Muốn thêm ngõ vào cách mức 12 V** (E-stop, cảm biến mức phễu, công tắc cửa): footprint
U9 vẫn nằm trên PCB — hàn IC + thêm header là có lại 4 kênh, đổi lại mất IO6–IO9.
Không phải làm lại board.

Hai đánh đổi cũ vẫn giữ (nay đã có đường lùi nhờ 6 chân dự phòng):

1. **Bỏ TFT MISO.** SPI chạy write-only — ILI9341 / ST7796 + LVGL không cần đọc
   thanh ghi. Đặt `TFT_MISO = -1` trong TFT_eSPI / driver panel của LVGL.
   IO41 được giải phóng để nhận `T_INT`.
2. **Bỏ TMC `PDN_UART`.** Cần IO36, đã bị octal PSRAM lấy. Chỉnh dòng bằng biến
   trở Vref trên module; không đọc được `DRV_STATUS` (quá nhiệt / hở pha).

**Đường thoát nếu sau này bí một chân:** hy sinh `T_INT` — poll FT6336 qua I2C ở
50–100 Hz (chỉ tốn ~1% băng thông bus) và **J17.11 / IO41 thành chân dự phòng**.
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
| `/BUZZER` | IO38 | LOW = im | ✅ module buzzer active có trở kéo base |

### Cảnh báo mua module

- **Chốt DevKitC-1 v1.1.** v1.1 để WS2812 onboard ở GPIO38 → trùng buzzer, vô
  hại (LED nháy theo còi). v1.0 để ở GPIO48 → **trùng I2C SCL của touch**.
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
- **PC817 4CH**: đổi trở hạn dòng LED phía field từ 1k lên **2.2k** (~5 mA
  thay vì ~11 mA). CTR của PC817 suy giảm theo thời gian dẫn — đây là fix
  rẻ nhất để đạt mục tiêu >3 năm.
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
| PC817 4CH ×2 | **OK** | Gọn hơn 8CH; shop rõ; LED field không đẩy dòng cao | ~0–10k |
| ~~DRV8871 ×3~~ → **ULN2003 ×3 + 74HC595 ×2** | **OK** | ~15k tổng thay vì 255k; không có gì phải chỉnh dòng; giải luôn bài toán GPIO | **−240k** |
| Capacitor 105°C | **CHỌN KỸ** | 470µ / 47µ long-life | +5–15k |
| Header mạ vàng | **CHỌN KỸ** | Field + socket U1 | +10–20k |
| Limit cơ khí | **CHỌN KỸ** | Omron-class nếu giá gần KW12 thường | +0–30k |
| BUP-30S Autonics | **OK** | Cảm biến chính; thổi bụi giúp tuổi thọ quang | baseline |
| ~~GA12-N20~~ → **28BYJ-48 12V** | **OK** | **Không chổi than**, datasheet >10.000 h vs 81 h thực dùng trong 3 năm. Điều kiện: firmware **cắt cả 4 pha khi dừng** (giữ dòng 24/7 mới là thứ giết nó) | −40k/trục so với N20 |
| Bơm màng 5V | **DỰ PHÒNG** | Màng cao su — burst ngắn + 1 bơm dự phòng | +20–40k dự phòng |
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

1. Module **PC817 4CH** thật: pad pitch / khoảng 2 hàng (~25.4?).  
2. **MP1584** pad span X/Y.  
3. ~~DRV8871 footprint~~ → **giắc JST-XH 5P** (J5–J7): đo pitch/pad thực tế của cáp
   nối dài mua kèm. U5–U7 / U10 / U11 là DIP-16 tiêu chuẩn, không cần đo.  
4. **ESP32-S3-DevKitC** row 25.4 / 44 pin.  
5. **AOD4184** jack J16 khớp dây.

```
python gen_power_carrier.py
```

---

## F) Lịch sử quyết định (tóm tắt)

| Đã bỏ / không dùng | Đã chọn thay |
|--------------------|--------------|
| ESP32 DevKit V1 + MCP23017 | ESP32-S3 DevKitC |
| Mini560 | MP1584EN ×2 (logic + BLW) |
| L298N | DRV8871 ×3 |
| PC817 8CH dài | PC817 4CH ×2 |
| Quạt 5015 | Bơm màng 5V |
| Limit quang hành trình | Limit **cơ khí** (chỉ jack trên board) |
| **DRV8871 ×3 + GA12-N20 ×3** (chổi than) | **ULN2003 ×3 + 28BYJ-48 12V ×3** (2026-08-28) |
| **6 limit (MIN+MAX × 3 trục)** | **3 limit HOME** — stepper đếm bước lo giới hạn, cữ cứng lo va chạm |
| Nối thẳng 12 pha vào GPIO (tràn 1 chân) | **2× 74HC595** nối tiếp — 12 pha còn 4 chân |
| PSU DIN DDR quá to | Mean Well 12V/3A |
| Buck / HMI công nghiệp đắt | Không (ràng buộc giá) |
