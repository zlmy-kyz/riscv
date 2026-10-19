"""Task034 direct board trial requested by the user after PDS timing passed."""
import inspect
import json
import sys
from pathlib import Path

import run_zmmul300_measurement as software

ROOT = Path(__file__).resolve().parents[4]
IDENTITY = ROOT / 'sim/cpu_store_ack/preparation_20261017_a/after_manifest.json'
SOC_SHA = '7e43a9d55c04db6372bd906b7e244debd544ae840681146842440d50764c2d04'
BRIDGE_SHA = '7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933'
BASELINE = ROOT / 'sim/cpu_inst_hit_overlap/board/final_review_20261017_01/board_review.json'


def require_trial_inputs():
    # This is an identity check, not a dynamic functional acceptance gate.
    rows = json.loads(IDENTITY.read_text(encoding='utf-8'))
    assert rows['myriscv/soc_top.v'] == SOC_SHA
    assert rows['myriscv/dual_sram_to_pango_ddr_bridge.v'] == BRIDGE_SHA
    for name, digest in rows.items():
        if name in ('RISCV.pds', 'constraint_check/temp_constraint_file.fdc'):
            continue  # PDS artifacts are user-owned, never a board-tool gate.
        if software.sha(ROOT / name) != digest:
            raise ValueError('Task034 static input changed: ' + name)
    return rows


def task_metadata():
    return dict(task='034', soc_top_sha256=SOC_SHA, bridge_sha256=BRIDGE_SHA,
                static_identity_sha256=software.sha(IDENTITY),
                authorization='USER_REPORTED_TIMING_PASS_AND_EXPLICITLY_REQUESTED_DIRECT_BOARD_TRIAL',
                dynamic_functional_simulation='NOT_RUN',
                functional_simulation_acceptance='NOT_CLAIMED',
                timing='PASS_REPORTED_BY_USER_NOT_INDEPENDENTLY_REVIEWED',
                baseline_review_sha256=software.sha(BASELINE),
                baseline=dict(task='033',performance_cycles=227882946,validation_cycles=227937510),
                peripheral_workload='CAMERA_PP_CNN_IDLE_EXPECTED_AFTER_RECONFIGURATION_AND_KEY0',
                programmed_design='USER_SELECTED_NOT_INDEPENDENTLY_OBSERVED',
                bitstream_audit_required=False)


def verify(path):
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    if raw.get('task034') != task_metadata():
        raise ValueError('Log does not match the Task034 direct-trial identity')
    return dict(software.verify(path), task034=raw['task034'])


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
    if sys.argv[1:] == ['--check-inputs']:
        require_trial_inputs()
        print('Task034 design/BIN identity verified; HDL NOT_RUN; serial NOT_OPENED')
        return
    if '--verify-log' not in sys.argv:
        require_trial_inputs()
    code = inspect.getsource(software.measurement.main)
    old_hash = 'sha(bit) if bit.is_file() else None'
    marker = '    a.log.parent.mkdir(parents=True, exist_ok=True)'
    old_prompt = "    print('先下载你生成的FPGA位流。关闭串口助手；按KEY0并释放，等待DDR就绪。')"
    if any(code.count(s) != 1 for s in (old_hash, marker, old_prompt)):
        raise ValueError('Frozen measurement entry changed')
    code = code.replace(old_hash, 'None')
    code = code.replace(marker, "    result['task034'] = task_metadata()\n" + marker)
    code = code.replace(old_prompt,
        "    print('034直接板试（相关动态仿真未验收）。本轮先重新下载同一个034位流，关闭串口助手，再KEY0并释放、等DDR就绪。')")
    namespace = dict(software.namespace, task_metadata=task_metadata, verify=verify)
    exec(compile(code, '<Task034_user_authorized_direct_board_trial>', 'exec'), namespace)
    namespace['main']()


if __name__ == '__main__':
    main()
