"""Independently audit actual UART application downloads; never open COM11."""
from pathlib import Path
import argparse,hashlib,json,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
from application import require_manifest,parse_output
from plan import make_plan
from upload import require_gate,BIT,sha

def verify(path):
    log=json.loads(Path(path).read_text())
    assert log['evidence_origin']=='ACTUAL_SERIAL' and log['status']=='UNIFIED_BSP_APPLICATION_BOARD_PASS'
    info=require_manifest(log['manifest_path']);assert info==log['application_info']
    assert log['manifest_sha256']==sha(Path(log['manifest_path']))
    assert log['gate_sha256']==require_gate(log['manifest_path'])
    assert log['retry_count']==0 and log['no_automatic_retry'] and log['port']=='COM11' and log['baud']==115200
    assert log['successful_bitstream_identity']==dict(path=BIT.as_posix(),sha256=sha(BIT))
    expected=make_plan(info);assert len(expected)==len(log['records'])==log['planned_responses']
    for row,want in zip(log['records'],expected):
        assert all(row[k]==v for k,v in want.items()) and row['result']=='PASS'
        tx=bytes.fromhex(row['tx_hex']);raw=bytes.fromhex(row['rx_hex'])
        assert row['written_bytes']==len(tx) and row['extra_rx_hex']==''
        assert len(raw)==60 and raw==bytes.fromhex(want['expected_hex'])
        assert struct.unpack_from('<I',raw,28)[0]==zlib.crc32(raw[:28])
        assert struct.unpack_from('<I',raw,56)[0]==zlib.crc32(raw[32:56])
    app=log['application'];assert app['result']=='PASS' and app['extra_rx_hex']==''
    parsed=parse_output(info,bytes.fromhex(app['rx_hex']),board=True,elapsed=app['seconds'])
    assert parsed==app['parsed'] and log['board_result']==parsed['status']
    if info['kind']=='coremark' and info['iterations']==60:
        prior=log['crc_prerequisite'];assert sha(Path(prior['path']))==prior['sha256']
        short=verify(Path(prior['path']))
        assert short['application_info']['kind']=='coremark' and short['application_info']['mode']==info['mode']
        assert short['application_info']['iterations']==1 and short['board_result']=='COREMARK_CRC_FUNCTIONAL_PASS'
        assert short['successful_bitstream_identity']==log['successful_bitstream_identity'] and short['gate_sha256']==log['gate_sha256']
    assert sum(bool(r.get('run')) for r in expected)==1
    return dict(status='UNIFIED_BSP_ACTUAL_BOARD_VERIFIED',board_result=parsed['status'],
                raw_sha256=sha(Path(path)),manifest_sha256=log['manifest_sha256'],
                application_info=info,application=parsed,successful_bitstream_identity=log['successful_bitstream_identity'],
                responses=len(expected),retry_count=0,run_count=1,gate_sha256=log['gate_sha256'],
                reset_independently_observed=False,JTAG_programming_independently_observed=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--log',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=verify(a.log);copy=a.output.with_name(a.output.stem+'_raw_verified.json')
    assert not a.output.exists() and not copy.exists()
    with copy.open('xb') as f:f.write(a.log.read_bytes())
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print('RESULT: PASS',result['board_result'],'independent actual-board audit')
