"""Task009: single-line data read buffer, one focused TB and two ISA cases."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / 'data_read_input_manifest.json'
MS = Path('D:/modelsim/win64pe')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require_inputs():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert len(manifest['isa_cases']) == 2
    for name, digest in manifest['sha256'].items():
        assert sha(ROOT / name) == digest, 'INPUT_CHANGED: ' + name
    return manifest


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def command(args, cwd, log, timeout=90):
    args = [str(a) for a in args]
    start = time.monotonic()
    try:
        run = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                             errors='replace', timeout=timeout)
        output, exit_code = run.stdout + run.stderr, run.returncode
    except subprocess.TimeoutExpired as exc:
        parts = [exc.stdout or '', exc.stderr or '']
        output = ''.join(p.decode(errors='replace') if isinstance(p, bytes) else p
                         for p in parts) + '\nRUNNER TIMEOUT\n'
        exit_code = -1
    log.write_text(output, encoding='utf-8')
    log.with_suffix('.command.json').write_text(json.dumps(dict(
        argv=args, cwd=str(cwd), exit_code=exit_code,
        seconds=time.monotonic() - start), indent=2) + '\n', encoding='utf-8')
    assert exit_code == 0, 'Command failed: ' + str(log)
    assert not re.search(r'RESULT: FAIL|\b(?:ERROR|FATAL):|\*\*\s*(?:Error|Fatal):',
                         output, re.I), str(log)
    return output


def git_snapshot(path):
    state = {}
    for key, args in (('head', ['rev-parse', 'HEAD']), ('status', ['status', '--short'])):
        run = subprocess.run(['git', *args], cwd=ROOT, capture_output=True,
                             text=True, errors='replace', timeout=15)
        assert run.returncode == 0, run.stderr
        state[key] = run.stdout
    path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    return state


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag')
    p.add_argument('--check-inputs', action='store_true')
    a = p.parse_args()
    manifest = require_inputs()
    if a.check_inputs:
        assert not a.tag
        print('INPUTS_MATCH_NOT_SIMULATED', manifest['isa_seed'], manifest['isa_cases'])
        return
    assert a.tag and re.fullmatch('[a-z0-9_-]+', a.tag)
    out = HERE / 'build' / a.tag
    out.mkdir(parents=True, exist_ok=False)
    result = dict(status='RUNNING', input_manifest_sha256=sha(MANIFEST),
                  isa_seed=manifest['isa_seed'], isa_cases=manifest['isa_cases'],
                  checks={}, formal_board='NOT_TESTED', pds_started=False,
                  serial_opened=False, functional_only_not_DDR_performance=True)
    result['git_before'] = git_snapshot(out / 'git_before.json')
    try:
        for mode, d_enabled, bridge in (
                ('baseline', 0, ROOT / manifest['baseline_bridge']),
                ('optimized', 1, ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v')):
            folder = out / mode
            folder.mkdir()
            work = folder / 'work'
            command([MS / 'vlib.exe', work], folder, folder / 'vlib.log')
            output = command([MS / 'vlog.exe', '-sv', '-work', work, bridge,
                              HERE / 'tb_data_read_buffer.sv'],
                             folder, folder / 'compile.log')
            assert 'Errors: 0' in output
            output = command([MS / 'vsim.exe', '-c', '-lib', work,
                              'tb_data_read_buffer', '-gENABLE=1',
                              '-gD_ENABLED=' + str(d_enabled),
                              '-do', 'run -all; quit -f'], folder,
                             folder / 'simulation.log', 60)
            matches = re.findall(
                r'RESULT: PASS data_read_buffer enabled=(\d+) tests=(\d+)', output)
            assert len(matches) == 1 and int(matches[0][0]) == d_enabled
            assert int(matches[0][1]) > 0 and 'Errors: 0' in output
            result['checks'][mode] = dict(status='PASS', tests=int(matches[0][1]))
        # Reuse the CPU-loader DDR-path TB, with separate images/output directory.
        # The model verifies function; only actual-board formal120 measures speed.
        folder = out / 'isa'
        folder.mkdir()
        sys.path.insert(0, str(ROOT / 'MyCpu_test'))
        builder = load(ROOT / 'MyCpu_test/build_ddr_stage.py', 'selected_images')
        builder.OUT = folder / 'images'
        sys.argv = ['build_ddr_stage.py', *manifest['isa_cases']]
        builder.main()
        runner = load(ROOT / 'MyCpu_test/run_ddr_rv32i_fast.py', 'selected_rv32i')
        binary = folder / 'selected.vvp'
        command([runner.IVERILOG, '-g2012', '-I' + str(ROOT / 'myriscv'),
                 '-s', 'tb_soc_ddr3_rv32i_fast', '-o', binary,
                 *[ROOT / n for n in runner.SOURCES]], ROOT, folder / 'compile.log')
        tohost = dict(line.split() for line in
                      (builder.OUT / 'tohost.tsv').read_text().splitlines())
        assert (builder.OUT / 'cases.txt').read_text().split() == manifest['isa_cases']
        for name in manifest['isa_cases']:
            output = command([runner.VVP, binary,
                              '+BOOT=' + (builder.OUT / 'boot_rom.dat').as_posix(),
                              '+IMAGE=' + (builder.OUT / (name + '.dat')).as_posix(),
                              '+TEST=' + name, '+TOHOST=' + tohost[name]],
                             ROOT, folder / (name + '.log'))
            lines = re.findall(r'^RESULT: (?:PASS|FAIL).*$', output, re.M)
            assert len(lines) == 1 and lines[0].startswith(
                'RESULT: PASS ' + name + ' DDR RV32I tohost=1')
            assert 'CHECK: ' + name + ' CPU loaded' in output
            result['checks']['isa_' + name] = dict(status='PASS')
        result['status'] = 'DATA_READ_BUFFER_KEY_TESTS_PASS'
    except BaseException as exc:
        result['status'] = 'FAIL'
        result['error'] = str(exc)
        raise
    finally:
        try:
            result['git_after'] = git_snapshot(out / 'git_after.json')
            require_inputs()
            assert sha(MANIFEST) == result['input_manifest_sha256']
            result['inputs_unchanged'] = True
        except BaseException as exc:
            result['status'] = 'FAIL'
            result['inputs_unchanged'] = False
            result['input_error'] = str(exc)
            raise
        finally:
            (out / 'result.json').write_text(
                json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('RESULT: PASS', out, manifest['isa_cases'])


if __name__ == '__main__':
    main()
