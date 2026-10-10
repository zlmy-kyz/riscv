"""Existing Full LOAD/VERIFY/RUN application TB, candidate RTL, isolated logs."""
from pathlib import Path
import argparse,inspect,re,sys
from run import ROOT,HERE,base,source,protect
from check_output import check
def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--application',choices=['performance_1','validation_1','performance_60','validation_60','hello','crc32'],required=True)
    p.add_argument('--software-build',default='tests/cpu_performance_2b/build/measure_20261010_c');p.add_argument('--native',action='store_true');a=p.parse_args();assert re.fullmatch('[a-z0-9_-]+',a.tag)
    folder=HERE/'build'/a.tag;folder.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
    m=base.module(ROOT/'sim/bsp_workflow/run.py','bsp_full_load')
    m.old.SOURCES=[source(p) for p in m.old.SOURCES]
    def manifest(name):
        return ROOT/('tests/bsp_workflow/build' if name in ('hello','crc32') else a.software_build)/name/'manifest.json'
    def parser(info,data):
        if info['kind']!='coremark':return m.parse_output(info,data)
        result=check(info,data)
        return dict(result,**result['crc'])
    code=inspect.getsource(m.main)
    code,n=re.subn(r"    folder=ROOT/f[^\n]+",'    folder=candidate_folder/"application"',code,count=1)
    assert n==1
    ns=dict(m.__dict__,manifest=manifest,protected=protect,parse_output=parser,candidate_folder=folder);exec(code,ns)
    sys.argv=['run.py','--application',a.application,'--tag',a.tag]+(['--native'] if a.native else [])
    ns['main']()
if __name__=='__main__':main()
