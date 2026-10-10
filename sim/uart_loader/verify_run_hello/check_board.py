"""Independent raw combined-session audit. No serial; fixtures cannot pass."""
import argparse,hashlib,json,struct,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/verify_run_hello'))
from board_cases import board_cases
from acceptance import require_gate,HELLO


def verify(path):
    log=json.loads(path.read_text(encoding='utf-8'))
    assert log['evidence_origin']=='ACTUAL_SERIAL' and log['status']=='COMBINED_BOARD_PASS'
    assert log['board_result']=='PASS_VERIFY_RUN_DDR_HELLO' and log['retry_count']==0
    assert log['no_automatic_retry'] and log['gate_sha256']==require_gate()
    selected=board_cases();assert log['frames']==len(selected)==len(log['records'])
    runs=0
    for row,c in zip(log['records'],selected):
        assert all(row[k]==v for k,v in c.items()),c['name']
        raw=bytes.fromhex(row['rx_hex']);tx=bytes.fromhex(row['tx_hex'])
        assert row['result']=='PASS' and row['written_bytes']==len(tx) and row['extra_rx_hex']==''
        assert len(raw)==60 and raw==bytes.fromhex(c['expected_hex'])
        h=struct.unpack('<4sBBH6I',raw[:32]);d=struct.unpack('<6I',raw[32:56])
        assert h[:4]==(b'RVLD',1,0x80,0) and h[-1]==zlib.crc32(raw[:28])
        assert struct.unpack_from('<I',raw,56)[0]==zlib.crc32(raw[32:56])
        assert h[4]==c['seq'] and d[0]==c['status'] and d[1]==c['cmd']
        if c.get('run'):
            assert bytes.fromhex(row['application_rx_hex'])==HELLO;runs+=1
        else:assert row['application_rx_hex']==''
    assert runs==1 and log['program_execute'] and log['hello_received_hex']==HELLO.hex()
    return dict(status='COMBINED_ACTUAL_BOARD_VERIFIED',board_result=log['board_result'],
                raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),responses=len(selected),run_count=1,
                expected_nacks=sum(bool(c['status']&0x8000) for c in selected),hello_hex=HELLO.hex(),
                downloaded_bitstream_identity=log['downloaded_bitstream_identity'],
                reset_independently_observed=False,physical_DDR_damage_injection_on_board=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--log',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=verify(a.log);copy=a.output.with_name(a.output.stem+'_raw_verified.json')
    assert not a.output.exists() and not copy.exists()
    with copy.open('xb') as f:f.write(a.log.read_bytes())
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print('RESULT: PASS independent actual combined board audit')
