#include "ddr_test.h"
#include "crc32.h"

static inline __attribute__((always_inline)) uint32_t pack_word(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

__attribute__((noinline, noclone))
int ddr_fixed_compare(const uint8_t *source, uint8_t *readback)
{
    volatile uint32_t *ddr = (volatile uint32_t *)LOADER_DDR_TEST_BASE;
    uint32_t different = 0;
    __asm__ volatile(".global loader_ddr_write_start\nloader_ddr_write_start:" ::: "memory");
    for (unsigned i = 0; i < 16; ++i) ddr[i] = pack_word(source + i * 4);
    __asm__ volatile(".global loader_ddr_write_end\nloader_ddr_write_end:\nfence rw,rw" ::: "memory");
    __asm__ volatile(".global loader_ddr_read_start\nloader_ddr_read_start:" ::: "memory");
    for (unsigned i = 0; i < 16; ++i) {
        uint32_t observed = ddr[i];
        different |= observed ^ pack_word(source + i * 4);
        for (unsigned lane = 0; lane < 4; ++lane)
            readback[i * 4 + lane] = (uint8_t)(observed >> (lane * 8));
    }
    __asm__ volatile(".global loader_ddr_read_end\nloader_ddr_read_end:" ::: "memory");
    return different == 0;
}

__attribute__((noinline, noclone))
uint32_t ddr_fixed_crc(uint8_t *readback)
{
    volatile const uint32_t *ddr = (volatile const uint32_t *)LOADER_DDR_TEST_BASE;
    __asm__ volatile(".global loader_ddr_crc_read_start\nloader_ddr_crc_read_start:" ::: "memory");
    for (unsigned i = 0; i < 16; ++i) {
        uint32_t observed = ddr[i];
        for (unsigned lane = 0; lane < 4; ++lane)
            readback[i * 4 + lane] = (uint8_t)(observed >> (lane * 8));
    }
    __asm__ volatile(".global loader_ddr_crc_read_end\nloader_ddr_crc_read_end:" ::: "memory");
    return loader_crc32(readback, 64);
}
