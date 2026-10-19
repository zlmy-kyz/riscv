"""Check only new hardware metadata, prompts and replay; no HDL/PDS/serial or firmware build."""
import argparse,builtins,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('colorbar_driver',ROOT/'tools/cnn_cam2_photo/run.py')
pc=importlib.util.module_from_spec(spec);spec.loader.exec_module(pc)
def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',default='checks_01');a=p.parse_args();out=HERE/a.tag;out.mkdir(exist_ok=False)
    report=dict(status='RUNNING',evidence_origin='OFFLINE_SYNTHETIC_TEST',serial_opened=False,PDS_started=False,HDL_run=False,firmware_rebuilt=False,checks=[])
    def reject(name,fn):
        try:fn()
        except (ValueError,AssertionError) as e:report['checks'].append(dict(name=name,rejected=True,error=str(e)));return
        raise AssertionError('wrongly accepted '+name)
    try:
        m=pc.fixed_image();h=pc.expected_hardware()
        assert '已重新生成并下载' in pc.PROMPT and '真实拍照' in pc.PROMPT and 'J10' in pc.PROMPT and 'KEY0' in pc.PROMPT
        assert 'CAM2/J5' in pc.PROMPT and '单摄像头' in pc.PROMPT and 'DDR双缓冲' in pc.PROMPT
        assert '本次仅换软件' not in pc.PROMPT and '沿用已下载' not in pc.PROMPT
        cmd=[sys.executable,'-X','utf8',str(ROOT/'tools/cnn_cam2_photo/run.py'),'--plan-only']
        r=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
        (out/'plan.log').write_bytes(r.stdout);pc.save(out/'plan.command.json',dict(argv=cmd,returncode=r.returncode))
        assert r.returncode==0;plan=json.loads(r.stdout);assert plan['requires_new_bitstream'] and plan['connector']=='J10' and not plan['serial_opened']
        fixture=ROOT/'sim/cnn/board_photo_20261016_a/checks_01/normal/pc'
        folder=out/'synthetic_replay';shutil.copytree(fixture,folder)
        # These bytes are prior native C/device-model data, not newly captured bars.
        r=pc.read(folder/'result.json');assert r['evidence_origin']=='OFFLINE_SYNTHETIC_TEST'
        shutil.copyfile(pc.HARDWARE,folder/'hardware.json');record=pc.hardware_record(h,False)
        pc.save(folder/'hardware_record.json',record);pc.live_note(folder,True)
        r.update(status='CAM2_PHOTO_CAPTURE_DATA_PASS_VISUAL_PENDING',hardware_record=record)
        r['file_sha256']={p.relative_to(folder).as_posix():pc.sha(p) for p in folder.rglob('*') if p.is_file() and p.name not in ('result.json','verified.json')}
        pc.save(folder/'result.json',r)
        check=pc.verify(folder,'OFFLINE_SYNTHETIC_TEST');assert check['visual_review']=='PENDING' and check['scene_independence']=='NOT_VERIFIED_BY_ONE_CAPTURE'
        assert not check['actual_downloaded_bitstream_independently_verified'];pc.save(out/'replay_review.json',check)
        reject('synthetic_is_not_board',lambda:pc.verify(folder))
        # A canceled prerequisite prompt must save failure evidence without importing/opening serial.
        release=out/'test_release.json';pc.save(release,dict(status='USER_AUTHORIZED_NEW_CAM2_PHOTO_BOARD_DIAGNOSTIC',firmware_sha256=pc.FIXED_BIN_SHA,hardware_manifest_sha256=pc.sha(pc.HARDWARE)))
        old_release=pc.RELEASE;old_input=builtins.input;pc.RELEASE=release;prompts=[]
        def cancel(text):prompts.append(text);raise KeyboardInterrupt('offline prerequisite-cancel probe')
        try:
            builtins.input=cancel
            try:pc.live(argparse.Namespace(log_dir=out/'cancel_before_serial',port='OFFLINE_NO_SERIAL'),m,h)
            except KeyboardInterrupt:pass
        finally:builtins.input=old_input;pc.RELEASE=old_release
        canceled=pc.read(out/'cancel_before_serial/result.json')
        assert prompts==[pc.PROMPT] and canceled['status']=='STOPPED_FIRST_FAILURE' and not canceled['serial_opened']
        assert not canceled['hardware_record']['operator_new_CAM2_bitstream_J10_KEY0_confirmation']
        assert not (out/'cancel_before_serial/uart.rx.bin').exists() and 'serial' not in sys.modules
        old_hardware=pc.HARDWARE
        for name,change in [('J25',lambda h:h.update(connector='J25')),('old_mode',lambda h:h.update(mode='OV5640_DVP_TEST_MODE0_8BIT')),
                            ('CAM1',lambda h:h.update(camera_connector='CAM1/J4')),
                            ('two_cameras',lambda h:h.update(camera_count=2)),
                            ('old_PCLK_PAD',lambda h:h['camera_pad_map'].__setitem__('camera_pclk','L22')),
                            ('no_rebuild',lambda h:h.update(requires_new_bitstream=False)),
                            ('RTL_hash',lambda h:h['design_sha256'].__setitem__('myriscv/board_top.v','0'*64))]:
            value=json.loads(json.dumps(h));change(value);path=out/(name+'.json');pc.save(path,value)
            try:pc.HARDWARE=path;reject('hardware_'+name,pc.expected_hardware)
            finally:pc.HARDWARE=old_hardware
        # Proven working transport code and fixed BIN remain byte-for-byte unchanged.
        pc.photo.image(pc.photo.DEFAULT)
        report.update(status='CAM2_PHOTO_PC_TOOL_CHECKS_PASS_NOT_HDL_NOT_BOARD',fixed_BIN_sha256=m['bin_sha256'],
            hardware_version=h['version'],raw_protocol_replay_packets=1829,
            unchanged_math_and_transport_evidence='sim/cnn/board_photo_20261016_a/checks_01/review.json',
            prompt_cancellation_before_serial=True,visual_PASS_not_claimed=True)
    except BaseException as e:report.update(status='STOPPED_FIRST_OFFLINE_FAILURE',error=repr(e));raise
    finally:
        report['input_sha256']={p.relative_to(ROOT).as_posix():pc.sha(p) for p in [Path(__file__),ROOT/'tools/cnn_cam2_photo/run.py',pc.HARDWARE,pc.photo.DEFAULT]}
        report['artifact_sha256']={p.relative_to(out).as_posix():pc.sha(p) for p in out.rglob('*') if p.is_file()}
        pc.save(out/'review.json',report)
    print(json.dumps({k:report[k] for k in ('status','fixed_BIN_sha256','raw_protocol_replay_packets')},indent=2))
if __name__=='__main__':main()
