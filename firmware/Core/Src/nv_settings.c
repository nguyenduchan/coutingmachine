#include "nv_settings.h"
#include "stm32g0xx_hal.h"

/* G030C8: 64 KiB flash, 2 KiB pages → last page index 31 */
#define NV_PAGE_SIZE      0x800u
#define NV_PAGE_ADDR      0x0800F800u
#define NV_PAGE_INDEX     31u
#define NV_MAGIC          0x434E5453u /* 'CNTS' */
#define NV_CHECK_XOR      0xA5A5A5A5u

#ifndef FLASH_KEY1
#define FLASH_KEY1        0x45670123U
#endif
#ifndef FLASH_KEY2
#define FLASH_KEY2        0xCDEF89ABU
#endif

typedef struct {
    uint32_t magic;
    uint32_t target;
    uint32_t rpm;
    uint32_t check;
} nv_blob_t;

static uint32_t blob_check(const nv_blob_t *b)
{
    return b->magic ^ b->target ^ b->rpm ^ NV_CHECK_XOR;
}

static bool blob_valid(const nv_blob_t *b)
{
    if (b->magic != NV_MAGIC) {
        return false;
    }
    if (blob_check(b) != b->check) {
        return false;
    }
    if (b->target > 9999u) {
        return false;
    }
    return true;
}

bool nv_settings_load(nv_settings_t *out)
{
    if (out == NULL) {
        return false;
    }

    const nv_blob_t *b = (const nv_blob_t *)NV_PAGE_ADDR;
    if (!blob_valid(b)) {
        return false;
    }

    out->target = b->target;
    out->rpm = b->rpm;
    return true;
}

static void flash_unlock(void)
{
    if ((FLASH->CR & FLASH_CR_LOCK) != 0u) {
        FLASH->KEYR = FLASH_KEY1;
        FLASH->KEYR = FLASH_KEY2;
    }
}

static void flash_lock(void)
{
    FLASH->CR |= FLASH_CR_LOCK;
}

static void flash_clear_errors(void)
{
    FLASH->SR = FLASH_SR_PROGERR | FLASH_SR_WRPERR | FLASH_SR_PGAERR
              | FLASH_SR_SIZERR | FLASH_SR_PGSERR | FLASH_SR_MISERR
              | FLASH_SR_EOP;
}

static bool flash_wait(void)
{
    uint32_t guard = 1000000u;
    while ((FLASH->SR & FLASH_SR_BSY1) != 0u) {
        if (--guard == 0u) {
            return false;
        }
    }
    if ((FLASH->SR & (FLASH_SR_PROGERR | FLASH_SR_WRPERR | FLASH_SR_PGAERR
                      | FLASH_SR_SIZERR | FLASH_SR_PGSERR | FLASH_SR_MISERR))
        != 0u) {
        flash_clear_errors();
        return false;
    }
    if ((FLASH->SR & FLASH_SR_EOP) != 0u) {
        FLASH->SR = FLASH_SR_EOP;
    }
    return true;
}

static bool flash_erase_page(void)
{
    if (!flash_wait()) {
        return false;
    }
    flash_clear_errors();
    FLASH->CR &= ~(FLASH_CR_PNB | FLASH_CR_PER | FLASH_CR_MER1);
    FLASH->CR |= FLASH_CR_PER;
    FLASH->CR |= (NV_PAGE_INDEX << FLASH_CR_PNB_Pos);
    FLASH->CR |= FLASH_CR_STRT;
    bool ok = flash_wait();
    FLASH->CR &= ~(FLASH_CR_PER | FLASH_CR_PNB);
    return ok;
}

static bool flash_program_u64(uint32_t addr, uint64_t data)
{
    if (!flash_wait()) {
        return false;
    }
    flash_clear_errors();
    FLASH->CR |= FLASH_CR_PG;
    *(__IO uint32_t *)addr = (uint32_t)data;
    *(__IO uint32_t *)(addr + 4u) = (uint32_t)(data >> 32);
    bool ok = flash_wait();
    FLASH->CR &= ~FLASH_CR_PG;
    return ok;
}

bool nv_settings_save(const nv_settings_t *in)
{
    if (in == NULL) {
        return false;
    }

    nv_blob_t b;
    b.magic = NV_MAGIC;
    b.target = (in->target > 9999u) ? 9999u : in->target;
    b.rpm = in->rpm;
    b.check = blob_check(&b);

    const nv_blob_t *cur = (const nv_blob_t *)NV_PAGE_ADDR;
    if (blob_valid(cur)
        && cur->target == b.target
        && cur->rpm == b.rpm) {
        return true;
    }

    __disable_irq();
    flash_unlock();

    bool ok = flash_erase_page();
    if (ok) {
        /* Two double-words; copy via bytes to avoid strict-alias issues */
        uint64_t dw0;
        uint64_t dw1;
        const uint8_t *src = (const uint8_t *)&b;
        uint8_t *d0 = (uint8_t *)&dw0;
        uint8_t *d1 = (uint8_t *)&dw1;
        for (uint32_t i = 0; i < 8u; i++) {
            d0[i] = src[i];
            d1[i] = src[i + 8u];
        }
        ok = flash_program_u64(NV_PAGE_ADDR, dw0)
          && flash_program_u64(NV_PAGE_ADDR + 8u, dw1);
    }

    flash_lock();
    __enable_irq();
    return ok;
}
