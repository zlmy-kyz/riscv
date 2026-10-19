"""Same frozen Zmmul300 transport; require reviewed functional evidence."""
import sys
from pathlib import Path
import json
import run_zmmul300_measurement as software

ROOT=Path(__file__).resolve().parents[4]
GATE=ROOT/'sim/mini_board_migration/build/ds_mini_data_write_hit_20261013_a/codex_review.json'
PREPARATION=ROOT/'sim/mini_board_migration/build/data_write_hit_preparation_20261013_a/pds_handoff.json'
verify=software.verify


def require_gate():
    assert GATE.exists(),'Wait for Codex Task025 raw-evidence review'
    gate=json.loads(GATE.read_text(encoding='utf-8'))
    assert gate['status']=='DATA_WRITE_HIT_RAW_EVIDENCE_REVIEW_PASS'
    preparation=json.loads(PREPARATION.read_text(encoding='utf-8'))
    assert software.sha(GATE)==preparation['functional_review_sha256']
    for n,h in {**preparation['source_sha256'],**gate['evidence_sha256']}.items():
        assert software.sha(ROOT/n)==h,n
    return gate


def main():
    if '--plan-only' not in sys.argv and '--verify-log' not in sys.argv:require_gate()
    software.namespace['main']()


if __name__=='__main__':main()
