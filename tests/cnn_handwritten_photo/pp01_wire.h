
#ifndef PP01_WIRE_H
#define PP01_WIRE_H

#include <stdint.h>

#define PP01_HEADER_BYTES 32u


void pp01_crc_init(void);

uint32_t pp01_crc_state(void);
uint32_t pp01_crc_step(uint32_t state, uint8_t byte);
uint32_t pp01_crc_finish(uint32_t state);

uint32_t pp01_crc_bytes(const uint8_t *data, uint32_t length);

void pp01_build_header(uint8_t out[PP01_HEADER_BYTES], uint32_t kind, uint32_t seq,
                       uint32_t offset, uint32_t length, uint32_t total,
                       uint32_t data_crc);

#endif 

