"""Offline review of the existing EX-redirect bitstream; do not alter RTL or run PDS."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'review.json').exists(), 'Preserve existing review'
obs=HERE/'observed'
obs.mkdir(exist_ok=False)
files=['generate_bitstream/board_top.sbit','generate_bitstream/run.log','generate_bitstream/board_top.bgr',
       'report_timing/board_top.rtr','report_timing/run.log','RISCV.pds',
       'myriscv/mycpu_sync.v','ipcore/inst_rom/inst_rom.idf','ipcore/data_ram/data_ram.idf']
for rel in files:
    dst=obs/rel
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes((ROOT/rel).read_bytes())
candidate=subprocess.run(['git','show','HEAD:myriscv/mycpu_sync.v'],cwd=ROOT,capture_output=True,check=True).stdout
assert b'id_ex_br_taken' in candidate and b'assign branch_redirect = ex_br_redirect;' in candidate
(obs/'candidate_cpu_from_HEAD.v.txt').write_bytes(candidate)
head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
cached=subprocess.run(['git','diff','--cached','--','myriscv/mycpu_sync.v'],cwd=ROOT,capture_output=True,check=True).stdout
(obs/'cpu_staged_difference.patch').write_bytes(cached)
timing=(obs/'report_timing/board_top.rtr').read_text(encoding='utf-8')
assert 'Design Summary : All Constraints Met.' in timing
bitlog=(obs/'generate_bitstream/run.log').read_text(encoding='utf-8')
assert 'Generating Programming File done.' in bitlog
markers={}
for rel in ('synthesize/board_top_syn.vm','place_route/board_top_pnr.netlist'):
    lines=(ROOT/rel).read_text(encoding='utf-8',errors='replace').splitlines()
    hits=[dict(line=i+1,text=s) for i,s in enumerate(lines) if 'id_ex_br_taken' in s or 'id_ex_br_target' in s]
    assert any('id_ex_br_taken' in s['text'] for s in hits) and any('id_ex_br_target' in s['text'] for s in hits)
    markers[rel]=dict(sha256=sha(ROOT/rel),markers=hits[:12])
prior=json.loads((ROOT/'sim/cpu_data_decode/preparation_20261018_a/after_manifest.json').read_text(encoding='utf-8'))
current={k:sha(ROOT/k) for k in prior}
changed=[k for k,v in prior.items() if current[k]!=v]
assert set(changed)<={'RISCV.pds','report_timing/board_top.rtr'},changed
paths=[]
for m in re.finditer(r'Startpoint\s*:\s*(.*?)\nEndpoint\s*:\s*(.*?)\nPath Group\s*:\s*(.*?)\n(.*?)(?=Startpoint|\Z)',timing,re.S):
    if m[3].strip()=='ddrphy_sysclk' and 'max (slow corner)' in m[4] and 'sequential timing path' in m[4]:
        paths.append(dict(start=m[1].strip(),end=m[2].strip(),slack_ns=float(re.search(r'Slack \(\w+\)\s+([-\d.]+)',m[4])[1])))
paths.sort(key=lambda a:a['slack_ns'])
baseline=ROOT/'sim/cpu_request_presample/board/review_20261018_01/board_review.json'
review=dict(status='EX_REDIRECT_EXISTING_BITSTREAM_TIMING_REVIEWED_READY_FOR_USER_DIRECT_APPLICATION_TRIAL',
    date='2026-10-18',candidate='ID_DECIDE_EX_REDIRECT_TARGET_FETCH_AFTER_PC_REGISTER',
    head=head,candidate_cpu_git_sha256=sha(obs/'candidate_cpu_from_HEAD.v.txt'),
    working_tree_cpu_sha256=sha(ROOT/'myriscv/mycpu_sync.v'),
    working_tree_cpu_is_candidate=False,working_tree_cpu_is_previous_ID_version=True,
    observed_sha256={p.relative_to(HERE).as_posix():sha(p) for p in obs.rglob('*') if p.is_file()},
    netlist_observations=markers,clock_hz=93750000,timing_report_date='Sun Oct 18 03:58:14 2026',
    slow_wns_ns=0.609,slow_tns_ns=0,setup_failing_endpoints=0,estimated_fmax_mhz=99.4270,
    top_reported_core_paths=paths[:3],bitstream_bytes=(obs/'generate_bitstream/board_top.sbit').stat().st_size,
    bitstream_sha256=sha(obs/'generate_bitstream/board_top.sbit'),
    bitstream_path=(obs/'generate_bitstream/board_top.sbit').relative_to(ROOT).as_posix(),
    unchanged_runtime_input_sha256={k:v for k,v in current.items() if k not in ('RISCV.pds','report_timing/board_top.rtr','myriscv/mycpu_sync.v')},
    baseline_review_path=baseline.relative_to(ROOT).as_posix(),baseline_review_sha256=sha(baseline),
    baseline_task='036',baseline_is_ID_CPU_plus_036_bridge='037 decoder is added in the EX candidate; no 037 board baseline exists',
    initialization_observation='ROM/RAM IDF point at verify_run_hello loader_rom.dat and loader_ram.dat; no independent reconstruction of programmed init bits',
    existing_isolated_logs_observed=['sim/br_ex_redirect/build/ab_cur_20261018_a/result.json',
        'sim/br_ex_redirect/build/ab_cur_20261018_a/bench/run.log','sim/br_ex_redirect/build/ab_base_20261018_b/bench/run.log'],
    functional_acceptance='FULL_NEW_CPU_SOC_ISA_INTERRUPT_RESET_NOT_REVIEWED',
    limits=['Current working-tree CPU has been reverted/staged to ID version. Existing netlists contain EX registers; source/bit identity is observational, not independently rebuilt.',
        'Do not use a tool that labels current working-tree CPU as the implemented EX candidate. No RTL restore or Git index modification performed.',
        'Existing isolated PASS logs are not a complete independently sealed ISA/SoC/IRQ/DDR/reset acceptance.',
        'Current frequency 93.75MHz unchanged; actual board cycles/time pending. Per-round reconfiguration does not validate KEY0 warm reset.',
        'This review does not start synthesis, simulation, programming or serial communication.'])
(HERE/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:review[k] for k in ('status','candidate_cpu_git_sha256','working_tree_cpu_sha256','slow_wns_ns','bitstream_sha256','bitstream_path')}))
