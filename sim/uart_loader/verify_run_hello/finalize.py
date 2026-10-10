"""Freeze one combined simulation release; no board result inferred here."""
from pathlib import Path
import hashlib,json,shutil,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'sim/uart_loader/build/verify_run_hello'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
gate_file=OUT/'deployment_gate.json';assert not gate_file.exists()
reports={};inputs={};evidence={}
for name,rel in [('positive','v3/positive'),('negative','v3/negative'),('native','v3/native'),
                 ('UART_verified_invalidation','uart_event_v2/negative'),('control_timeout_CRC','control_v1/negative')]:
    folder=OUT/rel;report=json.loads((folder/'results.json').read_text())
    assert report['status'].startswith('COMBINED_') and report['status'].endswith('_SIM_PASS'),rel
    assert report['protected_unchanged'] and report['image_unchanged'] and report['inputs_unchanged']
    for p,h in report['input_sha256'].items():assert sha(ROOT/p)==h,p
    inputs.update(report['input_sha256'])
    reports[name]=dict(path=(folder/'results.json').relative_to(ROOT).as_posix(),sha256=sha(folder/'results.json'),
                       frames=report['frames'],status=report['status'],evidence=report['evidence'],seconds=report['seconds'])
    for p in folder.rglob('*'):
        if p.is_file() and 'work' not in p.parts and p.suffix not in ('.wlf',):evidence[p.relative_to(ROOT).as_posix()]=sha(p)
pc=json.loads((OUT/'pc_offline.json').read_text());assert pc['status']=='COMBINED_PC_OFFLINE_PASS'
evidence[(OUT/'pc_offline.json').relative_to(ROOT).as_posix()]=sha(OUT/'pc_offline.json')
for base in (ROOT/'tests/uart_loader/candidates/verify_run_hello',ROOT/'tests/uart_loader/program_hello',
             ROOT/'tools/uart_loader/candidates/verify_run_hello',HERE):
    for p in base.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.md':inputs[p.relative_to(ROOT).as_posix()]=sha(p)
old=json.loads((ROOT/'sim/uart_loader/build/load_stage10/deployment_gate.json').read_text())
for key in ('input_sha256','evidence_sha256'):
    for p,h in old[key].items():assert sha(ROOT/p)==h,p
old_receipt=json.loads((ROOT/'sim/uart_loader/board/load_stage10_submission_result.json').read_text())
for item in old_receipt['workspace_snapshot']:assert sha(ROOT/item['source'])==sha(ROOT/item['archive'])==item['sha256']
image=json.loads((ROOT/'tests/uart_loader/candidates/verify_run_hello/build/manifest.json').read_text())
app=json.loads((ROOT/'tests/uart_loader/program_hello/build/manifest.json').read_text())
archive=[]
for rel,h in sorted(inputs.items()):
    target=OUT/'validated_sources'/rel;assert not target.exists(),target
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,target)
    assert sha(target)==h
    archive.append(dict(source=rel,archive=target.relative_to(ROOT).as_posix(),sha256=h))
gate=dict(status='COMBINED_SIM_PASS',date='2026-10-09',board_result='NOT_TESTED',reports=reports,
          input_sha256=inputs,evidence_sha256=evidence,source_archive=archive,
          image_sha256=image['sha256'],program_sha256=app['bin_sha256'],program_crc32=app['crc32'],program_bytes=app['bytes'],
          formal_verify_implemented=True,run_implemented=True,simulation_program_execute=True,
          hello_expected_hex=b'Hello World\r\n'.hex(),physical_UART_fault_in_this_stage=False,
          actual_UART_timing_suite='native',software_builds=dict(loader=1,application=1),
          stage10_inputs_and_evidence_unchanged=True,stage10_deployed_workspace_unchanged=True,
          codex_opened_serial=False,board_programming_completed=False)
with gate_file.open('x',encoding='utf-8') as f:json.dump(gate,f,indent=2);f.write('\n')
print('RESULT: PASS COMBINED_SIM_PASS frozen',len(inputs),'inputs,',len(evidence),'evidence; board NOT_TESTED')
