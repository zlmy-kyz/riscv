"""Audit the stopped Task021 diagnostic without running HDL or changing old evidence."""
import hashlib
import json
import re
import subprocess
from resume_inst_drm64 import HERE, ROOT, MS, VENDOR, MANIFEST, require_inputs, script

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=HERE/'build/ds_mini_idrm64_diag_20261013_021854'
receipt=HERE/'build/inst_drm64_preparation_20261013_a/task021_rpc_review.json'
assert not receipt.exists(),'Preserve completed audit'
m=require_inputs()
assert sha(MANIFEST)=='d1b0b468223a42e164c6998ac397d13a334ac362bce174b33e7ede404c63df6d'
work=out/'work'
sources=[VENDOR/'GTP_GRS.v',VENDOR/'GTP_DRM36K_E1.v',
    *[ROOT/f'ipcore/{n}/rtl/ipm2l_sdpram_v1_10_{n}.v' for n in ['icache','dcache']],
    *[ROOT/f'ipcore/{n}/{n}.v' for n in ['icache','dcache']],
    ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v',HERE/'tb_inst_drm64_x32.sv',
    HERE/'tb_inst_drm64_progress_probe.sv']
expected={'vlib':[MS/'vlib.exe',work],'compile':[MS/'vlog.exe','-sv','-work',work,*sources],
    'simulation':[MS/'vsim.exe','-c','-l',out/'transcript','-do','do diagnostic.do']}
norm=lambda x:str(x).replace('\\','/').lower()
records={}
for step,argv in expected.items():
    r=json.loads((out/f'{step}.command.json').read_text())
    assert list(map(norm,r['argv']))==list(map(norm,argv)) and norm(r['cwd'])==norm(out)
    assert r['stdout_direct_to_file']
    if step=='simulation':
        assert r['exit_code']==-1 and r['timed_out'] and r['timeout_seconds']==180
        assert 180<=r['seconds']<183 and r['native_exit_after_wait']==1
        assert r['cleanup']['exit_code']==0
        assert r['cleanup']['argv']==['taskkill.exe','/PID',str(r['pid']),'/T','/F']
    else:assert r['exit_code']==0 and not r['timed_out'] and r['timeout_seconds']==60
    records[step]=r
compile_log=(out/'compile.log').read_text()
assert 'Errors: 0, Warnings: 0' in compile_log
assert re.findall(r'-- Compiling module (\S+)',compile_log)==[
    'GTP_GRS','GTP_DRM36K_E1','ipm2l_sdpram_v1_10_icache','ipm2l_sdpram_v1_10_dcache',
    'icache','dcache','dual_sram_to_pango_ddr_bridge','tb_inst_drm64_x32','tb_inst_drm64_progress_probe']
sim=(out/'simulation.log').read_text();trans=(out/'transcript').read_text()
assert 'RPC_Init: TCL_ERROR:' in sim and '::1:49689' in sim
assert "couldn't open socket: invalid argument" in sim and 'RPC_Init: Invalid argument' in sim
assert 'RUNNER TIMEOUT' in sim
assert not re.search(r'run -all|CHECK:|RESULT:|\$finish|IPSpecCheck:',sim+'\n'+trans)
phases=(out/'phases.log').read_text()
assert re.findall(r'^(\S+) wall_ms=\d+$',phases,re.M)==['TCL_ENTERED','BEFORE_LOAD']
assert (out/'diagnostic.do').read_text()==script(work)
assert not (out/'hdl_progress.log').exists() and not (out/'git_after.json').exists()
result=json.loads((out/'result.json').read_text())
assert result['status']=='DIAGNOSTIC_STOPPED' and result['functional_status']=='INCOMPLETE'
assert result['input_manifest_sha256']==sha(MANIFEST)
assert result['diagnosis']['location']=='DESIGN_LOAD_NOT_COMPLETED'
assert result['diagnosis']['phase_markers']==['TCL_ENTERED','BEFORE_LOAD']
assert not result['pds_started'] and not result['serial_opened'] and result['isa_cases']==[]
proc=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
    '@(Get-Process -Name vsim,vsimk,vish,vlm,pds_shell -ErrorAction SilentlyContinue).Count'],
    capture_output=True,text=True,timeout=15,check=True)
report=ROOT/'DeepSeek/任务021续测_结果_ds_mini_idrm64_diag_20261013_021854.md'
files=[*out.glob('*.json'),*out.glob('*.log'),out/'transcript',out/'diagnostic.do',report]
r=dict(status='MINI_INST_DRM64_RPC_LOAD_BLOCK_REVIEW_INCOMPLETE',
    bridge_sha256=sha(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v'),
    original_inputs=179,diagnostic_inputs=194,vendor_models=2,external_tools=5,
    compile_modules=9,compile_errors=0,compile_warnings=0,
    observed_phase_markers=['TCL_ENTERED','BEFORE_LOAD'],simulation_seconds=records['simulation']['seconds'],
    simulator_exit_sentinel=-1,native_exit_after_cleanup=1,cleanup_exit=0,
    transcript_bytes=(out/'transcript').stat().st_size,simulation_log_bytes=(out/'simulation.log').stat().st_size,
    functional_status='INCOMPLETE',observed_checks=0,run_started=False,
    verified_failure='Tcl design load blocked; native log records RPC_Init IPv6 loopback socket error',
    socket_test_evidence='Report includes IPv6 forbidden/IPv4 working test summary; no separate raw socket-test artifact supplied',
    socket_policy_root_cause='Not independently established; no host policy or permission change attempted',
    original_60s_root_cause='Still undetermined; this diagnostic used a different design-load path',
    observed_current_process_count=int(proc.stdout.strip()),
    git_after_and_nine_copies='Absent by failure path; before/after equivalence not established',
    raw_evidence_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(set(files))},
    next_entry='One original CLI/single-top load + direct console/explicit transcript + 180s vsim; no Tcl vsim or probe',
    HDL_rerun=False,PDS_started=False,serial_opened=False)
receipt.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(r['status'],'current_processes='+str(r['observed_current_process_count']))
