#ifndef DDR_RANDOM_H
#define DDR_RANDOM_H
#include <stdint.h>
/* Caller must validate the low 60 KiB window before invoking either function. */
void ddr_random_write(uint32_t address, const uint8_t *data, uint32_t length);
uint32_t ddr_random_crc(uint32_t address, uint32_t length, uint8_t *scratch);
#endif
