"""Check plans and parser metadata offline; fixtures are not EX board evidence."""
from pathlib import Path
import copy
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/perf_2b'))
import run_ex_redirect_reviewed_measurement as board
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'ready.json').exists(), 'Preserve existing readiness evidence'
r=board.require_inputs()
results={}
for app in ('performance_300','validation_300'):
    plan=json.loads((HERE/'plans'/(app+'.json')).read_text(encoding='utf-8'))
    assert not plan['serial_opened'] and plan['evidence_origin']=='OFFLINE_PLAN_NOT_BOARD'
    assert len(plan['plan'])==123 and sum(bool(x.get('run')) for x in plan['plan'])==1
    assert plan['ex_redirect_reviewed']==board.task_metadata()
    assert plan['bitstream_local_file']['sha256']==r['bitstream_sha256']
    old=ROOT/'sim/cpu_request_presample/board/task036_300_01'/(app+'.json')
    fixture=json.loads(old.read_text(encoding='utf-8'))
    assert plan['plan']==[{k:row[k] for k in expected} for expected,row in zip(plan['plan'],fixture['records'])]
    fixture['ex_redirect_reviewed']=board.task_metadata()
    fixture['bitstream_local_file']=plan['bitstream_local_file']
    out=board.verify_record(fixture)
    assert out['comparison_to_036']['cycles_delta']==0
    bad=copy.deepcopy(fixture)
    bad['application']['parsed']['counters']['cycles']+=1
    try:
        board.verify_record(bad)
    except (AssertionError,ValueError):
        pass
    else:
        raise AssertionError('corrupt counters accepted')
    bad=copy.deepcopy(fixture)
    bad['bitstream_local_file']['sha256']='0'*64
    try:
        board.verify_record(bad)
    except ValueError:
        pass
    else:
        raise AssertionError('wrong artifact accepted')
    results[app]=dict(responses=123,run_count=1,serial_opened=False,transport_plan_equals_036=True,
        plan_sha256=sha(HERE/'plans'/(app+'.json')),
        relabelled_036_fixture_only=dict(source_sha256=sha(old),zero_delta=True,corrupt_counter_rejected=True,
            wrong_artifact_rejected=True,is_EX_board_evidence=False))
tools=[ROOT/'tools/uart_loader/candidates/perf_2b'/p for p in
       ('run_ex_redirect_reviewed_measurement.py','run_ex_redirect_reviewed_measurements.ps1')]
ready=dict(status='EX_REVIEWED_BOARD_TOOL_READY_NOT_BOARD_OR_FULL_CPU_FUNCTIONAL_PASS',
    review_sha256=sha(HERE/'review.json'),tool_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in tools},
    plans=results,clock_hz=93750000,serial_opened=False,RTL_modified=False,HDL_started=False,PDS_started=False)
(HERE/'ready.json').write_text(json.dumps(ready,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'status':ready['status'],'modes':len(results),'serial_opened':False}))
