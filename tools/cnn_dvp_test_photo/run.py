"""Export OV5640 DVP test mode0/8bit raw bytes with the fixed BIN; requires NEW 503D00/474105 bitstream on J10."""
import argparse,hashlib,importlib.util,json,shutil,sys,time,struct,zlib
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'tools/cnn_digits_photo'))
spec=importlib.util.spec_from_file_location('fixed_photo_driver',ROOT/'tools/cnn_digits_photo/run.py')
photo=importlib.util.module_from_spec(spec);spec.loader.exec_module(photo)
STAGE=ROOT/'sim/camera/dvp_photo_20261017_a'
HARDWARE=STAGE/'hardware.json'
RELEASE=STAGE/'board_release.json'
FIXED_BIN_SHA='2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4'
PROMPT=('本次必须重新综合、映射、布局布线并生成/下载DVP模式0、8bit测试新位流（503D=00、4741=05）；旧PRE-ISP彩条位流不可用。'
        '确认实物J10、CAM1/J4，关闭串口助手，下载后按下/释放KEY0、等DDR就绪，再Enter导出原始字节（约3分钟或更久；PNG仅为RGB565解释的预览）：')
need=photo.need;sha=photo.sha
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def fixed_image():
    m=photo.image(photo.DEFAULT)
    need(m['bin_sha256']==FIXED_BIN_SHA and m['bytes']==42544,'wrong fixed photo BIN')
    return m
def expected_hardware():
    h=read(HARDWARE)
    need(h['mode']=='OV5640_DVP_TEST_MODE0_8BIT' and h['connector']=='J10' and h['camera_connector']=='CAM1/J4','wrong DVP test hardware contract')
    need(h['requires_new_bitstream'] is True and h['registers_expected']=={'503d':'00','4741':'05'},'wrong bitstream/config contract')
    for n,d in h['design_sha256'].items():need(sha(ROOT/n)==d,'changed DVP test design input '+n)
    for n,d in h['constraint_sha256'].items():need(sha(ROOT/n)==d,'changed J10 constraint '+n)
    need(sha(ROOT/h['astra_static_review'])==h['astra_static_review_sha256'],'changed Astra static receipt')
    return h
def hardware_record(h,confirmed):
    return dict(expected=h,expected_manifest_sha256=sha(HARDWARE),
        operator_new_dvp_test_bitstream_J10_KEY0_confirmation=confirmed,
        actual_downloaded_bitstream_independently_verified=False,
        dvp_test_config_registers_independently_read_by_PC=False,
        config_done_semantics='Expected new RTL checks 503D=00 and 4741=05; old BIN only exposes SENSOR_ID/CONFIG=OK',
        timing='NEW_DVP_TEST_IMPLEMENTATION_NOT_REVIEWED',key_HDL='NOT_COMPLETED',
        expected_image='DVP mode0/8bit pattern and geometry require board confirmation; no eight-RGB-bar assumption',
        visual_review='PENDING',scene_independence='NOT_VERIFIED_BY_ONE_CAPTURE',
        old_J10_timing_PASS_inherited=False)
def optional_bitstream_record():
    p=ROOT/'generate_bitstream/board_top.sbit'
    if not p.exists():return dict(file_present=False,download_verified=False)
    return dict(file_present=True,path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,
        sha256=sha(p),download_verified=False,note='Local file fingerprint only; operator confirms actual download, no hash prerequisite')
def dvp_note(folder,write):
    raw=(folder/'source.rgb565').read_bytes();need(len(raw)==1843200,'DVP source byte length')
    # With unchanged capture, DVP high byte is stored at odd offsets and low byte at even offsets.
    lanes={}
    for name,start in [('second_DVP_byte_stored_low',0),('first_DVP_byte_stored_high',1)]:
        data=raw[start::2];hist=Counter(data);ones=sum(n for value,n in hist.items() if value&1)
        lanes[name]=dict(bytes=len(data),byte_histogram={f'{v:02x}':hist[v] for v in sorted(hist)},
            D0_zeros=len(data)-ones,D0_ones=ones,D0_changes_between_same_lane_samples=sum(((a^b)&1)!=0 for a,b in zip(data,data[1:])),
            scope='Observed counts only; pattern may legitimately toggle D0; not an electrical error rate')
    rows=[f'{zlib.crc32(raw[i:i+2560])&0xffffffff:08x}' for i in range(0,len(raw),2560)]
    words=Counter(v[0] for v in struct.iter_unpack('<H',raw))
    note=dict(status='DVP_RAW_EXPORT_COMPLETE_PATTERN_REVIEW_PENDING',raw_bytes=len(raw),
        fixed_capture_geometry=dict(width=1280,height=720,line_bytes=2560),
        source_SHA256=sha(folder/'source.rgb565'),expected_PRE_ISP_disabled=True,expected_DVP_mode=0,expected_DVP_output_bits=8,
        pattern_layout_values_and_full_frame_CRC='NOT_ASSUMED',PNG='RGB565 interpretation for preview only, not RGB color correctness',
        byte_lanes=lanes,distinct_paired_words=len(words),most_common_paired_words=[dict(hex=f'{v:04x}',count=n) for v,n in words.most_common(24)],
        row_CRC32=rows,distinct_row_CRCs=len(set(rows)),adjacent_equal_rows=sum(a==b for a,b in zip(rows,rows[1:])),
        physical_D0_mapping='DVP D0: first byte -> paired word bit8, second byte -> paired word bit0; not bare sensor D0',
        pattern_correctness='PENDING',cross_frame_stability='NOT_VERIFIED_BY_ONE_CAPTURE',scene_independence='NOT_VERIFIED_BY_ONE_CAPTURE',
        scope='Raw facts and source->PP/CNN consistency do not prove correct test pattern, D0 integrity, timing or root cause')
    if write:save(folder/'dvp_assessment.json',note)
    else:need(read(folder/'dvp_assessment.json')==note,'DVP raw byte assessment changed')
    return note

def verify(folder,origin='ACTUAL_SERIAL'):
    folder=Path(folder);r=read(folder/'result.json')
    need(r['evidence_origin']==origin,'synthetic is not actual serial')
    need(r['status']=='DVP_TEST_CAPTURE_DATA_PASS_VISUAL_PENDING','DVP test capture not complete')
    h=read(folder/'hardware.json');record=read(folder/'hardware_record.json')
    need(h==record['expected'] and sha(folder/'hardware.json')==record['expected_manifest_sha256'],'hardware record identity')
    need(h['mode']=='OV5640_DVP_TEST_MODE0_8BIT' and h['connector']=='J10' and h['requires_new_bitstream'],'not new J10 DVP test mode')
    need(r['hardware_record']==record,'hardware ledger changed')
    if origin=='ACTUAL_SERIAL':need(record['operator_new_dvp_test_bitstream_J10_KEY0_confirmation'],'new bitstream/J10 confirmation absent')
    # Use the pinned transport/reference exchange without editing the old tool or evidence.
    checked=verify_base(folder,r,origin)
    dvp_note(folder,False)
    return dict(status='DVP_TEST_RAW_DATA_VERIFIED_VISUAL_PENDING',data_verification=checked,
        hardware_version=h['version'],actual_downloaded_bitstream_independently_verified=False,
        key_HDL='NOT_COMPLETED',timing='NEW_DVP_TEST_IMPLEMENTATION_NOT_REVIEWED',
        original_status=r['status'],visual_review='PENDING',scene_independence='NOT_VERIFIED_BY_ONE_CAPTURE')
def verify_base(folder,r,origin):
    need(origin in ('ACTUAL_SERIAL','OFFLINE_SYNTHETIC_TEST'),'invalid evidence origin')
    if origin=='ACTUAL_SERIAL':need(r['serial_opened'] and r['user_KEY0_confirmation'] and r['user_current_repaired_bitstream_confirmation'],'actual prerequisites')
    m=read(folder/'manifest.json');need(m==r['application'] and sha(folder/'manifest.json')==r['manifest_sha256'],'manifest identity')
    need(sha(folder/'application.bin')==m['bin_sha256']==FIXED_BIN_SHA,'fixed BIN identity')
    for n,d in r['file_sha256'].items():need(sha(folder/n)==d,'changed evidence '+n)
    model=photo.reference.load(folder/'model');need(model['meta']==m['diagnostic_model'],'model identity')
    w=photo.Replay((folder/'uart.rx.bin').read_bytes(),(folder/'uart.tx.bin').read_bytes())
    session=photo.exchange(w,m,folder,model,False);need(session==r['session'],'raw/session mismatch')
    need(w.rx_count==len(w.rx) and w.tx_count==len(w.tx),'extra RX/TX')
    return dict(source_bytes=1843200,preprocess_bytes_compared=27648,scores=session['scores'],
        prediction=session['job']['prediction'],cnn_ms=session['comparison']['cnn_ms'],trained_digit_accuracy=False)
def live(args,m,h):
    gate=read(RELEASE)
    need(gate['status']=='USER_AUTHORIZED_NEW_DVP_TEST_BOARD_DIAGNOSTIC' and gate['firmware_sha256']==FIXED_BIN_SHA and gate['hardware_manifest_sha256']==sha(HARDWARE),'DVP test release identity')
    need(args.log_dir is not None and not args.log_dir.exists(),'new --log-dir required')
    folder=args.log_dir.resolve();folder.mkdir(parents=True,exist_ok=False)
    for p,n in [(photo.DEFAULT,'manifest.json'),(ROOT/m['bin_path'],'application.bin'),(HARDWARE,'hardware.json'),(RELEASE,'board_release.json')]:shutil.copyfile(p,folder/n)
    shutil.copytree(photo.MODEL,folder/'model');model=photo.reference.load(folder/'model')
    record=hardware_record(h,False);save(folder/'hardware_record.json',record)
    r=dict(status='RUNNING',evidence_origin='ACTUAL_SERIAL',application=m,manifest_sha256=sha(photo.DEFAULT),
        serial_opened=False,user_KEY0_confirmation=False,user_current_repaired_bitstream_confirmation=False,
        hardware_record=record,port=args.port,baud=115200,retry_count=0,PDS_started=False,
        timing='NEW_DVP_TEST_IMPLEMENTATION_NOT_REVIEWED',key_HDL='NOT_COMPLETED',tool_sha256=sha(Path(__file__)))
    save(folder/'result.json',r);w=None;start=time.monotonic()
    try:
        print('OV5640 DVP模式0/8bit：503D=00、4741=05；必须新位流/J10/KEY0，旧彩条版本不可用。关键HDL及本版时序待验。')
        input(PROMPT)
        record=hardware_record(h,True);record['local_bitstream_file']=optional_bitstream_record()
        save(folder/'hardware_record.json',record);r.update(hardware_record=record,user_KEY0_confirmation=True,user_current_repaired_bitstream_confirmation=True)
        import serial
        with serial.Serial(args.port,115200,timeout=.05,write_timeout=2,xonxoff=False,rtscts=False,dsrdtr=False) as port:
            r['serial_opened']=True;w=photo.Wire(port,folder)
            try:
                need(port.in_waiting==0,'unexpected initial bytes; no flush/retry')
                r['session']=photo.exchange(w,m,folder,model,True,print)
                time.sleep(.05);need(port.in_waiting==0,'extra final bytes')
            except BaseException:
                until=time.monotonic()+2
                while time.monotonic()<until:
                    try:w.read(4096)
                    except Exception:break
                raise
        w.close();w=None;r['assessment']=dvp_note(folder,True)
        r['status']='DVP_TEST_CAPTURE_DATA_PASS_VISUAL_PENDING'
    except BaseException as e:r.update(status='STOPPED_FIRST_FAILURE',error=repr(e));raise
    finally:
        if w:w.close()
        r['wall_seconds_including_user_confirmation']=time.monotonic()-start
        r['file_sha256']={p.relative_to(folder).as_posix():sha(p) for p in folder.rglob('*') if p.is_file() and p.name not in ('result.json','verified.json')}
        save(folder/'result.json',r)
    checked=verify(folder);save(folder/'verified.json',checked);print(json.dumps(checked,ensure_ascii=False,indent=2))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',default='COM9');p.add_argument('--log-dir',type=Path)
    p.add_argument('--plan-only',action='store_true');p.add_argument('--verify',type=Path);a=p.parse_args()
    if a.verify:print(json.dumps(verify(a.verify),ensure_ascii=False,indent=2));return
    m=fixed_image();h=expected_hardware()
    if a.plan_only:
        print(json.dumps(dict(status='NEW_DVP_TEST_SOFTWARE_PLAN_NO_SERIAL',firmware_sha256=m['bin_sha256'],hardware_version=h['version'],
            requires_new_bitstream=True,connector='J10',PDS_started=False,serial_opened=False,prompt=PROMPT,
            visual_review='PENDING',timing='NEW_DVP_TEST_IMPLEMENTATION_NOT_REVIEWED'),ensure_ascii=False,indent=2));return
    live(a,m,h)
if __name__=='__main__':main()
