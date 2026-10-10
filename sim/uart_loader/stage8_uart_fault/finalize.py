"""Freeze approved diagnostic inputs only after both suites and offline tools PASS."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
BUILD=ROOT/'sim/uart_loader/build/uart_fault_stage8_diag'
IMAGE=ROOT/'tests/uart_loader/candidates/uart_fault_stage8_diag/build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    path=BUILD/'deployment_gate.json';archive=BUILD/'validated_sources'
    assert not path.exists() and not archive.exists(),'approved inputs already frozen'
    reports={}
    protected={};inputs={}
    image=json.loads((IMAGE/'manifest.json').read_text(encoding='utf8'))['sha256']
    for name in ['native','host']:
        p=BUILD/'v1'/name/'results.json';r=json.loads(p.read_text(encoding='utf8'))
        assert r['status']==f'STAGE8_UART_DIAGNOSTIC_{name.upper()}_SIM_PASS'
        assert r['protected_unchanged'] and r['image_unchanged'] and r['inputs_unchanged']
        assert r['image']['sha256']==image
        for key,target in [('protected_sha256',protected),('input_sha256',inputs)]:
            for file,h in r[key].items():assert sha(Path(file))==h,file;target[file]=h
        reports[name]=dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),results=r['results'],frames=r['frame_count'])
    native=json.loads((BUILD/'v1/native/results.json').read_text(encoding='utf8'))
    assert native['wire_events']['no_cpu_or_uart_force'] and native['wire_events']['frame']==1
    assert native['wire_events']['overflow']==native['wire_events']['dropped']==43
    assert native['wire_events']['clears']==2 and native['wire_events']['accepted']==369
    for file,status,count in [('pc/results.json','STAGE8_DIAGNOSTIC_PC_REGRESSION_PASS',13),('pc/board_verifier_results.json','DIAGNOSTIC_BOARD_VERIFIER_OFFLINE_PASS',11)]:
        p=BUILD/file;r=json.loads(p.read_text(encoding='utf8'));assert r['status']==status and len(r['checks'])==count and r['serial_opened'] is False
        reports[file]=dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),checks=count)
    for name,h in image.items():assert sha(IMAGE/name)==h
    source_files=list((ROOT/'tests/uart_loader/candidates/uart_fault_stage8_diag').glob('*'))+list((ROOT/'tools/uart_loader/candidates/uart_fault_stage8_diag').glob('*.py'))+list(HERE.glob('*.py'))+[HERE/'preparation.json',IMAGE/'manifest.json']
    source_files += [p for p in IMAGE.iterdir() if p.is_file()]
    source_files += list((ROOT/'myriscv').glob('*.v')) + [ROOT/'tests/uart_loader/image_to_dat.py',ROOT/'ipcore/ddr3/ddr3.idf',ROOT/'ipcore/ddr3/ddr3.v']
    for p in source_files:
        if p.is_file() and p.suffix!='.md':inputs[str(p)]=sha(p)
    # Binary images are included in the deployment contract too.
    for name in image:inputs[str(IMAGE/name)]=sha(IMAGE/name)
    archive.mkdir()
    entries=[]
    for file,h in inputs.items():
        p=Path(file);q=archive/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True)
        with q.open('xb') as stream:stream.write(p.read_bytes())
        assert sha(q)==h
        entries.append(dict(source=p.relative_to(ROOT).as_posix(),archive=q.relative_to(ROOT).as_posix(),sha256=h))
    evidence={}
    for folder in [BUILD/'v1/native',BUILD/'v1/host',BUILD/'pc']:
        for p in folder.rglob('*'):
            if p.is_file() and 'work' not in p.parts and p.suffix in ('.bin','.csv','.json','.log','.hex','.tcl'):
                evidence[p.relative_to(ROOT).as_posix()]=sha(p)
    gate=dict(evidence_sha256=evidence,date='2026-10-09',status='STAGE8_UART_DIAGNOSTIC_SIM_PASS',board_result='NOT_TESTED',
              image_sha256=image,wire_events=native['wire_events'],reports=reports,
              input_sha256={Path(k).relative_to(ROOT).as_posix():v for k,v in inputs.items()},
              protected_sha256={Path(k).relative_to(ROOT).as_posix():v for k,v in protected.items()},source_archive=entries,
              original_stage7_image_preserved=True,ip_changed=False,serial_opened_by_codex=False,load_verify_run_implemented=False,
              diagnostic_abi='RESPONSE payload capabilities bits24/25 mirror raw UART STATUS[4:5] only on NACK8005')
    with path.open('x',encoding='utf8') as stream:stream.write(json.dumps(gate,indent=2)+'\n')
    print('RESULT: PASS deployment gate; validated ELF/DAT and',len(entries),'input copies frozen; board NOT_TESTED')

if __name__=='__main__':main()
