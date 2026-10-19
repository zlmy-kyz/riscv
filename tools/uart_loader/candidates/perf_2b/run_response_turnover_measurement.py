"""Same P300/V300 transport; require only reviewed Task026 functional evidence."""
import json
import sys
from pathlib import Path
import run_zmmul300_measurement as software

ROOT=Path(__file__).resolve().parents[4]
GATE=ROOT/'sim/mini_board_migration/build/ds_mini_response_turnover_decl_resume_20261013_a/codex_review.json'
verify=software.verify


def require_gate():
    assert GATE.exists(),'Wait for Codex Task026 raw-evidence review'
    g=json.loads(GATE.read_text(encoding='utf-8'))
    assert g['status']=='RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS'
    for n,h in {**g['source_sha256'],**g['software_sha256'],**g['evidence_sha256']}.items():
        assert software.sha(ROOT/n)==h,n
    return g


def main():
    if '--plan-only' not in sys.argv and '--verify-log' not in sys.argv:require_gate()
    software.namespace['main']()


if __name__=='__main__':main()
