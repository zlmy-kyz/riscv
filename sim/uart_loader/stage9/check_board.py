"""Independent struct/zlib board audit; plans and offline fixtures never count as board."""
from pathlib import Path
import argparse,hashlib,json,math,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[3]
TOOLS=ROOT/'tools/uart_loader/candidates/random_stage9'
sys.path.insert(0,str(TOOLS))
from acceptance import board_cases
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def verify(path,check_gate=True):
    log=json.loads(Path(path).read_text(encoding='utf8'))
    assert log.get('evidence_origin') not in ('OFFLINE_FIXTURE_NOT_BOARD','OFFLINE_PLAN_NOT_BOARD') or not check_gate
    assert log['status']=='STAGE9_DIAGNOSTIC_BOARD_PASS' and log['board_result']=='PASS_RANDOM_DIAGNOSTIC_ONLY'
    assert log['port']=='COM11' and log['baud']==115200 and log['no_automatic_retry'] is True and log['retry_count']==0
    assert log['formal_load_verify_run_implemented'] is False and log['random_execute'] is False
    assert log['crc_errors']==log['uart_errors']==0
    directory=ROOT/'sim/uart_loader/build/random_stage9/corpus/board'
    plan,cases=board_cases(directory)
    assert log['corpus_sha256']==sha(directory/'manifest.json') and log['seed']==plan['seed']
    assert log['planned_images']==log['completed_images']==plan['image_count']==1000
    assert log['planned_payload_bytes']==log['payload_bytes']==plan['payload_bytes']
    assert log['planned_frames']==log['frames']==len(log['records'])==len(cases)
    identity=json.loads((ROOT/'tests/uart_loader/candidates/random_stage9/build/manifest.json').read_text())['sha256']
    assert log['image_sha256']==identity
    assert log['pc_input_sha256']=={p.name:sha(p) for p in sorted(TOOLS.glob('*.py'))}
    if check_gate:
        gate_path=ROOT/'sim/uart_loader/build/random_stage9/deployment_gate.json';gate=json.loads(gate_path.read_text())
        assert gate['status']=='STAGE9_SIM_PASS' and gate['image_sha256']==identity and log['gate_sha256']==sha(gate_path)
        for name,h in gate['input_sha256'].items():assert sha(ROOT/name)==h,name
    completed=0;wire_bytes=0;chunk_bytes=0;image_crcs=0;tail_crcs=0
    for c,r in zip(cases,log['records']):
        for key in ('name','tx_hex','cmd','seq','address','length','status','accepted','actual_crc','write_bytes','read_bytes'):
            assert c[key]==r[key],(c['name'],key)
        assert r['result']=='PASS' and r['extra_rx_hex']=='' and r['written_bytes']==len(bytes.fromhex(c['tx_hex']))
        assert math.isfinite(r['seconds']) and 0<=r['seconds']<5
        raw=bytes.fromhex(r['rx_hex']);assert len(raw)==60
        h=struct.unpack('<4sBBH6I',raw[:32]);p=struct.unpack('<6I',raw[32:56])
        expected_addr=c['address'] if c['cmd'] in (0x13,0x14) else 0x40000000
        accepted=c['length'] if c['cmd'] in (0x13,0x14) else 0
        assert h==(b'RVLD',1,0x80,0,c['seq'],expected_addr,24,61440,0,zlib.crc32(raw[:28]))
        assert p==(0,c['cmd'],accepted,c['actual_crc'],3,256)
        assert struct.unpack('<I',raw[56:])[0]==zlib.crc32(raw[32:56])
        d=r['decoded'];assert (d['status'],d['sequence'],d['address'],d['accepted_bytes'],d['actual_ddr_crc'],d['capabilities'],d['max_chunk'])==(p[0],h[4],h[5],p[2],p[3],p[4],p[5])
        wire_bytes+=r['written_bytes'];chunk_bytes+=c['write_bytes'];completed+=int(bool(c.get('completed_image')))
        image_crcs+=int(bool(c.get('image_end')));tail_crcs+=int(c['name'].endswith('_tail_guard'))
    assert completed==image_crcs==1000 and (completed>=1000 or log['payload_bytes']>=16*1024*1024)
    assert math.isfinite(log['seconds']) and log['seconds']>0
    assert math.isfinite(log['bytes_per_second']) and 0<log['bytes_per_second']<=11520
    return dict(status='STAGE9_DIAGNOSTIC_BOARD_VERIFIED',board_result='PASS_RANDOM_DIAGNOSTIC_ONLY',evidence=Path(path).name,
                sha256=sha(Path(path)),images=completed,image_crc_acks=image_crcs,tail_crc_acks=tail_crcs,frames=len(cases),
                payload_bytes=log['payload_bytes'],guard_write_bytes=chunk_bytes-log['payload_bytes'],tx_bytes=wire_bytes,rx_bytes=len(cases)*60,
                seed=plan['seed'],image_sha256=identity,corpus_sha256=log['corpus_sha256'],seconds=log['seconds'],
                bytes_per_second=log['bytes_per_second'],zero_error_zero_retry=True,random_execute=False,
                reset_independently_observed=False,downloaded_bitstream_identity=log.get('downloaded_bitstream_identity'))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('log',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    assert not args.output.exists()
    result=verify(args.log);copy=args.output.with_name(args.output.stem+'_verified.json');assert not copy.exists()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with copy.open('xb') as stream:stream.write(args.log.read_bytes())
    with args.output.open('x',encoding='utf8') as stream:stream.write(json.dumps(result,indent=2)+'\n')
    print('RESULT: PASS stage9 board raw evidence:',result['images'],'images;',result['frames'],'frames')

if __name__=='__main__':main()
