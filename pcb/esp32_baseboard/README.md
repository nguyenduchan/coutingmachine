# ESP32-S3 Baseboard — BOM + do ben >3 nam

**Danh sach module day du (ghi nho):** xem [`MODULES.md`](MODULES.md).

May van phong ~20 cm. PSU ngoai **Mean Well 12V/3A**. Limit = **co khi** (ngoai board); board chi co **chan cam**.

## 1) Linh kien TREN board (module / jack)

| Ref | Linh kien | Vai tro | Trang thai do ben |
|-----|-----------|---------|-------------------|
| J1 | Terminal 2P 5.0 mm | +12V_RAW / GND tu PSU | OK |
| **F1** | PTC radial ~3A 30V | Bao ve ngan mach | **Da them** (re) |
| **D1** | TVS P6KE15A (DO-41) | Clamp surge 12V | **Da them** (re) |
| **U1** | **ESP32-S3-DevKitC-1** (44-pin, N8R2/N16R8) | MCU | **Da doi** (bo DevKit V1 + MCP23017) |
| **U2** | **MP1584EN** 5V | +5V logic / TFT / buzzer | **Da doi** (bo Mini560) |
| **U8** | **MP1584EN** 5V | +5V_BLW rieng bom khi | **Da them** |
| **U3** | **TMC2209** stepstick | NEMA17 | Giu — chon hang tot (BTT), heatsink, I_run hop ly |
| **U4 / U9** | **PC817 4CH ×2** | Cach ly limit + BUP | **Da doi** (bo 8CH dai ~100mm) |
| **U5–U7** | **DRV8871** x3 | 3x GA12-N20 | **Da doi** (bo L298N) |
| C* / R10 | Bulk 470u @ driver; R10=10R + C10=47u + C11=100n SNS | Star power | Chon tu 105°C long-life |
| R1 | 4k7 axial | Pull-up BUP NPN | OK |
| J2 | Header 1x04 | NEMA17 A+/A−/B+/B− | Chi jack |
| J4 | Header 1x10 | OPTO field (limit + BUP IN) | Chi jack |
| J5–J7 | Header 1x02 | Motor DC 1..3 | Chi jack |
| **J8–J13** | Header 1x02 x6 | **Limit MIN/MAX** (co khi, day ra) | Chi jack — **khong** cam bien tren PCB |
| J14 | Header 1x04 | BUP-30S | Chi jack |
| J15 | Header 1x03 | Buzzer 5V | Chi jack |
| J16 | Header 1x04 | AOD4184 PWM/GND/+5V_BLW/FAN− | Chi jack (+ module AOD4184) |
| J17 | Header 1x12 | TFT SPI + touch I2C (+ RST / BL / T_INT) | Chi jack |

J3: **khong dung**.

## 2) Linh kien NGOAI board (day / module roi)

| Linh kien | SL | Ghi chu |
|-----------|----|---------|
| Mean Well **12V/3A** (hoac tuong duong cong nghiep) | 1 | PSU chinh — **da chot** (bo DDR-rail qua to) |
| NEMA17 stepper | 1 | Qua J2 |
| GA12-N20 12V | 3 | Qua J5–J7 |
| **Limit switch co khi** (NO/NC, Omron-style / KW11 / ME-8108…) | **6** | Qua **J8–J13**; day 2 loi +12V_SNS / COM; **khong** dung cam bien quang hanh trinh |
| Autonics **BUP-30S** | 1 | Qua J14; thoi bui dinh ky |
| Buzzer active 5V | 1 | Qua J15 |
| Module **AOD4184** (logic-level MOSFET) | 1 | Cam J16 |
| **Bom mang mini 5V** (diaphragm) | 1 | Ap cao / Q thap; ong silicone + tee 2 voi → BUP TX/RX |
| TFT + touch (SPI + I2C) | 1 | Qua J17 |
| Ong silicone Ø4 + tee + 2 voi phun | 1 bo | Co khi |

## 3) GPIO (tom tat)

| Chuc nang | GPIO |
|-----------|------|
| Limit OUT1..6 (qua opto) | IO1,2,4,5,6,7 |
| BUP OUT7 | IO8 |
| Spare OUT8 | IO9 |
| Motor1..3 IN1/IN2 | IO10/11, 12/13, 14/15 |
| TMC STEP/DIR/EN | IO16/17/18 |
| TFT SCK/MOSI/CS/DC (khong MISO) | IO39/40/42/21 |
| TFT RST (chung LCD+touch) / BL PWM | IO46 / IO45 |
| Touch SDA/SCL / INT | IO47/48 / IO41 |
| Buzzer | IO38 |
| AOD4184 / bom | IO3 |
| IO35 / IO36 / IO37 | **KHONG dung** - octal PSRAM (N16R8) |

### Passive trang thai boot (DA co tren PCB)

| Ref | Gia tri | Noi | Vi sao |
|-----|---------|-----|--------|
| R2 | 10k pull-**up** -> +3V3 | /EN_TMC (IO18) | EN active-low + float luc reset -> stepper bi cap dien truoc khi firmware chay |
| R3 | 10k pull-**down** -> GND | /BLOWER (IO3) | IO3 la strapping pin, KHONG co pull noi bo -> bom mang co the chay luc boot |
| D2 | 1N5819 (DO-41) | +5V_BLW <-> /BLW_RET | Freewheel cho bom mang (tai cam); module AOD4184 opto khong co san |

D2: vach tren than diode (cathode) = pad 1 = **+5V_BLW**. Lap nguoc la chap nguon.

IO45 / IO46 **khong** can dien tro: ca hai la strapping pin, co pull-down noi
bo giu suot reset -> BL tat va man giu trong reset ngay tu luc cap nguon.

### Canh bao mua module

- **Chot DevKitC-1 v1.1**: v1.1 dat WS2812 onboard tren GPIO38 (trung buzzer,
  vo hai - LED nhap nhay theo coi). v1.0 dat no tren GPIO48 = **trung I2C SCL**.
- **KHONG mua ban hau to V** (N16R8V / N32R16V): VDD_SPI = 1.8V keo GPIO47/48
  xuong muc logic 1.8V -> hong bus touch.
- IO35/36 chi trong tren **N8R2** (quad PSRAM). Voi N16R8 (octal) thi bo trong
  J17.12 (T_INT) va poll touch controller.

## 4) Da doi theo goi y do ben (OK)

- MCU: ESP32-S3, du GPIO, **khong MCP23017**
- Motor DC: **DRV8871** thay L298N (nong / de chet)
- Buck logic: **MP1584EN** thay Mini560; **U8** tach bom khi
- PSU: Mean Well 12V/3A (khong DIN-rail qua lon)
- Star power SNS / MOT; thoi BUP = bom mang + AOD4184

## 5) Do ben >3 nam — chi doi khi gia tang it

| Muc | Quyet dinh | Chi phi |
|-----|------------|---------|
| **F1 PTC + D1 TVS @ J1** | **Da them tren PCB** (RXE030/~3A + P6KE15A) | +~5–15k VND |
| **MP1584** | Giu module re; chon **ban 5V co dinh** (khong ADJ) | ~0 (cung gia) |
| **Buck cong nghiep** | **Khong doi** (Mean Well/Recom dat) | — |
| **TMC2209** | Mua **BTT that** + heatsink nho (cung form stepstick) | +~20–40k vs clone |
| **PC817** | **2× 4CH** (~48×38) thay 8CH | ~0–10k |
| **Header** | Pin **ma vang** / header chat (khong doi sang JST dat) | +~10–20k |
| **GA12-N20 / bom mang** | **Khong doi** loai; duty thap + du phong | ~0 |
| **TFT** | Chon **2.8" IPS** cung phan khuc (tranh man sieu re) | +0–30k |
| **Socket ESP32** | Header ma vang; han that sau thu neu can | it |

Limit **co khi** Omron-class neu gia gan KW12; board **chi jack**.

## 6) Bom / thoi BUP

```
U8 +5V_BLW → AOD4184 (J16) → bom mang 5V → ong → tee → 2 voi (TX/RX BUP)
```

Khong dung quat 5015 (ap thap).

## 7) Kich thuoc module — chon gon + chat luong

Carrier PCB hien ~**175×175 mm**. Opto: **U4+U9 PC817 4CH ×2** (~48×38 moi cai).

| Ref | Footprint board | Kich thuoc that (typ.) | Chon gon + chat luong | Bo / tranh |
|-----|-----------------|------------------------|------------------------|------------|
| U1 | Socket 2×22, row 25.4 | DevKitC-1 **~63×25.4×13** | **DevKitC-1 N8R2** (Espressif) — gon hop ly, USB-C, du GPIO | Module bare WROOM (mat USB debug); DevKit V1 30-pin |
| U2/U8 | 22×17 | MP1584 **22×17×4** | **MP1584EN fixed 5V** (khong bien tro) — nho hon Mini560 (29×18), du 1–1.5A derate | Mini560; buck “5A” sieu re; ADJ de lech 5V |
| U3 | ~20×20 | BTT **15.24×20.32** | **BigTreeTech TMC2209 V1.3** + heatsink nho | Clone vo ten; driver lon SPI |
| U4/U9 | ~48×38 ×2 | Module 4ch | **2× PC817 4CH** (Shopee) — do pad truoc fab | 8ch dai ~100mm |
| U5–U7 | 28×20 ×3 | Adafruit **~24×20**; Shopee ~25–30×20 | Module **DRV8871** ~25×20, chip that, heatsink; I_lim ~1–1.5A (N20) | L298N (~43×43); TB6612 yeu 12V |
| J16 mod | Header 1×04 | AOD4184 **~23×16** (co ban ~33×16) | Module **~23×16** opto+AOD4184 | MOSFET khong heatsink / khong opto neu nhieu nhieu |
| Bom khi | Off-board | 030 ~**38 mm**; 370 ~**55–60 mm** | **Bom mang 5V “030”** neu ap du; else **370** — burst ngan | Quat 5015; bom AC 220V |
| Limit | Chi jack | Micro **~20×6×10** (Omron SS/D2F) | **Omron SS-5 / D2F / KW12** co khi, day 2 loi | Cam bien quang hanh trinh; limit sieu re vo nhua mong |
| BUP | Chi jack | BUP-30S **~50×25×40** (khoang) | Autonics **BUP-30S** giu | Clone quang |
| TFT | Chi jack | 2.8" ~**70×50**; 3.5" ~**85×55** | **2.8" IPS + capacitive** (SPI+I2C) — du HMI, gon hop 20 cm | 7" HDMI; man resistive re |
| PSU | Ngoai vo | LRS-35-12 **~99×82×30** | Mean Well **LRS-35-12** / RSP nho | Adapter no-name; DIN DDR qua to |

### Goi y layout gon (khong doi chuc nang)

1. **U4/U9**: da doi **2×4ch** — do footprint that module Shopee truoc fab.
2. **U2/U8**: giu MP1584 22×17; dat sat J1 / J16.
3. **U5–U7**: 3 module ~25×20 xep doc, heatsink thap.
4. **Bom + AOD4184**: treo off-board / vach vo (khong an dien tich PCB).
5. Carrier target thuc te: **~120×100 … 140×120 mm** neu gom opto 4ch×2 (sau khi layout lai).

### Chat luong vs “nho nhat”

- Nho hon MP1584 ma van >1A tin cay → kho (module re de chay). Can hon: Recom/Murata ~0.5–1A **chi** neu tach TFT sang rail rieng.
- Khong cat DRV8871 / TMC / DevKitC de “sieu nho” — day la diem do ben.

## Tai tao

```
python gen_power_carrier.py
```

Do that truoc fab: ESP32-S3 DevKitC, DRV8871, MP1584 x2, AOD4184, opto 4ch, TFT pinout.
