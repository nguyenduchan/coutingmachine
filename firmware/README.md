# Firmware — STM32CubeIDE (STM32G030C8T6)

Build target: **STM32CubeIDE** + **STM32CubeMX** (`.ioc`).  
MCU: STM32G030C8T6 LQFP48 · PCB: `pcb/STM32G030C8T6/` · Pinmap: `board_pins.h`

## Layout (Cube standard)

```
firmware/
  CountingMachine_G030.ioc   ← mở bằng CubeIDE / CubeMX
  Core/
    Inc/   main.h, app.h, board_*, tmc_*, count_*
    Src/   main.c, app.c, board_motors.c, tmc_step.c, count_*.c, …
  Drivers/                   ← Generate Code tạo CMSIS + HAL
  README.md
```

| File | Role |
|------|------|
| `Core/Src/main.c` | Cube template — `App_Init` / `App_Loop` |
| `Core/Src/app.c` | Logic máy: motor + đếm + keypad |
| `Core/Src/tmc_step.c` | TMC2208/2209 STEP/DIR/EN |
| `Core/Src/board_motors.c` | 1–2 trục độc lập |
| `Core/Src/count_*.c` | Đếm BUP / FIBER / CNT5 + chống nhiễu |
| `Core/Src/keypad_4x4.c` | Bàn phím dán 4×4 (J_KEY) |
| `Core/Src/app_count_ui.c` | State machine: SET (chuỗi số) / START commit / STOP / # / * |
| `Core/Src/nv_settings.c` | Lưu target + RPM vào Flash page cuối (giữ sau tắt nguồn) |
| `Core/Src/tm1637.c` | Module LED 7 đoạn 4 số TM1637 (J_DISP) |

## Build nhanh (Makefile — không cần Generate Code)

Toolchain lấy từ STM32CubeIDE đã cài. Lần đầu clone HAL vào `_lib/` (đã gitignore):

```powershell
cd firmware
# nếu chưa có _lib:
git clone --depth 1 https://github.com/STMicroelectronics/stm32g0xx_hal_driver.git _lib/hal
git clone --depth 1 https://github.com/STMicroelectronics/cmsis_device_g0.git _lib/cmsis_device
git clone --depth 1 https://github.com/STMicroelectronics/cmsis_core.git _lib/cmsis_core

mingw32-make -j4
# → build/CountingMachine_G030.elf /.hex /.bin
```

## Mở & build lần đầu (CubeIDE GUI)

1. Cài [STM32CubeIDE](https://www.st.com/en/development-tools/stm32cubeide.html) (kèm CubeMX + FW_G0).
2. **File → Open Projects from File System…** → chọn thư mục `firmware/`  
   **hoặc** double-click `CountingMachine_G030.ioc` → Open with STM32CubeIDE.
3. Trong CubeMX tab: **Project Manager → Project → Toolchain = STM32CubeIDE**,  
   **Code Generator → Keep User Code** = ON.
4. **GENERATE CODE** — tạo `Drivers/`, startup, linker script.
5. Sau generate, kiểm tra `main.c` vẫn còn:
   ```c
   App_Init();   // USER CODE BEGIN 2
   App_Loop();   // trong while(1)
   ```
   Nếu Cube ghi đè, copy lại 2 dòng từ git.
6. **Project → Build All** (búa / Ctrl+B).

## Cấu hình board (compile flags)

Trong CubeIDE: **Project → Properties → C/C++ Build → Settings → MCU GCC Compiler → Preprocessor → Define symbols**:

| Symbol | Ý nghĩa |
|--------|---------|
| `BOARD_COUNT_SENSOR` | (đã bỏ) luôn đọc PA0+PA3 |
| `USE_HAL_DRIVER` / `STM32G030xx` | Cube thường đã thêm |

Firmware **luôn** điều khiển 2 kênh TMC (M1 đĩa CCW + M2 bánh răng CW). **TMC2/NEMA2 có thể không lắp** — đế trống vẫn an toàn.

Mặc định cũng nằm trong `Core/Inc/board_config.h` nếu không set `-D`.

Tốc độ đĩa/bánh răng **tăng/giảm dần** (`MOTOR_ACCEL_RPM_S` / `MOTOR_DECEL_RPM_S`) — không nhảy RPM đột ngột. STOP = soft ramp; jam = hard stop.

## Nạp & bảo vệ code

- Dev: SWD (nếu có) hoặc UART bootloader (CH340 + BOOT0) khi **RDP=0**.
- Xuất xưởng: nạp `.elf`/`.bin` rồi dùng **STM32CubeProgrammer** set **RDP Level 1**.  
  Xem lưu ý BOOT0 / `nBOOT_SEL` trong chat trước — RDP1 hạn chế system bootloader.

## Keypad 4×4 (J_KEY)

```
1 2 3 A
4 5 6 B
7 8 9 C
* 0 # D
```

`keypad_tick()` + `keypad_poll()` — debounce 30 ms.  
App phím:
| Phím | Chức năng |
|------|-----------|
| **D** ngắn | SET — nhập **số lượng** dạng chuỗi (chưa ghi); **A** mới parse + lưu Flash |
| **D** giữ ≥0,8 s | Nhập **RPM** đĩa (15…**80** max) → **A** lưu Flash · **B** hủy |
| **A** START | Commit set (nếu đang SET) rồi đếm; bật nguồn dùng lại target đã lưu |
| **C** XẢ | Xả hết, bỏ qua set |
| **B** STOP | Dừng |
| **#** / **\*** | Hiện set / tổng |

**RPM max = 80** (`COUNT_UI_RPM_MAX`): đĩa đếm thuốc/hạt Ø~120–180 mm trên NEMA17 — cao hơn dễ văng vật nhẹ. Mặc định **50** RPM.

## TM1637 4 số (J_DISP)

Module kiểu [Shopee TM1637 4 chữ số](https://shopee.vn/M%C3%B4-%C4%90un-tm1637-7-K%C3%AD-T%E1%BB%B1-4-Ch%E1%BB%AF-S%E1%BB%91-led-0.36-0.56--i.81431289.23877915626): **CLK · DIO · +5V · GND** → PA15 / PD0.

```c
tm1637_init();
tm1637_set_brightness(5);     // 0..7
tm1637_show_uint(count, false); // 0..9999, ẩn số 0 đầu
```

Số đếm cập nhật tự động khi `count_sensor_get()` đổi; phím **C** (XẢ) / clear theo UI.

## Cảm biến — luôn 2 kênh

- **PA0** `/BUP` (J14 hoặc J15) + **PA3** `/CNT5`
- Xung hợp lệ đầu → khóa kênh; kênh kia không cộng
- Kẹt mức trước khi khóa → bỏ kênh (giắc trống)

```c
count_sensor_init();
count_sensor_tick();
uint32_t n = count_sensor_get();
count_channel_t ch = count_sensor_channel(); /* NONE / BUP / CNT5 */
```

## API nhanh

```c
motors_run_counting(60);   /* M1 đĩa CCW + M2 bánh răng CW */
motors_stop_all();

count_sensor_tick();
uint32_t n = count_sensor_get();

keypad_tick();
keypad_event_t e;
while (keypad_poll(&e)) {
    if (e.type == KEYPAD_EVT_PRESS && e.is_digit) { /* e.ch */ }
}
```
