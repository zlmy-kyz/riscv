"""Resume task018 once after user PDS finishes; immutable evidence rebinding, no ISA/PDS/serial."""
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
MANIFEST = HERE / 'inst_cache32_resume_inputs.json'
MS = Path('D:/modelsim/win64pe')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def project_configuration(text):
    """Exclude generated flow state/output records, preserving design options."""
    node = re.compile(r'\(_(?:comment|timespec|gci_state|db_output|output)\b')
    while match := node.search(text):
        depth, quoted, escaped = 0, False, False
        for stop in range(match.start(), len(text)):
            char = text[stop]
            if quoted:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    break
        else:
            raise ValueError('Unbalanced project metadata')
        text = text[:match.start()] + text[stop+1:]
    return re.sub(r'\s+', ' ', text).strip()


def pds_shell_count():
    # Enforce the existing prohibition on concurrent PDS and simulation.
    proc = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
        '(Get-Process -Name pds_shell -ErrorAction SilentlyContinue | Measure-Object).Count'],
        check=True, capture_output=True, text=True, timeout=15)
    return int(proc.stdout.strip())


def planned_counts():
    """Expand TB loops/calls statically; this is not HDL execution."""
    source = (HERE / 'tb_inst_cache32_x32.sv').read_text(encoding='utf-8')
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
        bound = match[2].strip()
        iterations = {'I_LINES': 32, 'D_LINES': 16}[bound] if bound in ('I_LINES', 'D_LINES') else int(bound)
        return count(text[:match.start()]) + iterations*count(text[match.end():end_start]) + count(text[end_stop:])
    main = source[source.index('    initial begin : run_tests'):]
    sections = re.split(r'\$display\("CHECK: (\S+) PASS"\);', main)
    assert len(sections) == 11
    rows = [dict(group=sections[i+1], checks=count(sections[i])) for i in range(0, 10, 2)]
    assert [r['checks'] for r in rows] == [325, 83, 111, 75, 240]
    assert sum(r['checks'] for r in rows) == 834
    return rows


def require_inputs():
    m = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name, digest in m['sha256'].items():
        assert sha(ROOT / name) == digest, 'Protected input changed: ' + name
    original_path = ROOT / m['original_input_manifest']
    assert sha(original_path) == m['original_input_manifest_sha256']
    original = json.loads(original_path.read_text(encoding='utf-8'))
    for source, destination in m['baseline_rebindings'].items():
        assert sha(ROOT / destination) == original['sha256'][source], source
    assert project_configuration((ROOT / 'RISCV.pds').read_text(encoding='utf-8')) == \
           project_configuration((ROOT / m['frozen_project']).read_text(encoding='utf-8')), \
           'PDS design options changed beyond generated flow metadata'
    assert planned_counts() == m['unit_plan']
    assert m['expected_checks'] == 834 and m['isa_cases'] == []
    # Only I array/index/reset change from successful MINI I16/D16.
    old = (ROOT / m['baseline_bridge']).read_text(encoding='utf-8')
    new = (ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v').read_text(encoding='utf-8')
    start = '    assign selected_addr ='
    assert old[old.index(start):] == new[new.index(start):]
    d_decl = '    // 16 行数据读缓冲'
    idle = '    wire idle_ready;'
    assert old[old.index(d_decl):old.index(idle)] == new[new.index(d_decl):new.index(idle)]
    d_assign = '    assign data_read_line_index ='
    i_block = '    always @(posedge clk) begin\n        if (!resetn) begin\n            inst_line_valid'
    assert old[old.index(d_assign):old.index(i_block)] == new[new.index(d_assign):new.index(i_block)]
    # Exact minimal transform guards the I change, including readiness/reset.
    expected = old.replace('指令缓存为 16 行直接映射，数据读缓冲为 8 行直接映射。',
                           '指令缓存为 32 行直接映射，数据读缓冲为 16 行直接映射。')
    replacements = {
        '// 16 行直接映射指令缓存': '// 32 行直接映射指令缓存',
        'reg [15:0]  inst_line_valid;': 'reg [31:0]  inst_line_valid;',
        'inst_line_tag [0:15];': 'inst_line_tag [0:31];',
        'inst_line_data [0:15];': 'inst_line_data [0:31];',
        'wire [3:0]  inst_line_index;': 'wire [4:0]  inst_line_index;',
        'wire [3:0]  data_line_index;': 'wire [4:0]  data_line_index;',
        'wire [3:0]  fill_line_index;': 'wire [4:0]  fill_line_index;',
        'inst_req_addr[BEAT_ADDR_BITS+3:BEAT_ADDR_BITS];': 'inst_req_addr[BEAT_ADDR_BITS+4:BEAT_ADDR_BITS];',
        'assign data_line_index = data_req_addr[BEAT_ADDR_BITS+3:BEAT_ADDR_BITS];':
            'assign data_line_index = data_req_addr[BEAT_ADDR_BITS+4:BEAT_ADDR_BITS];',
        'assign fill_line_index = request_line_tag[3:0];': 'assign fill_line_index = request_line_tag[4:0];',
        "inst_line_valid <= 16'b0;": "inst_line_valid <= 32'b0;",
        'reset_line < 16;': 'reset_line < 32;',
    }
    for before, after in replacements.items():
        assert before in expected, before
        expected = expected.replace(before, after)
    assert expected == new, 'Unexpected change beyond I32 declaration/index/reset and header correction'
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
        print('INPUTS_MATCH_NOT_SIMULATED', len(m['sha256']), 'checks=834 ISA=0')
        return
    assert args.tag and re.fullmatch(r'[A-Za-z0-9_-]+', args.tag), 'Use a new simple tag'
    assert pds_shell_count() == 0, 'Wait for user PDS completion; no HDL has been launched'
    out = HERE / 'build' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    manifest_sha = sha(MANIFEST)
    before = git_snapshot()
    (out / 'git_before.json').write_text(json.dumps(before, indent=2)+'\n', encoding='utf-8')
    result = dict(status='RUNNING', input_manifest_sha256=manifest_sha,
        original_input_manifest_sha256=m['original_input_manifest_sha256'],
        immutable_baseline_rebinding=True,
        isa_cases=[], pds_started=False, serial_opened=False,
        formal_board='NOT_TESTED', model_scope='Functional x32 user-port model, no DDR IP/PHY performance evidence')
    try:
        work = out / 'work'
        command([MS / 'vlib.exe', work], out, out / 'vlib')
        log = command([MS / 'vlog.exe', '-sv', '-work', work,
            ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v', HERE / 'tb_inst_cache32_x32.sv'], out, out / 'compile')
        assert 'Errors: 0' in log
        log = command([MS / 'vsim.exe', '-c', '-lib', work, 'tb_inst_cache32_x32',
            '-do', 'run -all; quit -f'], out, out / 'simulation')
        assert 'Errors: 0' in log
        assert re.findall(r'RESULT: PASS inst_cache32_x32 tests=(\d+)', log) == ['834']
        groups = re.findall(r'CHECK: (\S+) PASS', log)
        assert groups == [r['group'] for r in m['unit_plan']]
        assert require_inputs() == m and sha(MANIFEST) == manifest_sha
        after = git_snapshot()
        (out / 'git_after.json').write_text(json.dumps(after, indent=2)+'\n', encoding='utf-8')
        assert after == before, 'Working tree changed during execution; preserve evidence'
        for src in [ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v', HERE / 'tb_inst_cache32_x32.sv',
                    Path(__file__), MANIFEST, HERE / 'run_inst_cache32.py', original_path := ROOT / m['original_input_manifest']]:
            shutil.copy2(src, out / src.name)
        result.update(status='MINI_INST_CACHE32_KEY_TEST_PASS', checks=834,
            check_groups=groups, inputs_unchanged=True, git_snapshots_identical=True)
        print('RESULT: PASS', out, 'checks=834 ISA=0')
    except Exception as exc:
        result.update(status='FAIL', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
