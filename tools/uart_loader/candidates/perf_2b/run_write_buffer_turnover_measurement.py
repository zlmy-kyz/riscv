"""Task031 frozen P300/V300; functional evidence gate only, no PDS/bitstream audit."""
from pathlib import Path
import inspect
import json
import sys
import run_zmmul300_measurement as software

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'sim/write_buffer_turnover'))
from check_inputs import MANIFEST, require_inputs, sha

GATE = ROOT / 'sim/write_buffer_turnover/build/ds_write_buffer_turnover_20261014_a/codex_review.json'
verify = software.verify


def require_gate():
    require_inputs()
    if not GATE.is_file():
        raise ValueError('Wait for Codex Task031 raw simulation evidence review')
    gate = json.loads(GATE.read_text(encoding='utf-8'))
    if gate['status'] != 'WRITE_BUFFER_TURNOVER_RAW_EVIDENCE_REVIEW_PASS':
        raise ValueError('Task031 functional gate has not passed')
    if gate['input_manifest_sha256'] != sha(MANIFEST):
        raise ValueError('Task031 input manifest changed')
    if not gate['evidence_sha256']:
        raise ValueError('Task031 raw simulation evidence is missing')
    for name, digest in gate['evidence_sha256'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Simulation evidence changed: ' + name)
    return gate


def main():
    if '--plan-only' not in sys.argv and '--verify-log' not in sys.argv:
        require_gate()
    # Keep frozen software parsing/transport. Do not read or hash a bitstream.
    source = inspect.getsource(software.measurement.main)
    old = 'sha(bit) if bit.is_file() else None'
    if source.count(old) != 1:
        raise ValueError('Frozen measurement entry changed')
    namespace = dict(software.namespace)
    exec(compile(source.replace(old, 'None'), '<Task031_user_measurement>', 'exec'), namespace)
    namespace['main']()


if __name__ == '__main__':
    main()
