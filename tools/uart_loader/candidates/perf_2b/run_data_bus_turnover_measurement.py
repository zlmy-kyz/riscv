"""Task032 user-operated frozen P300/V300, bound to reviewed raw evidence."""
import json
import sys
import run_write_buffer_turnover_measurement as original

sys.path.insert(0, str(original.ROOT / 'sim/data_bus_turnover'))
import run_ip_count_key_resume as simulation

original.GATE = simulation.HERE / 'build' / simulation.TAG / 'codex_review.json'
verify = original.verify


def require_gate():
    simulation.require_inputs()
    gate = json.loads(original.GATE.read_text(encoding='utf-8'))
    if gate['status'] != 'DATA_BUS_RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS':
        raise ValueError('Task032 raw functional review has not passed')
    if gate['review_kind'] != 'TASK032_KEY_WITH_REUSED_CONTROL_NO_HDL_RERUN':
        raise ValueError('Wrong Task032 review')
    if gate['manifest_sha256'] != simulation.sha(simulation.MANIFEST):
        raise ValueError('Task032 sealed inputs changed')
    if not gate['evidence_sha256']:
        raise ValueError('Task032 raw evidence is missing')
    for name, digest in gate['evidence_sha256'].items():
        if simulation.sha(original.ROOT / name) != digest:
            raise ValueError('Task032 raw evidence changed: ' + name)
    return gate


original.require_gate = require_gate


if __name__ == '__main__':
    original.main()
