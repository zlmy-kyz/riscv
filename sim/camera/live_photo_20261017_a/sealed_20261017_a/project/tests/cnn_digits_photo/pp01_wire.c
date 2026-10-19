#include "pp01_wire.h"

static uint32_t crc_table[256];

void pp01_crc_init(void)
{
    for (uint32_t i = 0; i < 256u; i++) {
        uint32_t c = i;
        for (unsigned bit = 0; bit < 8u; bit++) {
            c = (c >> 1) ^ ((c & 1u) ? 0xedb88320u : 0u);
        }
        crc_table[i] = c;
    }
}

uint32_t pp01_crc_state(void) { return 0xffffffffu; }

uint32_t pp01_crc_step(uint32_t state, uint8_t byte)
{
    return (state >> 8) ^ crc_table[(state ^ (uint32_t)byte) & 255u];
}

uint32_t pp01_crc_finish(uint32_t state) { return ~state; }

uint32_t pp01_crc_bytes(const uint8_t *data, uint32_t length)
{
    uint32_t state = pp01_crc_state();
    while (length--) {
        state = pp01_crc_step(state, *data++);
    }
    return pp01_crc_finish(state);
}

static void put_le32(uint8_t *p, uint32_t value)
{
    for (unsigned i = 0; i < 4u; i++) {
        p[i] = (uint8_t)value;
        value >>= 8;
    }
}

void pp01_build_header(uint8_t out[PP01_HEADER_BYTES], uint32_t kind, uint32_t seq,
                       uint32_t offset, uint32_t length, uint32_t total,
                       uint32_t data_crc)
{
    out[0] = 'C';
    out[1] = 'N';
    out[2] = '0';
    out[3] = '2';
    put_le32(out + 4, kind);
    put_le32(out + 8, seq);
    put_le32(out + 12, offset);
    put_le32(out + 16, length);
    put_le32(out + 20, total);
    put_le32(out + 24, data_crc);
    put_le32(out + 28, pp01_crc_bytes(out, 28u));
}
