"""DeepSeek execution entry. Creating this script does not execute simulation."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / 'input_manifest.json'
BRIDGE = 'myriscv/dual_sram_to_pango_ddr_bridge.v'
BASELINE = ('sim/cpu_performance_2b/build/main_pds_board_20261010_a/'
            'frozen_inputs/' + BRIDGE)
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_inputs():
    receipt = json.loads(MANIFEST.read_text())
    for name, digest in receipt['sha256'].items():
        assert sha(ROOT / name) == digest, 'INPUT_CHANGED: ' + name
    assert sha(ROOT / BASELINE) == receipt['baseline_bridge_sha256']
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--suite', choices=['unit', 'micro', 'coremark', 'compare'], required=True)
    parser.add_argument('--mode', choices=['baseline', 'optimized'], default='optimized')
    parser.add_argument('--engine', choices=['functional', 'physical'], default='functional')
    parser.add_argument('--baseline-tag')
    parser.add_argument('--optimized-tag')
    args = parser.parse_args()
    assert re.fullmatch('[a-z0-9_-]+', args.tag)
    for tag in (args.baseline_tag, args.optimized_tag):
        assert tag is None or re.fullmatch('[a-z0-9_-]+', tag)
    before = require_inputs()
    out = HERE / 'build' / args.tag
    assert not out.exists(), 'Use a fresh tag; do not overwrite evidence'
    sys.path.insert(0, str(ROOT / 'sim/cpu_performance_2b'))
    spec = importlib.util.spec_from_file_location('line_perf', ROOT / 'sim/cpu_performance_2b/run.py')
    perf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(perf)
    result = dict(status='RUNNING', suite=args.suite, mode=args.mode,
                  engine=args.engine, board_result='NOT_TESTED', pds_started=False,
                  serial_opened=False, input_manifest_sha256=sha(MANIFEST))
    try:
        if args.suite == 'unit':
            out.mkdir(parents=True)
            for enable in (0, 1):
                folder = out / ('enable_' + str(enable))
                folder.mkdir()
                work = folder / 'work'
                perf.base.command([perf.base.MS / 'vlib.exe', work], folder, folder / 'vlib.log')
                output, _ = perf.base.command(
                    [perf.base.MS / 'vlog.exe', '-sv', '-work', work,
                     ROOT / BRIDGE, HERE / 'tb_inst_line_buffer.sv'], folder, folder / 'compile.log')
                assert 'Errors: 0' in output
                output, _ = perf.base.command(
                    [perf.base.MS / 'vsim.exe', '-c', '-lib', work, 'tb_inst_line_buffer',
                     '-gENABLE=' + str(enable), '-do', 'run -all; quit -f'],
                    folder, folder / 'simulation.log', 60)
                assert f'RESULT: PASS inst_line_buffer enable={enable}' in output
                assert 'Errors: 0' in output and not re.search(r'\bERROR:', output)
            result['functional_only_not_DDR_performance'] = True
        elif args.suite == 'compare':
            assert args.baseline_tag and args.optimized_tag
            out.mkdir(parents=True)
            receipts = [json.loads((HERE / 'build' / tag / 'line_buffer_receipt.json').read_text())
                        for tag in (args.baseline_tag, args.optimized_tag)]
            for receipt, mode in zip(receipts, ('baseline', 'optimized')):
                assert receipt['status'] == 'INST_LINE_BUFFER_VERIFICATION_PASS'
                assert receipt['mode'] == mode and receipt['inputs_unchanged']
                assert receipt['input_manifest_sha256'] == sha(MANIFEST)
            assert receipts[0]['suite'] == receipts[1]['suite']
            assert receipts[0]['engine'] == receipts[1]['engine'] == args.engine
            rows = []
            for name in ('micro', 'performance_1', 'validation_1'):
                bp = HERE / 'build' / args.baseline_tag / name / 'summary.json'
                op = HERE / 'build' / args.optimized_tag / name / 'summary.json'
                if not bp.exists() and not op.exists():
                    continue
                b, o = json.loads(bp.read_text()), json.loads(op.read_text())
                assert b['status'] == o['status'] == 'PASS' and b['engine'] == o['engine']
                assert len(b['windows']) == len(o['windows'])
                for bw, ow in zip(b['windows'], o['windows']):
                    assert bw['id'] == ow['id'] and bw['name'] == ow['name']
                    assert bw['instret'] == ow['instret'], 'retirement/window change requires review'
                    rows.append(dict(application=name, window=bw['name'],
                                     baseline=bw, optimized=ow,
                                     cycle_ratio=bw['cycles'] / ow['cycles'],
                                     ar_reduction=bw['ddr_ar_commands'] - ow['ddr_ar_commands'],
                                     physical_performance_evidence=b['engine'].startswith('physical')))
            assert rows, 'No comparable summaries'
            result['comparisons'] = rows
        else:
            def selected_source(path):
                return ROOT / BASELINE if args.mode == 'baseline' and path == ROOT / BRIDGE else path
            perf.source = selected_source
            perf.HERE = HERE
            sys.argv = ['run.py', '--tag', args.tag, '--suite', args.suite,
                        '--engine', args.engine]
            perf.main()
        result['status'] = 'INST_LINE_BUFFER_VERIFICATION_PASS'
    except BaseException as error:
        result.update(status='FAIL', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        if out.exists():
            try:
                after = require_inputs()
                assert before == after
                result['inputs_unchanged'] = True
            except BaseException:
                result['inputs_unchanged'] = False
                result['status'] = 'INPUT_CHANGED'
                raise
            finally:
                (out / 'line_buffer_receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print('RESULT: PASS', args.suite, args.tag)


if __name__ == '__main__':
    main()
