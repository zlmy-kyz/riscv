/* Frozen PP01 wire encoding and reflected IEEE CRC32.
 *
 * Compiled unchanged into the RISC-V board program and into the host check
 * program (native_check.c), so the byte layout and the CRC table implementation
 * that the board actually transmits can be compared against the peer PC tool
 * (tools/camera_preprocess_uart/protocol.py, which uses zlib.crc32).
 *
 * 32-byte header, all fields uint32 little endian:
 *   [0:4)  magic 'PP01'
 *   [4:8)  kind  1 source DATA, 2 source END, 3 RGB888 DATA, 4 RGB888 END
 *   [8:12) source_seq      Camera source frame sequence of the group
 *   [12:16) offset         byte offset inside the corresponding stream
 *   [16:20) payload_len    DATA min(1024,total-offset); END 0
 *   [20:24) total_len      1843200 source / 27648 RGB888
 *   [24:28) data_crc       DATA CRC32(payload); END CRC32(whole stream)
 *   [28:32) header_crc     CRC32(header[0:28])
 * CRC32 is reflected IEEE (init 0xffffffff, polynomial 0xedb88320, final xor
 * 0xffffffff) exactly like zlib.crc32.
 */
#ifndef PP01_WIRE_H
#define PP01_WIRE_H

#include <stdint.h>

#define PP01_HEADER_BYTES 32u

/* Fill the 256-entry CRC table once before any CRC call. */
void pp01_crc_init(void);
/* Streaming reflected IEEE CRC32 state helpers. */
uint32_t pp01_crc_state(void);
uint32_t pp01_crc_step(uint32_t state, uint8_t byte);
uint32_t pp01_crc_finish(uint32_t state);
/* One-shot CRC32 over a byte range. */
uint32_t pp01_crc_bytes(const uint8_t *data, uint32_t length);
/* Encode one complete 32-byte PP01 header. */
void pp01_build_header(uint8_t out[PP01_HEADER_BYTES], uint32_t kind, uint32_t seq,
                       uint32_t offset, uint32_t length, uint32_t total,
                       uint32_t data_crc);

#endif /* PP01_WIRE_H */
