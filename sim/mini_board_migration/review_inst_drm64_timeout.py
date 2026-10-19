"""Read-only audit of Task021 timeout; never launches ModelSim/PDS or changes old evidence."""
import hashlib
import json
import re
import subprocess
from run_inst_drm64 import HERE, ROOT, MS, VENDOR, MANIFEST, require_inputs

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=HERE/'build/ds_mini_idrm64_20261013_013143'
prep=HERE/'build/inst_drm64_preparation_20261013_a'
receipt=prep/'task021_timeout_review.json'
assert not receipt.exists(),'Preserve completed audit'
m=require_inputs()
assert sha(MANIFEST)=='9e74eb569e075bb9b64e7ebc852b2bcc2baf9d9e7f3dbc42cf6c23d08cd2d68c'
work=out/'work'
sources=[VENDOR/'GTP_GRS.v',VENDOR/'GTP_DRM36K_E1.v',
    *[ROOT/f'ipcore/{n}/rtl/ipm2l_sdpram_v1_10_{n}.v' for n in ['icache','dcache']],
    *[ROOT/f'ipcore/{n}/{n}.v' for n in ['icache','dcache']],
    ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v',HERE/'tb_inst_drm64_x32.sv']
expected={'vlib':[MS/'vlib.exe',work],'compile':[MS/'vlog.exe','-sv','-work',work,*sources],
          'simulation':[MS/'vsim.exe','-c','-lib',work,'tb_inst_drm64_x32','-do','run -all; quit -f']}
norm=lambda x:str(x).replace('\\','/').lower()
for step,argv in expected.items():
    r=json.loads((out/f'{step}.command.json').read_text())
    assert list(map(norm,r['argv']))==list(map(norm,argv)) and norm(r['cwd'])==norm(out)
    if step=='simulation':assert r['exit_code']==-1 and 60<=r['seconds']<62
    else:assert r['exit_code']==0
compile_log=(out/'compile.log').read_text()
assert 'Errors: 0, Warnings: 0' in compile_log
assert re.findall(r'-- Compiling module (\S+)',compile_log)==[
    'GTP_GRS','GTP_DRM36K_E1','ipm2l_sdpram_v1_10_icache','ipm2l_sdpram_v1_10_dcache',
    'icache','dcache','dual_sram_to_pango_ddr_bridge','tb_inst_drm64_x32']
sim=(out/'simulation.log').read_text()
assert 'RUNNER TIMEOUT' in sim and not re.search(r'Loading |run -all|CHECK:|RESULT:|\$finish|IPSpecCheck:',sim)
assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|\bERROR:|\bFATAL\b',sim)
assert (out/'transcript').stat().st_size==0
result=json.loads((out/'result.json').read_text())
assert result['status']=='FAIL' and result['input_manifest_sha256']==sha(MANIFEST)
assert not result['pds_started'] and not result['serial_opened'] and result['isa_cases']==[]
assert not (out/'git_after.json').exists()
before=json.loads((out/'git_before.json').read_text());assert before['head']=='7af48d2185bc01a62be528c70b83c42689394c31'
proc=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
    '@(Get-Process -Name vsim,vsimk,vish,vlm,pds_shell -ErrorAction SilentlyContinue).Count'],
    capture_output=True,text=True,timeout=15,check=True)
report=ROOT/'DeepSeek/任务021_结果_ds_mini_idrm64_20261013_013143.md'
files=[*out.glob('*.json'),*out.glob('*.log'),out/'transcript',report]
r=dict(status='MINI_INST_DRM64_TIMEOUT_AUDIT_INCOMPLETE_NOT_FUNCTIONAL_FAIL',
    original_manifest_sha256=sha(MANIFEST),bridge_sha256=m['candidate_bridge_sha256'],
    protected_inputs=179,vendor_models=2,compile_exit=0,compile_errors=0,compile_warnings=0,
    simulator_exit_sentinel=-1,wall_seconds=json.loads((out/'simulation.command.json').read_text())['seconds'],
    transcript_bytes=0,checks_completed='NOT_ESTABLISHED',functional_status='INCOMPLETE',
    location='No auditable load/run/finish evidence; stdout buffering prevents exact localization',
    root_cause='UNDETERMINED; startup/load, time convergence, or process/pipe exit remain hypotheses',
    observed_process_count=int(proc.stdout.strip()),process_query='Get-Process accessible; CIM query denied, no permissions changed',
    git_after_and_eight_copies='Absent by failure path; cannot claim before/after snapshot equivalence',
    raw_evidence_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(set(files))},
    new_run_policy='One diagnostic continuation; vlib/vlog 60s, vsim 180s, direct console log + phase file + read-only HDL probe',
    HDL_rerun=False,PDS_started=False,serial_opened=False)
receipt.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(r['status'],'current_processes='+str(r['observed_process_count']))
