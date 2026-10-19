"""Audit Task019 raw evidence once before DCache edits; never invokes HDL."""
from pathlib import Path
import hashlib
import json
import re
from run_inst_drm import require_inputs, ROOT, HERE, MS, VENDOR, MANIFEST

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
out = HERE / 'build/ds_mini_idrm_20261012_181906'
receipt = out / 'codex_review.json'
assert not receipt.exists(), 'Existing audit receipt must be preserved'
m = require_inputs()
result = json.loads((out / 'result.json').read_text(encoding='utf-8'))
assert result['status'] == 'MINI_INST_DRM_KEY_TEST_PASS' and result['checks'] == 1093
assert result['input_manifest_sha256'] == sha(MANIFEST)
assert result['inputs_unchanged'] and result['git_snapshots_identical']
assert result['isa_cases'] == [] and not result['pds_started'] and not result['serial_opened']
assert result['formal_board'] == 'NOT_TESTED'
work = out / 'work'
sources = [VENDOR/'GTP_GRS.v',VENDOR/'GTP_DRM36K_E1.v',
    ROOT/'ipcore/icache/rtl/ipm2l_sdpram_v1_10_icache.v',ROOT/'ipcore/icache/icache.v',
    ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v',HERE/'tb_inst_drm_x32.sv']
expected = {'vlib':[MS/'vlib.exe',work], 'compile':[MS/'vlog.exe','-sv','-work',work,*sources],
    'simulation':[MS/'vsim.exe','-c','-lib',work,'tb_inst_drm_x32','-do','run -all; quit -f']}
norm = lambda s: str(s).replace('\\','/').lower()
for step, argv in expected.items():
    row=json.loads((out/f'{step}.command.json').read_text(encoding='utf-8'))
    assert row['exit_code']==0 and norm(row['cwd'])==norm(out)
    assert list(map(norm,row['argv']))==list(map(norm,argv)),step
    log=(out/f'{step}.log').read_text(encoding='utf-8')
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|\bERROR:|RUNNER TIMEOUT',log)
    if step!='vlib': assert 'Errors: 0, Warnings: 0' in log
sim=(out/'simulation.log').read_text(encoding='utf-8')
assert re.findall(r'CHECK: (\S+) PASS',sim)==[r['group'] for r in m['unit_plan']]
assert re.findall(r'RESULT: PASS inst_drm_x32 tests=(\d+)',sim)==['1093']
assert re.findall(r'IPSpecCheck: (\d+)',sim)==['04030130']
assert 'Time: 62700 ns' in sim and 'tb_inst_drm_x32.sv(397)' in sim
assert re.search(r'Loading .*work.GTP_DRM36K_E1',sim) and re.search(r'Loading .*work.icache',sim)
trans=(out/'transcript').read_text(encoding='utf-8')
assert sim[sim.index('# vsim '):].strip()==trans[trans.index('# vsim '):].strip()
assert (out/'git_before.json').read_bytes()==(out/'git_after.json').read_bytes()
head=json.loads((out/'git_before.json').read_text())['head']
assert head=='7af48d2185bc01a62be528c70b83c42689394c31'
for src in [*sources[2:],HERE/'run_inst_drm.py',MANIFEST]:
    assert sha(out/src.name)==sha(src),src.name
report=ROOT/'DeepSeek/任务019_结果_ds_mini_idrm_20261012_181906.md'
files=[*out.glob('*.json'),*out.glob('*.log'),out/'transcript',*out.glob('*.v'),out/'tb_inst_drm_x32.sv',
       out/'run_inst_drm.py',report]
audit=dict(status='MINI_INST_DRM_RAW_EVIDENCE_REVIEW_PASS',bridge_sha256=sha(sources[-2]),
    manifest_sha256=sha(MANIFEST),protected_inputs=172,vendor_models=2,checks=1093,
    check_groups=m['unit_plan'],finish_ns=62700,finish_line=397,head=head,
    commands_verified=3,copies_verified=6,git_snapshots_identical=True,
    ip_spec_diagnostics=['04030130'],modelsim_errors=0,modelsim_warnings=0,
    pds='NOT_RUN',board='NOT_TESTED',scope='Real DRM primitive + functional DDR user-port, no PHY/CPU program',
    raw_evidence_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(set(files))})
receipt.write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(audit['status'],'checks=1093 finish=62700ns commands=3 copies=6 ISA=0')
