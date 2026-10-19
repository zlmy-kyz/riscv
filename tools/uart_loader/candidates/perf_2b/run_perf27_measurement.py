"""Independent PERF27 P/V300 UART entry. Offline modes do not open serial."""
from pathlib import Path
import argparse
import inspect
import json
import re
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT/'tests/cpu_performance_2b'))
from perf27_software import require_manifest, parse_measurement, sha
from perf27_fixed_software import DEFAULT_FIXED_TAG
from zmmul300_software import measurement as legacy

WATCH = ['myriscv/mycpu_sync.v', 'myriscv/dual_sram_to_pango_ddr_bridge.v',
         'myriscv/simple_mmio.v', 'myriscv/soc_top.v', 'myriscv/soc_ddr3_top.v',
         'myriscv/board_top.v', 'tests/cpu_performance_2b/perf27.c',
         'tests/cpu_performance_2b/perf27_software.py',
         'tests/cpu_performance_2b/perf27_fixed_software.py',
         'tests/cpu_performance_2b/build_perf27_fixed.py',
         'tools/uart_loader/candidates/perf_2b/run_perf27_measurement.py']

def read_response(port, length, row, timeout=5):
    """Keep partial bytes on the existing deadline; never retry or flush."""
    data = bytearray()
    row['expected_response_bytes'] = length
    row['received_response_bytes'] = 0
    row['rx_hex'] = ''
    end = time.monotonic()+timeout
    while len(data)<length and time.monotonic()<end:
        part = port.read(length-len(data))
        if part:
            data += part
            row['rx_hex'] = data.hex()
            row['received_response_bytes'] = len(data)
    if len(data)!=length:
        raise ValueError(f'response timeout/short read: received {len(data)}/{length} bytes')
    return bytes(data)

def main():
    extra = argparse.ArgumentParser(add_help=False)
    extra.add_argument('--build-tag')
    extra.add_argument('--core-clock-hz', type=int, default=93_750_000)
    extra.add_argument('--reset-method', choices=['key0','jtag'], default='key0')
    options, rest = extra.parse_known_args()
    if options.build_tag is None and '--verify-log' in rest:
        record = json.loads(Path(rest[rest.index('--verify-log')+1]).read_text(encoding='utf-8'))
        options.build_tag = Path(record['manifest_path']).parent.parent.name
    if options.build_tag is None:
        options.build_tag = DEFAULT_FIXED_TAG
    assert re.fullmatch('[a-z0-9_-]+', options.build_tag)
    assert options.core_clock_hz == 93_750_000, 'This BIN/BSP requires actual core_clk=93.75 MHz; rebuild software/peripheral parameters before changing frequency'
    build = ROOT/'tests/cpu_performance_2b/build'/options.build_tag
    def manifest_for(name):
        assert name in ('performance_300', 'validation_300')
        return build/name/'manifest.json'
    # Keep RVLD stop-and-wait framing, startup handling and first-failure policy.
    code = inspect.getsource(legacy.upload.execute)
    guard = "b'PORT_DONE ticks=' in output and output.endswith(b'\\n')"
    assert code.count(guard) == 1
    code = code.replace(guard, "output.endswith(b'PERF2B_DONE\\n')", 1)
    response_call = 'raw=read_exact(port,60);'
    assert code.count(response_call) == 1
    code = code.replace(response_call,'raw=read_response(port,60,row);',1)
    transport = dict(legacy.upload.__dict__, parse_output=parse_measurement,read_response=read_response)
    exec(compile(code, '<PERF27_RVLD_transport>', 'exec'), transport)
    ns = dict(legacy.__dict__, manifest_for=manifest_for, require_manifest=require_manifest,
              parse_measurement=parse_measurement, execute=transport['execute'],
              USER_RESET_METHOD=options.reset_method,
              APPLICATIONS=('performance_300', 'validation_300'), FORMAL_APPLICATIONS=())
    for name in ['verify_record', 'verify', 'main']:
        entry = inspect.getsource(getattr(legacy, name))
        if name == 'main':
            confirmation = "        result['user_KEY0_confirmation'] = True"
            assert entry.count(confirmation) == 1
            entry = entry.replace(confirmation,confirmation+
                "\n        result['user_reset_method'] = USER_RESET_METHOD"+
                "\n        result['user_reported_KEY0_press'] = USER_RESET_METHOD == 'key0'",1)
            if options.reset_method == 'jtag':
                original = '先下载你生成的FPGA位流。关闭串口助手；按KEY0并释放，等待DDR就绪。'
                assert entry.count(original) == 1
                entry = entry.replace(original,'先JTAG重新下载当前同一位流。关闭串口助手；KEY0保持释放，不再按键，等待DDR就绪。',1)
        exec(compile(entry, '<PERF27_'+name+'>', 'exec'), ns)
    if '--log' in rest:
        log = Path(rest[rest.index('--log')+1])
        assert not log.exists(), 'Preserve existing log'
        ident = log.parent/'identity.json'
        identity = dict(candidate='PERF27_V1', core_clock_hz=options.core_clock_hz,
            requested_reset_method=options.reset_method,
            build_tag=options.build_tag, acceptance_scope='COREMARK_P_V300_CRC_UART_TIMER_AND_27_COUNTERS',
            sha256={n:sha(ROOT/n) for n in WATCH})
        for app in ['performance_300', 'validation_300']:
            info = require_manifest(manifest_for(app))
            identity['layout_schema'] = info.get('layout_schema', 'UNFIXED_PERF27_LAYOUT')
            for n in [info['bin_path'], info['elf_path'], manifest_for(app).relative_to(ROOT).as_posix()]:
                identity['sha256'][n] = sha(ROOT/n)
        if ident.exists():
            assert json.loads(ident.read_text(encoding='utf-8')) == identity, 'Identity changed between P and V'
        else:
            ident.parent.mkdir(parents=True, exist_ok=True)
            ident.write_text(json.dumps(identity, indent=2)+'\n', encoding='utf-8')
    sys.argv = [sys.argv[0], *rest]
    ns['main']()
    if '--log' in rest and '--plan-only' not in rest:
        parsed = json.loads(Path(rest[rest.index('--log')+1]).read_text(encoding='utf-8'))['application']['parsed']
        rates = parsed['cache_hit_rates_basis_points']
        def percent(bp):
            return 'N/A' if bp is None else f'{bp//100}.{bp%100:02d}%'
        print('CACHE_HIT_RATE I='+percent(rates['icache_hit_rate_bp'])+
              ' D_read='+percent(rates['dcache_read_hit_rate_bp']))

if __name__ == '__main__': main()
