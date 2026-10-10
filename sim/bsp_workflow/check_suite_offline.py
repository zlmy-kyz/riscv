"""Test ten-round audit structure using explicitly offline logs and a mocked single-run verifier."""
from pathlib import Path
from unittest.mock import patch
import copy,datetime,json,sys
import check_ten
from check_board import ROOT,sha
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
from suite import SEQUENCE
from upload import BIT
folder=ROOT/'sim/bsp_workflow/build/suite_fixtures3';assert not folder.exists();folder.mkdir()
identity=dict(path=BIT.as_posix(),sha256=sha(BIT));short={};records=[]
for i,name in enumerate(SEQUENCE,1):
    path=folder/f'round_{i:02}_{name}.json';manifest=ROOT/f'tests/bsp_workflow/build/{name}/manifest.json'
    raw=dict(fixture_round=i,evidence_origin='OFFLINE_FIXTURE_NOT_BOARD',manifest_path=manifest.as_posix(),records=[dict(seq=1,cmd=1,received=0,complete=0,verified=0)])
    if name.endswith('_60'):raw['crc_prerequisite']=dict(path=short[name.rsplit('_',1)[0]].as_posix())
    if name.endswith('_1'):short[name.rsplit('_',1)[0]]=path
    path.write_text(json.dumps(raw))
    start=datetime.datetime(2026,10,10,0,i,0,tzinfo=datetime.timezone.utc).isoformat()
    end=datetime.datetime(2026,10,10,0,i,30,tzinfo=datetime.timezone.utc).isoformat()
    records.append(dict(round=i,application=name,result='PASS',user_KEY0_confirmation=True,start_utc=start,end_utc=end,log_path=path.as_posix(),log_sha256=sha(path)))
journal=dict(status='AWAITING_AUDIT',evidence_origin='USER_OPERATED_ACTUAL_SERIAL_SUITE',sequence=list(SEQUENCE),records=records,bitstream_rebuilt=False)
save=lambda j:(folder/'suite.json').write_text(json.dumps(j))
def mocked_verify(path):
    raw=json.loads(path.read_text());assert raw['evidence_origin']=='OFFLINE_FIXTURE_NOT_BOARD'
    manifest=Path(raw['manifest_path']);info=json.loads(manifest.read_text())
    return dict(application_info=info,manifest_sha256=sha(manifest),successful_bitstream_identity=identity,gate_sha256='offline-gate',run_count=1,responses=1,application=dict(formal_benchmark=info['iterations']==60))
checks=[]
def audit(j):
    save(j)
    with patch.object(check_ten,'verify',side_effect=mocked_verify):return check_ten.verify_ten(folder)
assert audit(journal)['successful_rounds']==10
checks.append(dict(name='ten_round_structure_accepts_valid_mock',result='PASS'))
for name,edit in [
    ('nine_rounds',lambda j:j['records'].pop()),
    ('missing_KEY0_confirmation',lambda j:j['records'][3].update(user_KEY0_confirmation=False)),
    ('wrong_application_order',lambda j:j['records'][2].update(application='hello')),
    ('reused_log',lambda j:j['records'][4].update(log_path=j['records'][0]['log_path'])),
    ('wrong_log_hash',lambda j:j['records'][0].update(log_sha256='0'*64)),
    ('time_order',lambda j:j['records'][4].update(start_utc=j['records'][0]['start_utc'])),
    ('unfinished_suite',lambda j:j.update(status='RUNNING')),
    ('bitstream_rebuilt',lambda j:j.update(bitstream_rebuilt=True)),
]:
    changed=copy.deepcopy(journal);edit(changed)
    try:audit(changed)
    except AssertionError:checks.append(dict(name=name,result='PASS'));continue
    raise AssertionError('did not reject '+name)
save(journal)
for name,index,change in [('duplicate_raw_log',4,lambda r:json.loads((folder/'round_01_hello.json').read_text())),
                          ('wrong_formal_CRC_prerequisite',8,lambda r:{**r,'crc_prerequisite':dict(path=(folder/'round_03_performance_1.json').as_posix())})]:
    path=Path(journal['records'][index]['log_path']);original=path.read_bytes()
    raw=change(json.loads(path.read_text()));path.write_text(json.dumps(raw));changed=copy.deepcopy(journal);changed['records'][index]['log_sha256']=sha(path)
    try:audit(changed)
    except AssertionError:checks.append(dict(name=name,result='PASS'))
    else:raise AssertionError('did not reject '+name)
    finally:path.write_bytes(original)
save(journal)
result=dict(status='UNIFIED_BSP_SUITE_OFFLINE_PASS',evidence_origin='MOCKED_OFFLINE_NOT_BOARD',count=len(checks),checks=checks,serial_opened=False)
with (folder.parent/'pc_suite_v3.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print('RESULT: PASS',len(checks),'offline suite checks; no actual board evidence')
