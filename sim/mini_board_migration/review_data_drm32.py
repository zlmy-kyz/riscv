"""Task020 raw evidence audit and PDS/board handoff. No HDL/PDS/serial execution."""
import hashlib
import json
import re
from run_data_drm32 import require_inputs, ROOT, HERE, MS, VENDOR, MANIFEST

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=HERE/'build/ds_mini_ddrm32_20261012_185339'
receipt=out/'codex_review.json'
handoff=HERE/'build/data_drm32_preparation_20261012_a/pds_handoff.json'
assert not receipt.exists() and not handoff.exists(),'Preserve completed audit/handoff'
m=require_inputs()
assert sha(MANIFEST)=='c5cbd73db8c9a6b5af5cc567520450e9863ba0378b50a8e607514aa4806d1c4f'
result=json.loads((out/'result.json').read_text(encoding='utf-8'))
assert result['status']=='MINI_DATA_DRM32_KEY_TEST_PASS' and result['checks']==1521
assert result['input_manifest_sha256']==sha(MANIFEST)
assert result['inputs_unchanged'] and result['git_snapshots_identical']
assert result['isa_cases']==[] and not result['pds_started'] and not result['serial_opened']
assert result['formal_board']=='NOT_TESTED'
assert result['check_groups']==[r['group'] for r in m['unit_plan']]
assert result['ip_spec_diagnostics']==['04030130','04030130']
work=out/'work'
ip_sources=[ROOT/f'ipcore/{n}/rtl/ipm2l_sdpram_v1_10_{n}.v' for n in ['icache','dcache']]+\
           [ROOT/f'ipcore/{n}/{n}.v' for n in ['icache','dcache']]
sources=[VENDOR/'GTP_GRS.v',VENDOR/'GTP_DRM36K_E1.v',*ip_sources,
         ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v',HERE/'tb_data_drm32_x32.sv']
expected={'vlib':[MS/'vlib.exe',work],'compile':[MS/'vlog.exe','-sv','-work',work,*sources],
          'simulation':[MS/'vsim.exe','-c','-lib',work,'tb_data_drm32_x32','-do','run -all; quit -f']}
norm=lambda s:str(s).replace('\\','/').lower()
for step,argv in expected.items():
    row=json.loads((out/f'{step}.command.json').read_text(encoding='utf-8'))
    assert row['exit_code']==0 and norm(row['cwd'])==norm(out)
    assert list(map(norm,row['argv']))==list(map(norm,argv)),step
    log=(out/f'{step}.log').read_text(encoding='utf-8')
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|\bERROR:|\bFATAL\b|RUNNER TIMEOUT',log)
    if step!='vlib': assert 'Errors: 0, Warnings: 0' in log
compile_log=(out/'compile.log').read_text(encoding='utf-8')
modules=['GTP_GRS','GTP_DRM36K_E1','ipm2l_sdpram_v1_10_icache','ipm2l_sdpram_v1_10_dcache',
         'icache','dcache','dual_sram_to_pango_ddr_bridge','tb_data_drm32_x32']
assert re.findall(r'-- Compiling module (\S+)',compile_log)==modules
sim=(out/'simulation.log').read_text(encoding='utf-8')
assert re.findall(r'CHECK: (\S+) PASS',sim)==[r['group'] for r in m['unit_plan']]
assert re.findall(r'RESULT: PASS data_drm32_x32 tests=(\d+)',sim)==['1521']
assert len(re.findall('RESULT:',sim))==1
assert re.findall(r'IPSpecCheck: (\d+)',sim)==['04030130','04030130']
assert 'Time: 85570 ns' in sim and 'tb_data_drm32_x32.sv(483)' in sim
for name in modules: assert re.search(r'Loading .*work\.'+name+r'\s',sim),name
trans=(out/'transcript').read_text(encoding='utf-8')
assert sim[sim.index('# vsim '):].strip()==trans[trans.index('# vsim '):].strip()
assert (out/'git_before.json').read_bytes()==(out/'git_after.json').read_bytes()
head=json.loads((out/'git_before.json').read_text(encoding='utf-8'))['head']
assert head=='7af48d2185bc01a62be528c70b83c42689394c31'
for src in [*sources[2:],HERE/'run_data_drm32.py',MANIFEST]: assert sha(out/src.name)==sha(src),src.name
report=ROOT/'DeepSeek/任务020_结果_ds_mini_ddrm32_20261012_185339.md'
files=[*out.glob('*.json'),*out.glob('*.log'),*out.glob('*.v'),out/'transcript',
       out/'tb_data_drm32_x32.sv',out/'run_data_drm32.py',report]
audit=dict(status='MINI_DATA_DRM32_RAW_EVIDENCE_REVIEW_PASS',bridge_sha256=sha(sources[-2]),
    manifest_sha256=sha(MANIFEST),protected_inputs=181,vendor_models=2,checks=1521,check_groups=m['unit_plan'],
    commands_verified=3,copies_verified=8,git_snapshots_identical=True,head=head,finish_ns=85570,finish_line=483,
    modelsim_errors=0,modelsim_warnings=0,ip_spec_diagnostics=['04030130','04030130'],
    pds='NOT_RUN',board='UNAVAILABLE_NOT_TESTED',scope='Bridge with real I/D DRM + functional DDR user-port; no PHY/CPU program',
    raw_evidence_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(set(files))})
old=HERE/'build/inst_cache32_preparation_20261012_a/pds_review.json'
base=json.loads(old.read_text(encoding='utf-8'))
registered=dict(base['registered_input_sha256'])
registered['myriscv/dual_sram_to_pango_ddr_bridge.v']=sha(sources[-2])
for name in ['icache','dcache']:
    for path in [f'ipcore/{name}/{name}.idf',f'ipcore/{name}/{name}.v',f'ipcore/{name}/rtl/ipm2l_sdpram_v1_10_{name}.v']:
        registered[path]=sha(ROOT/path)
for path,digest in registered.items(): assert sha(ROOT/path)==digest,path
logdir=ROOT/'sim/mini_board_migration/board/coremark_idrm_d32_01'
assert not logdir.exists(),'Choose a new board directory if already used'
pending=dict(status='MINI_DATA_DRM32_READY_FOR_USER_PDS_BOARD_DEFERRED',functional_audit=str(receipt.relative_to(ROOT)).replace('\\','/'),
    design_top='board_top',device='PG2L200H',package='FBB676',speedgrade='-6',core_clk_hz=93750000,
    capacity_bytes={'I':1024,'D':1024},registered_input_count=len(registered),registered_input_sha256=registered,
    expected_project_configuration_sha256=m['project_configuration_sha256'],baseline_pds_review=str(old.relative_to(ROOT)).replace('\\','/'),
    baseline_pds_review_sha256=sha(old),baseline_bitstream_sha256=base['bitstream_sha256'],
    baseline_board_directory=m['baseline_board_directory'],baseline_physical_FF=23245,baseline_physical_LUT=13745,baseline_DRM=8,
    expected_added_DRM36K=8,expected_total_DRM=16,resource_expectation='Estimate only; user final synthesis/map/PnR required',
    successful_loader_initialization=base['loader'],
    fixed_software_sha256=base['fixed_software_sha256'],board_status='UNAVAILABLE_NOT_TESTED',
    board_log_directory=str(logdir).replace('\\','/'),PDS='USER_PENDING',
    verification=['Actual I/D DRM instances, x32 data FF arrays removed, 32 valid/27bit tags each',
        'Final seed and all multi-corner timing groups at 93.75MHz; final resource hierarchy and worst path',
        'Loader ROM/RAM synthesized INIT unchanged; source identities and new bitstream SHA',
        'Actual DDR fixed120 P/V each once after board available; no I-only intermediate test'])
receipt.write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
handoff.write_text(json.dumps(pending,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(audit['status'],'checks=1521 finish=85570ns commands=3 copies=8 registered='+str(len(registered)))
