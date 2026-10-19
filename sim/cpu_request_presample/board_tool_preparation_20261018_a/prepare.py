"""Prepare Task036 user-run trial from Task035's transport; offline QA only."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TOOLS = ROOT/'tools/uart_loader/candidates/perf_2b'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare():
    py = (TOOLS/'run_task035_measurement.py').read_text(encoding='utf-8')
    py = py.replace('035','036').replace('034','035')
    replacements = {
        'sim/cpu_dual_read/rdata_timing_repair_20261018_a/after_manifest.json':
            'sim/cpu_request_presample/timing_repair_20261018_a/after_manifest.json',
        'sim/cpu_store_ack/board/review_20261017_01/board_review.json':
            'sim/cpu_dual_read/board/review_20261018_01/board_review.json',
        'sim/cpu_store_ack/board/coremark_store_ack_300_01/':
            'sim/cpu_dual_read/board/task035_300_01/',
        '1abf54fe01fb76659943fd14818154cfffe1bde23cd9f996b711b185452afe67':
            '4d628cfa4e9f68e18671b1e42399ceaddcb2ddabeca3d9b505e5d632821db589',
        'TASK035_FIXED_P300_V300_BOARD_RAW_PASS_HDL_NOT_RUN':
            'TASK035_FIXED_P300_V300_APPLICATION_BOARD_RAW_PASS_HDL_NOT_RUN',
        'USER_REQUESTED_TASK036_FUNCTION_AND_ACTUAL_PERFORMANCE_BOARD_ACCEPTANCE':
            'USER_DIRECT_TASK036_BOARD_REQUEST_WITH_DYNAMIC_AND_POST_REPAIR_TIMING_NOT_REVIEWED',
        'EXISTING_REPORT_ALL_CONSTRAINTS_MET_93_75MHZ_WNS_PLUS_0_151NS_NOT_INDEPENDENT_REBUILD':
            'POST_REPAIR_NOT_REVIEWED_LAST_REVIEW_PRE_REPAIR_WNS_MINUS_0_034NS_USER_DIRECT_BOARD_REQUEST',
        'performance_cycles=227315593,validation_cycles=227420763':
            'performance_cycles=226659014,validation_cycles=226664360',
        '同一个036位流': '同一个最终036冲突CE修复版位流',
    }
    for old,new in replacements.items():
        assert old in py, old
        py = py.replace(old,new)
    # Record the purpose without promising a frequency/cycle gain.
    old = "        dynamic_RTL_functional_simulation='NOT_RUN',"
    assert py.count(old) == 1
    py = py.replace(old, old+"\n        clock_hz=93750000, frequency_changed=False,\n        expected_cycle_change='NONE_FROM_FIELD_PRESAMPLING',")
    with (TOOLS/'run_task036_measurement.py').open('x', encoding='utf-8', newline='\n') as f:
        f.write(py)
    ps = (TOOLS/'run_task035_measurements.ps1').read_text(encoding='utf-8').replace('035','036')
    ps = ps.replace('sim/cpu_dual_read/board/task036_300_01',
                    'sim/cpu_request_presample/board/task036_300_01')
    with (TOOLS/'run_task036_measurements.ps1').open('x', encoding='utf-8', newline='\n') as f:
        f.write(ps)
    print('Task036 tools created; serial not opened')

def qa():
    if (HERE/'ready.json').exists():
        raise RuntimeError('preserve existing readiness evidence')
    argv = ['C:/python/python.exe','-B',str(TOOLS/'run_task036_measurement.py'),'--check-inputs']
    check = subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,check=True)
    (HERE/'check_inputs.log').write_text(check.stdout+check.stderr,encoding='utf-8')
    command = ['powershell.exe','-NoProfile','-File',str(TOOLS/'run_task036_measurements.ps1'),
               '-Port','COM9','-LogDirectory',str(HERE/'plans'),'-PlanOnly']
    result = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,check=True)
    (HERE/'plan_only.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    sys.path.insert(0,str(TOOLS))
    import run_task036_measurement as tool
    rows = tool.require_inputs()
    verified = {}
    for name in ('performance_300','validation_300'):
        p = HERE/'plans'/(name+'.json')
        plan = json.loads(p.read_text(encoding='utf-8'))
        assert plan['serial_opened'] is False and plan['evidence_origin'] == 'OFFLINE_PLAN_NOT_BOARD'
        assert len(plan['plan']) == 123 and sum(bool(r.get('run')) for r in plan['plan']) == 1
        assert plan['task036'] == tool.task_metadata()
        original = ROOT/'sim/cpu_dual_read/board/task035_300_01'/(name+'.json')
        source = json.loads(original.read_text(encoding='utf-8'))
        assert plan['plan'] == [{k:r[k] for k in expected} for expected,r in zip(plan['plan'],source['records'])]
        fixture = copy.deepcopy(source)
        fixture.pop('task035')
        fixture['task036'] = tool.task_metadata()
        out = tool.verify_record(fixture)
        assert out['comparison_to_035']['cycles_delta'] == 0
        assert out['comparison_to_035']['time_change_percent'] == 0
        broken = copy.deepcopy(fixture)
        broken['application']['parsed']['counters']['cycles'] += 1
        rejected = False
        try:
            tool.verify_record(broken)
        except (AssertionError, ValueError):
            rejected = True
        assert rejected
        verified[name] = dict(plan_sha256=sha(p),responses=123,run_count=1,serial_opened=False,
            bin_sha256=plan['application_info']['bin_sha256'] if 'bin_sha256' in plan['application_info'] else
                sha(ROOT/plan['application_info']['bin_path']),transport_equals_035=True,
            synthetic_relabelled_035_parser_fixture_only=dict(source_sha256=sha(original),
                zero_baseline_delta=True,corrupt_counter_rejected=True,is_task036_board_evidence=False))
    ready = dict(status='TASK036_DIRECT_BOARD_TOOL_READY_NOT_TIMING_OR_BOARD_PASS', date='2026-10-18',
        design_sha256=tool.PINNED,static_manifest_sha256=sha(tool.IDENTITY),
        baseline_review_sha256=sha(tool.BASELINE),source_identity_entries=len(rows),
        dynamic_RTL_simulation='NOT_RUN',post_repair_timing='NOT_REVIEWED_USER_DIRECT_BOARD_REQUEST',
        full_protocol_reset_acceptance='NOT_CLAIMED',per_round_reprogram_same_final036_bitstream=True,
        clock_hz=93750000,frequency_changed=False,
        tool_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in
            (TOOLS/'run_task036_measurement.py',TOOLS/'run_task036_measurements.ps1')},
        commands=[dict(argv=argv,cwd=str(ROOT),exit_code=check.returncode),
                  dict(argv=command,cwd=str(ROOT),exit_code=result.returncode)],
        plans_and_offline_QA=verified,serial_opened=False,RTL_modified=False)
    (HERE/'ready.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':ready['status'],'plans':len(verified),'serial_opened':False}))

if __name__ == '__main__':
    {'prepare':prepare,'qa':qa}[sys.argv[1]]()
