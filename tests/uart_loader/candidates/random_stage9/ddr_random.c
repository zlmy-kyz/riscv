#include "ddr_random.h"
#include "crc32.h"

void ddr_random_write(uint32_t address, const uint8_t *data, uint32_t length)
{
    /* Only valid bytes are written, even for a one-byte file or unaligned chunk. */
    while (length && (address & 3u)) {
        *(volatile uint8_t *)address++ = *data++; --length;
    }
    while (length >= 4) {
        uint32_t word = (uint32_t)data[0] | ((uint32_t)data[1] << 8) |
                        ((uint32_t)data[2] << 16) | ((uint32_t)data[3] << 24);
        *(volatile uint32_t *)address = word;
        address += 4; data += 4; length -= 4;
    }
    while (length--) *(volatile uint8_t *)address++ = *data++;
    __asm__ volatile("fence rw,rw" ::: "memory");
}

static void read_range(uint32_t address, uint8_t *scratch, uint32_t length)
{
    while (length && (address & 3u)) {
        *scratch++ = *(volatile const uint8_t *)address++; --length;
    }
    while (length >= 4) {
        uint32_t word = *(volatile const uint32_t *)address;
        for (unsigned lane = 0; lane < 4; ++lane) scratch[lane] = (uint8_t)(word >> (8u * lane));
        address += 4; scratch += 4; length -= 4;
    }
    while (length--) *scratch++ = *(volatile const uint8_t *)address++;
}

uint32_t ddr_random_crc(uint32_t address, uint32_t length, uint8_t *scratch)
{
    uint32_t crc = 0xFFFFFFFFu;
    while (length) {
        uint32_t count = length > 256 ? 256 : length;
        read_range(address, scratch, count);
        crc = loader_crc32_update(crc, scratch, count);
        address += count; length -= count;
    }
    return crc ^ 0xFFFFFFFFu;
}
