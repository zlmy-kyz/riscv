"""Stage10 LOAD/READY protocol; independent PC zlib framing, no RUN."""
import struct,zlib
BASE=0x40000000;LIMIT=61440;CHUNK=256
crc=lambda data:zlib.crc32(data)&0xffffffff
crc32=crc;DDR_BASE=BASE;RX_TEST=0x10;DDR_TEST=0x11;DDR_CRC_TEST=0x12
FIXED_DATA=bytes((0,255,0x55,0xaa,0x52,0x56,0x4c,0x44,10,13,128,127,254,1,2,0))+bytes((i*37+11)&255 for i in range(16,64))

def header(cmd,seq,address=0,length=0,total=0,image_crc=0,flags=0,version=1):
    prefix=struct.pack('<4sBBH5I',b'RVLD',version,cmd,flags,seq,address,length,total,image_crc)
    return prefix+struct.pack('<I',crc(prefix))

def packet(cmd,seq,address=0,data=b'',length=None,total=0,image_crc=0,flags=0,version=1):
    return header(cmd,seq,address,len(data) if length is None else length,total,image_crc,flags,version)+data+struct.pack('<I',crc(data))

def response(seq,cmd,status=0,address=BASE,accepted=0,actual_crc=0,image_crc=0,complete=False,uart_error_flags=0):
    payload=struct.pack('<6I',status,cmd,accepted,actual_crc,3|(int(complete)<<16)|(uart_error_flags<<20),256)
    return packet(0x80,seq,address,payload,total=LIMIT,image_crc=image_crc)

def decode(raw,expected):
    if len(raw)!=60:raise ValueError('expected exactly 60 response bytes')
    h=struct.unpack('<4sBBH6I',raw[:32]);p=struct.unpack('<6I',raw[32:56])
    if h[-1]!=crc(raw[:28]) or struct.unpack_from('<I',raw,56)[0]!=crc(raw[32:56]):raise ValueError('response CRC')
    if raw!=expected:raise ValueError('response READY/ACK/state/identity/CRC mismatch')
    return dict(sequence=h[4],address=h[5],image_crc=h[8],status=p[0],request_cmd=p[1],
                accepted_bytes=p[2],actual_ddr_crc=p[3],capabilities_and_state=p[4],max_chunk=p[5])

# Unchanged base simulation helper import compatibility only.
def decode_response(raw,seq,request_cmd=1,**kw):
    return decode(raw,response(seq,request_cmd))

expected_response=response
