"""Freeze same validated Loader DAT pair and real program.bin before user deployment."""
from pathlib import Path
import hashlib,importlib.util,json,re,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/load_stage10'))
import run
from cases import PROGRAM
from check_board import verify
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BUILD=ROOT/'sim/uart_loader/build/load_stage10'

def main():
    out=BUILD/'deployment_gate.json';assert not out.exists(), 'Do not replace a frozen gate'
    info=run.image_info()
    app=json.loads((PROGRAM.parent/'manifest.json').read_text())
    assert app['status']=='STAGE10_PROGRAM_ELF_BIN_AUDIT_PASS' and app['execute_in_stage10'] is False
    for name,h in app['sha256'].items():assert sha(ROOT/name)==h,name
    spec=importlib.util.spec_from_file_location('app_audit',PROGRAM.parent.parent/'build.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    # Re-extract/audit the already built ELF against the same BIN in a new
    # evidence directory. Never rewrite the successful application manifest.
    audit_dir=BUILD/'program_audit';assert not audit_dir.exists();audit_dir.mkdir()
    for name in ('program.elf','program.bin'):
        (audit_dir/name).write_bytes((PROGRAM.parent/name).read_bytes())
    module.OUT=audit_dir;module.audit()
    audited=json.loads((audit_dir/'manifest.json').read_text())
    for key in ('sections','bytes','crc32','bin_sha256','entry','base'):assert audited[key]==app[key],key
    original=json.loads((BUILD/'protected_before.json').read_text())
    assert all(sha(ROOT/name)==h for name,h in original.items()), 'Previous successful baseline changed'
    reports={};evidence={};extra_inputs=set()
    proof=BUILD/'input_check.json';assert json.loads(proof.read_text())['status']=='STAGE10_READ_ONLY_INPUTS_PASS'
    evidence[proof.relative_to(ROOT).as_posix()]=sha(proof)
    plan=BUILD/'board_plan.json';planned=json.loads(plan.read_text())
    assert planned['evidence_origin']=='OFFLINE_PLAN_NOT_BOARD' and planned['serial_opened'] is False
    assert planned['program_sha256']==app['bin_sha256'] and planned['planned_frames']==8
    evidence[plan.relative_to(ROOT).as_posix()]=sha(plan)
    for name,path in [
        ('positive','v1/positive'),('negative','v1/negative'),('native','v1/native'),
        ('extended','extended_v1/negative'),('window','window_v1/positive'),
        ('unverified','unverified_v1/positive'),('uart_faults','faults_v4/native')]:
        folder=BUILD/path;d=json.loads((folder/'results.json').read_text())
        assert d['status'].startswith('STAGE10_') and d['status'].endswith('_SIM_PASS')
        assert d['protected_unchanged'] and d['image_unchanged'] and d['inputs_unchanged']
        assert d['image_sha256']==info['sha256']
        assert all(sha(ROOT/p)==h for p,h in d['input_sha256'].items()), name
        extra_inputs.update(d['input_sha256'])
        cases=json.loads((folder/'cases.json').read_text())
        responses=b''.join(bytes.fromhex(c['expected_hex']) for c in cases)
        requests=b''.join(bytes.fromhex(c['tx_hex']) for c in cases)
        assert (folder/'uart_rx.bin').read_bytes()==requests and (folder/'uart_tx.bin').read_bytes()==responses
        log=(folder/'modelsim.log').read_text()
        assert len(re.findall(r'^(?:# )?RESULT: PASS load_stage10.*$',log,re.M))==1
        assert 'RESULT: FAIL' not in log and 'Errors: 0' in log
        compiled=(folder/'compile.log').read_text();assert 'Errors: 0' in compiled
        reports[name]=dict(path=(folder/'results.json').relative_to(ROOT).as_posix(),sha256=sha(folder/'results.json'),
                          status=d['status'],frames=len(cases),ready=sum(c['status']==1 for c in cases),
                          nacks=sum(bool(c['status']&0x8000) for c in cases),seconds=d['seconds'],evidence=d['evidence'])
        if name=='uart_faults':
            m=re.search(r'LOAD_WIRE_ERRORS frame=(\d+) overflow=(\d+) dropped=(\d+) clears=(\d+) accepted=(\d+)',log)
            assert m and int(m[1])==1 and int(m[2])>0 and int(m[2])==int(m[3]) and int(m[4])>=2
            reports[name]['wire_events']=dict(zip(('frame','overflow','dropped','clears','accepted'),map(int,m.groups())))
            assert d['time_scale']==1 and d['transport']=='115200_REAL_PINS'
        for p in folder.iterdir():
            if p.is_file():evidence[p.relative_to(ROOT).as_posix()]=sha(p)
    pc=BUILD/'pc/results.json';pc_info=json.loads(pc.read_text());assert pc_info['status']=='STAGE10_PC_OFFLINE_PASS'
    assert pc_info['check_count']==19
    assert verify(BUILD/'pc/fixture_OFFLINE_NOT_BOARD.json',gate_check=False,offline=True)['responses']==8
    reports['pc']=dict(path=pc.relative_to(ROOT).as_posix(),sha256=sha(pc),status=pc_info['status'],checks=19)
    for p in (BUILD/'pc').iterdir():
        if p.is_file():evidence[p.relative_to(ROOT).as_posix()]=sha(p)
    for p in audit_dir.iterdir():evidence[p.relative_to(ROOT).as_posix()]=sha(p)
    files={ROOT/p for p in extra_inputs}
    for prefix in ('tests/uart_loader/candidates/load_stage10','tests/uart_loader/program_stage10',
                   'tools/uart_loader/candidates/load_stage10','sim/uart_loader/stage10'):
        files.update(p for p in (ROOT/prefix).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='README.md')
    files.add(BUILD/'protected_before.json')
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)}
    archive=[]
    for source,h in hashes.items():
        target=BUILD/'validated_sources'/source;target.parent.mkdir(parents=True,exist_ok=True)
        assert not target.exists()
        with target.open('xb') as handle:handle.write((ROOT/source).read_bytes())
        assert sha(target)==h
        archive.append(dict(source=source,archive=target.relative_to(ROOT).as_posix(),sha256=h))
    # Current entry README files are documentation, separate from protected successful inputs.
    protected={p:h for p,h in original.items() if p not in ('tests/uart_loader/README.md','tools/uart_loader/README.md')}
    result=dict(status='STAGE10_SIM_PASS',date='2026-10-09',board_result='NOT_TESTED',reports=reports,
                image_sha256=info['sha256'],program_sha256=app['bin_sha256'],program_bytes=app['bytes'],
                program_crc32=app['crc32'],input_sha256=hashes,source_archive=archive,evidence_sha256=evidence,
                protected_sha256=protected,formal_load_implemented=True,formal_verify_implemented=False,
                run_implemented=False,program_execute=False,state_after_END='LOADED_UNVERIFIED',
                ip_changed_by_codex=False,serial_opened_by_codex=False)
    with out.open('x',encoding='utf8') as handle:json.dump(result,handle,indent=2);handle.write('\n')
    print('RESULT: PASS STAGE10_SIM_PASS;',len(hashes),'frozen inputs;',len(evidence),'evidence files; board NOT_TESTED; no RUN')

if __name__=='__main__':main()
