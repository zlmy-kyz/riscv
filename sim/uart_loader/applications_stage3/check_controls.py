"""Offline CLI prerequisite checks; prohibit all serial opens and board claims."""
from pathlib import Path
import copy,json,sys,types
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/applications_stage3'))
import upload
import check_board
OUT=ROOT/'sim/uart_loader/build/applications_stage3';resultpath=OUT/'pc_controls.json'
assert not resultpath.exists()
folder=OUT/'offline_cli';assert not folder.exists();folder.mkdir()
serial_calls=[]
def prohibited(*args,**kwargs):serial_calls.append(True);raise RuntimeError('Serial must never open in these checks')
fake=types.SimpleNamespace(Serial=prohibited)
base=dict(application_info=dict(kind='coremark',mode='performance',iterations=1),
          board_result='COREMARK_CRC_FUNCTIONAL_PASS',gate_sha256='offline-test-gate',
          successful_bitstream_identity=dict(path=upload.BIT.as_posix(),sha256=upload.sha(upload.BIT)))
checks=[]
cases=[('missing_crc_log',None)]
for name,field,value in [('wrong_mode','mode','validation'),('wrong_iterations','iterations',60)]:
    row=copy.deepcopy(base);row['application_info'][field]=value;cases.append((name,row))
for name,field,value in [('wrong_CRC_status','board_result','COREMARK_FORMAL_BOARD_PASS'),
                         ('wrong_gate','gate_sha256','wrong'),('wrong_bitstream','successful_bitstream_identity',{})]:
    row=copy.deepcopy(base);row[field]=value;cases.append((name,row))
prior=folder/'placeholder.txt';prior.write_text('offline placeholder, never an actual-board log')
for name,row in cases:
    logfile=folder/(name+'.json')
    argv=['upload.py','--application','performance_60','--log',str(logfile)]
    if row is not None:argv+=['--crc-log',str(prior)]
    with patch.object(sys,'argv',argv),patch.object(upload,'require_gate',return_value='offline-test-gate'),patch.object(check_board,'verify',return_value=row),patch.dict(sys.modules,serial=fake):
        try:upload.main()
        except AssertionError:pass
        else:raise AssertionError('Did not reject '+name)
    assert not logfile.exists() and not serial_calls
    checks.append(dict(name=name,result='PASS',serial_opened=False))
plan=folder/'plan_only.json'
with patch.object(sys,'argv',['upload.py','--application','second','--plan-only','--log',str(plan)]),patch.dict(sys.modules,serial=fake):upload.main()
assert json.loads(plan.read_text())['evidence_origin']=='OFFLINE_PLAN_NOT_BOARD' and not serial_calls
try:check_board.verify(plan)
except AssertionError:pass
else:raise AssertionError('Plan accepted as actual board evidence')
checks.append(dict(name='plan_only_rejected_as_board_evidence',result='PASS',serial_opened=False))
result=dict(status='APPLICATIONS_CLI_OFFLINE_PASS',evidence_origin='OFFLINE_FIXTURE_NOT_BOARD',checks=checks,count=len(checks),serial_opened=False)
with resultpath.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print('RESULT: PASS offline CLI controls',len(checks),'no serial')
