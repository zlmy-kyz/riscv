"""User-operated Loader download + camera UART CRC/image acceptance. Never starts PDS."""
import argparse,hashlib,importlib.util,json,shutil,sys,time
from pathlib import Path
from protocol import Wire,need,line,exact,read_summary,receive_frame,verify_session
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
DEFAULT=ROOT/'tests/camera_uart/build/camera_uart_20261015_a/manifest.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def loader_plan(info):
    path=ROOT/'tools/uart_loader/candidates/bsp_workflow/plan.py'
    spec=importlib.util.spec_from_file_location('camera_existing_loader_plan',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.make_plan(info)

def require_image(path):
    m=json.loads(Path(path).read_text(encoding='utf-8'))
    need(m['status']=='CAMERA_UART_BUILD_STATIC_AUDIT_PASS','image build status')
    need(sha(ROOT/m['bin_path'])==m['bin_sha256'] and sha(ROOT/m['elf_path'])==m['elf_sha256'],'fixed image changed')
    for n,d in m['source_sha256'].items():need(sha(ROOT/n)==d,'source changed after build: '+n)
    return m

def save(folder,r):(Path(folder)/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def execute(wire,info,folder,r,scene_confirm=input,progress=print):
    need(wire.in_waiting==0,'unexpected initial UART bytes; reset first, no automatic flush')
    for plan in loader_plan(info):
        row=dict(name=plan['name'],tx_offset=wire.tx_count,rx_offset=wire.rx_count);r['loader_records'].append(row)
        wire.write(bytes.fromhex(plan['tx_hex']));response=exact(wire,60)
        need(response==bytes.fromhex(plan['expected_hex']),'Loader response/CRC/state mismatch: '+plan['name'])
        row['result']='PASS'
        if not plan.get('run'):
            time.sleep(.002);need(wire.in_waiting==0,'unexpected UART bytes before next Loader request')
    r['ready_rx_start']=wire.rx_count;ready=[]
    for _ in range(10):
        s=line(wire);ready.append(s);progress(s)
        if s=='CAMERA_READY':break
    else:raise ValueError('camera application did not become ready')
    need('CAMERA_APP=1' in ready and 'SENSOR_ID=00005640 CONFIG=OK' in ready,'application identity/sensor/config')
    r['ready_rx_end']=wire.rx_count
    for seq in range(1,r['requested_frames']+1):
        if seq>1:
            scene_confirm('遮住镜头或明显改变画面，稳定后按 Enter 采第二帧：')
            r['user_scene_change_confirmation']=True
        row=dict(capture_tx_offset=wire.tx_count);r['frames'].append(row)
        wire.write(b'C');summary=read_summary(wire,seq);row['summary']=summary
        for s in summary['lines']:progress(s)
        if seq>1:need(summary['crc32']!=r['frames'][seq-2]['summary']['crc32'],'scene change not observed: CRC unchanged')
        save(folder,r)
        if not r['summary_only']:
            row['export_tx_offset']=wire.tx_count;wire.write(b'D');row['export_rx_start']=wire.rx_count
            need(line(wire)=='EXPORT_BEGIN','export start')
            receive_frame(wire,folder,summary,row,progress=lambda n:progress(f'FRAME={seq} RX={n}/1843200'))
            need(line(wire)==f'EXPORT_DONE FRAME={seq} PC_ACK=1','export finish')
            progress(f'PC_CRC=MATCH FRAME={seq} IMAGE={row["png_path"]} VISUAL_REVIEW=PENDING')
            save(folder,r)
    r['finish_tx_offset']=wire.tx_count;r['finish_rx_start']=wire.rx_count;wire.write(b'Q');last=line(wire)
    want=f'SESSION_DONE CAPTURES={r["requested_frames"]} EXPORTS={0 if r["summary_only"] else r["requested_frames"]} CPU_CHECK=PASS'
    need(last==want,'session finish mismatch');r['session_finish']=last

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,default=DEFAULT);ap.add_argument('--port',default='COM9')
    ap.add_argument('--log-dir',type=Path);ap.add_argument('--captures',type=int,choices=[1,2],default=2)
    ap.add_argument('--summary-only',action='store_true');ap.add_argument('--plan-only',action='store_true')
    ap.add_argument('--verify',type=Path);a=ap.parse_args()
    if a.verify:
        print(json.dumps(verify_session(a.verify,loader_plan),indent=2));return
    info=require_image(a.manifest);plan=loader_plan(info)
    if a.plan_only:
        print(json.dumps(dict(status='CAMERA_UART_PLAN_ONLY_SERIAL_NOT_OPENED',bin_sha256=info['bin_sha256'],bytes=info['bytes'],loader_responses=len(plan),RUN_commands=sum(bool(r.get('run')) for r in plan),captures=a.captures,export=not a.summary_only,frame_wire_min_seconds=165.0),indent=2));return
    need(a.log_dir is not None and not a.log_dir.exists(),'use a new --log-dir; never overwrite a prior run')
    folder=a.log_dir.resolve();folder.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(a.manifest,folder/'manifest.json');shutil.copyfile(ROOT/info['bin_path'],folder/'application.bin')
    r=dict(status='RUNNING',evidence_origin='ACTUAL_SERIAL',application=info,manifest_sha256=sha(a.manifest),
        port=a.port,baud=115200,requested_frames=a.captures,summary_only=a.summary_only,
        retry_count=0,serial_opened=False,PDS_started=False,KEY0_independently_observed=False,
        loader_records=[],frames=[],visual_review='NOT_CONFIRMED',tool_sha256={p.name:sha(p) for p in [Path(__file__),HERE/'protocol.py']})
    save(folder,r)
    print('使用当前含 Camera RTL 的新版位流；程序将通过既有 Loader 下载固定 BIN。')
    wire=None
    try:
        input('关闭串口助手；按 KEY0 后释放，等待 DDR 就绪，再按 Enter：')
        r['user_KEY0_confirmation']=True
        import serial
        with serial.Serial(a.port,115200,timeout=.05,write_timeout=2,xonxoff=False,rtscts=False,dsrdtr=False) as port:
            r['serial_opened']=True;time.sleep(.25);wire=Wire(port,folder)
            execute(wire,info,folder,r)
        wire.close();wire=None
        r['status']='UART_CPU_SUMMARY_CHECK_PASS_NO_PC_FRAME_CHECK' if a.summary_only else 'UART_FRAME_DATA_CHECK_PASS_VISUAL_PENDING'
        save(folder,r)
        if not a.summary_only:
            verified=verify_session(folder,loader_plan)
            (folder/'verified.json').write_text(json.dumps(verified,indent=2)+'\n',encoding='utf-8');print(verified['status'])
    except BaseException as exc:r.update(status='STOPPED_FIRST_FAILURE',error=repr(exc));raise
    finally:
        if wire:wire.close()
        save(folder,r)
    print('日志目录：',folder)
if __name__=='__main__':main()
