"""Offline negative fixtures and generated-TB preservation checks; no HDL tools."""
from pathlib import Path
import argparse
import ast
import copy
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare_micro as compare
import resume_checks as resume


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag', required=True)
    a = p.parse_args()
    assert resume.re.fullmatch('[a-z0-9_-]+', a.tag)
    before = resume.require_inputs()
    out = HERE / 'build' / a.tag
    assert not out.exists()
    checks = {}
    for name in ('compare_micro.py', 'resume_checks.py', 'check_adapters.py'):
        ast.parse((HERE / name).read_text())
        checks['AST_' + name] = 'PASS'
    original = (resume.ROOT / 'sim/bsp_workflow/tb/tb_applications.v').read_text(encoding='utf-8')
    checker = (HERE / 'loader_traffic_check.svh').read_text(encoding='utf-8')
    old = '        check(user_aw==user_w && user_aw+user_ar<=req_count+if_reqs && req_count+if_reqs-user_aw-user_ar<=1,"Pango transaction conservation");'
    generated = {}
    for enable in (0, 1):
        tb = resume.generate_loader_tb(enable)
        restored = tb.replace(checker + '\nendmodule', 'endmodule', 1)
        header = (f'    localparam integer LINE_CHECK_ENABLE={enable};\n'
                  f'    defparam dut.g_ddr.u_ddr_bridge.INST_LINE_BUFFER_ENABLE={enable};\n')
        restored = restored.replace(header, '', 1).replace('        line_finish();', old, 1)
        assert restored == original, 'unexpected change to original TB'
        assert tb.count('line_finish();') == 1
        generated[enable] = tb
        checks['original_TB_preserved_enable_' + str(enable)] = 'PASS'
    root = HERE / 'build'
    meta = json.loads((HERE / 'input_manifest.json').read_text())
    b = compare.read_run(root / 'ds_line_resume_20261011_001434_phy_base', 'baseline', resume.ORIGINAL_HASH, meta['baseline_bridge_sha256'])
    o = compare.read_run(root / 'ds_line_resume_20261011_001434_phy_opt', 'optimized', resume.ORIGINAL_HASH, meta['optimized_bridge_sha256'])
    args = [b['trace'], o['trace'], b['info']['cases'], b['timers'], o['timers'], b['binary']]
    verified = compare.verify_trace_pair(*args)
    assert len(verified['boundary_attribution_changes']) == 8
    checks['real_physical_trace_positive'] = 'PASS'

    def reject(name, edit):
        values = copy.deepcopy(args)
        edit(values)
        try:
            compare.verify_trace_pair(*values)
        except AssertionError as error:
            checks[name] = dict(status='REJECTED_AS_REQUIRED', reason=str(error))
        else:
            raise AssertionError('invalid fixture accepted: ' + name)

    reject('dropped_instruction', lambda v: v[1].pop(40))
    reject('changed_PC', lambda v: v[1][40].update(pc='400000ac'))
    reject('changed_write_enable', lambda v: v[1][40].update(write='0'))
    reject('changed_destination', lambda v: v[1][40].update(rd='11'))
    reject('changed_non_timer_value', lambda v: v[1][40].update(value='00000002'))
    reject('timer_value_not_equal_accepted_CYCLE', lambda v: v[1][39].update(value='00000001'))
    reject('interior_window_change', lambda v: v[1][40].update(window='0'))
    reject('boundary_attributed_to_wrong_window', lambda v: v[1][38].update(window='2'))
    reject('duplicate_marker_PC', lambda v: v[2][1].update(start=v[2][0]['start']))
    reject('unordered_retirement_cycle', lambda v: v[1][40].update(cycle=v[1][39]['cycle']))
    assert resume.require_inputs() == before
    out.mkdir(parents=True)
    for enable, tb in generated.items():
        (out / f'tb_enable_{enable}.sv').write_text(tb, encoding='utf-8')
    result = dict(status='INST_LINE_BUFFER_ADAPTER_OFFLINE_CHECK_PASS', checks=checks,
        manifests=before, inputs_unchanged=True, simulation_started=False, pds_started=False,
        HDL_compile_result='NOT_RUN', loader_simulation_result='NOT_RUN')
    (out / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('RESULT: PASS offline adapter checks', len(checks), '; HDL compilation and Loader simulation NOT_RUN')


if __name__ == '__main__':
    main()
