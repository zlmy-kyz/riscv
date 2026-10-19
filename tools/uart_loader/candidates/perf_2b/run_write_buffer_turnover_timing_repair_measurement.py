"""Task031 timing repair: frozen P300/V300 with the new raw functional gate."""
import json
import run_write_buffer_turnover_measurement as original
import simulation_timing_repair as timing

original.GATE = original.ROOT / ('sim/write_buffer_turnover/build/' + timing.TAG + '/codex_review.json')
verify = original.verify


def require_gate():
    timing.require_inputs()
    if not original.GATE.is_file():
        raise ValueError('Wait for Codex Task031 timing repair raw evidence review')
    gate = json.loads(original.GATE.read_text(encoding='utf-8'))
    if gate['status'] != 'WRITE_BUFFER_TURNOVER_RAW_EVIDENCE_REVIEW_PASS':
        raise ValueError('Timing repair functional gate has not passed')
    if gate['repair_kind'] != 'TASK031_X32_RESPONSE_REGISTER_CE_TIMING_REPAIR':
        raise ValueError('Wrong repair gate')
    if gate['manifest_sha256'] != timing.sha(timing.DESIGN):
        raise ValueError('Timing repair input manifest changed')
    if not gate['evidence_sha256']:
        raise ValueError('Timing repair raw evidence is missing')
    for name, digest in gate['evidence_sha256'].items():
        if timing.sha(original.ROOT / name) != digest:
            raise ValueError('Simulation evidence changed: ' + name)
    return gate


original.require_gate = require_gate


if __name__ == '__main__':
    original.main()
