"""Audit CLI RPC failure and loopback/startup preflights; no HDL test or host changes."""
import hashlib
import json
import re
from resume_inst_drm64_cli import HERE, ROOT, MS, VENDOR, MANIFEST, require_inputs, simulation_argv

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=HERE/'build/ds_mini_idrm64_cli_20261013_a'
prep=HERE/'build/inst_drm64_preparation_20261013_a'
receipt=prep/'task021_cli_rpc_review.json'
assert not receipt.exists(),'Preserve completed audit'
m=require_inputs()
assert sha(MANIFEST)=='b0640ab8b08f2676b1ab4f916862c757bbf27ed20e9eea44f4ef4c4031f682c8'
work=out/'work'
sources=[VENDOR/'GTP_GRS.v',VENDOR/'GTP_DRM36K_E1.v',
    *[ROOT/f'ipcore/{n}/rtl/ipm2l_sdpram_v1_10_{n}.v' for n in ['icache','dcache']],
    *[ROOT/f'ipcore/{n}/{n}.v' for n in ['icache','dcache']],
    ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v',HERE/'tb_inst_drm64_x32.sv']
expected={'vlib':[MS/'vlib.exe',work],'compile':[MS/'vlog.exe','-sv','-work',work,*sources],
          'simulation':simulation_argv(work,out)}
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
    'icache','dcache','dual_sram_to_pango_ddr_bridge','tb_inst_drm64_x32']
sim=(out/'simulation.log').read_text()
assert 'RPC_Init: TCL_ERROR:' in sim and '::1:65511' in sim
assert "couldn't open socket: invalid argument" in sim and 'RPC_Init: Invalid argument' in sim
assert 'RUNNER TIMEOUT' in sim
assert not re.search(r'run -all|CHECK:|RESULT:|\$finish|IPSpecCheck:',sim)
assert (out/'transcript').stat().st_size==0 and not (out/'git_after.json').exists()
result=json.loads((out/'result.json').read_text())
assert result['status']=='CLI_RESUME_STOPPED' and result['functional_status']=='INCOMPLETE'
assert result['input_manifest_sha256']==sha(MANIFEST)
assert result['evidence']['rpc_error_seen'] and result['evidence']['check_groups']==[]
assert not result['pds_started'] and not result['serial_opened'] and result['isa_cases']==[]
probes=[]
for name in ['loopback_default.json','loopback_outside.json']:
    r=json.loads((prep/name).read_text(encoding='utf-8'))
    assert r['results'][0]['address']=='127.0.0.1' and r['results'][0]['status']=='PASS'
    assert r['results'][1]['address']=='::1' and r['results'][1]['status']=='FAIL'
    assert r['results'][1]['stage']=='connect_loopback' and r['results'][1]['winerror']==10013
    assert not r['host_settings_changed'] and not r['ModelSim_started']
    probes.append(r)
startup=prep/'batch_startup_preflight'
start_result=json.loads((startup/'result.json').read_text())
start_cmd=json.loads((startup/'startup.command.json').read_text())
assert start_result['status']=='MODELSIM_BATCH_TOOL_STARTUP_PASS_NO_HDL'
assert start_cmd['exit_code']==0 and not start_cmd['timed_out']
assert start_cmd['argv'][1]=='-batch' and start_cmd['argv'][-1]=='puts {MODELSIM_BATCH_STARTUP_OK}; quit -f -code 0'
assert 'MODELSIM_BATCH_STARTUP_OK' in (startup/'startup.log').read_text()
assert 'RPC_Init:' not in (startup/'startup.log').read_text()
report=ROOT/'DeepSeek/任务021命令行续测_结果_ds_mini_idrm64_cli_20261013_a.md'
files=[*out.glob('*.json'),*out.glob('*.log'),out/'transcript',report,
    prep/'loopback_default.json',prep/'loopback_outside.json',
    *[p for p in startup.iterdir() if p.is_file()]]
r=dict(status='MINI_INST_DRM64_CLI_RPC_BLOCK_REVIEW_BATCH_STARTUP_ONLY_PASS',
    bridge_sha256=sha(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v'),
    protected_inputs=210,original_inputs=179,vendor_models=2,external_tools=5,
    compile_modules=8,compile_errors=0,compile_warnings=0,simulation_seconds=records['simulation']['seconds'],
    functional_status='INCOMPLETE',observed_checks=0,transcript_bytes=0,
    verified_failure='Both -c CLI loading and Tcl loading show RPC_Init IPv6 loopback failure',
    corrected_hypothesis='Failure is not specific to Tcl vsim design-load entry',
    original_60s_root_cause='RPC is plausible but unproven; original log has no RPC text',
    host_preflight='IPv4 passes; IPv6 connect fails with 10013 in default and approved outside-sandbox contexts',
    host_root_cause='Specific Windows/session/network-policy mechanism not identified; outside-sandbox alone did not help',
    batch_tool_startup='PASS in default context, exit0, no RPC, no design or run command',
    batch_functional_verdict='NOT_RUN; startup-only success does not validate I64 or design elaboration',
    git_after_and_eight_copies='Absent by failure path; before/after equivalence not established',
    raw_evidence_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(set(files))},
    HDL_rerun=False,host_settings_changed=False,PDS_started=False,serial_opened=False)
receipt.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(r['status'])
