"""User-operated fixed P300/V300 board trial for the EX-redirect candidate.

Reuses the frozen Zmmul300 transport, parsers and 13-counter decoding (same
BIN, same UART protocol, same 93.75 MHz bitstream flow). Unlike
run_zmmul300_measurement.py it does NOT assert a pre-recorded bitstream/RTL
gate, because this candidate has no board baseline yet: the existing gates
still pin the pre-change RTL and would reject the new bitstream.

Instead the current identity is written into the log directory before the run,
so the evidence carries its own provenance. Acceptance is unchanged: fixed
P300 then V300, one run each, CRC/13 counters/protocol must match, first
failure stops and the log directory is never reused.
"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))

import run_zmmul300_measurement as base

WATCH = [
    'generate_bitstream/board_top.sbit',
    'myriscv/mycpu_sync.v',
    'myriscv/data_bus_interconnect.v',
    'myriscv/inst_bus_interconnect.v',
    'myriscv/dual_sram_to_pango_ddr_bridge.v',
    'myriscv/soc_top.v',
    'myriscv/soc_ddr3_top.v',
    'myriscv/board_top.v',
    'myriscv/simple_mmio.v',
    'tests/cpu_performance_2b/build/measure_zmmul300_20261013_a/performance_300/program.bin',
    'tests/cpu_performance_2b/build/measure_zmmul300_20261013_a/validation_300/program.bin',
]


def record_identity(log_path):
    # Missing inputs must not silently produce an empty provenance record.
    missing = [name for name in WATCH if not (ROOT / name).is_file()]
    if missing:
        raise ValueError('Missing EX identity inputs: ' + ', '.join(missing))
    ident = {name: base.sha(ROOT / name) for name in WATCH}
    out = Path(log_path).parent / 'identity.json'
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            'candidate': 'EX_REDIRECT_ID_DECIDE_EX_REDIRECT',
            'acceptance_scope': 'FIXED_P300_V300_APPLICATION_CRC_UART_TIMER_AND_13_COUNTERS',
            'note': 'No pre-recorded gate: pre-change gates pin the older RTL/bitstream.',
            'sha256': ident,
        }, indent=2) + '\n', encoding='utf-8')
    return ident


def main():
    log_path = None
    for i, a in enumerate(sys.argv):
        if a == '--log' and i + 1 < len(sys.argv):
            log_path = sys.argv[i + 1]
    if log_path:
        record_identity(log_path)
        print('EX-redirect identity recorded for', log_path)
    base.namespace['main']()


if __name__ == '__main__':
    main()
