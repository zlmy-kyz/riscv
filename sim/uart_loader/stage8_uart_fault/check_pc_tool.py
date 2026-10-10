"""Offline PC fault-tool regressions, independent struct/zlib fixture, no serial."""
from pathlib import Path
import importlib.util,json,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[3]
TOOLS=ROOT/'tools/uart_loader/candidates/uart_fault_stage8_diag'
sys.path.insert(0,str(TOOLS))
from acceptance import exercise
from cases import board_cases,CRC

def response(c,flags=None,status=None):
    code=c['status'] if status is None else status
    accepted=64 if c['cmd'] in (0x10,0x11,0x12) and code==0 else 0
    data=struct.pack('<6I',code,c['cmd'],accepted,CRC if c.get('crc_read') else 0,3|((c.get('uart_error_flags',0) if flags is None else flags)<<20),256)
    prefix=struct.pack('<4sBBH5I',b'RVLD',1,0x80,0,c['seq'],0 if c['cmd']==0x10 else 0x40000000,24,61440,0)
    return prefix+struct.pack('<I',zlib.crc32(prefix))+data+struct.pack('<I',zlib.crc32(data))

class Fixture:
    def __init__(self,selected,mutate=None,early=False,short=False,break_error=False,extra=False):
        self.selected=selected;self.now=0;self.next=0;self.queue=[];self.writes=[]
        self.mutate=mutate;self.early=early;self.short=short;self.break_error=break_error;self.extra=extra
    def clock(self):return self.now
    def enqueue(self,c,base=None):
        delay=.010
        if c.get('uart_error_flags'):delay=.115 if not self.early else .001
        elif c.get('negative') and c['status']==0x8004:delay=.205
        elif c.get('recover'):delay=.115
        raw=response(c)
        if self.mutate:raw=self.mutate(c,raw)
        if raw is not None:self.queue.append([self.now+delay if base is None else base+delay,bytearray(raw)])
    def write(self,data):
        c=self.selected[self.next];assert data==bytes.fromhex(c['tx_hex']),c['name']
        self.writes.append(data);self.enqueue(c);self.next+=1
        if c['name']=='wire_flood_trigger_ping':self.enqueue(self.selected[self.next],base=self.now);self.next+=1
        return len(data)-1 if self.short else len(data)
    def flush(self):pass
    def read(self,size):
        if not self.queue:self.now+=.05;return b'X' if self.extra else b''
        ready,buffer=self.queue[0];self.now=max(self.now,ready)+.00001
        count=min(size,7,len(buffer));raw=bytes(buffer[:count]);del buffer[:count]
        if not buffer:self.queue.pop(0)
        return raw
    def break_fn(self,port):
        if self.break_error:raise OSError('fixture native BREAK refused')
        c=self.selected[self.next];assert c['name']=='wire_break';self.enqueue(c);self.next+=1
        return dict(api='FIXTURE_ONLY',set_success=True,clear_success=True,hold_seconds=.020)

def test(name,mode='faults',reject=False,**kw):
    selected=board_cases(mode);fixture=Fixture(selected,**kw);report=dict(mode=mode,records=[])
    caught=None
    try:exercise(fixture,selected,report,lambda:None,clock=fixture.clock,break_fn=fixture.break_fn,emit=lambda *a,**k:None)
    except Exception as e:caught=str(e)
    assert (caught is not None)==reject,(name,caught)
    if not reject:
        assert all(r['result']=='PASS' for r in report['records'])
        assert len(report['records'])==(117 if mode=='all' else 9)
        assert len(fixture.writes)==(115 if mode=='all' else 7)
        assert [r['decoded']['uart_error_flags'] for r in report['records'] if r.get('uart_error_flags')]==[16,32]
    else:assert report['status']=='FAIL' and report['records'][-1]['result']=='FAIL'
    return dict(name=name,result='PASS',expected_rejection=reject,error=caught,frames=len(report['records']),writes=len(fixture.writes))


def main():
    results=[test('9 wire responses and queued overflow NACK; 7-byte reads'),test('117 combined responses; no extra writes',mode='all'),
     test('original firmware common UART_ERROR cannot pass telemetry',reject=True,mutate=lambda c,r:response(c,flags=0) if c.get('uart_error_flags') else r),
     test('wrong frame cause rejected',reject=True,mutate=lambda c,r:response(c,flags=32) if c['name']=='wire_break' else r),
     test('wrong overflow cause rejected',reject=True,mutate=lambda c,r:response(c,flags=16) if c['name']=='wire_fifo_overflow' else r),
     test('mixed UART causes rejected',reject=True,mutate=lambda c,r:response(c,flags=48) if c.get('uart_error_flags') else r),
     test('bad response data CRC rejected',reject=True,mutate=lambda c,r:r[:-1]+bytes([r[-1]^1])),
     test('UART pseudo ACK rejected',reject=True,mutate=lambda c,r:response(c,flags=16,status=0) if c['name']=='wire_break' else r),
     test('missing overflow NACK times out',reject=True,mutate=lambda c,r:None if c['name']=='wire_fifo_overflow' else r),
     test('early fault NACK rejected',reject=True,early=True),test('short write rejected',reject=True,short=True),
     test('native BREAK refusal stops test',reject=True,break_error=True),test('unexpected extra UART data rejected',reject=True,extra=True)]
    folder=ROOT/'sim/uart_loader/build/uart_fault_stage8_diag/pc';folder.mkdir(parents=True,exist_ok=True)
    path=folder/'results.json'
    with path.open('x',encoding='utf8') as f:f.write(json.dumps(dict(status='STAGE8_DIAGNOSTIC_PC_REGRESSION_PASS',serial_opened=False,checks=results),indent=2)+'\n')
    print('RESULT: PASS',len(results),'PC offline checks; no serial opened')

if __name__=="__main__":main()
