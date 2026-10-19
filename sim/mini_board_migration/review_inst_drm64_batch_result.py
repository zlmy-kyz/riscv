"""Audit completed Task021 batch result once; no HDL/PDS/serial execution."""
import hashlib
import json
import re
from resume_inst_drm64_batch import HERE, ROOT, MS, VENDOR, MANIFEST, require_inputs, simulation_argv

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=HERE/'build/ds_mini_idrm64_batch_20261013_a'
receipt=out/'codex_review.json'
assert not receipt.exists(),'Preserve completed review'
m=require_inputs()
assert sha(MANIFEST)=='98cee935fd5f77a3d905dc14af930bf296738264e52088019e3ae63991d7b1ec'
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
    assert r['exit_code']==r['native_exit_after_wait']==0 and not r['timed_out']
    assert r['stdout_direct_to_file'] and r['cleanup'] is None
    assert r['timeout_seconds']==(180 if step=='simulation' else 60)
    assert 0<=r['seconds']<r['timeout_seconds']
    records[step]=r
compile_log=(out/'compile.log').read_text()
assert 'Errors: 0, Warnings: 0' in compile_log
assert re.findall(r'-- Compiling module (\S+)',compile_log)==[
    'GTP_GRS','GTP_DRM36K_E1','ipm2l_sdpram_v1_10_icache','ipm2l_sdpram_v1_10_dcache',
    'icache','dcache','dual_sram_to_pango_ddr_bridge','tb_inst_drm64_x32']
assert 'Top level modules:\n\ttb_inst_drm64_x32\n' in compile_log
sim=(out/'simulation.log').read_text();trans=(out/'transcript').read_text()
assert sim==trans and trans,'Console/transcript differ after newline normalization'
assert not re.search(r'RPC_Init:|RESULT: FAIL|\*\* (?:Error|Fatal)|\bERROR:|\bFATAL\b|RUNNER TIMEOUT',sim)
assert re.findall(r'RESULT: PASS inst_drm64_x32 tests=(\d+)',sim)==['2449']
assert len(re.findall(r'RESULT:',sim))==1
groups=re.findall(r'CHECK: (\S+) PASS',sim)
assert groups==[x['group'] for x in m['unit_plan']]
assert sum(x['checks'] for x in m['unit_plan'])==2449
assert re.findall(r'IPSpecCheck: (\d+)',sim)==['04030130','04030130']
assert re.findall(r'Errors: (\d+), Warnings: (\d+)',sim)==[('0','0')]
assert re.search(r'^# run -all\s*$',sim,re.M)
assert re.search(r'\$finish\s*:.*tb_inst_drm64_x32\.sv\(483\)',sim)
assert re.search(r'Time: 133570 ns\s+Iteration: 1\s+Instance: /tb_inst_drm64_x32',sim)
loading=re.findall(r'^# Loading (\S+)',sim,re.M)
assert len(loading)==9 and loading[0]=='sv_std.std'
assert [x.rsplit('.',1)[-1] for x in loading[1:]]==[
    'tb_inst_drm64_x32','GTP_GRS','dual_sram_to_pango_ddr_bridge','icache',
    'ipm2l_sdpram_v1_10_icache','dcache','ipm2l_sdpram_v1_10_dcache','GTP_DRM36K_E1']
before=json.loads((out/'git_before.json').read_text());after=json.loads((out/'git_after.json').read_text())
assert before==after and sha(out/'git_before.json')==sha(out/'git_after.json')
assert before['head']=='7af48d2185bc01a62be528c70b83c42689394c31'
copy_hash={}
for src in [*sources[2:],HERE/'resume_inst_drm64_batch.py',MANIFEST]:
    copy=out/src.name
    assert sha(src)==sha(copy),src
    copy_hash[src.name]=sha(copy)
assert len(copy_hash)==8
result=json.loads((out/'result.json').read_text())
assert result['status']=='MINI_INST_DRM64_BATCH_RESUME_KEY_TEST_PASS' and result['functional_status']=='PASS'
assert result['input_manifest_sha256']==sha(MANIFEST) and result['checks']==2449
assert result['check_groups']==groups and result['inputs_unchanged'] and result['git_snapshots_identical']
assert result['ip_spec_diagnostics']==['04030130','04030130'] and result['isa_cases']==[]
assert not result['pds_started'] and not result['serial_opened'] and not result['host_settings_changed']
assert result['formal_board']=='NOT_TESTED'
report=ROOT/'DeepSeek/任务021批处理续测_结果_ds_mini_idrm64_batch_20261013_a.md'
files=[*out.glob('*.json'),*out.glob('*.log'),out/'transcript',report,
    *[out/p for p in copy_hash]]
r=dict(status='MINI_INST_DRM64_RAW_EVIDENCE_REVIEW_PASS',
    bridge_sha256=sha(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v'),
    manifest_sha256=sha(MANIFEST),protected_inputs=233,original_inputs=179,vendor_models=2,
    external_tools=5,external_references=2,checks=2449,unit_plan=m['unit_plan'],
    compile_modules=8,loading_lines=9,loading_scope='8 work modules plus sv_std.std',
    command_exit_codes=[records[s]['exit_code'] for s in ['vlib','compile','simulation']],
    command_seconds={s:records[s]['seconds'] for s in records},
    modelsim_errors=0,modelsim_warnings=0,ip_spec_diagnostics=['04030130','04030130'],
    finish_time_ns=133570,finish_source_line=483,mode='-batch',RPC_Init_count=0,
    console_bytes=(out/'simulation.log').stat().st_size,transcript_bytes=(out/'transcript').stat().st_size,
    console_transcript_equal_after_newline_normalization=True,raw_console_transcript_byte_equal=False,
    copies_sha256=copy_hash,git_snapshots_identical=True,current_protected_inputs_match=True,
    raw_evidence_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(set(files))},
    scope='Bridge x32 I64/D32 real I/D DRM + functional DDR user-port model; no CPU/PHY/board/PDS coverage',
    host_network_fixed=False,original_60s_failure_cause='Not proven by this pass',
    new_I64_PDS='NOT_TESTED',new_I64_board='NOT_TESTED',isa_cases=[],
    review_reran_HDL=False,review_started_PDS=False,review_opened_serial=False)
receipt.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(r['status'],'checks=2449 finish=133570ns copies=8')
