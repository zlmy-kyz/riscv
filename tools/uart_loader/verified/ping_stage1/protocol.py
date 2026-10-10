"""Stage-1 RVLD binary PING codec. LOAD/VERIFY/RUN are not implemented."""
import struct
import zlib

MAGIC = b'RVLD'
HEADER = struct.Struct('<4sBBH6I')
ACK = 0


def crc32(data):
    return zlib.crc32(data) & 0xffffffff


def packet(cmd=1, seq=1, address=0, payload=b'', total=0, image_crc=0, flags=0, version=1):
    prefix = struct.pack('<4sBBH5I', MAGIC, version, cmd, flags, seq, address,
                         len(payload), total, image_crc)
    return prefix + struct.pack('<I', crc32(prefix)) + payload + struct.pack('<I', crc32(payload))


def expected_response(seq, cmd=1, status=0):
    data = struct.pack('<6I', status, cmd, 0, 0, 3, 256)
    return packet(0x80, seq, 0x40000000, data, 61440)


def decode_response(raw, seq):
    if len(raw) != 60: raise ValueError('expected 60-byte PING response')
    magic, version, cmd, flags, actual_seq, address, length, maximum, image_crc, header_crc = HEADER.unpack(raw[:32])
    if (magic, version, cmd, flags, actual_seq, length) != (MAGIC, 1, 0x80, 0, seq, 24):
        raise ValueError('bad response envelope/sequence')
    if crc32(raw[:28]) != header_crc or crc32(raw[32:56]) != struct.unpack('<I', raw[56:])[0]:
        raise ValueError('bad response CRC32')
    status, request, accepted, ddr_crc, capabilities, chunk = struct.unpack('<6I', raw[32:56])
    if request != 1 or address != 0x40000000 or maximum != 61440 or image_crc != 0:
        raise ValueError('unexpected PING identity/limits')
    if (accepted, ddr_crc, capabilities, chunk) != (0, 0, 3, 256):
        raise ValueError('unexpected PING-only state/capabilities')
    return {'status': status, 'sequence': seq, 'base': address, 'maximum_bin': maximum,
            'max_chunk': chunk, 'capabilities': capabilities, 'stage': 'PING_ONLY'}
