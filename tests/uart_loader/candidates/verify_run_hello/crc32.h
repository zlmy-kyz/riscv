#ifndef LOADER_CRC32_H
#define LOADER_CRC32_H
#include <stdint.h>
uint32_t loader_crc32_update(uint32_t crc, const uint8_t *data, uint32_t length);
uint32_t loader_crc32(const uint8_t *data, uint32_t length);
#endif
