"""Inspect existing serial-drain-repair PDS products, without running PDS or RTL."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE / 'review.json').exists(), 'Preserve review'
files = ['generate_bitstream/board_top.sbit', 'generate_bitstream/run.log',
         'generate_bitstream/board_top.bgr', 'report_timing/board_top.rtr',
         'report_timing/run.log', 'myriscv/mycpu_sync.v', 'RISCV.pds',
         'synthesize/run.log', 'place_route/run.log',
         'ipcore/inst_rom/inst_rom.idf', 'ipcore/data_ram/data_ram.idf']
hashes = {}
for rel in files:
    dst = HERE / 'observed' / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes((ROOT / rel).read_bytes())
    hashes[rel] = sha(dst)
cpu = (ROOT / 'myriscv/mycpu_sync.v').read_text(encoding='utf-8')
assert 'fetch_valid && serial_candidate && !redirect_valid' in cpu
assert 'else if (!serial_candidate)' in cpu
assert hashes['myriscv/mycpu_sync.v'] == '9eb803138292427293db785e27eeff9f15295622a95514e695f017cca505093f'
timing = (ROOT / 'report_timing/board_top.rtr').read_text()
assert 'Design Summary : All Constraints Met.' in timing
assert 'Generating Programming File done.' in (ROOT / 'generate_bitstream/run.log').read_text()
prior = json.loads((ROOT / 'sim/cpu_ex_redirect/board_review_20261018_b/review.json').read_text())
net = ROOT / 'place_route/board_top_pnr.netlist'
net_hash = sha(net)
assert net_hash != prior['pnr_netlist_sha256']
assert 'id_ex_br_taken' in net.read_text() and 'id_ex_br_target' in net.read_text()
paths = []
for m in re.finditer(r'Startpoint\s*:\s*(.*?)\nEndpoint\s*:\s*(.*?)\nPath Group\s*:\s*(.*?)\n(.*?)(?=Startpoint|\Z)', timing, re.S):
    if m[3].strip() == 'ddrphy_sysclk' and 'max (slow corner)' in m[4] and 'sequential timing path' in m[4]:
        paths.append(dict(start=m[1].strip(), end=m[2].strip(), slack_ns=float(re.search(r'Slack \(\w+\)\s+([-\d.]+)', m[4])[1])))
paths.sort(key=lambda p: p['slack_ns'])
result = dict(status='SERIAL_DRAIN_REPAIR_NEW_BITSTREAM_CONSTRAINED_TIMING_PASS_BOARD_PENDING',
    observed_sha256=hashes, bitstream_bytes=(ROOT / files[0]).stat().st_size,
    bitstream_mtime_local='2026-10-18 06:47:08', report_date='2026-10-18 06:46:22',
    cpu_commit='ce11dfefc361fc863670178a3d1ec1f32cb3a0cf',
    core_clock_mhz=93.75, slow_setup_wns_ns=0.797, tns_ns=0, estimated_fmax_mhz=101.3211,
    wns_improvement_ns=0.188, pnr_netlist_sha256=net_hash, pnr_netlist_changed=True,
    top_reported_core_paths=paths[:3],
    limits=['Source and generation chronology plus changed EX netlist support repaired implementation identity; no independent rebuild or bitstream decode.',
            'Existing task038 report observed, but full frozen-input/trace acceptance not independently reviewed in this bitstream inspection.',
            'No board evidence for repaired candidate; prior failures remain historical failures.',
            'No RTL edit, HDL run, PDS execution, programming or serial operation performed.'])
(HERE / 'review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: result[k] for k in ('status', 'slow_setup_wns_ns', 'pnr_netlist_changed', 'top_reported_core_paths')}, ensure_ascii=False))
