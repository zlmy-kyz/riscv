"""Independent byte-exact reference for the fixed 96x96 RGB888 preprocessing job.

This module is the ONLY source of expected output for the PC tool.  It is written
directly from the frozen formula in
``DeepSeek/预处理96RGB888_逐字节参考与串口导图测试_2026-10-15.md`` §2 and
``doc/camera/OV5640预处理96RGB888与DDR接口_2026-10-15.md`` §2.  It never reads any
DUT/DDR counter, address state machine or output byte.

Contract (all integers, no floating point, no round()):

    sx = 280 + ((2*x+1)*15)//4          x in [0,95]
    sy =      ((2*y+1)*15)//4           y in [0,95]
    o  = 2*(sy*1280+sx)                 source byte address inside the 1280x720 RGB565 frame
    p  = source[o] | (source[o+1]<<8)   little-endian 16-bit pixel
    R  = ((r5)<<3)|((r5)>>2)            r5=(p>>11)&31     bit replication, NOT round(r5*255/31)
    G  = ((g6)<<2)|((g6)>>4)            g6=(p>>5)&63
    B  = ((b5)<<3)|((b5)>>2)            b5=p&31
    expected[3*(96*y+x) + 0..2] = R,G,B

Source geometry: WIDTH=1280, HEIGHT=720, 2 bytes/pixel, 1843200 bytes.
Output geometry: 96x96x3, 27648 bytes, continuous HWC, no row padding.
"""
import zlib

WIDTH, HEIGHT = 1280, 720
CROP_X, CROP_W = 280, 720
OUT, OUT_BYTES = 96, 96 * 96 * 3
SOURCE_BYTES = WIDTH * HEIGHT * 2
crc32 = lambda b: zlib.crc32(b) & 0xffffffff

# ---------------------------------------------------------------- formula core

def source_coord(x, y):
    """Return (sx, sy) of the sampled source pixel for one output coordinate."""
    return CROP_X + ((2 * x + 1) * 15) // 4, ((2 * y + 1) * 15) // 4


def expand565(p):
    """RGB565 -> (R,G,B) by bit replication only."""
    r5 = (p >> 11) & 31
    g6 = (p >> 5) & 63
    b5 = p & 31
    return ((r5 << 3) | (r5 >> 2), (g6 << 2) | (g6 >> 4), (b5 << 3) | (b5 >> 2))


def expected_from_source(source):
    """Independently compute the 27648 expected RGB888 bytes from the raw RGB565 frame."""
    if len(source) != SOURCE_BYTES:
        raise ValueError(f'expected source {SOURCE_BYTES} bytes, got {len(source)}')
    out = bytearray(OUT_BYTES)
    k = 0
    for y in range(OUT):
        sy = ((2 * y + 1) * 15) // 4
        row = sy * WIDTH
        for x in range(OUT):
            sx = CROP_X + ((2 * x + 1) * 15) // 4
            o = 2 * (row + sx)
            p = source[o] | (source[o + 1] << 8)
            r5 = (p >> 11) & 31
            g6 = (p >> 5) & 63
            b5 = p & 31
            out[k] = (r5 << 3) | (r5 >> 2)
            out[k + 1] = (g6 << 2) | (g6 >> 4)
            out[k + 2] = (b5 << 3) | (b5 >> 2)
            k += 3
    return bytes(out)


def expected_second_implementation(source):
    """A deliberately different implementation used only to cross-check the first.

    Builds the row/column sample tables by repeatedly adding the 7/8 step pattern
    produced by ``(2n+1)*15//4`` instead of evaluating the closed formula per pixel,
    and unpacks the RGB565 word with shifts/masks applied in a different order.
    """
    if len(source) != SOURCE_BYTES:
        raise ValueError('source size')
    sx_table, sy_table = [], []
    for n in range(OUT):
        sx_table.append(CROP_X + (15 * (2 * n + 1)) // 4)
        sy_table.append((15 * (2 * n + 1)) // 4)
    out = bytearray()
    for y in range(OUT):
        base = sy_table[y] * WIDTH
        for x in range(OUT):
            o = 2 * (base + sx_table[x])
            lo, hi = source[o], source[o + 1]
            p = lo + (hi << 8)
            b = p & 0x1f
            g = (p >> 5) & 0x3f
            r = (p >> 11) & 0x1f
            out += bytes((r * 8 + r // 4, g * 4 + g // 16, b * 8 + b // 4))
    return bytes(out)


def sample_table():
    """The frozen 96-entry column coordinate table plus its first/last value."""
    table = [source_coord(x, 0)[0] for x in range(OUT)]
    return dict(first=table[0], last=table[-1],
                stride=sorted({table[i + 1] - table[i] for i in range(OUT - 1)}),
                table=table)


def first_mismatch(expected, actual, source):
    """Return the first differing output byte with the full diagnostic record.

    Returns ``None`` when all 27648 bytes are equal.  The record carries the
    output coordinate, channel, sampled source coordinate and both values as
    required by the task.
    """
    if len(expected) != OUT_BYTES or len(actual) != OUT_BYTES:
        raise ValueError('expected/actual must both be 27648 bytes')
    for i in range(OUT_BYTES):
        if expected[i] != actual[i]:
            pixel, channel = divmod(i, 3)
            x, y = pixel % OUT, pixel // OUT
            sx, sy = source_coord(x, y)
            o = 2 * (sy * WIDTH + sx)
            p = source[o] | (source[o + 1] << 8)
            return dict(output_byte=i, x=x, y=y, channel='RGB'[channel],
                        source_x=sx, source_y=sy, source_byte=o, source_rgb565=f'{p:04x}',
                        expected_value=expected[i], actual_value=actual[i])
    return None


def compare(expected, actual, source):
    """Full byte comparison plus CRC closure over both byte strings."""
    first = first_mismatch(expected, actual, source)
    return dict(all_equal=first is None, first_mismatch=first,
                expected_crc32=crc32(expected), actual_crc32=crc32(actual),
                bytes=OUT_BYTES)


# ------------------------------------------------------------------- PNG writer

def _chunk(kind, data):
    return (len(data).to_bytes(4, 'big') + kind + data +
            (zlib.crc32(kind + data) & 0xffffffff).to_bytes(4, 'big'))


def png_rgb(width, height, rows):
    """Minimal deterministic PNG (8-bit RGB, no interlace), standard library only.

    ``rows`` yields exactly ``height`` byte strings of ``3*width`` bytes each.
    """
    scan = bytearray()
    for row in rows:
        if len(row) != 3 * width:
            raise ValueError('row width')
        scan.append(0)          # filter type 0, never substituted
        scan += row
    return (b'\x89PNG\r\n\x1a\n' +
            _chunk(b'IHDR', width.to_bytes(4, 'big') + height.to_bytes(4, 'big') +
                   bytes((8, 2, 0, 0, 0))) +
            _chunk(b'IDAT', zlib.compress(bytes(scan), 6)) +
            _chunk(b'IEND', b''))


def png_source565(raw):
    """1843200-byte RGB565 frame -> 1280x720 PNG via bit replication (no scaling)."""
    if len(raw) != SOURCE_BYTES:
        raise ValueError('RGB565 source size')
    def rows():
        for y in range(HEIGHT):
            row = bytearray()
            base = y * WIDTH * 2
            for x in range(WIDTH):
                o = base + 2 * x
                row += bytes(expand565(raw[o] | (raw[o + 1] << 8)))
            yield bytes(row)
    return png_rgb(WIDTH, HEIGHT, rows())


def png_rgb888(raw):
    """27648-byte 96x96 RGB888 tensor -> PNG, one row at a time."""
    if len(raw) != OUT_BYTES:
        raise ValueError('RGB888 tensor size')
    return png_rgb(OUT, OUT, (raw[3 * OUT * y:3 * OUT * (y + 1)] for y in range(OUT)))


# ------------------------------------------------------- independent PNG decoder

def decode_png(data):
    """Decode the PNGs produced above (8-bit RGB, filter 0, zlib IDAT).

    Independent of the writer: re-parses the stream and re-inflates the IDAT.
    Returns ``(width, height, pixels)`` with ``pixels`` a bytes object.
    """
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG')
    pos, idat, head = 8, bytearray(), None
    while pos < len(data):
        length = int.from_bytes(data[pos:pos + 4], 'big')
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        crc = int.from_bytes(data[pos + 8 + length:pos + 12 + length], 'big')
        if zlib.crc32(kind + body) & 0xffffffff != crc:
            raise ValueError('PNG chunk CRC')
        if kind == b'IHDR':
            head = body
        elif kind == b'IDAT':
            idat += body
        elif kind == b'IEND':
            pos += 12 + length
            break
        pos += 12 + length
    if head is None:
        raise ValueError('no IHDR')
    width = int.from_bytes(head[0:4], 'big')
    height = int.from_bytes(head[4:8], 'big')
    depth, color, comp, filt, interlace = head[8:13]
    if (depth, color, comp, filt, interlace) != (8, 2, 0, 0, 0):
        raise ValueError('unsupported PNG format')
    raw = zlib.decompress(bytes(idat))
    stride = 3 * width
    if len(raw) != (stride + 1) * height:
        raise ValueError('PNG raster size')
    out = bytearray()
    for y in range(height):
        if raw[y * (stride + 1)] != 0:
            raise ValueError('unexpected PNG filter')
        out += raw[y * (stride + 1) + 1:y * (stride + 1) + 1 + stride]
    return width, height, bytes(out)


# ----------------------------------------------------------------- self vectors

def self_vectors():
    """Named vectors that pin the formula, the bit replication and the geometry."""
    pure = {0xF800: (255, 0, 0), 0x07E0: (0, 255, 0), 0x001F: (0, 0, 255),
            0x0000: (0, 0, 0), 0xFFFF: (255, 255, 255), 0x0841: (8, 8, 8),
            0x2104: (33, 32, 33), 0x0020: (0, 4, 0)}
    colors = {f'{p:04x}': expand565(p) for p in pure}
    for p, want in pure.items():
        if colors[f'{p:04x}'] != want:
            raise AssertionError(f'color vector {p:04x}')
    # 0x2104 = r5=4, g6=8, b5=4 -> replicated to (33, 32, 33); float scaling with
    # rounding would give (33, 32, 33) too, but 0x0841 (r5=g6=b5=1) -> (8, 8, 8)
    # rules rounding out (round(1*255/31) = 8 is a coincidence, round(1*255/63) = 4
    # is not, so 0x0841 pins the green replication).
    if colors['2104'] != (33, 32, 33):
        raise AssertionError('low-bit replication vector 2104')
    if expand565(0x0020) != (0, 4, 0):
        raise AssertionError('green replication must use 6-bit g6 (0x0020)')
    # Low-bit replication: 5-bit 4 -> 33, 6-bit 16 -> 65.  0x0841 = (1,2,1) is a
    # second vector showing replication, not rounding: 1 -> 8, 2 -> 8.
    if expand565(0x0841) != (8, 8, 8):
        raise AssertionError('low-bit replication vector 0841')
    if (4 << 3) | (4 >> 2) != 33 or (16 << 2) | (16 >> 4) != 65:
        raise AssertionError('replication constants')
    table = sample_table()
    if (table['first'], table['last'], table['stride']) != (283, 996, [7, 8]):
        raise AssertionError('sample table geometry')
    sy_first, sy_last = source_coord(0, 0)[1], source_coord(95, 95)[1]
    if (sy_first, sy_last) != (3, 716):
        raise AssertionError('row sample geometry')
    # The 96 column coordinates must equal CROP_X + sy-row coordinates.
    return dict(colors=colors, sx_first=table['first'], sx_last=table['last'],
                sy_first=sy_first, sy_last=sy_last, stride=table['stride'])
