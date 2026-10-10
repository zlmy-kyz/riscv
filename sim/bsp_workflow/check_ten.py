"""Independently verify ten actual fresh-Loader epochs; no serial or board control."""
from pathlib import Path
import argparse,json,datetime,sys
from check_board import verify,ROOT,sha
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
from suite import SEQUENCE
def verify_ten(folder):
    folder=Path(folder).resolve();journal=json.loads((folder/'suite.json').read_text())
    assert journal['status'] in ('AWAITING_AUDIT','UNIFIED_BSP_TEN_ROUND_BOARD_PASS')
    assert journal['evidence_origin']=='USER_OPERATED_ACTUAL_SERIAL_SUITE' and tuple(journal['sequence'])==SEQUENCE
    assert len(journal['records'])==10 and not journal['bitstream_rebuilt']
    runs=[];last_end=None;identity=gate=None;paths=set();hashes=set();short={}
    for i,(name,row) in enumerate(zip(SEQUENCE,journal['records']),1):
        assert row['round']==i and row['application']==name and row['result']=='PASS' and row['user_KEY0_confirmation']
        start=datetime.datetime.fromisoformat(row['start_utc']);end=datetime.datetime.fromisoformat(row['end_utc'])
        assert start<=end and (last_end is None or last_end<=start);last_end=end
        log=folder/f'round_{i:02}_{name}.json';assert log.as_posix()==row['log_path'] and sha(log)==row['log_sha256']
        assert log not in paths;paths.add(log)
        assert sha(log) not in hashes,'Duplicated raw log cannot count as another round'
        hashes.add(sha(log))
        checked=verify(log);info=checked['application_info'];raw=json.loads(log.read_text())
        expected=ROOT/f'tests/bsp_workflow/build/{name}/manifest.json'
        assert Path(raw['manifest_path']).resolve()==expected.resolve() and checked['manifest_sha256']==sha(expected)
        first=raw['records'][0];assert first['seq']==1 and first['cmd']==1 and first['received']==0 and first['complete']==first['verified']==0
        if i==1:identity=checked['successful_bitstream_identity'];gate=checked['gate_sha256']
        assert checked['successful_bitstream_identity']==identity and checked['gate_sha256']==gate and checked['run_count']==1
        if name.endswith('_60'):
            mode=name.rsplit('_',1)[0];assert raw['crc_prerequisite']['path']==short[mode].as_posix()
            assert checked['application']['formal_benchmark']
        if name.endswith('_1'):short[name.rsplit('_',1)[0]]=log
        runs.append(dict(round=i,application_name=name,**checked))
    baseline=json.loads((ROOT/'sim/uart_loader/board/verify_run_hello_board_result.json').read_text())
    assert identity==baseline['downloaded_bitstream_identity']
    return dict(status='UNIFIED_BSP_TEN_ROUND_ACTUAL_BOARD_VERIFIED',runs=runs,successful_rounds=10,
                responses=sum(r['responses'] for r in runs),successful_RUN_count=10,successful_bitstream_identity=identity,
                same_BSP=True,gate_sha256=gate,retry_count=0,unexpected_extra_rx_bytes=0,
                reset_evidence='User KEY0 confirmations plus ten SEQ1 fresh-state PING checks; KEY0 not independently observed',
                source_journal_sha256=sha(folder/'suite.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();result=verify_ten(a.directory)
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print('RESULT: PASS ten fresh Loader epochs; unified Hello/CRC32/CoreMark; same bitstream')
