"""Continue fast regression without requiring identical timing for known ISA gaps."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import inspect
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def failure_identity(text, expected_name):
    """Ignore only the final cycles field; require one complete known-gap result."""
    assert expected_name in ('fence_i', 'ma_data')
    assert not re.search(r'\*\* (?:Error|Fatal)|\bERROR:|Traceback', text)
    lines = re.findall(r'RESULT: FAIL[^\r\n]*', text)
    assert len(lines) == 1, 'missing or duplicate failure diagnostic'
    match = re.fullmatch(
        r'RESULT: FAIL (\w+) DDR RV32I tohost=([0-9a-fA-F]{8}) '
        r'failed_test=(\d+) cycles=(\d+)', lines[0])
    assert match, 'unexpected failure format; do not treat as known gap'
    name, tohost, failed_test, cycles = match.groups()
    assert name == expected_name and int(tohost, 16) != 1 and int(cycles) > 0
    # Keep exact case/field text; only execution duration may differ.
    return dict(semantic=lines[0].rsplit(' cycles=', 1)[0],
                raw=lines[0], cycles=int(cycles))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    assert re.fullmatch('[a-z0-9_-]+', args.tag)
    spec = importlib.util.spec_from_file_location('line_runner', HERE / 'run.py')
    line = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(line)
    before = line.require_inputs()
    resume_manifest = json.loads((HERE / 'resume_input_manifest.json').read_text())
    for name, digest in resume_manifest['sha256'].items():
        assert sha(ROOT / name) == digest, 'INPUT_CHANGED: ' + name
    sys.path.insert(0, str(ROOT / 'sim/cpu_performance_2b'))
    import regress
    folder = HERE / 'build' / args.tag
    folder.mkdir(parents=True, exist_ok=False)
    comparisons = {}

    def baseline_source(name):
        old = ROOT / 'sim/cpu_performance_2b/build/frozen_inputs' / name
        if name.startswith('myriscv/'):
            assert old.is_file(), 'missing frozen baseline RTL: ' + name
        return old if old.is_file() else ROOT / name

    def semantic_failure(path, name):
        parsed = failure_identity(path.read_text(), name)
        comparisons.setdefault(name, {})[path.name] = parsed
        return parsed['semantic']

    code = inspect.getsource(regress.fast)
    needle = "return re.findall(r'RESULT: FAIL[^\\r\\n]*',p.read_text())"
    assert code.count(needle) == 1, 'unexpected original checker; review before adapting'
    code = code.replace(needle, 'return semantic_failure(p,name)', 1)
    needle = '[ROOT/n for n in r.SOURCES]'
    assert code.count(needle) == 1
    code = code.replace(needle, '[baseline_source(n) for n in r.SOURCES]', 1)
    namespace = dict(regress.__dict__, baseline_source=baseline_source,
                     semantic_failure=semantic_failure)
    exec(compile(code, '<line_buffer_fast_adapter>', 'exec'), namespace)
    result = dict(status='RUNNING', suite='fast',
                  original_input_manifest_sha256=sha(HERE / 'input_manifest.json'),
                  resume_input_manifest_sha256=sha(HERE / 'resume_input_manifest.json'),
                  ignored_failure_field='cycles only', pds_started=False,
                  serial_opened=False, board_result='NOT_TESTED')
    try:
        result['checks'] = namespace['fast'](folder)
        result['status'] = 'INST_LINE_BUFFER_FAST_REGRESSION_PASS'
    except BaseException as error:
        result.update(status='FAIL', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        result['failure_comparisons'] = comparisons
        try:
            assert line.require_inputs() == before
            for name, digest in resume_manifest['sha256'].items():
                assert sha(ROOT / name) == digest, 'INPUT_CHANGED: ' + name
            result['inputs_unchanged'] = True
        except BaseException:
            result.update(status='INPUT_CHANGED', inputs_unchanged=False)
            raise
        finally:
            (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('RESULT: PASS fast regression; only known-gap timing field excluded')


if __name__ == '__main__':
    main()
