"""Run actual firmware with native mock MMIO and independently replay synthetic UART. No HDL/serial."""
import argparse,hashlib,json,subprocess,sys,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/camera_uart'))
import loop100 as host
from protocol import Wire
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=HERE/'offline_tests_b');args=ap.parse_args()
    out=args.out.resolve();out.mkdir(exist_ok=False)
    exe=out/'native_firmware.exe'
    cmd=['D:/mingw64/bin/gcc.exe','-O2','-std=c11','-Wall','-Wextra','-Werror',str(HERE/'native_harness.c'),'-o',str(exe)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    (out/'compile.log').write_text(p.stdout+p.stderr,encoding='utf-8');(out/'compile.command.json').write_text(json.dumps(dict(argv=cmd,returncode=p.returncode),indent=2));assert p.returncode==0,p.stderr
    patterns=[ROOT/f'sim/camera/key/generated/frame{i}.bin' for i in (1,2)]
    crc=[f'{zlib.crc32(p.read_bytes())&0xffffffff:08x}' for p in patterns]
    expected={1:'CAPTURE_ERROR',2:'CAPTURE_TIMEOUT',3:'METADATA_OR_STATUS',4:'METADATA_OR_STATUS',5:'METADATA_OR_STATUS',
              6:'METADATA_OR_STATUS',7:'CRC_MISMATCH',8:'CAPTURE_STATE',9:'METADATA_OR_STATUS',10:'CPU_READ_TIMEOUT',
              11:'CONFIG_ERROR',12:'START_COMMAND',13:'DONE_WITHOUT_BUSY'}
    outcomes={};positive=None
    for mode in range(14):
        argv=[str(exe),str(mode),'4294967245',*map(str,patterns),*crc]
        p=subprocess.run(argv,capture_output=True,text=True,timeout=30)
        (out/f'native_{mode}.stdout.log').write_text(p.stdout,encoding='ascii');(out/f'native_{mode}.stderr.log').write_text(p.stderr,encoding='ascii')
        (out/f'native_{mode}.command.json').write_text(json.dumps(dict(argv=argv,returncode=p.returncode),indent=2));assert p.returncode==0,p.stderr
        if mode:
            assert f'FAIL REASON={expected[mode]} ' in p.stdout,p.stdout
            assert 'RESULT=PASS' not in p.stdout
            success=0 if mode in (11,12) else 1
            assert f'LOOP100_END RESULT=FAIL SUCCESS={success} ' in p.stdout
            assert f'ARMS={0 if mode in (11,12) else 2} ' in p.stderr
            outcomes[str(mode)]=dict(expected_failure=expected[mode],stopped_without_retry=True,successful_prefix=success)
        else:
            lines=p.stdout.splitlines();base=host.start_parse(lines[3]);rows=[host.row_parse(s,i,base) for i,s in enumerate(lines[4:104],1)]
            stats=host.end_parse(lines[104],rows);assert rows[0]['crc32']==crc[0] and rows[-1]['crc32']==crc[1]
            assert stats['adjacent_equal_crc']==98 and stats['distinct_crcs']==2 and stats['total_ticks']>2**32
            assert any(f['seq']==0 for f in rows)
            assert 'TOTAL_WORDS=46080000 ' in p.stderr
            positive=p.stdout.encode('ascii');outcomes['native_positive']=dict(status='ACTUAL_C_CONTROL_FLOW_WITH_MOCK_MMIO_PASS',statistics=stats,
                 actual_firmware_full_frame_words=46080000,independent_zlib_pattern_crc=crc,sequence_and_cycle_wrap=True)
    # Tiny Loader payload avoids claiming the native executable is an actual board image.
    fixture=out/'synthetic_application.bin';fixture.write_bytes(bytes(range(64)))
    info=dict(status='OFFLINE_FIXTURE',bytes=64,bin_path=fixture.relative_to(ROOT).as_posix(),bin_sha256=host.sha(fixture),crc32=zlib.crc32(fixture.read_bytes())&0xffffffff)
    class SyntheticPort:
        def __init__(self,app):self.plans=host.loader_plan(info);self.i=0;self.buf=bytearray();self.app=app
        @property
        def in_waiting(self):return len(self.buf)
        def read(self,n):
            n=min(n,17,len(self.buf));b=bytes(self.buf[:n]);del self.buf[:n];return b
        def write(self,b):
            if self.i<len(self.plans):
                plan=self.plans[self.i];assert b==bytes.fromhex(plan['tx_hex']);self.buf+=bytes.fromhex(plan['expected_hex']);self.i+=1
                if plan.get('run'):self.buf+=b'\n'.join(self.app.split(b'\n')[:3])+b'\n'
            else:assert b==b'G';self.buf+=b'\n'.join(self.app.split(b'\n')[3:])
            return len(b)
    mutations={'ok':positive,
       'bad_crc':positive.replace(b'CRC_CPU='+crc[0].encode(),b'CRC_CPU=00000000',1),
       'bad_sequence':positive.replace(b'FRAME=4294967246 ',b'FRAME=4294967247 ',1),
       'bad_status':positive.replace(b'STATUS=00000005',b'STATUS=0000000d',1),
       'bad_statistics':positive.replace(b'SUCCESS=100',b'SUCCESS=99'),
       'missing_frame':b'\n'.join(positive.split(b'\n')[:4]+positive.split(b'\n')[5:]),
       'bad_timing':positive.replace(b'WAIT_TICKS=',b'WAIT_TICKS=999999999',1),
       'extra_bytes':positive+b'UNEXPECTED\n'}
    for name,app in mutations.items():
        folder=out/name;folder.mkdir();(folder/'application.bin').write_bytes(fixture.read_bytes());(folder/'manifest.json').write_text(json.dumps(info))
        r=dict(status='RUNNING',evidence_origin='OFFLINE_SYNTHETIC_TEST',serial_opened=False,application=info,
               manifest_sha256=host.sha(folder/'manifest.json'),loader_records=[],frames=[],user_KEY0_confirmation=True)
        wire=Wire(SyntheticPort(app),folder);error=None
        try:
            host.execute(wire,info,folder,r,progress=lambda _:None)
            assert wire.in_waiting==0,'extra bytes'
        except (ValueError,AssertionError) as exc:error=str(exc)
        finally:wire.close()
        if error:r['status']='STOPPED_FIRST_FAILURE'
        else:r['status']='UART_LOOP100_DATA_CHECK_PASS'
        host.save(folder,r)
        if name=='ok':
            assert error is None,error
            replay=host.verify(folder,'OFFLINE_SYNTHETIC_TEST');outcomes['wire_positive']=replay
            try:host.verify(folder)
            except ValueError:outcomes['synthetic_rejected_as_board']=True
            else:raise AssertionError('synthetic accepted as board')
            # Same CRC on all 100 rows is legal if the complete flow/statistics pass.
            all_same=app.replace(crc[1].encode(),crc[0].encode())
            b=host.start_parse(all_same.decode().splitlines()[3]);rr=[host.row_parse(s,i,b) for i,s in enumerate(all_same.decode().splitlines()[4:104],1)]
            assert host.end_parse(all_same.decode().splitlines()[104],rr)['distinct_crcs']==1
            outcomes['all_same_crc_legal']=True
            rx=folder/'uart.rx.bin';original=rx.read_bytes();rx.write_bytes(b'X'+original[1:])
            try:host.verify(folder,'OFFLINE_SYNTHETIC_TEST')
            except ValueError:outcomes['tampered_rx_rejected']=True
            else:raise AssertionError('tamper accepted')
            rx.write_bytes(original)
        else:assert error is not None,name;outcomes[name]=dict(rejected=True,reason=error)
    receipt=dict(status='LOOP100_NATIVE_AND_OFFLINE_CHECKS_PASS_BOARD_NOT_RUN',serial_opened=False,HDL_run=False,
                 evidence_origin='NATIVE_MOCK_MMIO_AND_OFFLINE_SYNTHETIC_TEST',outcomes=outcomes,
                 source_sha256={p.relative_to(ROOT).as_posix():host.sha(p) for p in [HERE/'native_harness.c',Path(__file__),ROOT/'tests/camera_loop100/main.c',ROOT/'tools/camera_uart/loop100.py']})
    (out/'review.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],native_cases=14,host_cases=len(mutations),out=outcomes['native_positive']),indent=2))
if __name__=='__main__':main()
