# Counting machine — danh sách module (ghi nhớ)

**Cập nhật:** 2026-08-26  
**PCB:** `esp32_baseboard` (generator: `gen_power_carrier.py`)  
**Mục tiêu:** văn phòng ~20 cm, **ổn định >3 năm**, **tổng giá kinh tế** (chỉ nâng cấp khi chênh ít).

Nguồn 12V ngoài → J1 → F1 PTC → `+12V` (+ D1 TVS) → các rail / driver.

```
PSU 12V ──J1── F1 ── +12V ──┬── U2 MP1584 ── +5V ── U1 / TFT / buzzer
                            ├── U8 MP1584 ── +5V_BLW ── J16 AOD4184 ── bơm màng
                            ├── U3 TMC2209 ── J2 NEMA17
                            ├── U5–U7 DRV8871 ── J5–J7 N20
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
| **U4** | **PC817 4CH** | ~48×38 | 1 | Level-shift ch1–4 | Field IN1–4 → OUT → IO1,2,4,5 |
| **U9** | **PC817 4CH** | ~48×38 | 1 | Level-shift ch5–8 | IN5–6 limit, IN7 BUP, IN8 spare → IO6,7,8,9 |

> ⚠️ **Không phải cách ly galvanic.** `GND_I` nối thẳng vào `GND` (một PSU
> duy nhất thì không cách ly được). Vai trò thật của U4/U9 là **hạ mức
> 12 V → 3.3 V + chắn xung trên dây field**, đừng kỳ vọng khả năng chống
> nhiễu của opto cách ly thật.
| **U5** | **DRV8871** module | ~25–28×20 | 1 | Motor DC trục 1 | IN IO10/11 → J5 |
| **U6** | **DRV8871** module | ~25–28×20 | 1 | Motor DC trục 2 | IN IO12/13 → J6 |
| **U7** | **DRV8871** module | ~25–28×20 | 1 | Motor DC trục 3 | IN IO14/15 → J7 |
| **R1** | Điện trở axial **4k7** | pitch ~7.5 | 1 | Pull-up BUP NPN | `+12V_SNS` → OUT |
| **R2** | Điện trở axial **10k** | pitch ~7.5 | 1 | Pull-up EN của TMC2209 | `/EN_TMC` → `+3V3` |
| **R3** | Điện trở axial **10k** | pitch ~7.5 | 1 | Pull-down PWM bơm | `/BLOWER` → GND |
| **D2** | **1N5819** (DO-41) | axial | 1 | Freewheel bơm màng | `+5V_BLW` ↔ `/BLW_RET` |
| **R10** | 10Ω 1206 | — | 1 | Lọc star SNS | `+12V` → `+12V_SNS` |
| **C10** | 47µF radial 25V (105°C) | Ø~6 | 1 | Bulk SNS | `+12V_SNS`–GND |
| **C11** | 100nF 0805 | — | 1 | HF SNS | `+12V_SNS`–GND |
| **C20–C23** | 470µF 25V radial (105°C) | Ø~8 | **4** | Bulk: C20 @ TMC VM, C21–C23 @ U5–U7 | `+12V`–GND mỗi driver |

### Jack trên board (chỉ chân cắm — không gắn sensor/motor lên PCB)

| Ref | Header | SL | Cắm ra ngoài |
|-----|--------|----|--------------|
| **J2** | 1×04 | 1 | NEMA17 A2/A1/B1/B2 |
| **J4** | 1×10 | 1 | Opto field (GND_I, VCC_I, IN1…IN8) — thường dùng song song với J8–J14 |
| **J5** | 1×02 | 1 | Motor DC 1 |
| **J6** | 1×02 | 1 | Motor DC 2 |
| **J7** | 1×02 | 1 | Motor DC 3 |
| **J8** | 1×02 | 1 | Limit MIN trục 1 (cơ khí) |
| **J9** | 1×02 | 1 | Limit MAX trục 1 |
| **J10** | 1×02 | 1 | Limit MIN trục 2 |
| **J11** | 1×02 | 1 | Limit MAX trục 2 |
| **J12** | 1×02 | 1 | Limit MIN trục 3 |
| **J13** | 1×02 | 1 | Limit MAX trục 3 |
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
| 4 | **DRV8871** 3.6A cầu H | 3 | 255.000 | U5–U7 | ✅ đúng — xem R-5 |
| 5 | **AOD4184** MOSFET cách ly | 1 | 25.000 | → J16 | ✅ đúng |
| 6 | **MKS TMC2209 V2.0** (Makerbase, hàng đặt trước) | 1 | 160.313 | U3 | ⚠️ xem R-4 |
| 7 | **NEMA 17** 42×34 mm | 1 | 225.000 | → J2 | ✅ đúng |
| 8 | **GA12-N20** 3–12 V, **500 RPM** | 3 | 207.000 | → J5–J7 | ⚠️ xem R-6 |
| 9 | **OMRON SS-5GL2** (SPDT, cần gạt bản lề) | 6 | 192.000 | → J8–J13 | ✅ đúng, dùng chân **NC** |
| 10 | **PC817 opto 4 kênh** | 2 | 94.000 | U4 / U9 | ✅ đúng — đo footprint trước fab |
| 11 | Autonics **BUP-30S** | 1 | 480.000 | → J14 | ✅ đúng |
| 12 | **TFT 3.5" 320×480 SPI ILI9488** | 1 | 395.000 | → J17 | 🔴 **xem R-1 — chặn fab** |
| 13 | Bơm khí mini, phân loại **"BƠM 280 3.7V"** | 1 | 44.000 | tải AOD4184 | 🔴 xem R-3 |

**Tổng phần điện đã đặt: ~2.633.000₫** · cơ khí + dụng cụ ~665.000₫ · **toàn giỏ ~3.298.000₫**

### Cơ khí / dụng cụ trong cùng đơn

Ty ren M4×40 inox 304 · đai ốc đồng M4 ×60 · khớp nối cứng 4–3 mm ×4 · khớp mềm
D19 L25 (5–8 mm) ×2 · khớp mặt bích 8 mm ×2 · gối đỡ KFL08 ×5 · thanh trượt Ø8
L100 · gen co nhiệt Ø2 · tay quay taro M3–M8.

---

## B2) CHƯA MUA — thiếu là không lắp được board

| Nhóm | Linh kiện | SL | Ghi chú |
|------|-----------|----|---------|
| Bảo vệ | PTC radial ~3A/30V (RXE030 / MF-R300) — **F1** | 1 | |
| Bảo vệ | TVS **P6KE15A** DO-41 — **D1** | 1 | |
| Passive | Điện trở axial **4k7** — **R1** | 1 | pull-up BUP |
| Passive | Điện trở axial **10k** — **R2**, **R3** | 2 | boot-state, **bắt buộc** |
| Passive | Diode **1N5819** DO-41 — **D2** | 1 | freewheel bơm |
| Passive | Tụ **470µF 25V 105°C** — C20–C23 | **4** | |
| Passive | Tụ 47µF 25V 105°C (C10) · 100nF 0805 (C11) · R 10Ω 1206 (R10) | 1 mỗi loại | star SNS |
| Nhiệt | **Heatsink** cho TMC2209 | 1 | MKS không kèm sẵn |
| Báo hiệu | **Buzzer active 5V** | 1 | → J15 |
| Đầu nối | Terminal block 2P pitch 5.0 mm — **J1** | 1 | |
| Đầu nối | Socket cái 2×22 pitch 2.54 (cho U1) — **mạ vàng** | 1 bộ | |
| Đầu nối | Header đực 2.54: 1×2 ×9, 1×3, 1×4 ×3, 1×10, 1×11 | — | mạ vàng |
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

### ⚠️ R-5 — DRV8871: phải đo R_ILIM

Module 3.6 A nhưng **N20 stall 1,5–2 A**. Máy đếm thì kẹt là chuyện thường.
Đo R_ILIM trên module thật và chỉnh về **~1,2 A**; kèm timeout phát hiện kẹt
trong firmware.

### ⚠️ R-6 — GA12-N20 500 RPM

Hỏi shop **RPM đo ở điện áp nào**: nếu 500 RPM là ở 6 V thì ở 12 V sẽ thành
~1000 RPM. Với vít me M4 (bước 0,7 mm): 500 RPM ≈ **5,8 mm/s**, hành trình
21,6 mm hết ~3,7 s — hợp lý. Nhưng bản 500 RPM là tỉ số truyền thấp →
**mô-men thấp**, mà ren tam giác M4 hiệu suất chỉ ~20–30 %. Phải thử tải thật
trước khi chốt; nếu thiếu lực thì đổi sang bản RPM thấp hơn (100–200 RPM).

### ✅ Điểm tốt trong đơn

- **LRS-50-12** đúng theo khuyến nghị nâng cấp, lại có nắp che cầu đấu tặng kèm.
- **OMRON SS-5GL2** là loại tốt, có sẵn chân NC → đấu fail-safe được ngay.
  *Lưu ý ngược chiều:* việc đổi trở LED opto 1k → 2,2 k (~5 mA) vẫn **trên
  ngưỡng wetting current** của tiếp điểm bạc — đừng hạ thấp hơn 2,2 k, nếu
  không tiếp điểm dễ oxy hoá ở dòng quá nhỏ.
- **DRV8871 / AOD4184 / PC817 / BUP-30S / NEMA17** đều đúng loại đã chốt.

---

## C) GPIO map (nhớ nhanh)

| Chức năng | GPIO |
|-----------|------|
| Limit (opto OUT1–6) | IO1, 2, 4, 5, 6, 7 |
| BUP (OUT7) | IO8 |
| Spare (OUT8) | IO9 |
| Motor1 / 2 / 3 | IO10–11 / 12–13 / 14–15 |
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
| Thiết kế dùng | 28 |
| Để trống bắt buộc (IO0, IO19, IO20, IO43, IO44) | 5 |
| **Dự phòng** | **0** |

Vừa khít. Hai đánh đổi để nhét vừa 33 chân:

1. **Bỏ TFT MISO.** SPI chạy write-only — ILI9341 / ST7796 + LVGL không cần đọc
   thanh ghi. Đặt `TFT_MISO = -1` trong TFT_eSPI / driver panel của LVGL.
   IO41 được giải phóng để nhận `T_INT`.
2. **Bỏ TMC `PDN_UART`.** Cần IO36, đã bị octal PSRAM lấy. Chỉnh dòng bằng biến
   trở Vref trên module; không đọc được `DRV_STATUS` (quá nhiệt / hở pha).

**Đường thoát nếu sau này bí một chân:** hy sinh `T_INT` — poll FT6336 qua I2C ở
50–100 Hz (chỉ tốn ~1% băng thông bus) và **J17.11 / IO41 thành chân dự phòng**.
Ngoài ra kênh **opto OUT8 (IO9)** vẫn còn trống: đã có sẵn 1 ngõ vào cách mức
12 V dùng được ngay cho E-stop hoặc cảm biến mức phễu, không tốn GPIO nào.

### Trạng thái chân lúc power-on (trước khi firmware chạy)

ESP32 thả toàn bộ GPIO về high-Z khi reset, nên mọi ngõ vào cơ cấu chấp hành
phải có mức an toàn xác định bằng phần cứng:

| Net | GPIO | Mức an toàn | Cách đảm bảo |
|-----|------|-------------|--------------|
| `/EN_TMC` | IO18 | HIGH = driver tắt | ✅ **R2** 10k pull-up → 3V3 |
| `/BLOWER` | IO3 | LOW = bơm tắt | ✅ **R3** 10k pull-down → GND |
| `/TFT_BL` | IO45 | LOW = đèn nền tắt | ✅ pull-down nội bộ của strapping pin |
| `/TFT_RST` | IO46 | LOW = giữ trong reset | ✅ pull-down nội bộ của strapping pin |
| `/DC*_IN1/2` | IO10–15 | LOW = motor thả trôi | ✅ DRV8871 có pull-down nội bộ (**đo lại trên module Shopee**) |
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
- **DRV8871**: đo R_ILIM trên module thật và chỉnh về **~1.2 A**. N20 stall
  1.5–2 A; máy đếm thì kẹt là chuyện thường, không phải ngoại lệ.
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
| DRV8871 ×3 | **OK** | MOSFET, mát hơn L298N; chip thật + I_lim ~1–1.5A | baseline |
| Capacitor 105°C | **CHỌN KỸ** | 470µ / 47µ long-life | +5–15k |
| Header mạ vàng | **CHỌN KỸ** | Field + socket U1 | +10–20k |
| Limit cơ khí | **CHỌN KỸ** | Omron-class nếu giá gần KW12 thường | +0–30k |
| BUP-30S Autonics | **OK** | Cảm biến chính; thổi bụi giúp tuổi thọ quang | baseline |
| GA12-N20 | **DỰ PHÒNG** | Chổi than mòn — duty thấp + 1–2 motor dự phòng | +30–60k dự phòng |
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
| 3× N20 + NEMA17 + 6 limit + BUP + buzzer + bơm + ống | ~600k–1.2tr |
| TFT 2.8" touch | ~150–350k |
| **Tổng điện + cơ điện điển hình (1 máy)** | **~2–3.5tr** (chưa cơ khí khung / in 3D) |

→ Tối ưu kinh tế: **giữ kiến trúc hiện tại**; chỉ “chọn đúng SKU” (BTT, MP1584 fixed 5V, cap 105°C, pin vàng, limit tốt) thay vì đổi sang linh kiện công nghiệp đắt.

---

## E) Việc cần đo trước khi fab PCB

1. Module **PC817 4CH** thật: pad pitch / khoảng 2 hàng (~25.4?).  
2. **MP1584** pad span X/Y.  
3. **DRV8871** footprint Shopee.  
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
| PSU DIN DDR quá to | Mean Well 12V/3A |
| Buck / HMI công nghiệp đắt | Không (ràng buộc giá) |
