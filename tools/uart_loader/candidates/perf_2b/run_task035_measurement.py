"""Task035 fixed-BIN application-function and actual-DDR performance trial."""
import inspect
import json
import sys
from pathlib import Path

import run_zmmul300_measurement as software

ROOT = Path(__file__).resolve().parents[4]
IDENTITY = ROOT / 'sim/cpu_dual_read/rdata_timing_repair_20261018_a/after_manifest.json'
BASELINE = ROOT / 'sim/cpu_store_ack/board/review_20261017_01/board_review.json'
PINNED = {
    'myriscv/soc_top.v': 'cd3d820aee9ad2572e52972ba4f8942221054d42ea7457e87f7517a90322232b',
    'myriscv/dual_sram_to_pango_ddr_bridge.v': '1abf54fe01fb76659943fd14818154cfffe1bde23cd9f996b711b185452afe67',
    'myriscv/inst_bram_adapter.v': 'fa4ac709ef35b606f02f17b96383f5f0c0f09bd76bba1af8065343e2e9456b7d',
}


def require_inputs():
    rows = json.loads(IDENTITY.read_text(encoding='utf-8'))
    for name, digest in PINNED.items():
        if rows[name] != digest or software.sha(ROOT / name) != digest:
            raise ValueError('Task035 final design identity differs: ' + name)
    for name, digest in rows.items():
        if name in ('RISCV.pds', 'constraint_check/temp_constraint_file.fdc', 'report_timing/board_top.rtr'):
            continue
        if software.sha(ROOT / name) != digest:
            raise ValueError('Task035 static input changed: ' + name)
    base = json.loads(BASELINE.read_text(encoding='utf-8'))
    if base['status'] != 'TASK034_FIXED_P300_V300_BOARD_RAW_PASS_HDL_NOT_RUN':
        raise ValueError('Task034 performance baseline differs')
    # Only baseline UART evidence must still match: old design source hashes in
    # that historical review intentionally belong to Task034, not Task035.
    for name, digest in base['evidence_sha256'].items():
        if name.startswith('sim/cpu_store_ack/board/coremark_store_ack_300_01/'):
            if software.sha(ROOT / name) != digest:
                raise ValueError('Task034 baseline UART evidence changed: ' + name)
    return rows


def task_metadata():
    return dict(task='035', design_sha256=PINNED,
        static_identity_sha256=software.sha(IDENTITY),
        authorization='USER_REQUESTED_TASK035_FUNCTION_AND_ACTUAL_PERFORMANCE_BOARD_ACCEPTANCE',
        acceptance_scope='FIXED_P300_V300_APPLICATION_CRC_UART_TIMER_AND_13_COUNTERS',
        dynamic_RTL_functional_simulation='NOT_RUN',
        full_protocol_conflict_and_reset_coverage='NOT_ACCEPTED_BY_COREMARK_ALONE',
        timing='EXISTING_REPORT_ALL_CONSTRAINTS_MET_93_75MHZ_WNS_PLUS_0_151NS_NOT_INDEPENDENT_REBUILD',
        baseline_review_sha256=software.sha(BASELINE),
        baseline=dict(task='034',performance_cycles=227315593,validation_cycles=227420763),
        peripheral_workload='CAMERA_PP_CNN_IDLE_EXPECTED_AFTER_RECONFIGURATION_AND_KEY0',
        programmed_design='USER_SELECTED_NOT_INDEPENDENTLY_OBSERVED',bitstream_audit_required=False)


def verify_record(raw):
    if raw.get('task035') != task_metadata():
        raise ValueError('Log does not match the Task035 final-design trial')
    out = software.namespace['verify_record'](raw)
    mode = 'P' if out['application_name'] == 'performance_300' else 'V'
    base = json.loads(BASELINE.read_text(encoding='utf-8'))['verified'][mode]['application']
    current = out['application']
    if current['clock_hz'] != base['clock_hz']:
        raise ValueError('Clock contract differs from Task034')
    comparison = dict(baseline_task='034',baseline_cycles=base['ticks'],baseline_seconds=base['seconds'],
        current_cycles=current['ticks'],current_seconds=current['seconds'],
        cycles_delta=current['ticks']-base['ticks'],
        time_change_percent=(current['ticks']/base['ticks']-1)*100,
        throughput_change_percent=(base['ticks']/current['ticks']-1)*100,
        instret_delta=current['counters']['instret']-base['counters']['instret'],
        counter_deltas={n:v-base['counters'][n] for n,v in current['counters'].items()},
        scope='Single fixed-BIN engineering comparison; no significance or formal benchmark claim')
    return dict(out,task035=raw['task035'],comparison_to_034=comparison)


def verify(path):
    return verify_record(json.loads(Path(path).read_text(encoding='utf-8')))


def print_comparison(verified):
    p = verified['comparison_to_034']
    print(f"VS034 baseline={p['baseline_seconds']:.9f}s cycles_delta={p['cycles_delta']:+d} "
          f"time_change={p['time_change_percent']:+.6f}% throughput_change={p['throughput_change_percent']:+.6f}%")


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
        require_inputs()
        print('Task035 final bridge/SoC/ROM-adapter/BIN identity verified; HDL NOT_RUN; serial NOT_OPENED')
        return
    if '--verify-log' not in sys.argv:
        require_inputs()
    code = inspect.getsource(software.measurement.main)
    old_hash = 'sha(bit) if bit.is_file() else None'
    marker = '    a.log.parent.mkdir(parents=True, exist_ok=True)'
    old_prompt = "    print('先下载你生成的FPGA位流。关闭串口助手；按KEY0并释放，等待DDR就绪。')"
    done = "        print('RESULT: PASS measurement application')"
    if any(code.count(s) != 1 for s in (old_hash,marker,old_prompt,done)):
        raise ValueError('Frozen measurement entry changed')
    code = code.replace(old_hash,'None')
    code = code.replace(marker,"    result['task035'] = task_metadata()\n"+marker)
    code = code.replace(old_prompt,
        "    print('035应用功能/实际性能板测（完整协议/复位动态覆盖未验收）。本轮先重新下载同一个035位流，关闭串口助手，再KEY0、等DDR就绪。')")
    code = code.replace(done,done+'\n        print_comparison(verified)')
    namespace = dict(software.namespace,task_metadata=task_metadata,verify_record=verify_record,
                     verify=verify,print_comparison=print_comparison)
    exec(compile(code,'<Task035_fixed_BIN_function_and_performance>','exec'),namespace)
    namespace['main']()


if __name__ == '__main__':
    main()
