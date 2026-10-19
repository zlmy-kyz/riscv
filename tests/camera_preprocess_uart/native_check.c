/* tests/camera_preprocess_uart/native_check.c -- host-only harness.
 *
 * NEVER compiled into the board image.  It drives the *exact* board modules
 * (preprocess_ref.c, pp01_wire.c) on the host so that
 *
 *   1) the sampling coordinates and the RGB565 -> RGB888 bit-replication
 *      expansion compiled for the board can be compared byte-by-byte against the
 *      frozen Python formula on fixed patterns, and
 *   2) the PP01 header encoder and the CRC32 table implementation the board
 *      transmits can be compared byte-for-byte against the peer PC tool.
 *
 * Usage:
 *   native_check --vectors
 *   native_check --ref <source.rgb565> <expected.rgb> <coords.bin>
 *   native_check --wire <records.bin>
 *
 * --ref coords.bin is 9216 records of six little-endian uint32 fields:
 *   x, y, sx, sy, source_byte_offset, rgb565_pixel
 * Every value comes from preprocess_ref.c; nothing is recomputed here.
 *
 * --wire records.bin is, for each fixed tuple, 32 header bytes followed by
 * `payload_len` payload bytes (payload_len = 0 for END tuples).  Tuple list and
 * payload formula are frozen below; build.py regenerates both independently.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pp01_wire.h"
#include "preprocess_ref.h"

#define SRC_BYTES (1280u * 720u * 2u)
#define OUT_BYTES (96u * 96u * 3u)
#define OUT_PIXELS (96u * 96u)
#define RECORD_WORDS 6u

static uint8_t payload_byte(uint32_t offset, uint32_t index)
{
    return (uint8_t)(((offset + index) * 37u + 11u) & 0xffu);
}

static int write_file(const char *path, const uint8_t *data, size_t bytes)
{
    FILE *f = fopen(path, "wb");
    if (f == NULL) {
        fprintf(stderr, "cannot open %s\n", path);
        return 1;
    }
    if (bytes && fwrite(data, 1, bytes, f) != bytes) {
        fprintf(stderr, "short write %s\n", path);
        fclose(f);
        return 1;
    }
    if (fclose(f) != 0) {
        fprintf(stderr, "close failed %s\n", path);
        return 1;
    }
    return 0;
}

static void print_rgb(const char *tag, uint16_t pixel)
{
    uint8_t rgb[3];
    pp_expand(pixel, rgb);
    printf("%s %04x %02x%02x%02x\n", tag, (unsigned)pixel, rgb[0], rgb[1], rgb[2]);
}

static int vectors(void)
{
    uint32_t sx, sy;
    print_rgb("VECTOR", 0x0000u);
    print_rgb("VECTOR", 0xffffu);
    print_rgb("VECTOR", 0x2104u);
    print_rgb("VECTOR", 0x0841u);
    print_rgb("VECTOR", 0xf800u);
    print_rgb("VECTOR", 0x07e0u);
    print_rgb("VECTOR", 0x001fu);
    print_rgb("VECTOR", 0x0001u);
    print_rgb("VECTOR", 0x0010u);
    pp_source_coord(0u, 0u, &sx, &sy);
    printf("FIRST %u %u %u\n", sx, sy, pp_source_byte_offset(0u, 0u));
    pp_source_coord(95u, 95u, &sx, &sy);
    printf("LAST %u %u %u\n", sx, sy, pp_source_byte_offset(95u, 95u));
    pp_source_coord(0u, 0u, &sx, &sy);
    uint32_t prev = sx;
    unsigned step7 = 0, step8 = 0, other = 0;
    for (unsigned x = 1u; x < 96u; x++) {
        pp_source_coord(x, 0u, &sx, &sy);
        uint32_t delta = sx - prev;
        if (delta == 7u) {
            step7++;
        } else if (delta == 8u) {
            step8++;
        } else {
            other++;
        }
        prev = sx;
    }
    printf("STRIDE 7=%u 8=%u other=%u\n", step7, step8, other);
    return 0;
}

static int reference(const char *source_path, const char *expected_path,
                     const char *coords_path)
{
    FILE *f = fopen(source_path, "rb");
    if (f == NULL) {
        fprintf(stderr, "cannot open %s\n", source_path);
        return 1;
    }
    uint8_t *source = (uint8_t *)malloc(SRC_BYTES);
    uint8_t *expected = (uint8_t *)malloc(OUT_BYTES);
    uint8_t *coords = (uint8_t *)malloc((size_t)OUT_PIXELS * RECORD_WORDS * 4u);
    if (source == NULL || expected == NULL || coords == NULL) {
        fprintf(stderr, "out of memory\n");
        fclose(f);
        free(source);
        free(expected);
        free(coords);
        return 1;
    }
    if (fread(source, 1, SRC_BYTES, f) != SRC_BYTES) {
        fprintf(stderr, "short read %s\n", source_path);
        fclose(f);
        free(source);
        free(expected);
        free(coords);
        return 1;
    }
    if (fclose(f) != 0) {
        fprintf(stderr, "close failed %s\n", source_path);
        free(source);
        free(expected);
        free(coords);
        return 1;
    }
    if (((uintptr_t)source & 3u) != 0u) {
        fprintf(stderr, "source buffer is not 4-byte aligned\n");
        free(source);
        free(expected);
        free(coords);
        return 1;
    }
    const volatile uint32_t *words = (const volatile uint32_t *)source;
    for (unsigned y = 0; y < 96u; y++) {
        for (unsigned x = 0; x < 96u; x++) {
            uint32_t sx, sy;
            uint8_t rgb[3];
            uint8_t *rec = coords + ((size_t)(y * 96u + x) * RECORD_WORDS * 4u);
            pp_source_coord(x, y, &sx, &sy);
            uint32_t offset = pp_source_byte_offset(x, y);
            uint16_t pixel = pp_pixel_at(words, offset);
            pp_expected(words, x, y, rgb);
            expected[3u * (y * 96u + x) + 0u] = rgb[0];
            expected[3u * (y * 96u + x) + 1u] = rgb[1];
            expected[3u * (y * 96u + x) + 2u] = rgb[2];
            uint32_t fields[RECORD_WORDS] = { x, y, sx, sy, offset, (uint32_t)pixel };
            for (unsigned k = 0; k < RECORD_WORDS; k++) {
                rec[4u * k] = (uint8_t)fields[k];
                rec[4u * k + 1u] = (uint8_t)(fields[k] >> 8);
                rec[4u * k + 2u] = (uint8_t)(fields[k] >> 16);
                rec[4u * k + 3u] = (uint8_t)(fields[k] >> 24);
            }
        }
    }
    int status = write_file(expected_path, expected, OUT_BYTES);
    if (status == 0) {
        status = write_file(coords_path, coords, (size_t)OUT_PIXELS * RECORD_WORDS * 4u);
    }
    if (status == 0) {
        printf("NATIVE_REF source_bytes=%u out_bytes=%u coords=%u records=%u\n",
               (unsigned)SRC_BYTES, (unsigned)OUT_BYTES,
               (unsigned)(OUT_PIXELS * RECORD_WORDS * 4u), (unsigned)OUT_PIXELS);
    }
    free(source);
    free(expected);
    free(coords);
    return status;
}

/* kind, source_seq, offset, total_len; payload_len derived as the protocol does. */
static const uint32_t tuples[10][4] = {
    { 1u,          1u,         0u, 1843200u },
    { 1u,          1u,      1024u, 1843200u },
    { 1u,          3u,       512u, 1843200u },
    { 1u, 4294967295u,   1842176u, 1843200u },
    { 2u,          1u,   1843200u, 1843200u },
    { 2u, 4294967295u,   1843200u, 1843200u },
    { 3u,          2u,         0u,   27648u },
    { 3u,          2u,     26624u,   27648u },
    { 4u,          2u,     27648u,   27648u },
    { 4u,          7u,     27648u,   27648u },
};

static int wire(const char *path)
{
    uint8_t *out = (uint8_t *)malloc((size_t)10 * (PP01_HEADER_BYTES + 1024u));
    if (out == NULL) {
        fprintf(stderr, "out of memory\n");
        return 1;
    }
    pp01_crc_init();
    size_t pos = 0;
    for (unsigned t = 0; t < 10u; t++) {
        uint32_t kind = tuples[t][0], seq = tuples[t][1];
        uint32_t offset = tuples[t][2], total = tuples[t][3];
        uint32_t length = (kind == 1u || kind == 3u) ? total - offset : 0u;
        if (length > 1024u) {
            length = 1024u;
        }
        for (uint32_t i = 0; i < length; i++) {
            out[pos + PP01_HEADER_BYTES + i] = payload_byte(offset, i);
        }
        uint32_t data_crc = pp01_crc_bytes(out + pos + PP01_HEADER_BYTES, length);
        pp01_build_header(out + pos, kind, seq, offset, length, total, data_crc);
        pos += PP01_HEADER_BYTES + length;
    }
    int status = write_file(path, out, pos);
    if (status == 0) {
        printf("NATIVE_WIRE tuples=10 bytes=%u\n", (unsigned)pos);
    }
    free(out);
    return status;
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "--vectors") == 0) {
        return vectors();
    }
    if (argc == 5 && strcmp(argv[1], "--ref") == 0) {
        return reference(argv[2], argv[3], argv[4]);
    }
    if (argc == 3 && strcmp(argv[1], "--wire") == 0) {
        return wire(argv[2]);
    }
    fprintf(stderr, "usage: %s --vectors | --ref <src> <expected> <coords> | --wire <out>\n",
            argv[0]);
    return 2;
}
