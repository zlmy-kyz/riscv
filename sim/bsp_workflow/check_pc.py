"""Offline transport/parser rejection checks; no serial or board evidence."""
from pathlib import Path
import copy,json,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
from application import require_manifest,parse_output,OUTPUTS
from plan import make_plan
from upload import execute
OUT=ROOT/'sim/bsp_workflow/build/pc_offline.json'
assert not OUT.exists()
def info(name):
    return require_manifest(ROOT/f'tests/bsp_workflow/build/{name}/manifest.json')

def text(i):
    return OUTPUTS[i['kind']] if i['kind']!='coremark' else (ROOT/f'tools/uart_loader/candidates/bsp_workflow/references/{i["mode"]}_{i["iterations"]}.txt').read_text().encode('ascii')
class Port:
    def __init__(self,i,mutate=None,short=False,startup=False):
        self.rows=make_plan(i);self.i=i;self.buf=bytearray(b'x' if startup else b'');self.index=0;self.writes=[];self.short=short;self.mutate=mutate
    @property
    def in_waiting(self):return len(self.buf)
    def write(self,data):
        self.writes.append(data);want=self.rows[self.index];assert data==bytes.fromhex(want['tx_hex'])
        raw=bytes.fromhex(want['expected_hex']);raw=self.mutate(raw,self.index) if self.mutate else raw
        self.buf+=raw
        if want.get('run'):self.buf+=text(self.i)
        self.index+=1
        return len(data)-(1 if self.short else 0)
    def read(self,n):
        result=bytes(self.buf[:min(n,7)]);del self.buf[:len(result)];return result
checks=[]
for name in ('hello','crc32','irq_probe','performance_1','validation_1','performance_60','validation_60'):
    i=info(name);port=Port(i);records=[];app={}
    result=execute(port,i,records,app,quiet=lambda _:None,board=False)
    assert port.index==len(port.rows) and sum(bool(r.get('run')) for r in records)==1
    checks.append(dict(name=name+'_fragmented_download_and_output',result='PASS',responses=len(records)))
    if i['kind']=='coremark':
        elapsed=30 if i['iterations']==60 else 1
        parsed=parse_output(i,text(i),board=True,elapsed=elapsed)
        assert parsed['formal_benchmark']==(i['iterations']==60)
        checks.append(dict(name=name+'_strict_board_rules_fixture',result='PASS'))
second=info('hello')
def reject(name,action):
    try:action()
    except (AssertionError,ValueError):checks.append(dict(name=name,result='PASS'));return
    raise AssertionError('did not reject '+name)
def bad_session(**kw):
    port=Port(second,**kw)
    try:execute(port,second,[],{},quiet=lambda _:None,board=False)
    finally:assert len(port.writes)<=1 and not any(len(b)==36 and b[5]==4 for b in port.writes)
reject('bad_response_crc_stops_before_LOAD',lambda:bad_session(mutate=lambda raw,n:raw[:-1]+bytes([raw[-1]^1])))
reject('short_write_stops_without_retry',lambda:bad_session(short=True))
reject('startup_RX_stops_without_flush',lambda:bad_session(startup=True))
reject('wrong_second_output',lambda:parse_output(second,OUTPUTS['hello'].replace(b'char=Q',b'char=R')))
reject('duplicate_second_output',lambda:parse_output(second,OUTPUTS['hello']+OUTPUTS['hello']))
for mode in ('performance','validation'):
    i=info(mode+'_60');raw=text(i)
    reject(mode+'_wrong_algorithm_crc',lambda:parse_output(i,raw.replace(b'[0]crclist       : 0x',b'[0]crclist       : 0xf'),board=True,elapsed=30))
    reject(mode+'_missing_final_status',lambda:parse_output(i,raw.replace(b'Correct operation validated.',b''),board=True,elapsed=30))
    reject(mode+'_timer_period_exceeded',lambda:parse_output(i,raw,board=True,elapsed=46))
    reject(mode+'_unobserved_long_benchmark',lambda:parse_output(i,raw,board=True,elapsed=.1))
    reject(mode+'_unexpected_output_line',lambda:parse_output(i,b'EXTRA\n'+raw,board=True,elapsed=30))
    reject(mode+'_duplicate_done',lambda:parse_output(i,raw+raw[raw.index(b'PORT_DONE'):],board=True,elapsed=30))
    reject(mode+'_short_output_as_formal',lambda:parse_output(i,text(info(mode+'_1')),board=True,elapsed=1))
result=dict(status='APPLICATIONS_PC_OFFLINE_PASS',evidence_origin='OFFLINE_FIXTURE_NOT_BOARD',checks=checks,count=len(checks),serial_opened=False)
OUT.write_text(json.dumps(result,indent=2)+'\n')
print('RESULT: PASS offline application checks',len(checks),'no serial; fixtures are not board evidence')
