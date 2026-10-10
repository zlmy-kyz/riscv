"""Isolated stage9 bounded diagnostics; raw protocol checks, no RUN capability."""
import struct,zlib
MAGIC=b'RVLD';HEADER=struct.Struct('<4sBBH6I');DDR_BASE=0x40000000;LIMIT=61440;CHUNK=256
RX_TEST=0x10;DDR_TEST=0x11;DDR_CRC_TEST=0x12;WRITE=0x13;RANGE_CRC=0x14
FIXED_DATA=bytes((0,255,0x55,0xaa,0x52,0x56,0x4c,0x44,10,13,128,127,254,1,2,0))+bytes((i*37+11)&255 for i in range(16,64))
crc32=lambda data:zlib.crc32(data)&0xffffffff

def packet(cmd=1,seq=1,address=0,payload=b'',total=0,image_crc=0,flags=0,version=1,length=None):
    prefix=struct.pack('<4sBBH5I',MAGIC,version,cmd,flags,seq,address,len(payload) if length is None else length,total,image_crc)
    return prefix+struct.pack('<I',crc32(prefix))+payload+struct.pack('<I',crc32(payload))

def expected_response(seq,cmd=1,status=0,actual_crc=0,uart_error_flags=0,*,address=None,accepted=None):
    if accepted is None:accepted=64 if cmd in (RX_TEST,DDR_TEST,DDR_CRC_TEST) and not status else 0
    if address is None:address=0 if cmd==RX_TEST else DDR_BASE
    payload=struct.pack('<6I',status,cmd,accepted,actual_crc,3|(uart_error_flags<<20),CHUNK)
    return packet(0x80,seq,address,payload,LIMIT)

def response(case):
    return expected_response(case['seq'],case['cmd'],case['status'],case.get('actual_crc',0),case.get('uart_error_flags',0),
                             address=case.get('response_address'),accepted=case.get('accepted'))

def decode(raw,case):
    if len(raw)!=60:raise ValueError('response must be exactly 60 bytes')
    h=HEADER.unpack(raw[:32]);p=struct.unpack('<6I',raw[32:56])
    if crc32(raw[:28])!=h[-1] or crc32(raw[32:56])!=struct.unpack('<I',raw[56:])[0]:raise ValueError('response CRC mismatch')
    if raw!=response(case):raise ValueError(f"response identity/status/actual DDR CRC differs: {case['name']}")
    return dict(status=p[0],sequence=h[4],address=h[5],accepted_bytes=p[2],actual_ddr_crc=p[3],capabilities=p[4],max_chunk=p[5])

def decode_response(raw,seq,request_cmd=1,expected_crc=None,uart_error_flags=0):
    # Compatibility export for importing the unchanged stage7 shell helpers.
    if len(raw)!=60:raise ValueError('response length')
    status=struct.unpack_from('<I',raw,32)[0]
    actual=struct.unpack_from('<I',raw,44)[0]
    if request_cmd==DDR_CRC_TEST and status==0 and actual!=(crc32(FIXED_DATA) if expected_crc is None else expected_crc):raise ValueError('DDR CRC mismatch')
    return decode(raw,dict(name='legacy',seq=seq,cmd=request_cmd,status=status,actual_crc=actual,uart_error_flags=uart_error_flags))
