"""Recheck saved raw evidence without rerunning or rebuilding successful BINs."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
from analyze import summarize

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def run(folder,canonical=None):
    folder=Path(folder).resolve()
    original=json.loads((folder/'input_manifest.json').read_text())
    info=dict(original)
    if canonical:
        canonical=Path(canonical).resolve()
        corrected=json.loads((canonical/'manifest.json').read_text())
        assert info['kind']=='micro'
        assert corrected['sha256']['program.bin']==info['sha256']['program.bin']
        # Changes to display metadata are permitted only with identical workload.
        assert [(r['id'],r['start'],r['stop'],r['expected']) for r in corrected['cases']]==[
            (r['id'],r['start'],r['stop'],r['expected']) for r in info['cases']]
        info['cases']=corrected['cases']
    old=json.loads((folder/'summary.json').read_text())
    parent_result=folder.parent/'result.json'
    prior=json.loads(parent_result.read_text()).get(folder.name,{}) if parent_result.exists() else {}
    initial=folder/'summary_initial.json'
    if not initial.exists(): initial.write_text(json.dumps(old,indent=2)+'\n')
    result=summarize(folder,info,old['engine'])
    result['wall_seconds']=old.get('wall_seconds',prior.get('wall_seconds'))
    if info['kind']=='coremark':
        path=ROOT/'tools/uart_loader/candidates/bsp_workflow/application.py'
        spec=importlib.util.spec_from_file_location('coremark_output',path)
        app=importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
        result['crc']=app.parse_output(info['original'],(folder/'uart.txt').read_bytes())
        assert result['crc']['ticks']==result['windows'][0]['cycles']
    result['reanalysis']=dict(source_sha256=hashlib.sha256((HERE/'analyze.py').read_bytes()).hexdigest(),
        canonical_micro_manifest=str(canonical/'manifest.json') if canonical else None,
        raw_evidence_sha256={n:hashlib.sha256((folder/n).read_bytes()).hexdigest()
            for n in ['metrics.csv','latency.csv','retire_pc.csv','retire_trace.csv','timer.csv','uart.txt']})
    (folder/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    if parent_result.exists():
        parent_original=parent_result.with_name('result_initial.json')
        if not parent_original.exists(): parent_original.write_bytes(parent_result.read_bytes())
        combined=json.loads(parent_result.read_text())
        combined[folder.name]=result
        parent_result.write_text(json.dumps(combined,indent=2)+'\n')
    print(f'REANALYSIS PASS {folder}')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('folder')
    parser.add_argument('--canonical-micro-build')
    args=parser.parse_args()
    run(args.folder,args.canonical_micro_build)
