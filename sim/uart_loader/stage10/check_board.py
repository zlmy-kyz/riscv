"""Independent raw stage10 board audit, no serial; rejects PC fixtures."""
from pathlib import Path
import argparse,hashlib,json,math,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[3]
TOOLS=ROOT/'tools/uart_loader/candidates/load_stage10';sys.path.insert(0,str(TOOLS))
from cases import cases,PROGRAM
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def verify(path,gate_check=True,offline=False):
    log=json.loads(Path(path).read_text());selected=cases('native')
    if not offline and log.get('evidence_origin') in ('OFFLINE_FIXTURE_NOT_BOARD','OFFLINE_PLAN_NOT_BOARD'):
        raise ValueError('offline fixture/plan is not board evidence')
    assert log['status']=='STAGE10_REAL_PROGRAM_BOARD_PASS' and log['board_result']=='PASS_LOAD_ONLY_UNVERIFIED'
    assert log['port']=='COM11' and log['baud']==115200 and log['retry_count']==0 and log['no_automatic_retry'] is True
    assert log['formal_load_implemented'] is True and log['formal_verify_implemented'] is False
    assert log['run_implemented'] is False and log['program_execute'] is False and log['state']=='LOADED_UNVERIFIED'
    assert log['frames']==log['planned_frames']==len(log['records'])==len(selected)==8
    assert log['crc_errors']==log['uart_errors']==0
    info=json.loads((PROGRAM.parent/'manifest.json').read_text())
    assert log['program_bytes']==info['bytes']==383 and log['program_crc32']==info['crc32']
    assert log['program_sha256']==sha(PROGRAM)==info['bin_sha256']
    assert log['program_manifest_sha256']==sha(PROGRAM.parent/'manifest.json')
    identity=json.loads((ROOT/'tests/uart_loader/candidates/load_stage10/build/manifest.json').read_text())['sha256']
    assert log['image_sha256']==identity
    assert log['pc_input_sha256']=={p.name:sha(p) for p in sorted(TOOLS.glob('*.py'))}
    if gate_check:
        gate_path=ROOT/'sim/uart_loader/build/load_stage10/deployment_gate.json';g=json.loads(gate_path.read_text())
        assert g['status']=='STAGE10_SIM_PASS' and log['gate_sha256']==sha(gate_path)
        assert all(sha(ROOT/p)==h for p,h in g['input_sha256'].items())
    for record,case in zip(log['records'],selected):
        for key,value in case.items():assert record[key]==value,(case['name'],key)
        tx=bytes.fromhex(record['tx_hex']);raw=bytes.fromhex(record['rx_hex'])
        assert record['result']=='PASS' and record['written_bytes']==len(tx) and record['extra_rx_hex']==''
        assert math.isfinite(record['seconds']) and 0<=record['seconds']<5
        assert len(raw)==60 and raw==bytes.fromhex(case['expected_hex'])
        h=struct.unpack('<4sBBH6I',raw[:32]);p=struct.unpack('<6I',raw[32:56])
        assert h[:4]==(b'RVLD',1,0x80,0) and h[-1]==zlib.crc32(raw[:28])
        assert struct.unpack_from('<I',raw,56)[0]==zlib.crc32(raw[32:56])
        assert h[4]==case['seq'] and p[1]==case['cmd'] and p[0]==case['status']
        assert p[4]&((1<<17)|4)==0, 'No VERIFIED or RUN capability'
        assert record['decoded']==dict(sequence=h[4],address=h[5],image_crc=h[8],status=p[0],request_cmd=p[1],
                accepted_bytes=p[2],actual_ddr_crc=p[3],capabilities_and_state=p[4],max_chunk=p[5])
    assert math.isfinite(log['seconds']) and log['seconds']>0
    return dict(status='STAGE10_REAL_PROGRAM_BOARD_VERIFIED',board_result='PASS_LOAD_ONLY_UNVERIFIED',
                sha256=sha(Path(path)),responses=8,ready=2,load_ack=2,ping=3,diagnostic_ddr_crc=1,
                program_bytes=383,program_crc32=info['crc32'],program_sha256=info['bin_sha256'],
                image_sha256=identity,zero_error_zero_retry=True,state='LOADED_UNVERIFIED',program_execute=False,
                reset_independently_observed=False,downloaded_bitstream_identity=log.get('downloaded_bitstream_identity'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--first',type=Path,required=True)
    p.add_argument('--after-reset',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    first=verify(a.first);second=verify(a.after_reset)
    assert first['sha256']!=second['sha256'],'two distinct actual board rounds required'
    targets=[a.output,a.output.with_name(a.output.stem+'_first_verified.json'),a.output.with_name(a.output.stem+'_after_reset_verified.json')]
    assert all(not p.exists() for p in targets)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    for source,target in zip((a.first,a.after_reset),targets[1:]):
        with target.open('xb') as f:f.write(source.read_bytes())
    with a.output.open('x',encoding='utf8') as f:
        json.dump(dict(status='STAGE10_TWO_ROUND_BOARD_PASS',board_result='PASS_LOAD_ONLY_UNVERIFIED',
                       rounds=[first,second],program_execute=False,formal_verify_implemented=False,run_implemented=False),f,indent=2)
    print('RESULT: PASS two stage10 real program LOAD board rounds; LOADED_UNVERIFIED; no execution')
