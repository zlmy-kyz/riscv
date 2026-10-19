"""Read existing PDS products only; no implementation or board operation."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

assert not (HERE / 'review.json').exists(), 'Preserve original review'
prior = json.loads((ROOT / 'sim/cpu_ex_redirect/board_review_20261018_a/review.json').read_text(encoding='utf-8'))
files = ['generate_bitstream/board_top.sbit', 'generate_bitstream/run.log',
         'generate_bitstream/board_top.bgr', 'report_timing/board_top.rtr',
         'report_timing/run.log', 'myriscv/mycpu_sync.v', 'RISCV.pds']
hashes = {}
for rel in files:
    src = ROOT / rel
    dst = HERE / 'observed' / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    hashes[rel] = sha(dst)
timing = (HERE / 'observed/report_timing/board_top.rtr').read_text(encoding='utf-8')
assert 'Design Summary : All Constraints Met.' in timing
assert 'Generating Programming File done.' in (ROOT / 'generate_bitstream/run.log').read_text()
net = sha(ROOT / 'place_route/board_top_pnr.netlist')
assert net == prior['netlist_observations']['place_route/board_top_pnr.netlist']['sha256']
assert hashes['myriscv/mycpu_sync.v'] == prior['candidate_cpu_git_sha256']
result = dict(status='REGENERATED_EX_BITSTREAM_TIMING_REVIEWED_FUNCTIONAL_FAILURE_UNRESOLVED',
              observed_sha256=hashes,
              bitstream_bytes=(ROOT / files[0]).stat().st_size,
              bitstream_mtime_local='2026-10-18 06:15:22',
              report_date=re.search(r'\| Date\s*:\s*(.*?)\s*\n', timing)[1],
              core_clock_mhz=93.75, slow_setup_wns_ns=0.609, tns_ns=0,
              estimated_fmax_mhz=99.4270,
              pnr_netlist_sha256=net, pnr_netlist_identical_to_previous_review=True,
              previous_bitstream_sha256=prior['bitstream_sha256'],
              bitstream_changed=hashes[files[0]] != prior['bitstream_sha256'],
              limits=['Existing constrained timing passes; no simulation or board run performed.',
                      'Same EX CPU and identical PNR netlist; serial-drain defect is not fixed.',
                      'Prior P300 RUN-ACK followed by zero application RX remains unresolved.',
                      'Bitstream initialization was not independently decoded.',
                      'Prior reviewed board script pins the old bitstream; this review does not change that identity.'])
(HERE / 'review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
