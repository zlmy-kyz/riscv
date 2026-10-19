"""PP01 32-byte framed binary protocol, strict byte-order checks and raw evidence replay.

Frozen wire contract for this task (see README.md and the task document §7).  All
header fields are uint32 little endian::

    magic[4]='PP01'  (0..3)
    kind             (4..7)   1 source DATA, 2 source END, 3 RGB888 DATA, 4 RGB888 END
    source_seq       (8..11)  Camera source frame sequence, one per group
    offset           (12..15) byte offset inside the corresponding data stream
    payload_len      (16..19) DATA = min(1024, total_len-offset); END = 0
    total_len        (20..23) source 1843200 / RGB888 27648
    data_crc         (24..27) DATA = CRC32 of this payload; END = CRC32 of the whole stream
    header_crc       (28..31) CRC32(header[0:28])

Strictness rules implemented here and enforced by the session runner:

* no magic scanning / resynchronisation, ever -- a bad 32-byte header is fatal;
* no NACK, no retransmission, no error recovery; first failure stops everything;
* short reads and timeouts are fatal;
* exactly one ``K`` ACK per accepted packet (DATA and END);
* source and RGB888 streams must not interleave; the order is source DATA/END then
  RGB888 DATA/END, one complete pair of streams per group;
* trailing bytes after an END block, a duplicated END or a missing END are fatal;
* the only accepted final state is the application session-done line with exactly
  2 completed group pairs.
"""
import struct
import time
from pathlib import Path

import reference
from reference import crc32

MAGIC = b'PP01'
HEADER_BYTES = 32
SOURCE_TOTAL = 1843200
RGB_TOTAL = 27648
CHUNK = 1024
KIND_SOURCE_DATA, KIND_SOURCE_END, KIND_RGB_DATA, KIND_RGB_END = 1, 2, 3, 4
KIND_NAME = {1: 'source_data', 2: 'source_end', 3: 'rgb888_data', 4: 'rgb888_end'}
TOTALS = {1: SOURCE_TOTAL, 2: SOURCE_TOTAL, 3: RGB_TOTAL, 4: RGB_TOTAL}
ACK = b'K'
GROUP_PAIRS = 2

# --------------------------------------------------------- ASCII boundary lines
# Every varint-free line below is byte-exact; the runner fails on any deviation and
# records the raw bytes at their absolute RX/TX offsets.
LINE_SESSION_OPEN = 'G'
LINE_CAPTURE = 'C'
LINE_EXPORT = 'D'
LINE_FINISH = 'Q'
LINE_APP_HEADER = 'PP_APP=1 ID=50525001 HZ=93750000 TARGET=2 WIDTH=1280 HEIGHT=720 OUT=96x96'
LINE_SENSOR = 'SENSOR_ID=00005640 CONFIG=OK'
LINE_READY = 'PP_READY'
LINE_EXPORT_BEGIN = 'PPX_BEGIN'
LINE_EXPORT_DONE = 'PPX_DONE'
LINE_SESSION_DONE = 'PPX_SESSION_DONE GROUPS=2 CPU_CHECK=PASS'
SUMMARY_FMT = ('PP_GROUP={g} BUF={buf} SEQ={seq} SRC={src_buf} SRC_SEQ={src_seq} '
               'LAYOUT=1280x720x2 SRC_CRC={src_crc:08x} SRC_BYTES=1843200 '
               'BASE=42000000 BYTES=27648 SIZE=00600060 READ=9216 WRITE=864 '
               'PRODUCED=27648 CRC_PP={pp_crc:08x} CRC_CPU={cpu_crc:08x} '
               'CRC_REREAD={re_crc:08x} ERR=00000000')


def summary_line(group, buf, seq, src_buf, src_seq, src_crc, pp_crc):
    """The exact capture summary the firmware must emit for one group."""
    return SUMMARY_FMT.format(g=group, buf=buf, seq=seq, src_buf=src_buf,
                              src_seq=src_seq, src_crc=src_crc, pp_crc=pp_crc,
                              cpu_crc=pp_crc, re_crc=pp_crc)


# --------------------------------------------------------------------- failures

class ProtocolError(ValueError):
    """Fatal protocol violation; carries the byte offset of the failure."""


def need(ok, why, offset=None):
    if not ok:
        raise ProtocolError(why if offset is None else f'{why} @byte {offset}')


# ----------------------------------------------------------------- packet coding

def build_header(kind, seq, offset, length, total, data_crc):
    head = struct.pack('<4s6I', MAGIC, kind, seq, offset, length, total, data_crc)
    return head + struct.pack('<I', crc32(head))


def unpack_header(raw, position=None):
    """Parse and fully validate one 32-byte header; never resynchronises."""
    need(len(raw) == HEADER_BYTES, f'short header: {len(raw)} bytes',
         position)
    magic, kind, seq, offset, length, total, data_crc, header_crc = struct.unpack('<4s7I', raw)
    need(magic == MAGIC, f'bad magic {raw[:4]!r}', position)
    need(header_crc == crc32(raw[:28]), 'header CRC mismatch', position)
    need(kind in KIND_NAME, f'unknown kind {kind}', position)
    need(total == TOTALS[kind], f'total_len {total} invalid for kind {kind}', position)
    need(offset <= total, f'offset {offset} beyond total {total}', position)
    if kind in (KIND_SOURCE_DATA, KIND_RGB_DATA):
        want = min(CHUNK, total - offset)
        need(want > 0, f'DATA after end of stream: offset {offset}', position)
        need(length == want, f'DATA payload_len {length}, expected {want}', position)
    else:
        need(length == 0, f'END payload_len must be 0, got {length}', position)
        need(offset == total, f'END offset {offset} must equal total {total}', position)
    return dict(kind=kind, source_seq=seq, offset=offset, payload_len=length,
                total_len=total, data_crc=data_crc, header_crc=header_crc,
                kind_name=KIND_NAME[kind], header_hex=raw.hex())


# ------------------------------------------------------------------ raw streams

class RawEvidence:
    """Records the complete actual RX/TX byte streams, including invalid bytes."""

    def __init__(self, folder):
        from pathlib import Path
        folder = Path(folder)
        self.rx = (folder / 'uart.rx.bin').open('xb')
        self.tx = (folder / 'uart.tx.bin').open('xb')
        self.rx_count = 0
        self.tx_count = 0

    def read(self, port, n):
        b = port.read(n)
        self.rx.write(b)
        self.rx_count += len(b)
        return b

    def write(self, port, b):
        n = port.write(b)
        self.tx.write(b[:n])
        self.tx_count += n
        need(n == len(b), 'short UART write')
        return n

    def close(self):
        self.rx.close()
        self.tx.close()


def exact(reader, n, seconds, what):
    """Read exactly n bytes or fail; no resynchronisation, no retry.

    ``reader`` is any object exposing ``read(n)`` -- either a raw port or the raw
    evidence recorder bound to a port.
    """
    end = time.monotonic() + seconds
    buf = bytearray()
    while len(buf) < n:
        need(time.monotonic() < end, f'timeout waiting for {what} ({len(buf)}/{n} bytes)')
        part = reader.read(n - len(buf))
        if part:
            buf += part
    return bytes(buf)


class LineReader:
    """Buffered ASCII line reader over the raw evidence recorder."""

    def __init__(self, wire, port, limit=512):
        self.wire, self.port, self.buf, self.limit = wire, port, bytearray(), limit

    def line(self, seconds, what):
        end = time.monotonic() + seconds
        while b'\n' not in self.buf:
            need(time.monotonic() < end, f'timeout waiting for {what}')
            self.buf += self.wire.read(self.port, 1)
            need(len(self.buf) <= self.limit, f'{what} line exceeds {self.limit} bytes')
        raw = bytes(self.buf[:self.buf.index(b'\n') + 1])
        del self.buf[:self.buf.index(b'\n') + 1]
        text = raw.decode('ascii').rstrip('\n')
        need(not text.endswith('\r'), f'CR in {what} line')
        return text, raw

    def flush(self, port_read, seconds=.05):
        """Drain unexpected bytes so diagnostics survive, never to resynchronise."""
        end = time.monotonic() + seconds
        drained = 0
        while time.monotonic() < end:
            part = self.wire.read(self.port, 4096) if port_read else b''
            if not part:
                break
            drained += len(part)
        return drained

    @property
    def pending(self):
        """Bytes already read from the port but still buffered (line not consumed)."""
        return len(self.buf)

    def position(self):
        """Logical RX position: physically read bytes minus what is still buffered."""
        return self.wire.rx_count - len(self.buf)


# ------------------------------------------------------------------- the runner

class PacketReceiver:
    """Strictly sequential PP01 receiver for one serial session.

    Accepts a ``reader``/``writer`` pair so the exact same code runs against a
    synthetic offline stream and a real port.  Any violation calls ``need`` and
    raises :class:`ProtocolError`; no further command is ever emitted afterwards.
    """

    def __init__(self, lines, writer, ledger, timeout=.5, group_seconds=600.0):
        self.lines = lines
        self.writer = writer
        self.ledger = ledger
        self.timeout = timeout
        self.group_seconds = group_seconds
        self.groups = []

    def block(self, reader, wire, port, expected_seq, deadline):
        """Receive one complete source+RGB888 stream pair for one group."""
        need(time.monotonic() < deadline, 'group export deadline')
        row = dict(group=len(self.groups) + 1, packets=[], stream_order=[],
                   source_offsets=[], rgb_offsets=[])
        state = {'source': 'data', 'rgb': 'data'}
        running = {'source': 0, 'rgb': 0}
        offset = {'source': 0, 'rgb': 0}
        end_crc = {'source': None, 'rgb': None}
        payloads = []
        while True:
            need(time.monotonic() < deadline, 'group export deadline')
            position = wire.rx_count
            raw = exact(reader, HEADER_BYTES, self.timeout, 'PP01 header')
            head = unpack_header(raw, position)
            side = 'source' if head['kind'] in (KIND_SOURCE_DATA, KIND_SOURCE_END) else 'rgb'
            need(state[side] != 'done', f'{side} DATA after {side} END', position)
            need(head['source_seq'] == expected_seq,
                 f'group {row["group"]} source_seq {head["source_seq"]} != {expected_seq}', position)
            payload = b''
            if head['kind'] in (KIND_SOURCE_DATA, KIND_RGB_DATA):
                if side == 'rgb':
                    need(state['source'] == 'done',
                         'source and RGB888 streams interleaved: rgb DATA before source END',
                         position)
                payload = exact(reader, head['payload_len'], self.timeout,
                                f'{side} payload')
                need(head['offset'] == offset[side],
                     f'{side} offset {head["offset"]} != {offset[side]}', position)
                need(crc32(payload) == head['data_crc'], f'{side} payload CRC', position)
                running[side] = running_crc(payload, running[side])
                offset[side] += len(payload)
                if side == 'source':
                    row['source_offsets'].append(head['offset'])
                else:
                    row['rgb_offsets'].append(head['offset'])
                payloads.append(payload)
            else:
                need(running[side] == head['data_crc'], f'{side} whole-stream CRC', position)
                need(offset[side] == head['total_len'],
                     f'{side} END at {offset[side]}/{head["total_len"]}', position)
                end_crc[side] = head['data_crc']
                state[side] = 'done'
            ack_at = wire.tx_count
            self.writer.ack(wire, port)
            entry = dict(group=row['group'], kind=head['kind'], kind_name=head['kind_name'],
                         source_seq=head['source_seq'], offset=head['offset'],
                         payload_len=head['payload_len'], total_len=head['total_len'],
                         data_crc=f'{head["data_crc"]:08x}', header_hex=head['header_hex'],
                         header_crc_ok=True, rx_offset=position,
                         rx_end=position + HEADER_BYTES + head['payload_len'],
                         tx_ack_offset=ack_at, ack_byte='K')
            row['packets'].append(entry)
            self.ledger.append(entry)
            row['stream_order'].append(side)
            if state['source'] == 'done' and state['rgb'] == 'done':
                break
        # No interleaving: every source packet must precede every RGB888 packet and
        # source must be complete (its END consumed) before the first RGB888 packet.
        order = row['stream_order']
        need(order == sorted(order, key=lambda s: 0 if s == 'source' else 1),
             'source and RGB888 streams interleaved')
        row.update(source_bytes=offset['source'], rgb_bytes=offset['rgb'],
                   source_crc32=f'{end_crc["source"]:08x}', rgb_crc32=f'{end_crc["rgb"]:08x}',
                   payloads=payloads)
        self.groups.append(row)
        return row

    def session_done(self, line):
        need(line == LINE_SESSION_DONE, f'session finish line mismatch: {line!r}')
        need(len(self.groups) == GROUP_PAIRS,
             f'session ended with {len(self.groups)} complete group pairs, expected {GROUP_PAIRS}')


def running_crc(payload, running):
    """CRC32 over concatenated payloads, equivalent to one pass over all bytes."""
    import zlib
    return zlib.crc32(payload, running) & 0xffffffff


def read_summary(line, group):
    """Parse and validate one PP_GROUP summary line byte-exactly."""
    import re
    m = re.fullmatch(
        r'PP_GROUP=(\d+) BUF=([01]) SEQ=(\d+) SRC=([01]) SRC_SEQ=(\d+) '
        r'LAYOUT=1280x720x2 SRC_CRC=([0-9a-f]{8}) SRC_BYTES=(\d+) '
        r'BASE=42000000 BYTES=27648 SIZE=00600060 READ=9216 WRITE=864 '
        r'PRODUCED=27648 CRC_PP=([0-9a-f]{8}) CRC_CPU=([0-9a-f]{8}) '
        r'CRC_REREAD=([0-9a-f]{8}) ERR=00000000', line)
    need(m is not None, f'capture summary format: {line!r}')
    g, buf, seq, src_buf, src_seq, src_crc, src_bytes, pp, cpu, re_crc = m.groups()
    need(int(g) == group, f'summary group {g} != {group}')
    need(int(src_bytes) == SOURCE_TOTAL, 'summary source byte count')
    need(pp == cpu == re_crc, 'CPU / reread / PP CRC mismatch in summary')
    return dict(group=int(g), buf=int(buf), seq=int(seq), source_buf=int(src_buf),
                source_seq=int(src_seq), capture_crc=src_crc, pp_crc=pp, cpu_crc=cpu,
                reread_crc=re_crc)


# ------------------------------------------------------------------ ledger check

class Trace:
    """Read-only view over an evidence directory's raw RX/TX byte streams."""

    def __init__(self, folder):
        from pathlib import Path
        folder = Path(folder)
        self.rx = (folder / 'uart.rx.bin').read_bytes()
        self.tx = (folder / 'uart.tx.bin').read_bytes()
        self.tx_start = 0
        self.rx_start = 0


def png_selfcheck_pixels(path, expect_width, expect_height, raw, raw_height=None,
                         row_bytes=None):
    """Decode a generated PNG and require bit-identical pixels with the raw bytes.

    ``raw`` holds the reference raster row by row.  For the RGB565 source the raw
    bytes are two per pixel, so the caller passes ``raw_height`` (rows to check) and
    ``row_bytes`` (3*width) and the comparison expands each 16-bit pixel with the
    frozen bit replication; for RGB888 the raw tensor is compared directly.
    """
    data = Path(path).read_bytes()
    width, height, pixels = reference.decode_png(data)
    need((width, height) == (expect_width, expect_height), f'{Path(path).name} dimensions')
    if row_bytes is None:
        need(pixels == raw, f'{Path(path).name} decoded pixels differ from raw bytes')
        checked = len(pixels)
    else:
        rows = raw_height if raw_height is not None else height
        need(len(raw) >= 2 * width * rows, f'{Path(path).name} short RGB565 reference')
        stride = row_bytes
        want = bytearray()
        for y in range(rows):
            for x in range(width):
                o = 2 * (y * width + x)
                want += bytes(reference.expand565(raw[o] | (raw[o + 1] << 8)))
        need(pixels[:stride * rows] == bytes(want),
             f'{Path(path).name} decoded pixels differ from the bit-replicated source')
        checked = stride * rows
    return dict(path=Path(path).name, width=width, height=height,
                pixels_checked=checked, pixels_sha256=_sha(pixels))


def _sha(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()
