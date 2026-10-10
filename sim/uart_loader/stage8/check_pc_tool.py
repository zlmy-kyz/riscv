"""Offline checks of stage8 host acceptance, not board/firmware evidence."""
from pathlib import Path
import importlib.util, json, struct, sys, zlib
ROOT=Path(__file__).resolve().parents[3]
TOOLS=ROOT/'tools/uart_loader/candidates/ack_nack_stage8'
sys.path.insert(0,str(TOOLS))
import acceptance
from cases import cases, CRC
selected=cases(uart_faults=False)
# Independent struct/zlib encoding of the response fixture.
def fixture(c):
    accepted=64 if c['status']==0 and c['cmd'] in (0x10,0x11,0x12) else 0
    data=struct.pack('<6I',c['status'],c['cmd'],accepted,CRC if c.get('crc_read') else 0,3,256)
    head=struct.pack('<4sBBH5I',b'RVLD',1,0x80,0,c['seq'],0 if c['cmd']==0x10 else 0x40000000,24,61440,0)
    return head+struct.pack('<I',zlib.crc32(head))+data+struct.pack('<I',zlib.crc32(data))
class Clock:
    def __init__(self): self.value=0
    def __call__(self): return self.value
class Port:
    def __init__(self,clock,mutate=None,short=False,missing=False,extra=False):
        self.clock=clock;self.index=0;self.buf=b'';self.mutate=mutate;self.short=short;self.missing=missing;self.extra=extra;self.writes=[]
    def write(self,data):
        c=selected[self.index];assert data.hex()==c['tx_hex'];self.writes.append(data)
        self.buf=fixture(c)
        if self.mutate: self.buf=self.mutate(self.buf)
        if self.missing: self.buf=self.buf[:19]
        self.pending_delay=.201 if c['name'].startswith('truncated_') else .101 if c.get('recover') else .001
        self.index+=1
        return len(data)-int(self.short)
    def flush(self): pass
    def read(self,n):
        self.clock.value+=self.pending_delay;self.pending_delay=.005
        if self.buf:
            got=self.buf[:min(n,7)];self.buf=self.buf[len(got):];return got
        if self.extra: self.extra=False;return b'\x52'
        return b''
def test(label,**kw):
    clock=Clock();port=Port(clock,**kw);report={'records':[]};saved=[]
    failure=None
    try: acceptance.exercise(port,selected,report,lambda:saved.append(json.loads(json.dumps(report))),clock=clock,emit=lambda *a,**k:None)
    except (RuntimeError,ValueError) as e: failure=str(e)
    if kw:
        assert failure and report['status']=='FAIL' and report['records'][-1]['result']=='FAIL'
        assert len(port.writes)==1,'failure must stop without retry'
        assert saved[-1]['records'][-1]['tx_hex'] and 'rx_hex' in saved[-1]['records'][-1]
    else:
        assert not failure and len(report['records'])==108 and report['board_result']=='PASS_HOST_INJECTABLE_ONLY'
        assert report['stage8_full_board_result']=='NOT_COMPLETE'
    return dict(name=label,result='PASS',injected_failure=failure,frames_sent=len(port.writes))
def wrong_status(raw):
    raw=bytearray(raw);struct.pack_into('<I',raw,32,0x8007);struct.pack_into('<I',raw,40,0);struct.pack_into('<I',raw,56,zlib.crc32(raw[32:56]));return bytes(raw)
def wrong_seq(raw):
    raw=bytearray(raw);struct.pack_into('<I',raw,8,99);struct.pack_into('<I',raw,28,zlib.crc32(raw[:28]));return bytes(raw)
results=[test('108 frames; reads at most 7 bytes'),test('bad packet CRC',mutate=lambda raw:raw[:-1]+bytes([raw[-1]^1])),
    test('valid CRC wrong status',mutate=wrong_status),test('valid CRC wrong seq',mutate=wrong_seq),
    test('short write',short=True),test('truncated response timeout',missing=True),test('unsolicited extra byte',extra=True)]
# A CRC-valid ACK with forged DDR CRC is rejected independently.
from protocol import decode_response
raw=bytearray(fixture(selected[1]));struct.pack_into('<I',raw,44,CRC^1);struct.pack_into('<I',raw,56,zlib.crc32(raw[32:56]))
try: decode_response(bytes(raw),2,0x12)
except ValueError: results.append(dict(name='valid packet CRC forged DDR CRC ACK',result='PASS'))
else: raise AssertionError('forged DDR CRC accepted')
out=ROOT/'sim/uart_loader/build/ack_nack_stage8/pc_tool_results.json'
out.write_text(json.dumps(dict(status='STAGE8_PC_TOOL_OFFLINE_PASS',board_result='NOT_TESTED',tests=results),indent=2)+'\n',encoding='utf8')
print('RESULT: PASS',len(results),'offline PC-tool checks; firmware and board not simulated by fixtures')

