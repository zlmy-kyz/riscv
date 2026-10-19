"""One targeted MINI D8 bridge simulation; no ISA, PDS or serial operations."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / 'data_cache8_inputs.json'
MS = Path('D:/modelsim/win64pe')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def planned_counts():
    """Expand TB loops/calls statically; this is not HDL execution."""
    source = (HERE / 'tb_data_cache8_x32.sv').read_text(encoding='utf-8')
    weights = {n: 1 for n in ['fetch', 'load_word', 'store_word', 'cached_contention']}
    for name in ['queued_inst_fill', 'queued_data_fill']:
        body = re.search(r'task automatic ' + name + r'\b(.*?)endtask', source, re.S)[1]
        weights[name] = len(re.findall(r'\b(?:fetch|load_word|store_word)\(', body)) + \
                        len(re.findall(r'tests=tests\+1;', body))
    loop = re.compile(r'for\s*\(\s*(\w+)=0;\s*\1<([^;]+);\s*\1=\1\+1\s*\)\s*begin')
    def count(text):
        match = loop.search(text)
        if not match:
            return sum(weights[n] for n in re.findall(r'\b('+'|'.join(weights)+r')\(', text))
        depth = 1
        for token in re.finditer(r'\b(begin|end)\b', text[match.end():]):
            depth += 1 if token[1] == 'begin' else -1
            if depth == 0:
                end_start, end_stop = match.end()+token.start(), match.end()+token.end()
                break
        else:
            raise ValueError('Unbalanced static loop')
        iterations = 8 if match[2].strip() == 'D_LINES' else int(match[2])
        return count(text[:match.start()]) + iterations*count(text[match.end():end_start]) + count(text[end_stop:])
    main = source[source.index('    initial begin : run_tests'):]
    sections = re.split(r'\$display\("CHECK: (\S+) PASS"\);', main)
    assert len(sections) == 11
    rows = [dict(group=sections[i+1], checks=count(sections[i])) for i in range(0, 10, 2)]
    assert [r['checks'] for r in rows] == [85, 35, 47, 27, 80]
    assert sum(r['checks'] for r in rows) == 274
    return rows


def require_inputs():
    m = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name, digest in m['sha256'].items():
        assert sha(ROOT / name) == digest, 'Protected input changed: ' + name
    assert planned_counts() == m['unit_plan']
    assert m['expected_checks'] == 274 and m['isa_cases'] == []
    # Guard the scope: only D array/index/reset changed from successful MINI D4.
    old = (ROOT / m['baseline_bridge']).read_text(encoding='utf-8')
    new = (ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v').read_text(encoding='utf-8')
    start = '    assign selected_addr ='
    assert old[old.index(start):] == new[new.index(start):]
    start_i = '    always @(posedge clk) begin\n        if (!resetn) begin\n            inst_line_valid'
    assert old[old.index(start_i):old.index(start)] == new[new.index(start_i):new.index(start)]
    return m


def command(argv, cwd, prefix):
    start = time.monotonic()
    try:
        proc = subprocess.run(list(map(str, argv)), cwd=cwd, capture_output=True,
                              text=True, errors='replace', timeout=60)
        output = proc.stdout + proc.stderr
        code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        output = str(exc.stdout or '') + '\nRUNNER TIMEOUT\n'
        code = -1
    prefix.with_suffix('.log').write_text(output, encoding='utf-8')
    prefix.with_suffix('.command.json').write_text(json.dumps(dict(argv=list(map(str, argv)),
        cwd=str(cwd), exit_code=code, seconds=time.monotonic()-start), indent=2)+'\n', encoding='utf-8')
    assert code == 0 and not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|\bFATAL\b|RUNNER TIMEOUT', output), str(prefix)
    return output


def git_snapshot():
    def run(*args):
        return subprocess.run(['git', *args], cwd=ROOT, check=True,
                              capture_output=True, text=True, encoding='utf-8').stdout
    return dict(head=run('rev-parse', 'HEAD').strip(), status=run('status', '--porcelain', '-uall'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag')
    parser.add_argument('--check-inputs', action='store_true')
    args = parser.parse_args()
    m = require_inputs()
    if args.check_inputs:
        print('INPUTS_MATCH_NOT_SIMULATED', len(m['sha256']), 'checks=274 ISA=0')
        return
    assert args.tag and re.fullmatch(r'[A-Za-z0-9_-]+', args.tag), 'Use a new simple tag'
    out = HERE / 'build' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    manifest_sha = sha(MANIFEST)
    before = git_snapshot()
    (out / 'git_before.json').write_text(json.dumps(before, indent=2)+'\n', encoding='utf-8')
    result = dict(status='RUNNING', input_manifest_sha256=manifest_sha,
        isa_cases=[], pds_started=False, serial_opened=False,
        formal_board='NOT_TESTED', model_scope='Functional x32 user-port model, no DDR IP/PHY performance evidence')
    try:
        work = out / 'work'
        command([MS / 'vlib.exe', work], out, out / 'vlib')
        log = command([MS / 'vlog.exe', '-sv', '-work', work,
            ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v', HERE / 'tb_data_cache8_x32.sv'], out, out / 'compile')
        assert 'Errors: 0' in log
        log = command([MS / 'vsim.exe', '-c', '-lib', work, 'tb_data_cache8_x32',
            '-do', 'run -all; quit -f'], out, out / 'simulation')
        assert 'Errors: 0' in log
        assert re.findall(r'RESULT: PASS data_cache8_x32 tests=(\d+)', log) == ['274']
        groups = re.findall(r'CHECK: (\S+) PASS', log)
        assert groups == [r['group'] for r in m['unit_plan']]
        assert require_inputs() == m and sha(MANIFEST) == manifest_sha
        after = git_snapshot()
        (out / 'git_after.json').write_text(json.dumps(after, indent=2)+'\n', encoding='utf-8')
        assert after == before, 'Working tree changed during execution; preserve evidence'
        for src in [ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v', HERE / 'tb_data_cache8_x32.sv',
                    Path(__file__), MANIFEST]:
            shutil.copy2(src, out / src.name)
        result.update(status='MINI_DATA_CACHE8_KEY_TEST_PASS', checks=274,
            check_groups=groups, inputs_unchanged=True, git_snapshots_identical=True)
        print('RESULT: PASS', out, 'checks=274 ISA=0')
    except Exception as exc:
        result.update(status='FAIL', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
