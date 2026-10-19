#include "preprocess_ref.h"

void pp_source_coord(unsigned x, unsigned y, uint32_t *sx, uint32_t *sy)
{
    *sx = PP_CROP_X + (((2u * (uint32_t)x) + 1u) * 15u) / 4u;
    *sy = (((2u * (uint32_t)y) + 1u) * 15u) / 4u;
}

uint32_t pp_source_byte_offset(unsigned x, unsigned y)
{
    uint32_t sx, sy;
    pp_source_coord(x, y, &sx, &sy);
    return 2u * ((sy * PP_SRC_WIDTH) + sx);
}

uint16_t pp_pixel_at(const volatile uint32_t *source_words, uint32_t byte_offset)
{
    uint32_t word = source_words[byte_offset >> 2];
    uint32_t shift = (byte_offset & 2u) ? 16u : 0u;
    return (uint16_t)((word >> shift) & 0xffffu);
}

void pp_expand(uint16_t pixel, uint8_t out[3])
{
    uint32_t value = (uint32_t)pixel;
    uint32_t r5 = (value >> 11) & 31u;
    uint32_t g6 = (value >> 5) & 63u;
    uint32_t b5 = value & 31u;
    out[0] = (uint8_t)((r5 << 3) | (r5 >> 2));
    out[1] = (uint8_t)((g6 << 2) | (g6 >> 4));
    out[2] = (uint8_t)((b5 << 3) | (b5 >> 2));
}

void pp_expected(const volatile uint32_t *source_words, unsigned x, unsigned y,
                 uint8_t out[3])
{
    pp_expand(pp_pixel_at(source_words, pp_source_byte_offset(x, y)), out);
}
