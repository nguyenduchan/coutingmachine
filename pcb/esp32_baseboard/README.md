# ESP32-S3 Baseboard — BOM (ULN2003 + 74HC595-24IO module)

**Full module list:** see [`MODULES.md`](MODULES.md).

PSU **Mean Well 12V**. Limits = mechanical HOME only (J8/J10/J12). Board is jacks + drivers.

## On-board

| Ref | Part | Role |
|-----|------|------|
| J1 / F1 / D1 | Terminal + PTC + TVS | 12V in + protect |
| U1 | ESP32-S3-DevKitC-1 N16R8 | MCU |
| U2 | MP1584EN 5V | Logic buck (only) |
| U3 | TMC2209 | NEMA17 trên Mot (không J2) |
| U41–U44 | PC817 DIP-4 ×4 | HOME1-3 + BUP |
| R41–R44 | 2k2 axial | LED series (~5 mA @12V) |
| R45–R48 | 10k axial | Collector pull-up → +3V3 |
| **U10** | **74HC595-24IO module** (3×595) | [Shopee](https://shopee.vn/-C%C3%B3-s%E1%BA%B5n-M%E1%BA%A1ch-m%E1%BB%9F-r%E1%BB%99ng-I-O-24-ch%C3%A2n-74HC595-thegioimodule-i.951399259.42633627766) — **bên phải ESP32** |
| J24 / J25 | Header cái 1×6 + 1×24 | CTRL + Q (cắm module) |
| R4 | 10k axial | LDEN/`OE` pull-up → +3V3 |
| U5–U7 | **ULN2003AN** DIP-16 | 28BYJ; IN←SR_Q*; COM=+12V |
| R1 | 4k7 | BUP NPN pull-up → OPTO_IN4 |
| R2/R3 | 10k | EN_TMC PU / BLOWER PD |
| C20 | 470µ | Bulk @ TMC |
| C21 | 100µ | Shared ULN COM bulk |
| ~~J2~~ | — | **XOÁ** (Mot trên U3) |
| J5–J7 | **1×05** | 28BYJ-48 |
| J8/J10/J12 | 1×04 endstop | HOME NC @12V → opto |
| J14 | 1×04 | BUP-30S |
| J15–J18/J23 | — | Buzzer / TFT LCD+touch / EC11 |

**Deleted:** J2, J4/J9/J11/J13, J19–J22 field (optional later), U4/U9, DRV8871.

> All footprints on **TOP (F.Cu)**; B.Cu for routing only.

## GPIO

| Function | GPIO |
|----------|------|
| HOME OUT1-3 / BUP OUT4 | IO1,2,4,5 |
| SER / SRCLK / RCLK / OE_595 | IO10–13 |
| TMC STEP/DIR/EN | IO16–18 |
| TFT SPI + BL + touch | IO39/40/42/21/46/45 + MISO47 T_CS48 T_IRQ6 |
| ENC_A / ENC_B | IO38 / IO41 |
| Buzzer / blower | IO9 / IO3 |
| Spare | IO7,8,14,15 |

## Regenerate

```
$env:PCB_SKIP_MAZE=1; python gen_power_carrier.py
```

Board size target **220×160 mm**. Modules ≥10 mm from edge; ≥10 mm from MCU Eco; ≥8 mm between Ecos. Power netclass track **0.70 mm** (matches FreeRouting).
