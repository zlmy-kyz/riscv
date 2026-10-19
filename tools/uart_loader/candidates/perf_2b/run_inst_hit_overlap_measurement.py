"""Task033: frozen P300/V300 transport with reviewed functional evidence."""
import inspect
import json
import sys
from pathlib import Path

import run_zmmul300_measurement as software

ROOT = Path(__file__).resolve().parents[4]
GATE = ROOT / 'sim/cpu_inst_hit_overlap/review_20261017_02/codex_review.json'
BRIDGE_SHA = '7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933'
STATUS = 'TASK033_RAW_FUNCTIONAL_EVIDENCE_REVIEW_PASS'


def require_gate():
    gate = json.loads(GATE.read_text(encoding='utf-8'))
    if gate['status'] != STATUS or gate['bridge_sha256'] != BRIDGE_SHA:
        raise ValueError('Task033 reviewed bridge identity differs')
    if not gate['evidence_sha256']:
        raise ValueError('Task033 raw evidence missing')
    for mapping in ('evidence_sha256', 'design_and_test_sha256', 'software_sha256'):
        for name, digest in gate[mapping].items():
            p = Path(name)
            if not p.is_absolute():
                p = ROOT / p
            if software.sha(p) != digest:
                raise ValueError('Task033 reviewed input/evidence changed: ' + name)
    if software.sha(ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v') != BRIDGE_SHA:
        raise ValueError('Task033 bridge changed after review')
    return gate


def task_metadata():
    return dict(task='033', bridge_sha256=BRIDGE_SHA,
                functional_review_sha256=software.sha(GATE),
                baseline=dict(task='032', performance_cycles=210246597,
                              validation_cycles=210056980),
                comparison_scope='032 historical configuration differs from current Camera/PP/CNN integration; delta is not isolated to 033',
                camera_preprocess_cnn_workload='IDLE_EXPECTED_AFTER_KEY0_NO_CAPTURE_OR_INFERENCE_STARTED',
                programmed_design='USER_SELECTED_NOT_INDEPENDENTLY_OBSERVED',
                bitstream_audit_required=False)


def verify(path):
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    if raw.get('task033') != task_metadata():
        raise ValueError('Log does not match the Task033 reviewed context')
    return dict(software.verify(path), task033=raw['task033'])


# Same frozen packets, timeout and no-retry behavior; retain partial bytes if
# the existing five-second reader fails, as in the accepted Task032 transport.
_read_exact = software.transport_namespace['read_exact']


def read_exact_with_evidence(port, n, timeout=5):
    received = bytearray()

    class ObservedPort:
        def read(self, size):
            part = port.read(size)
            received.extend(part)
            return part

        def __getattr__(self, name):
            return getattr(port, name)

    try:
        return _read_exact(ObservedPort(), n, timeout)
    except ValueError as error:
        raise ValueError(f'{error}; received={len(received)}/{n}; partial_rx_hex={received.hex()}') from error


software.transport_namespace['read_exact'] = read_exact_with_evidence


def main():
    if sys.argv[1:] == ['--check-gate']:
        require_gate()
        print('Task033 functional evidence verified; serial/PDS/board NOT_RUN')
        return
    if '--verify-log' not in sys.argv:
        require_gate()
    # Reuse only the reviewed software's parser and transport. Its old hardware
    # gate is deliberately not called: Task033 has its own evidence above.
    code = inspect.getsource(software.measurement.main)
    old = 'sha(bit) if bit.is_file() else None'
    marker = '    a.log.parent.mkdir(parents=True, exist_ok=True)'
    if code.count(old) != 1 or code.count(marker) != 1:
        raise ValueError('Frozen measurement entry changed')
    code = code.replace(old, 'None')
    code = code.replace(marker, "    result['task033'] = task_metadata()\n" + marker)
    namespace = dict(software.namespace, task_metadata=task_metadata, verify=verify)
    exec(compile(code, '<Task033_frozen_P300_V300_transport>', 'exec'), namespace)
    namespace['main']()


if __name__ == '__main__':
    main()
