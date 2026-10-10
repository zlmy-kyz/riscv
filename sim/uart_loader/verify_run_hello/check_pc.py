"""Offline PC behavior checks. Fixtures never establish actual board PASS."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/verify_run_hello'))
from board_cases import board_cases
from acceptance import run_cases,HELLO
selected=board_cases()


class Port:
    def __init__(self,mode='ok'):
        self.i=0;self.buf=bytearray();self.mode=mode
    @property
    def in_waiting(self):return len(self.buf)
    def write(self,tx):
        c=selected[self.i];assert tx==bytes.fromhex(c['tx_hex'])
        self.i+=1;self.buf=bytearray.fromhex(c['expected_hex'])
        if self.mode=='bad_crc' and self.i==1:self.buf[-1]^=1
        if self.mode=='wrong_SEQ' and self.i==1:self.buf[8]^=1
        if self.mode=='wrong_state' and self.i==1:self.buf[50]^=2
        if self.mode=='extra' and self.i==1:self.buf+=b'x'
        if c.get('run'):
            self.buf+=HELLO if self.mode!='wrong_Hello' else b'Hello Error\r\n'
            if self.mode=='duplicate_Hello':self.buf+=HELLO
        return len(tx)-1 if self.mode=='short_write' and self.i==1 else len(tx)
    def read(self,n):
        take=min(n,7,len(self.buf));raw=bytes(self.buf[:take]);del self.buf[:take];return raw


rows=[];p=Port();assert run_cases(p,selected,rows,quiet=lambda _:None)==len(selected)
assert p.i==len(selected) and rows[-1]['application_rx_hex']==HELLO.hex()
checks=['full_157_response_session_fragmented_read','exact_Hello','one_RUN_only',
        'expected_NACKs_accepted_no_retry','READY_before_body']
for mode in ('bad_crc','wrong_SEQ','wrong_state','extra','wrong_Hello','duplicate_Hello','short_write'):
    port=Port(mode);rows=[]
    try:run_cases(port,selected,rows,quiet=lambda _:None)
    except ValueError:
        assert rows[-1]['result']=='FAIL'
        assert port.i==len(rows), 'unexpected automatic retry'
        checks.append(mode+'_stops_and_preserves_failure')
    else:raise AssertionError(mode)
port=Port();port.buf+=b'old';rows=[]
try:run_cases(port,selected,rows,quiet=lambda _:None)
except ValueError:assert port.i==0 and not rows;checks.append('startup_RX_rejected_without_flush')
else:raise AssertionError('startup')
assert sum(bool(c.get('run')) for c in selected)==1
assert selected[-1]['cmd']==4 and selected[-1]['status']==0
assert not any(c.get('inject_offset') for c in selected)
checks.append('board_cases_do_not_claim_physical_fault_injection')
out=ROOT/'sim/uart_loader/build/verify_run_hello/pc_offline.json';assert not out.exists()
out.write_text(json.dumps(dict(status='COMBINED_PC_OFFLINE_PASS',evidence_origin='OFFLINE_FIXTURE_NOT_BOARD',
                              board_result='NOT_TESTED',checks=checks,responses=len(selected),
                              nacks=sum(bool(c['status']&0x8000) for c in selected)),indent=2)+'\n')
print('RESULT: PASS combined PC offline',len(checks),'checks;',len(selected),'responses; one RUN; not board evidence')
