#ifndef DDR_TEST_H
#define DDR_TEST_H
#include <stdint.h>
#define LOADER_DDR_TEST_BASE 0x40000000u
/* Only the caller's already validated 64-byte fixed diagnostic is permitted. */
int ddr_fixed_compare(const uint8_t *source, uint8_t *readback);
/* Always reread physical DDR, including duplicate verification requests. */
uint32_t ddr_fixed_crc(uint8_t *readback);
#endif
