"""RVLD fixed diagnostics and read-only DDR CRC32; no program download."""
import struct
import zlib

MAGIC = b'RVLD'
HEADER = struct.Struct('<4sBBH6I')
ACK = 0
RX_TEST = 0x10
DDR_TEST = 0x11
DDR_CRC_TEST = 0x12
DDR_BASE = 0x40000000
FIXED_DATA = bytes((0, 255, 0x55, 0xaa, 0x52, 0x56, 0x4c, 0x44,
                    10, 13, 128, 127, 254, 1, 2, 0)) + bytes((i * 37 + 11) & 255 for i in range(16, 64))


def crc32(data):
    return zlib.crc32(data) & 0xffffffff


def packet(cmd=1, seq=1, address=0, payload=b'', total=0, image_crc=0, flags=0, version=1, length=None):
    prefix = struct.pack('<4sBBH5I', MAGIC, version, cmd, flags, seq, address,
                         len(payload) if length is None else length, total, image_crc)
    return prefix + struct.pack('<I', crc32(prefix)) + payload + struct.pack('<I', crc32(payload))


def expected_response(seq, cmd=1, status=0, actual_crc=0):
    accepted = 64 if cmd in (RX_TEST, DDR_TEST, DDR_CRC_TEST) and status == ACK else 0
    data = struct.pack('<6I', status, cmd, accepted, actual_crc, 3, 256)
    return packet(0x80, seq, 0 if cmd == RX_TEST else 0x40000000, data, 61440)


def decode_response(raw, seq, request_cmd=1, expected_crc=None):
    if len(raw) != 60: raise ValueError('expected 60-byte response')
    magic, version, cmd, flags, actual_seq, address, length, maximum, image_crc, header_crc = HEADER.unpack(raw[:32])
    if (magic, version, cmd, flags, actual_seq, length) != (MAGIC, 1, 0x80, 0, seq, 24):
        raise ValueError('bad response envelope/sequence')
    if crc32(raw[:28]) != header_crc or crc32(raw[32:56]) != struct.unpack('<I', raw[56:])[0]:
        raise ValueError('bad response CRC32')
    status, request, accepted, ddr_crc, capabilities, chunk = struct.unpack('<6I', raw[32:56])
    if request != request_cmd or address != (0 if request_cmd == RX_TEST else 0x40000000) or maximum != 61440 or image_crc != 0:
        raise ValueError('unexpected response identity/limits')
    expected_accepted = 64 if request_cmd in (RX_TEST, DDR_TEST, DDR_CRC_TEST) and status == ACK else 0
    if (accepted, capabilities, chunk) != (expected_accepted, 3, 256):
        raise ValueError('unexpected diagnostic state/capabilities')
    if request_cmd != DDR_CRC_TEST and ddr_crc != 0: raise ValueError('unexpected DDR CRC')
    if request_cmd == DDR_CRC_TEST and status == ACK:
        if ddr_crc != (crc32(FIXED_DATA) if expected_crc is None else expected_crc):
            raise ValueError('ACK DDR CRC differs from PC CRC')
    return {'status': status, 'sequence': seq, 'base': address, 'maximum_bin': maximum,
            'max_chunk': chunk, 'capabilities': capabilities, 'accepted_bytes': accepted,
            'actual_ddr_crc': ddr_crc,
            'stage': 'DDR_CRC_READBACK' if request_cmd == DDR_CRC_TEST else 'DDR_FIXED_COMPARE' if request_cmd == DDR_TEST else 'RAM_RX_TEST' if request_cmd == RX_TEST else 'PING_ONLY'}
