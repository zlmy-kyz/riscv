"""Task 006: strict offline physical comparison and checked Loader simulations.

Only --suite loader launches ModelSim. Codex prepares this entry; DeepSeek runs
the simulations. All original manifests, runners, TBs and FAIL logs are retained.
"""
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
ORIGINAL_HASH = '1173f29a185651c99bdbc3053946c2b109aea789b9e14851543994d2dc6027ea'
RESUME_HASH = '40f5bb2227483cc8fc5d8ea3e5156455c38f90ea7d0a9b316a95d270c1134002'
APPLICATIONS = ('hello', 'crc32', 'performance_1', 'validation_1')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_inputs():
    assert sha(HERE / 'input_manifest.json') == ORIGINAL_HASH
    assert sha(HERE / 'resume_input_manifest.json') == RESUME_HASH
    manifests = {}
    for name in ('input_manifest.json', 'resume_input_manifest.json', 'checks_input_manifest.json'):
        p = HERE / name
        data = json.loads(p.read_text())
        for n, h in data['sha256'].items():
            assert sha(ROOT / n) == h, 'INPUT_CHANGED: ' + n
        manifests[name] = sha(p)
    return manifests


def generate_loader_tb(enable):
    assert enable in (0, 1)
    p = ROOT / 'sim/bsp_workflow/tb/tb_applications.v'
    tb = p.read_text(encoding='utf-8')
    old = '        check(user_aw==user_w && user_aw+user_ar<=req_count+if_reqs && req_count+if_reqs-user_aw-user_ar<=1,"Pango transaction conservation");'
    assert tb.count(old) == 1, 'original conservation assertion changed'
    tb = tb.replace(old, '        line_finish();', 1)
    needle = '    localparam real TBIT=1.0e9/115200.0;'
    assert tb.count(needle) == 1
    extra = (f'    localparam integer LINE_CHECK_ENABLE={enable};\n'
             f'    defparam dut.g_ddr.u_ddr_bridge.INST_LINE_BUFFER_ENABLE={enable};\n')
    tb = tb.replace(needle, extra + needle, 1)
    assert tb.count('endmodule') == 1
    checker = (HERE / 'loader_traffic_check.svh').read_text(encoding='utf-8')
    tb = tb.replace('endmodule', checker + '\nendmodule', 1)
    return tb


def loader(folder, application, enable):
    sys.path.insert(0, str(ROOT / 'sim/cpu_performance_2b'))
    import run as perf
    from check_output import check
    perf.CAND = ROOT / 'myriscv'
    m = perf.base.module(ROOT / 'sim/bsp_workflow/run.py', 'line_checked_bsp')
    m.old.SOURCES = [perf.source(p) for p in m.old.SOURCES]
    generated = folder / 'generated'
    generated.mkdir()
    tbpath = generated / 'tb_applications_checked.sv'
    tbpath.write_text(generate_loader_tb(enable), encoding='utf-8')

    def manifest(name):
        base = ('tests/bsp_workflow/build' if name in ('hello', 'crc32')
                else 'tests/cpu_performance_2b/build/measure_20261010_c')
        return ROOT / base / name / 'manifest.json'

    def parser(info, data):
        if info['kind'] != 'coremark':
            return m.parse_output(info, data)
        result = check(info, data)
        return dict(result, **result['crc'])

    code = inspect.getsource(m.main)
    code, n = re.subn(r'    folder=ROOT/f[^\n]+', '    folder=candidate_folder/"application"', code, count=1)
    assert n == 1
    needle = "sources=old.SOURCES[:-1]+[HERE/'tb/tb_applications.v']"
    assert code.count(needle) == 1
    code = code.replace(needle, 'sources=old.SOURCES[:-1]+[checked_tb]', 1)
    namespace = dict(m.__dict__, manifest=manifest, protected=perf.protect,
                     parse_output=parser, candidate_folder=folder, checked_tb=tbpath)
    exec(compile(code, '<checked_loader_entry>', 'exec'), namespace)
    sys.argv = ['run.py', '--application', application, '--tag', folder.name]
    namespace['main']()
    app = folder / 'application'
    result = json.loads((app / 'results.json').read_text())
    assert result['status'] == 'SAME_LOADER_APPLICATION_SIM_PASS'
    assert result['protected_unchanged'] and result['inputs_unchanged']
    assert result['input_sha256'][tbpath.relative_to(ROOT).as_posix()] == sha(tbpath)
    transcript = (app / 'modelsim.log').read_text(errors='replace')
    matches = re.findall(r'CHECK: LINE_LEDGER enable=(\d+) IF=(\d+) hit=(\d+) miss=(\d+) IF_rsp=(\d+) data=(\d+) data_rsp=(\d+) AR_IF=(\d+) AR_DATA=(\d+) AW=(\d+) R=(\d+) W=(\d+) pending=(\d+)', transcript)
    assert len(matches) == 1, 'independent ledger must finish exactly once'
    fields = 'enable if_requests hits misses if_responses data_requests data_responses ar_if ar_data aw r w pending'.split()
    ledger = dict(zip(fields, map(int, matches[0])))
    assert ledger['enable'] == enable and ledger['if_requests'] == ledger['hits']+ledger['misses']
    assert ledger['hits'] > 0 if enable else ledger['hits'] == 0
    assert ledger['aw'] == ledger['w'] and ledger['data_requests'] == ledger['data_responses']
    assert ledger['pending'] in (0, 1)
    assert re.search(r'APP:.*ecalls=1 irqs=0', transcript), 'original final trap check and timer summary missing'
    return dict(application=application, buffer_enable=enable, ledger=ledger,
                application_result=result['application_result'],
                generated_tb_sha256=sha(tbpath), original_tb_sha256=sha(ROOT / 'sim/bsp_workflow/tb/tb_applications.v'),
                original_final_checks_executed=True, board_result='NOT_TESTED',
                performance_evidence=False, transport='BYTE_TRANSPORT_REAL_MMIO_FIFO')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag', required=True)
    p.add_argument('--suite', choices=('compare', 'loader'), required=True)
    p.add_argument('--baseline-tag', default='ds_line_resume_20261011_001434_phy_base')
    p.add_argument('--optimized-tag', default='ds_line_resume_20261011_001434_phy_opt')
    p.add_argument('--application', choices=APPLICATIONS)
    p.add_argument('--buffer-enable', type=int, choices=(0, 1), default=1)
    a = p.parse_args()
    assert all(re.fullmatch('[a-z0-9_-]+', t) for t in (a.tag, a.baseline_tag, a.optimized_tag))
    before = require_inputs()
    folder = HERE / 'build' / a.tag
    folder.mkdir(parents=True, exist_ok=False)
    result = dict(status='RUNNING', suite=a.suite, simulation_started=False, pds_started=False,
                  serial_opened=False, board_result='NOT_TESTED', manifests=before)
    try:
        if a.suite == 'compare':
            datasets = [HERE / 'build' / t for t in (a.baseline_tag, a.optimized_tag)]
            paths = set()
            for dataset in datasets:
                paths.update(dataset.glob('*.json'))
                paths.update(dataset.joinpath('micro').glob('*'))
                paths.update(dataset.joinpath('compile').glob('*.log'))
                paths.update(dataset.joinpath('compile').glob('*.sv'))
                paths.update(dataset.joinpath('compile').glob('ddr3_mem.v'))
                paths.update(p for p in dataset.joinpath('compile/source_snapshot').rglob('*') if p.is_file())
            evidence = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths if p.is_file()}
            assert evidence, 'missing comparison evidence'
            result['evidence_sha256'] = evidence
            m = load_module(HERE / 'compare_micro.py', 'line_micro_compare')
            original = json.loads((HERE / 'input_manifest.json').read_text())
            result['comparison'] = m.compare(HERE / 'build' / a.baseline_tag,
                HERE / 'build' / a.optimized_tag, ORIGINAL_HASH,
                original['baseline_bridge_sha256'], original['optimized_bridge_sha256'])
        else:
            assert a.application
            result['simulation_started'] = True
            result['loader'] = loader(folder, a.application, a.buffer_enable)
        result['status'] = 'INST_LINE_BUFFER_ADAPTED_CHECK_PASS'
    except BaseException as error:
        result.update(status='FAIL', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        try:
            assert require_inputs() == before
            if a.suite == 'compare':
                assert all(sha(ROOT / n) == h for n, h in result.get('evidence_sha256', {}).items()), 'comparison evidence changed'
            result['inputs_unchanged'] = True
        except BaseException:
            result.update(status='INPUT_CHANGED', inputs_unchanged=False)
            raise
        finally:
            (folder / 'adapted_check_receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    print('RESULT: PASS adapted check', a.suite, folder, flush=True)


if __name__ == '__main__':
    main()
