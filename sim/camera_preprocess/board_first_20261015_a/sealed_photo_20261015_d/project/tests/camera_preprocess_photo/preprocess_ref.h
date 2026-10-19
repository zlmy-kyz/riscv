/* Frozen integer reference for the 96x96 RGB888 preprocessing job.
 *
 * This header/c file is the single source of expected output inside the board
 * program.  It is compiled unchanged into the RISC-V image and into the native
 * host harness (native_ref_check.c) so the exact board code path can be checked
 * byte-by-byte against the Python formula on the host.
 *
 *   sx = 280 + ((2*x+1)*15)/4        (integer division)
 *   sy =       ((2*y+1)*15)/4
 *   o  = 2*(sy*1280 + sx)            byte offset inside the 1280x720 RGB565 frame
 *   R  = (r5<<3)|(r5>>2),  r5=(p>>11)&31     bit replication, never float/round
 *   G  = (g6<<2)|(g6>>4),  g6=(p>>5)&63
 *   B  = (b5<<3)|(b5>>2),  b5=p&31
 *
 * The pixel is read as one little-endian 32-bit word at (o & ~3) and the 16-bit
 * halfword is selected with bit 1 of the byte offset; this mirrors the RTL
 * source-tap selection (source_addr[4:1]) and needs no sub-word DDR access.
 */
#ifndef PP_PREPROCESS_REF_H
#define PP_PREPROCESS_REF_H

#include <stdint.h>

#define PP_SRC_WIDTH 1280u
#define PP_CROP_X 280u
#define PP_OUT 96u

/* Sampled source coordinates for one output coordinate. */
void pp_source_coord(unsigned x, unsigned y, uint32_t *sx, uint32_t *sy);
/* Byte offset 2*(sy*1280+sx) inside the RGB565 frame. */
uint32_t pp_source_byte_offset(unsigned x, unsigned y);
/* RGB565 pixel at a byte offset, read as one 32-bit little-endian word. */
uint16_t pp_pixel_at(const volatile uint32_t *source_words, uint32_t byte_offset);
/* RGB565 -> RGB888 by bit replication only. */
void pp_expand(uint16_t pixel, uint8_t out[3]);
/* Full reference: sampled pixel and expanded bytes for one output coordinate. */
void pp_expected(const volatile uint32_t *source_words, unsigned x, unsigned y,
                 uint8_t out[3]);

#endif /* PP_PREPROCESS_REF_H */
