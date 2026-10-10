"""Offline transport/parser checks; never open a serial device."""
from pathlib import Path
import importlib.util,json,argparse,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sim/cpu_performance_2b'))
from run import base,sha
def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);a=p.parse_args()
    out=ROOT/'sim/cpu_performance_2b/build'/a.tag;out.mkdir(parents=True,exist_ok=False)
    path=ROOT/'tools/uart_loader/candidates/perf_2b/run_board.py'
    spec=importlib.util.spec_from_file_location('perf_board',path);board=importlib.util.module_from_spec(spec);spec.loader.exec_module(board)
    folder=ROOT/'sim/cpu_performance_2b/build/functional_coremark_20261010_c/performance_1'
    info=json.loads((folder/'input_manifest.json').read_text())['original'];raw=(folder/'uart.txt').read_bytes()
    rows=board.make_plan(info)
    class Port:
        def __init__(self,data,corrupt=False):self.i=0;self.buf=b'';self.tail=[];self.data=data;self.corrupt=corrupt;self.read_stages=0
        @property
        def in_waiting(self):return len(self.buf)
        def write(self,data):
            row=rows[self.i];assert data==bytes.fromhex(row['tx_hex']);self.i+=1
            self.buf=bytes.fromhex(row['expected_hex'])
            if self.corrupt:self.buf=bytes([self.buf[0]^1])+self.buf[1:]
            if row.get('run'):
                prefix,sep,suffix=self.data.partition(b'PERF2B version=');self.tail=[prefix,sep+suffix]
            return len(data)
        def read(self,n):
            if not self.buf and self.tail:self.buf=self.tail.pop(0);self.read_stages+=1
            result=self.buf[:n];self.buf=self.buf[n:];return result
    records=[];app={};port=Port(raw)
    board.execute(port,info,records,app,quiet=lambda _:None,board=False)
    assert len(records)==129 and app['result']=='PASS' and port.read_stages==2 and not port.tail
    assert app['parsed']['counters']['cycles']==app['parsed']['ticks']
    rejected=[]
    for name,data,corrupt in [('bad_response_crc',raw,True),('missing_counter_tail',raw.partition(b'PERF2B version=')[0]+b'PERF2B_DONE\n',False),
        ('tampered_counter',raw.replace(b'PERF2B cycles=0000000000BB41AE',b'PERF2B cycles=0000000000BB41AF'),False),
        ('extra_output',raw+b'EXTRA\n',False)]:
        # Malformed completion fixtures must terminate promptly; no 40s real wait.
        if name=='extra_output':
            try:board.output_parser(info,data,board=False)
            except (AssertionError,ValueError):rejected.append(name)
            else:raise AssertionError(name)
            continue
        if name=='tampered_counter':
            # Derive the exact current value, rather than assuming a fixture cycle count.
            import re
            m=re.search(rb'PERF2B cycles=([0-9A-Fa-f]{16})',raw);assert m
            replacement=f'{int(m[1],16)+1:016X}'.encode();data=raw[:m.start(1)]+replacement+raw[m.end(1):]
        try:board.execute(Port(data,corrupt),info,[],{},quiet=lambda _:None,board=False)
        except (AssertionError,ValueError):rejected.append(name)
        else:raise AssertionError('invalid fixture accepted: '+name)
    report=dict(status='PERF2B_OFFLINE_TRANSPORT_PASS',serial_opened=False,positive_responses=129,
        final_RUN_count=sum(bool(r.get('run')) for r in records),completed_after_counter_tail=True,rejected=rejected,
        inputs={path.relative_to(ROOT).as_posix():sha(path),(folder/'uart.txt').relative_to(ROOT).as_posix():sha(folder/'uart.txt')})
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print('RESULT: PASS',report['status'])
if __name__=='__main__':main()
