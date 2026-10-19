"""Sol read-only acceptance of one actual photo; preserve every original evidence file."""
import datetime,hashlib,json,re,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/camera_preprocess_photo'))
import run as photo
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    folder=ROOT/'sim/camera_preprocess/board/photo_20261015_01';target=folder/'sol_review.json'
    assert not target.exists(), 'preserve completed review'
    original={p.name:sha(p) for p in folder.iterdir() if p.is_file()}
    assert len(original)==14
    replay=photo.verify(folder);assert replay==load(folder/'verified.json')
    r=load(folder/'result.json');m=photo.image(photo.DEFAULT)
    assert m==load(folder/'manifest.json')==r['application']
    assert m['bin_sha256']==original['application.bin']=='8a7b1c57cce723753ff73fd6c62dd8f8a099d4f1522902bbb3bb0b4a933bb7b3'
    for name,d in r['tool_sha256'].items():assert sha(ROOT/'tools/camera_preprocess_photo'/name)==d,name
    gate=load(folder/'board_release.json');assert sha(folder/'board_release.json')==sha(HERE/'board_release.json')
    assert gate['status']=='SOL_SOFTWARE_REVIEWED_USER_AUTHORIZED_BOARD_FIRST'
    assert gate['firmware_sha256']==m['bin_sha256'] and gate['firmware_manifest_sha256']==original['manifest.json']
    assert sha(ROOT/gate['review_path'])==gate['review_sha256']
    ready=load(ROOT/gate['review_path'])
    for n,d in ready['input_sha256'].items():assert sha(ROOT/n)==d,n
    assert r['retry_count']==0 and r['serial_opened'] and r['user_KEY0_confirmation'] and not r['PDS_started']
    s=r['session'];summary=photo.SUMMARY.fullmatch(s['summary']);assert summary
    source_crc,pp_crc,cpu_crc,reread_crc=summary.groups()
    assert pp_crc==cpu_crc==reread_crc=='1ee57037' and source_crc=='cddc099b'
    source=(folder/'source.rgb565').read_bytes();actual=(folder/'actual.rgb').read_bytes();expected=(folder/'expected.rgb').read_bytes()
    # Separate literal implementation, independent of the tool's reference/byte comparison.
    independent=bytearray()
    for y in range(96):
        for x in range(96):
            sx=280+((2*x+1)*15)//4;sy=((2*y+1)*15)//4;o=2*(sy*1280+sx)
            p=source[o]+256*source[o+1];red=(p>>11)&31;green=(p>>5)&63;blue=p&31
            independent.extend((red*8+red//4,green*4+green//16,blue*8+blue//4))
    assert bytes(independent)==expected==actual and len(actual)==27648
    assert zlib.crc32(actual)&0xffffffff==int(pp_crc,16) and zlib.crc32(source)&0xffffffff==int(source_crc,16)
    claim,discard,glob,state,cycles,elapsed=photo.RELEASED.fullmatch(s['release']).groups()
    assert (int(claim),int(discard),int(glob),int(state,16))==(2,1,2,0x130)
    assert s['finish']==photo.END
    assert len(s['loader_records'])==159 and sum(x['name']=='RUN_once' for x in s['loader_records'])==1
    assert len(s['packets'])==1829
    assert (folder/'actual96.png').read_bytes()==(folder/'expected96.png').read_bytes()
    assert original=={n:sha(folder/n) for n in original}
    receipt=dict(status='CAMERA_PREPROCESS_SINGLE_PHOTO_BOARD_BYTE_ACCEPTANCE_PASS',
        reviewed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        method='Exact actual Loader/RX/TX/packet/release replay; independent integer source-to-RGB888 computation and PNG pixel checks',
        original_evidence_sha256=original,review_script_sha256=sha(__file__),raw_replay=replay,
        fixed_BIN_sha256=m['bin_sha256'],manifest_sha256=original['manifest.json'],source_tools_ELF_identity_match=True,
        board_first_software_review_sha256=gate['review_sha256'],frozen_software_input_files_checked=len(ready['input_sha256']),
        loader_responses=159,loader_RUN_commands=1,application_commands=['G','C','D','Q'],packets=1829,
        DATA_packets=dict(source=1800,output=27),END_packets=2,retry_count=0,
        camera=dict(ABI='43414d02',sensor_ID='5640',config='OK',source_buf=0,source_seq=1,
                    pixels=921600,bytes=1843200,written_beats=57600,capture_CPU_PC_CRC=source_crc),
        preprocess=dict(ID='50525001',output='42000000',size=[96,96,3],layout='HWC/RGB',
                        sampled_source_first=[283,3],sampled_source_last=[996,716],
                        read_beats=9216,write_beats=864,produced_bytes=27648,
                        hardware_CPU_expected_CPU_reread_PC_CRC=pp_crc,byte_matches=27648,first_mismatch=None,
                        cycles=int(cycles),milliseconds=int(cycles)/93750000*1000,error=0),
        final=dict(claims=int(claim),discards=int(discard),GLOBAL_SEQ=int(glob),CAM_STATE=state,
                   source_and_tail_released=True,both_buffers_FREE=True,stream_stopped=True,PP_STATUS='00000002',
                   elapsed_ticks=int(elapsed),elapsed_seconds=int(elapsed)/93750000),
        original_rx_bytes=(folder/'uart.rx.bin').stat().st_size,original_tx_bytes=(folder/'uart.tx.bin').stat().st_size,
        visual=dict(Sol_viewed=['source.png','actual96.png'],
                    observation='96x96 result shows the central crop of the same tabletop and white/green cube; actual PNG equals independent expected PNG',
                    user_report='成功',user_explicit_visual_confirmation=False,original_visual_PENDING_unchanged=True),
        serial_opened_by_reviewer=False,HDL_run=False,RTL_modified=False,PDS_reaudited=False,
        limits=['One A/SEQ1 normal-path full-size source and byte-exact output; no B-source repeated-job board test',
                'Serial does not provide final-W/DONE cycle traces or prove early RELEASE rejection, fault draining or arbitration stress',
                'Native software tests and PDS timing remain separate evidence; HDL key group still not completed here',
                'Reported elapsed ticks include startup, CPU reference/CRC, UART export and software; not isolated processing latency',
                'No CNN/INT8, new Full Boot/PHY, or further RTL performance optimization'])
    target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],review_sha256=sha(target),
                         pp_ms=receipt['preprocess']['milliseconds'],elapsed_s=receipt['final']['elapsed_seconds']),indent=2))
if __name__=='__main__':main()
