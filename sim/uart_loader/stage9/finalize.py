"""Freeze a stage9 diagnostic candidate only after all CPU/wire/offline suites pass."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
BUILD=ROOT/'sim/uart_loader/build/random_stage9';CANDIDATE=ROOT/'tests/uart_loader/candidates/random_stage9';IMAGE=CANDIDATE/'build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    path=BUILD/'deployment_gate.json';archive=BUILD/'validated_sources';assert not path.exists() and not archive.exists()
    identity=json.loads((IMAGE/'manifest.json').read_text())['sha256'];inputs={};protected={};reports={};evidence={}
    for suite in ('negative','legacy','bulk','native','faults'):
        p=BUILD/'v1'/suite/'results.json';r=json.loads(p.read_text())
        expected='STAGE9_UART_COMPAT_NATIVE_SIM_PASS' if suite=='faults' else f'STAGE9_{suite.upper()}_SIM_PASS'
        assert r['status']==expected and r['protected_unchanged'] and r['inputs_unchanged'] and r['image_unchanged']
        image=r['image']['sha256'] if suite=='faults' else r['image_sha256'];assert image==identity
        for group,target in [('input_sha256',inputs),('protected_sha256',protected)]:
            for name,h in r[group].items():
                source=Path(name) if Path(name).is_absolute() else ROOT/name
                assert sha(source)==h,name;target[source.relative_to(ROOT).as_posix()]=h
        if suite=='faults':
            assert r['wire_events']['no_cpu_or_uart_force'] and r['wire_events']['frame']==1
            assert r['wire_events']['overflow']==r['wire_events']['dropped']>0 and r['wire_events']['clears']>=2
        if suite=='bulk':assert r['image_checks']==114 and r['frames']==980
        if suite=='native':assert r['image_checks']==10 and r['frames']==41 and r['time_scale']==1
        reports[suite]=dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),status=r['status'])
        for file in p.parent.rglob('*'):
            if file.is_file() and 'work' not in file.parts and file.suffix in ('.json','.bin','.hex','.log','.csv','.tcl'):
                evidence[file.relative_to(ROOT).as_posix()]=sha(file)
    p=BUILD/'write_fault_v1/negative/results.json';r=json.loads(p.read_text())
    assert r['status']=='STAGE9_NEGATIVE_SIM_PASS' and r['frames']==7 and r['negative_cases']==3
    assert r['protected_unchanged'] and r['inputs_unchanged'] and r['image_unchanged'] and r['image_sha256']==identity
    for group,target in [('input_sha256',inputs),('protected_sha256',protected)]:
        for name,h in r[group].items():assert sha(ROOT/name)==h;target[name]=h
    reports['write_fault']=dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),status=r['status'])
    for file in p.parent.iterdir():
        if file.is_file() and file.suffix in ('.json','.bin','.hex','.log','.csv','.tcl'):evidence[file.relative_to(ROOT).as_posix()]=sha(file)
    pc=BUILD/'pc/results.json';r=json.loads(pc.read_text());assert r['status']=='STAGE9_PC_OFFLINE_PASS' and len(r['checks'])==17 and r['serial_opened'] is False
    reports['pc']=dict(path=pc.relative_to(ROOT).as_posix(),sha256=sha(pc),checks=17)
    evidence[pc.relative_to(ROOT).as_posix()]=sha(pc)
    files=[p for p in CANDIDATE.iterdir() if p.is_file() and p.suffix!='.md']
    files += [p for p in IMAGE.iterdir() if p.is_file()]
    files += list((ROOT/'tools/uart_loader/candidates/random_stage9').glob('*.py'))+list(HERE.glob('*.py'))
    files += [HERE/'tb/tb_write_fault.v']
    files += [ROOT/'sim/uart_loader/run.py',ROOT/'ipcore/ddr3/ddr3.idf',ROOT/'ipcore/ddr3/ddr3.v']
    for directory in (BUILD/'corpus/sim',BUILD/'corpus/board'):
        files += [p for p in directory.iterdir() if p.is_file()]
    for p in files:inputs[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==h for n,h in inputs.items())
    for n,h in identity.items():assert sha(IMAGE/n)==h
    archive.mkdir();entries=[]
    for name,h in sorted(inputs.items()):
        source=ROOT/name;target=archive/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write(source.read_bytes())
        assert sha(target)==h;entries.append(dict(source=name,archive=target.relative_to(ROOT).as_posix(),sha256=h))
    corpus=json.loads((BUILD/'corpus/board/manifest.json').read_text())
    gate=dict(status='STAGE9_SIM_PASS',date='2026-10-09',board_result='NOT_TESTED',image_sha256=identity,reports=reports,
              input_sha256=inputs,evidence_sha256=evidence,protected_sha256=protected,source_archive=entries,
              corpus_images=corpus['image_count'],corpus_payload_bytes=corpus['payload_bytes'],seed=corpus['seed'],
              random_execute=False,formal_load_verify_run_implemented=False,ip_changed_by_codex=False,serial_opened_by_codex=False,
              fast_suite_transport='modeled bytes at real MMIO/FIFO; real CPU/interconnect/DDR; not wire speed evidence',
              native_suite_transport='original 93.75MHz 115200 RX/TX pins, TIME_SCALE1; no UART force',
              diagnostic_window=[0x40000000,0x4000f000],application_stack_window=[0x4000f000,0x40010000])
    with path.open('x',encoding='utf8') as stream:stream.write(json.dumps(gate,indent=2)+'\n')
    print('RESULT: PASS stage9 deployment gate;',len(entries),'inputs frozen; board NOT_TESTED; no RUN')

if __name__=='__main__':main()
