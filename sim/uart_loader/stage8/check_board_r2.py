"""Independently validate stage8 board raw frames with struct/zlib, then archive."""
from pathlib import Path
import argparse, hashlib, json, struct, sys, zlib
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/ack_nack_stage8'))
from cases import cases, CRC
EXPECTED_IMAGE={'loader.elf':'49744ef735f2c14461594969004641f318f62991589aadf2209f9e15cf6de178',
 'loader_rom.dat':'21a590346a9a433cade6a4e85c34829620f86ae8ea0238b7be514ff78fa2376a',
 'loader_ram.dat':'59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify(path):
    log=json.loads(path.read_text(encoding='utf8'))
    planned=cases(uart_faults=False)
    assert log['status']=='STAGE8_HOST_INJECTABLE_BOARD_PASS' and log['board_result']=='PASS_HOST_INJECTABLE_ONLY'
    assert log['image_sha256']==EXPECTED_IMAGE and len(log['records'])==108
    ack=nack=crc=0
    for c,r in zip(planned,log['records']):
        for key in ['name','tx_hex','cmd','seq','status']: assert r[key]==c[key],f'case metadata: {c["name"]}/{key}'
        assert r['result']=='PASS' and not r.get('extra_rx_hex')
        raw=bytes.fromhex(r['rx_hex']);assert len(raw)==60
        h=struct.unpack('<4sBBH6I',raw[:32]);p=struct.unpack('<6I',raw[32:56])
        assert h==(b'RVLD',1,0x80,0,c['seq'],0 if c['cmd']==0x10 else 0x40000000,24,61440,0,zlib.crc32(raw[:28]))
        accepted=64 if c['cmd'] in (0x10,0x11,0x12) and c['status']==0 else 0
        actual=CRC if c.get('crc_read') else 0
        assert p==(c['status'],c['cmd'],accepted,actual,3,256),f'payload {c["name"]}'
        assert struct.unpack('<I',raw[56:])[0]==zlib.crc32(raw[32:56])
        assert 0<=r['seconds']<5
        if c['name']=='bad_header_crc': assert r['seconds']>=.095
        if c.get('negative') and c['status']==0x8004: assert r['seconds']>=.195
        decoded=r['decoded']
        assert decoded['status']==p[0] and decoded['sequence']==h[4] and decoded['accepted_bytes']==p[2] and decoded['actual_ddr_crc']==p[3]
        nack+=c['status']!=0;ack+=c['status']==0;crc+=c.get('crc_read',False) and c['status']==0
    assert (ack,nack,crc)==(73,35,37)
    return dict(result='PASS_HOST_INJECTABLE_ONLY',evidence=path.name,sha256=sha(path),frames=108,ack_count=ack,nack_count=nack,
                crc_ack_count=crc,negative_cases=35,raw_frames_checked_with='independent struct/zlib',
                uart_frame_error_board='NOT_TESTED',uart_overflow_board='NOT_TESTED',stage8_full_board_result='NOT_COMPLETE',
                downloaded_bitstream_identity=log.get('downloaded_bitstream_identity'))
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('log',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=verify(args.log)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf8') as f: f.write(json.dumps(result,indent=2)+'\n')
    archive=args.output.with_name(args.output.stem+'_verified.json')
    with archive.open('xb') as f:f.write(args.log.read_bytes())
    print('RESULT: PASS',result['frames'],'raw board responses; host-injectable only')
if __name__=='__main__':
    try:main()
    except Exception as e:print('RESULT: FAIL board verification:',e,file=sys.stderr);sys.exit(1)
