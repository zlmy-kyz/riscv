"""Independent raw-frame audit for diagnostic stage8 board logs; archives new copies."""
from pathlib import Path
import argparse,hashlib,json,math,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[3]
TOOLS=ROOT/'tools/uart_loader/candidates/uart_fault_stage8_diag'
sys.path.insert(0,str(TOOLS))
from cases import board_cases,CRC
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def verify(path,check_gate=True):
    log=json.loads(path.read_text(encoding='utf8'));mode=log['mode'];assert mode in ('all','faults')
    assert log['status']=='STAGE8_DIAGNOSTIC_BOARD_PASS' and log['board_result']=='PASS_DIAGNOSTIC_CANDIDATE_ONLY'
    assert log['port']=='COM11' and log['baud']==115200 and log['no_automatic_retry'] is True
    assert log['load_verify_run_implemented'] is False
    assert log['uart_frame_error_board']=='PASS' and log['uart_overflow_board']=='PASS'
    assert log['host_matrix_board']==('PASS' if mode=='all' else 'NOT_TESTED_THIS_CANDIDATE')
    identity=json.loads((ROOT/'tests/uart_loader/candidates/uart_fault_stage8_diag/build/manifest.json').read_text(encoding='utf8'))['sha256']
    assert log['image_sha256']==identity
    for name,h in identity.items():assert sha(ROOT/'tests/uart_loader/candidates/uart_fault_stage8_diag/build'/name)==h
    assert log['input_sha256']=={p.name:sha(p) for p in sorted(TOOLS.glob('*.py'))}
    if check_gate:
        assert log.get('evidence_origin')!='OFFLINE_FIXTURE_NOT_BOARD'
        gate_path=ROOT/'sim/uart_loader/build/uart_fault_stage8_diag/deployment_gate.json';gate=json.loads(gate_path.read_text(encoding='utf8'))
        assert log['gate_sha256']==sha(gate_path) and gate['status']=='STAGE8_UART_DIAGNOSTIC_SIM_PASS' and gate['image_sha256']==identity
        for name,h in gate['input_sha256'].items():assert sha(ROOT/name)==h
    planned=board_cases(mode);assert len(log['records'])==len(planned)
    ack=nack=crc=0;flags_seen=[]
    for c,r in zip(planned,log['records']):
        for key in ('name','tx_hex','cmd','seq','status'):assert c[key]==r[key],(c['name'],key)
        assert c.get('fault',0)==r.get('fault',0)
        flags=c.get('uart_error_flags',0);assert r.get('uart_error_flags',0)==flags
        assert r['result']=='PASS' and not r.get('extra_rx_hex')
        raw=bytes.fromhex(r['rx_hex']);assert len(raw)==60
        h=struct.unpack('<4sBBH6I',raw[:32]);payload=struct.unpack('<6I',raw[32:56])
        assert h==(b'RVLD',1,0x80,0,c['seq'],0 if c['cmd']==0x10 else 0x40000000,24,61440,0,zlib.crc32(raw[:28]))
        accepted=64 if c['cmd'] in (0x10,0x11,0x12) and c['status']==0 else 0
        assert payload==(c['status'],c['cmd'],accepted,CRC if c.get('crc_read') else 0,3|(flags<<20),256),c['name']
        assert struct.unpack('<I',raw[56:])[0]==zlib.crc32(raw[32:56])
        assert math.isfinite(r['seconds']) and 0<=r['seconds']<5
        if c['name']=='bad_header_crc':assert r['seconds']>=.095
        if c.get('negative') and c['status']==0x8004:assert r['seconds']>=.195
        if flags:
            assert math.isfinite(r['seconds_since_injection']) and .095<=r['seconds_since_injection']<5
            flags_seen.append(flags)
        if c['name']=='wire_break':
            control=r['break_control'];assert control['api']=='Windows SetCommBreak/ClearCommBreak'
            assert control['set_success'] is True and control['clear_success'] is True and .002<=control['hold_seconds']<.075
        decoded=r['decoded'];assert (decoded['status'],decoded['sequence'],decoded['accepted_bytes'],decoded['actual_ddr_crc'],decoded['uart_error_flags'])==(payload[0],h[4],payload[2],payload[3],flags)
        ack+=c['status']==0;nack+=c['status']!=0;crc+=c['status']==0 and c.get('crc_read',False)
    assert flags_seen==[16,32]
    assert (ack,nack,crc)==((80,37,40) if mode=='all' else (7,2,3))
    return dict(status='STAGE8_DIAGNOSTIC_BOARD_VERIFIED',board_result='PASS_DIAGNOSTIC_CANDIDATE_ONLY',mode=mode,
                evidence=path.name,sha256=sha(path),frames=len(planned),ack_count=ack,nack_count=nack,crc_ack_count=crc,
                uart_frame_error_board='PASS',uart_overflow_board='PASS',raw_uart_flags=flags_seen,
                host_matrix_board=log['host_matrix_board'],image_sha256=identity,
                original_stage7_image_revalidated=False,reset_independently_observed=False,
                downloaded_bitstream_identity=log.get('downloaded_bitstream_identity'),
                fixed_ddr_bytes=64,load_verify_run_implemented=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('log',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=verify(args.log)
    frozen=args.output.with_name(args.output.stem+'_verified.json')
    assert not args.output.exists() and not frozen.exists()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with frozen.open('xb') as stream:stream.write(args.log.read_bytes())
    with args.output.open('x',encoding='utf8') as stream:stream.write(json.dumps(result,indent=2)+'\n')
    print('RESULT: PASS',result['frames'],'raw diagnostic responses; raw UART frame=0x10 overflow=0x20')

if __name__=='__main__':
    try:main()
    except Exception as error:print('RESULT: FAIL diagnostic board audit:',error,file=sys.stderr);sys.exit(1)
