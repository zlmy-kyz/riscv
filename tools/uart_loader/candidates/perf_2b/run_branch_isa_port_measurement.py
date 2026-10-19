"""Original P300/V300, final Task030 key+ISA functional gate; no PDS/bit audit."""
from pathlib import Path
import json,sys
import run_zmmul300_measurement as software
ROOT=Path(__file__).resolve().parents[4]
GATE=ROOT/'sim/cpu_branch_turnover/build/ds_cpu_branch_isa_port_resume_20261014_a/codex_review.json'
verify=software.verify
def require_gate():
    assert GATE.exists(),'Wait for Codex Task030 key+ISA closure review'
    g=json.loads(GATE.read_text());assert g['status']=='BRANCH_TURNOVER_KEY_PLUS_ISA_PORT_RESUME_RAW_EVIDENCE_REVIEW_PASS'
    for n,h in {**g['source_sha256'],**g['software_sha256'],**g['evidence_sha256']}.items():assert software.sha(ROOT/n)==h,n
    return g
def main():
    if '--plan-only' not in sys.argv and '--verify-log' not in sys.argv:require_gate()
    software.namespace['main']()
if __name__=='__main__':main()
