"""Independent Python reference for the 96x96 preprocess job (single authority).

Authority: doc/camera/OV5640预处理96RGB888与DDR接口_2026-10-15.md section 2 and
DeepSeek/预处理96RGB888_逐字节参考与串口导图测试_2026-10-15.md section 2.
Nothing here reads DUT data, DUT addresses or DUT counters: the source pixels and
the sampling coordinates are closed-form integer expressions only.
"""
import zlib

W, H = 1280, 720
OW = OH = 96
OUT_BYTES = OW * OH * 3          # 27648
CROP_X0, CROP_SIZE = 280, 720
SRC_BYTES = W * H * 2            # 1843200
OUT_CPU_BASE = 0x42000000
OUT_NATIVE_BASE = 0x00800000
SRC_A_CPU, SRC_B_CPU = 0x41000000, 0x41200000
READS, WRITES = OW * OH, OUT_BYTES // 32

# job: buffer 0=A,1=B; kind 'color' -> constant RGB565 word; 'asym' -> coordinate pattern
JOBS = [
    dict(job=1, buf=0, kind='color', param=0xF800),
    dict(job=2, buf=1, kind='color', param=0x07E0),
    dict(job=3, buf=0, kind='color', param=0x001F),
    dict(job=4, buf=0, kind='asym', param=1),
    dict(job=5, buf=1, kind='asym', param=2),
]
# Real-CPU group reuses one output address three times with three different k.
SOC_JOBS = [dict(job=4, buf=0, kind='asym', param=1),
            dict(job=5, buf=1, kind='asym', param=2),
            dict(job=6, buf=0, kind='asym', param=3)]


def source_pixel(x, y, kind, param):
    if kind == 'color':
        return param & 0xFFFF
    r5 = (3 * x + 5 * y + 7 * param) & 31
    g6 = (11 * x + 7 * y + 13 * param) & 63
    b5 = (x ^ (3 * y) ^ (17 * param)) & 31
    return (r5 << 11) | (g6 << 5) | b5


def source_bytes(kind, param):
    """Whole 1843200-byte little-endian RGB565 source frame."""
    out = bytearray(SRC_BYTES)
    i = 0
    for y in range(H):
        row = bytearray()
        for x in range(W):
            p = source_pixel(x, y, kind, param)
            row += bytes((p & 0xFF, (p >> 8) & 0xFF))
        out[i:i + len(row)] = row
        i += len(row)
    return bytes(out)


def source_word(addr, kind, param):
    """One 256-bit source beat (native address) for the given pattern."""
    off = (addr << 2) & 0x1FFFFF
    y, x0 = off // 2560, (off % 2560) // 2
    b = bytearray()
    for x in range(x0, x0 + 16):
        p = source_pixel(x, y, kind, param)
        b += bytes((p & 0xFF, (p >> 8) & 0xFF))
    return bytes(b)


def sample_xy(x, y):
    return CROP_X0 + ((2 * x + 1) * 15) // 4, ((2 * y + 1) * 15) // 4


def expand(p):
    r5, g6, b5 = (p >> 11) & 31, (p >> 5) & 63, p & 31
    return ((r5 << 3) | (r5 >> 2), (g6 << 2) | (g6 >> 4), (b5 << 3) | (b5 >> 2))


def expected_rgb(kind, param):
    out = bytearray(OUT_BYTES)
    for y in range(OH):
        sy = ((2 * y + 1) * 15) // 4
        for x in range(OW):
            sx = CROP_X0 + ((2 * x + 1) * 15) // 4
            r, g, b = expand(source_pixel(sx, sy, kind, param))
            i = 3 * (y * OW + x)
            out[i], out[i + 1], out[i + 2] = r, g, b
    return bytes(out)


def expected_words(kind, param):
    raw = expected_rgb(kind, param)
    return [int.from_bytes(raw[i:i + 4], 'little') for i in range(0, len(raw), 4)]


def crc32(data):
    return zlib.crc32(data) & 0xFFFFFFFF


def _local(buf, x, y):
    sx, sy = sample_xy(x, y)
    return (SRC_B_CPU if buf else SRC_A_CPU) - 0x40000000 + 2 * (sy * W + sx)


def native_read_addr(buf, x, y):
    return (_local(buf, x, y) & ~31) // 4


def slot_of(buf, x, y):
    return (_local(buf, x, y) & 31) // 2


def sample_order(buf):
    """(x,y,native_addr,slot) in the RTL's output-pixel order (row major)."""
    return [(x, y, native_read_addr(buf, x, y), slot_of(buf, x, y))
            for y in range(OH) for x in range(OW)]


def write_beats(kind, param):
    """864 (native_addr, 32-byte little-endian payload) output beats."""
    raw = expected_rgb(kind, param)
    return [(OUT_NATIVE_BASE + (i << 3), raw[i * 32:(i + 1) * 32]) for i in range(WRITES)]


def rtl_address_recurrence(buf):
    """Replay the RTL source-address recurrence independently (row/step checks).

    row_addr tracks the row start; source_addr advances inside the row. Both are
    updated at x==95, which is the only place the row stride applies.
    """
    row_addr = source_addr = 0x01002036 if not buf else 0x01202036
    out = []
    for y in range(OH):
        for x in range(OW):
            out.append(source_addr)
            if x == OW - 1:
                nxt = row_addr + (17920 if (y & 1) else 20480)
                row_addr = source_addr = nxt
            else:
                source_addr += 14 if (x & 1) else 16
    return out


def job_record(j):
    raw = expected_rgb(j['kind'], j['param'])
    words = expected_words(j['kind'], j['param'])
    return dict(job=j['job'], buf=j['buf'], kind=j['kind'], param=j['param'],
                bytes=len(raw), crc32=crc32(raw), words=len(words),
                word0=words[0], wordN=words[-1],
                first_pixel=raw[0:3].hex(), last_pixel=raw[-3:].hex(),
                sample_first=list(sample_xy(0, 0)), sample_last=list(sample_xy(OW - 1, OH - 1)),
                native_first=native_read_addr(j['buf'], 0, 0), slot_first=slot_of(j['buf'], 0, 0))


def frame_facts():
    facts = dict(first=sample_xy(0, 0), last=sample_xy(OW - 1, OH - 1),
                 first_native=native_read_addr(0, 0, 0), first_slot=slot_of(0, 0, 0),
                 black=expand(0x0000), white=expand(0xFFFF),
                 r5_4=expand(4 << 11), g6_16=expand(16 << 5), b5_4=expand(4))
    assert facts['first'] == (283, 3) and facts['last'] == (996, 716), facts
    assert facts['black'] == (0, 0, 0) and facts['white'] == (255, 255, 255)
    assert facts['r5_4'] == (33, 0, 0) and facts['g6_16'] == (0, 65, 0) and facts['b5_4'] == (0, 0, 33)
    assert facts['first_native'] == 0x400808 and facts['first_slot'] == 11, facts
    return facts


if __name__ == '__main__':
    import json
    jobs = [job_record(j) for j in JOBS]
    soc = [job_record(j) for j in SOC_JOBS]
    print(json.dumps(dict(status='PREPROCESS_REFERENCE_READY', jobs=jobs, soc_jobs=soc,
                          facts=frame_facts()), indent=2))
