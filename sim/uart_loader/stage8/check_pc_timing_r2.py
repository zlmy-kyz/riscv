"""Regression for fast recovery ACKs incorrectly classified as timeout NACKs."""
from pathlib import Path
import importlib.util,sys,json,struct,zlib
R=Path(__file__).resolve().parents[3];B=R/'sim/uart_loader/build/ack_nack_stage8_pc_r2'
sys.path.insert(0,str(R/'tools/uart_loader/candidates/ack_nack_stage8_r2'))
from cases import cases,CRC
from protocol import decode_response
selected=cases(uart_faults=False)
def module(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=module('old_acceptance',R/'tools/uart_loader/candidates/ack_nack_stage8/acceptance.py')
new=module('r2_acceptance',R/'tools/uart_loader/candidates/ack_nack_stage8_r2/acceptance.py')
old_validator=module('old_validator',R/'sim/uart_loader/stage8/check_board.py')
new_validator=module('r2_validator',R/'sim/uart_loader/stage8/check_board_r2.py')
def raw(c):
    accepted=64 if c['status']==0 and c['cmd'] in (0x10,0x11,0x12) else 0
    data=struct.pack('<6I',c['status'],c['cmd'],accepted,CRC if c.get('crc_read') else 0,3,256)
    head=struct.pack('<4sBBH5I',b'RVLD',1,0x80,0,c['seq'],0 if c['cmd']==0x10 else 0x40000000,24,61440,0)
    return head+struct.pack('<I',zlib.crc32(head))+data+struct.pack('<I',zlib.crc32(data))
class Clock:
    def __init__(self):self.now=0
    def __call__(self):return self.now
class Port:
    def __init__(self,clock,early=None):self.clock=clock;self.early=early;self.index=0;self.buffer=b''
    def write(self,data):
        c=selected[self.index];assert data.hex()==c['tx_hex'];self.buffer=raw(c);self.index+=1
        self.delay=.201 if c.get('negative') and c['status']==0x8004 else .101 if c.get('recover') else .001
        if c['name']==self.early:self.delay=.1
        return len(data)
    def flush(self):pass
    def read(self,n):
        self.clock.now+=self.delay;self.delay=.001
        got=self.buffer[:min(7,n)];self.buffer=self.buffer[len(got):];return got

def run(tool,early=None):
    clock=Clock();port=Port(clock,early);report={'records':[]};error=None
    try:tool.exercise(port,selected,report,lambda:None,clock=clock,emit=lambda *a,**k:None)
    except RuntimeError as e:error=str(e)
    return report,error
legacy,error=run(old)
assert legacy['failed_case']=='truncated_magic_recover_ping' and len(legacy['records'])==95 and error
fixed,error=run(new)
assert error is None and len(fixed['records'])==108 and fixed['board_result']=='PASS_HOST_INJECTABLE_ONLY'
assert all(c['seconds']<.020 for c in fixed['records'] if c['name'].startswith('truncated_') and not c.get('negative'))
tests=[dict(name='legacy bug reproduced at frame95 fast ACK',result='PASS'),dict(name='r2 complete108 with fast recovery ACK and read<=7 bytes',result='PASS')]
for name in ['truncated_magic','truncated_header','truncated_body','truncated_data_crc']:
    bad,error=run(new,early=name);assert error and bad['failed_case']==name and 'NACK before' in error
    tests.append(dict(name='early timeout NACK still rejected: '+name,result='PASS'))
# Independent validator must accept fast recovery, yet retain bounds on real timeout negatives.
fixed.update(image_sha256=new_validator.EXPECTED_IMAGE,fixture_notice='OFFLINE FIXTURE; NOT BOARD EVIDENCE')
f=B/'fast_recovery_fixture.json';f.write_text(json.dumps(fixed),encoding='utf8')
try:old_validator.verify(f)
except AssertionError:tests.append(dict(name='legacy validator timing bug reproduced',result='PASS'))
else:raise AssertionError('old verifier did not reproduce bug')
v=new_validator.verify(f);assert (v['ack_count'],v['nack_count'],v['crc_ack_count'])==(73,35,37)
tests.append(dict(name='r2 independent validator accepts fast recovery',result='PASS'))
for name in ['truncated_magic','truncated_header','truncated_body','truncated_data_crc']:
    bad=json.loads(json.dumps(fixed));next(c for c in bad['records'] if c['name']==name)['seconds']=.10
    f.write_text(json.dumps(bad),encoding='utf8')
    try:new_validator.verify(f)
    except AssertionError:tests.append(dict(name='r2 verifier rejects early timeout: '+name,result='PASS'))
    else:raise AssertionError('early timeout accepted by verifier')
f.write_text(json.dumps(fixed),encoding='utf8')
(B/'regression_results.json').write_text(json.dumps(dict(status='R2_TIMING_CLASSIFICATION_REGRESSION_PASS',board_result='NOT_TESTED',tests=tests),indent=2)+'\n',encoding='utf8')
print('RESULT: PASS',len(tests),'timing regressions; old bug reproduced; fast ACK accepted; early NACK remains rejected')
