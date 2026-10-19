#ifndef CAMERA_CRC32_H
#define CAMERA_CRC32_H
#include <stdint.h>
void crc32_init(void);
uint32_t crc32_bytes(const uint8_t *p, uint32_t n);
uint32_t crc32_words(volatile const uint32_t *p, uint32_t words);
void camera_header(uint8_t out[32], uint32_t type, uint32_t seq, uint32_t offset,
                   uint32_t length, uint32_t total, uint32_t crc);
#endif
