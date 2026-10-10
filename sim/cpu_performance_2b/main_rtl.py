"""Replay reviewed 2B tests using the actual myriscv/*.v design files.

Never runs PDS. Historical evidence remains under build/.
"""
from pathlib import Path
import argparse,inspect,json,re,sys
import run as perf

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tag',required=True)
    parser.add_argument('--suite',choices=['oracle','coremark','ddr','fast','irq','mmio','loader'],required=True)
    parser.add_argument('--application',choices=['hello','crc32','performance_1','validation_1','performance_60','validation_60'])
    args=parser.parse_args();assert re.fullmatch('[a-z0-9_-]+',args.tag)
    perf.CAND=perf.ROOT/'myriscv'
    hashes={str(p.relative_to(perf.ROOT).as_posix()):perf.sha(p) for p in
        [perf.CAND/(name+'.v') for name in ('mycpu_sync','soc_top','simple_mmio')]}
    if args.suite in ('oracle','coremark'):
        sys.argv=['run.py','--tag',args.tag,'--suite',args.suite];perf.main()
    elif args.suite=='loader':
        assert args.application
        import loader
        sys.argv=['loader.py','--tag',args.tag,'--application',args.application];loader.main()
    else:
        import regress
        # Known ISA gaps must be compared with the preserved pre-2B main RTL,
        # rather than compiling the newly promoted main files as a baseline.
        def baseline_source(name):
            old=perf.HERE/'build/frozen_inputs'/name
            return old if old.is_file() else perf.ROOT/name
        code=inspect.getsource(regress.fast).replace('[ROOT/n for n in r.SOURCES]',
            '[baseline_source(n) for n in r.SOURCES]')
        namespace=dict(regress.__dict__,baseline_source=baseline_source)
        exec(code,namespace);regress.fast=namespace['fast']
        sys.argv=['regress.py','--tag',args.tag,'--suite','physical' if args.suite=='ddr' else args.suite]
        regress.main()
    folder=perf.HERE/'build'/args.tag
    for rel,digest in hashes.items():assert perf.sha(perf.ROOT/rel)==digest
    for path in folder.rglob('run.tcl'):
        text=path.read_text()
        assert 'myriscv/candidates/perf_2b' not in text
    receipt=dict(status='MAIN_RTL_REGRESSION_PASS',suite=args.suite,
        design_source='myriscv/*.v',rtl_sha256=hashes,pds_started=False)
    with (folder/'main_rtl_receipt.json').open('x') as f:json.dump(receipt,f,indent=2)
    print('RESULT: PASS actual main RTL',args.suite,flush=True)

if __name__=='__main__':main()
