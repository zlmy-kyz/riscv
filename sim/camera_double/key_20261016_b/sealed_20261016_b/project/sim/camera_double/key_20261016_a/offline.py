"""Host/parser negative checks and sealed reference identities only. Never creates board/HDL evidence."""
import argparse,json,sys,zlib
from pathlib import Path
from seal import HERE,ROOT,sha,save
sys.path.insert(0,str(ROOT/'tools/camera_uart'))
import double100 as host
from prepare import frame
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=HERE/'preparation/offline_b');a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    g=json.loads((HERE/'generated/golden.json').read_text())
    for k,v in g.items():
        kind,p=k.split(':');data=frame(int(p),64,8 if kind=='soc' else 128)
        assert data==(HERE/f'generated/{kind}_{p}.bin').read_bytes() and len(data)==v['bytes'] and f'{zlib.crc32(data)&0xffffffff:08x}'==v['CRC']
    frames=[host.HEADER,'SENSOR_ID=00005640 CONFIG=OK','DB_READY']
    for i in range(1,102):
        frames.append(f'DB_{"FRAME" if i<=100 else "TAIL"} BUFFER={(i-1)%2} SEQ={i} CRC_CAPTURE=12345678 CRC_CPU=12345678 MATCH=1 ERROR=00000000 WAIT_TICKS=100 READ_TICKS=200 WAIT_CYCLES={i}')
    frames.append('DB_END RESULT=PASS SUCCESS=100 TAIL=1 TOTAL_TICKS=40000 WAIT_SUM=10000 WAIT_MIN=100 WAIT_MAX=100 READ_SUM=20000 READ_MIN=200 READ_MAX=200 WAIT_CYCLES=101')
    rows,stats=host.parse(frames);assert len(rows)==101 and stats['distinct_crcs']==1
    outcomes=dict(full100_plus_tail_same_CRC_allowed=True)
    mutations={
        'CRC_mismatch':('CRC_CPU=12345678','CRC_CPU=00000000'),
        'duplicate_sequence':('SEQ=2 ','SEQ=1 '),
        'wrong_ABI':('ID=43414d02','ID=43414d01'),
        'error_status':('ERROR=00000000','ERROR=00000002'),
        'bad_statistics':('WAIT_SUM=10000','WAIT_SUM=9999'),
        'bad_geometry':('WIDTH=1280','WIDTH=64'),
        'zero_duration':('WAIT_TICKS=100 ','WAIT_TICKS=0 '),
    }
    for n,(a,b) in mutations.items():
        changed='\n'.join(frames).replace(a,b,1).splitlines()
        try:host.parse(changed)
        except ValueError:outcomes[n]='REJECTED'
        else:raise AssertionError(n)
    # Independent raw fixture exercises Loader, RX/TX, CSV and origin checks without opening serial.
    fixture=out/'synthetic';fixture.mkdir();binary=bytes(range(64));(fixture/'application.bin').write_bytes(binary)
    m=dict(bytes=len(binary),bin_path=(fixture/'application.bin').relative_to(ROOT).as_posix(),bin_sha256=sha(fixture/'application.bin'),crc32=zlib.crc32(binary)&0xffffffff)
    save(fixture/'manifest.json',m);plans=host.loader_plan(m);rx=bytearray();tx=bytearray();ledger=[]
    for p in plans:
        ledger.append(dict(name=p['name'],tx_offset=len(tx),rx_offset=len(rx)));tx+=bytes.fromhex(p['tx_hex']);rx+=bytes.fromhex(p['expected_hex'])
    go=len(tx);tx+=b'G';rx+=('\n'.join(frames)+'\n').encode()
    (fixture/'uart.rx.bin').write_bytes(rx);(fixture/'uart.tx.bin').write_bytes(tx)
    import csv
    with (fixture/'frames.csv').open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    r=dict(status='ABI2_UART100_DATA_PASS',evidence_origin='OFFLINE_SYNTHETIC_TEST',serial_opened=False,application=m,
           manifest_sha256=sha(fixture/'manifest.json'),loader_records=ledger,frames=rows,statistics=stats,go_tx_offset=go)
    host.save(fixture,r);replay=host.verify(fixture,'OFFLINE_SYNTHETIC_TEST');assert replay['status']=='ABI2_OFFLINE_REPLAY_PASS'
    try:host.verify(fixture)
    except ValueError:outcomes['synthetic_as_board']='REJECTED'
    else:raise AssertionError('synthetic promoted to board')
    rx[10]^=1;(fixture/'uart.rx.bin').write_bytes(rx)
    try:host.verify(fixture,'OFFLINE_SYNTHETIC_TEST')
    except ValueError:outcomes['corrupt_original_RX']='REJECTED'
    else:raise AssertionError('raw corruption accepted')
    save(out/'review.json',dict(status='ABI2_REFERENCE_AND_HOST_OFFLINE_PASS',patterns=len(g),outcomes=outcomes,
         evidence_origin='OFFLINE_SYNTHETIC_TEST',serial_opened=False,HDL=False,source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [HERE/'prepare.py',Path(__file__),ROOT/'tools/camera_uart/double100.py']}))
    print(json.dumps(dict(status='ABI2_REFERENCE_AND_HOST_OFFLINE_PASS',patterns=len(g),checks=outcomes)))
if __name__=='__main__':main()
