"""Export sensor color bars with the existing fixed photo BIN; requires a NEW color-bar bitstream on J10."""
import argparse,hashlib,importlib.util,json,shutil,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'tools/cnn_digits_photo'))
spec=importlib.util.spec_from_file_location('fixed_photo_driver',ROOT/'tools/cnn_digits_photo/run.py')
photo=importlib.util.module_from_spec(spec);spec.loader.exec_module(photo)
STAGE=ROOT/'sim/camera/colorbar_photo_20261017_a'
HARDWARE=STAGE/'hardware.json'
RELEASE=STAGE/'board_release.json'
FIXED_BIN_SHA='2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4'
PROMPT=('本次必须重新综合、映射、布局布线并生成/下载启用内部彩条的新位流；旧位流不能输出彩条。'
        '确认实物为J10、CAM1/J4，关闭串口助手，下载后按下/释放KEY0、等DDR就绪，再Enter开始导图（约3分钟或更久）：')
need=photo.need;sha=photo.sha
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def fixed_image():
    m=photo.image(photo.DEFAULT)
    need(m['bin_sha256']==FIXED_BIN_SHA and m['bytes']==42544,'wrong fixed photo BIN')
    return m
def expected_hardware():
    h=read(HARDWARE)
    need(h['mode']=='OV5640_INTERNAL_COLOR_BARS' and h['connector']=='J10' and h['camera_connector']=='CAM1/J4','wrong colorbar hardware contract')
    need(h['requires_new_bitstream'] is True and h['registers_expected']=={'503d':'80','4741':'00'},'wrong bitstream/config contract')
    for n,d in h['design_sha256'].items():need(sha(ROOT/n)==d,'changed colorbar design input '+n)
    for n,d in h['constraint_sha256'].items():need(sha(ROOT/n)==d,'changed J10 constraint '+n)
    need(sha(ROOT/h['astra_static_review'])==h['astra_static_review_sha256'],'changed Astra static receipt')
    return h
def hardware_record(h,confirmed):
    return dict(expected=h,expected_manifest_sha256=sha(HARDWARE),
        operator_new_colorbar_bitstream_J10_KEY0_confirmation=confirmed,
        actual_downloaded_bitstream_independently_verified=False,
        colorbar_config_registers_independently_read_by_PC=False,
        config_done_semantics='Expected new RTL checks 503D=80 and 4741=00; old BIN only exposes SENSOR_ID/CONFIG=OK',
        timing='NEW_COLORBAR_IMPLEMENTATION_NOT_REVIEWED',key_HDL='NOT_COMPLETED',
        expected_image='Stable eight sensor-generated bars; should not change when lens is covered',
        visual_review='PENDING',scene_independence='NOT_VERIFIED_BY_ONE_CAPTURE',
        old_J10_timing_PASS_inherited=False)
def optional_bitstream_record():
    p=ROOT/'generate_bitstream/board_top.sbit'
    if not p.exists():return dict(file_present=False,download_verified=False)
    return dict(file_present=True,path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,
        sha256=sha(p),download_verified=False,note='Local file fingerprint only; operator confirms actual download, no hash prerequisite')
def colorbar_note(folder,write):
    note=dict(status='RAW_COLORBAR_EXPORT_COMPLETE_VISUAL_REVIEW_PENDING',
        raw_bytes=1843200,width=1280,height=720,
        expected='Stable eight bars with uniform interiors; inspect source.png/source.rgb565 before PP/CNN',
        known_full_frame_CRC=None,exact_color_order_boundaries_and_RGB565_values='NOT_ASSUMED',
        no_green_purple_dots_verified=False,scene_independence='NOT_VERIFIED_BY_ONE_CAPTURE',
        scope='Byte/CRC/PP/CNN agreement does not prove a clean color-bar image or root cause')
    if write:save(folder/'colorbar_assessment.json',note)
    else:need(read(folder/'colorbar_assessment.json')==note,'colorbar assessment changed')
    return note
def verify(folder,origin='ACTUAL_SERIAL'):
    folder=Path(folder);r=read(folder/'result.json')
    need(r['evidence_origin']==origin,'synthetic is not actual serial')
    need(r['status']=='COLORBAR_CAPTURE_DATA_PASS_VISUAL_PENDING','colorbar capture not complete')
    h=read(folder/'hardware.json');record=read(folder/'hardware_record.json')
    need(h==record['expected'] and sha(folder/'hardware.json')==record['expected_manifest_sha256'],'hardware record identity')
    need(h['mode']=='OV5640_INTERNAL_COLOR_BARS' and h['connector']=='J10' and h['requires_new_bitstream'],'not new J10 colorbar mode')
    need(r['hardware_record']==record,'hardware ledger changed')
    if origin=='ACTUAL_SERIAL':need(record['operator_new_colorbar_bitstream_J10_KEY0_confirmation'],'new bitstream/J10 confirmation absent')
    # Use the pinned transport/reference exchange without editing the old tool or evidence.
    checked=verify_base(folder,r,origin)
    colorbar_note(folder,False)
    return dict(status='COLORBAR_RAW_DATA_VERIFIED_VISUAL_PENDING',data_verification=checked,
        hardware_version=h['version'],actual_downloaded_bitstream_independently_verified=False,
        key_HDL='NOT_COMPLETED',timing='NEW_COLORBAR_IMPLEMENTATION_NOT_REVIEWED',
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
    need(gate['status']=='USER_AUTHORIZED_NEW_COLORBAR_BOARD_DIAGNOSTIC' and gate['firmware_sha256']==FIXED_BIN_SHA and gate['hardware_manifest_sha256']==sha(HARDWARE),'colorbar release identity')
    need(args.log_dir is not None and not args.log_dir.exists(),'new --log-dir required')
    folder=args.log_dir.resolve();folder.mkdir(parents=True,exist_ok=False)
    for p,n in [(photo.DEFAULT,'manifest.json'),(ROOT/m['bin_path'],'application.bin'),(HARDWARE,'hardware.json'),(RELEASE,'board_release.json')]:shutil.copyfile(p,folder/n)
    shutil.copytree(photo.MODEL,folder/'model');model=photo.reference.load(folder/'model')
    record=hardware_record(h,False);save(folder/'hardware_record.json',record)
    r=dict(status='RUNNING',evidence_origin='ACTUAL_SERIAL',application=m,manifest_sha256=sha(photo.DEFAULT),
        serial_opened=False,user_KEY0_confirmation=False,user_current_repaired_bitstream_confirmation=False,
        hardware_record=record,port=args.port,baud=115200,retry_count=0,PDS_started=False,
        timing='NEW_COLORBAR_IMPLEMENTATION_NOT_REVIEWED',key_HDL='NOT_COMPLETED',tool_sha256=sha(Path(__file__)))
    save(folder/'result.json',r);w=None;start=time.monotonic()
    try:
        print('OV5640内部彩条诊断：必须使用新生成/下载的彩条位流，接口J10；旧位流无效。关键HDL未完成，不继承旧时序PASS。')
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
        w.close();w=None;r['assessment']=colorbar_note(folder,True)
        r['status']='COLORBAR_CAPTURE_DATA_PASS_VISUAL_PENDING'
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
        print(json.dumps(dict(status='NEW_COLORBAR_SOFTWARE_PLAN_NO_SERIAL',firmware_sha256=m['bin_sha256'],hardware_version=h['version'],
            requires_new_bitstream=True,connector='J10',PDS_started=False,serial_opened=False,prompt=PROMPT,
            visual_review='PENDING',timing='NEW_COLORBAR_IMPLEMENTATION_NOT_REVIEWED'),ensure_ascii=False,indent=2));return
    live(a,m,h)
if __name__=='__main__':main()
