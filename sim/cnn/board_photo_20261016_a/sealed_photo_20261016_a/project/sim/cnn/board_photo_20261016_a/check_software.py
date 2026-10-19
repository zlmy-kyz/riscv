"""Only check added same-frame source export. Reuse previous integer CNN evidence."""
import hashlib,json,shutil,struct,subprocess,sys,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/cnn_digits_photo'))
import run as pc,reference
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    out=HERE/'checks_01';out.mkdir(exist_ok=False);r=dict(status='RUNNING',origin='OFFLINE_SYNTHETIC_TEST',HDL=False,real_CPU=False,serial_opened=False,checks=[])
    def command(name,args):
        args=list(map(str,args));p=subprocess.run(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
        (out/(name+'.log')).write_bytes(p.stdout);save(out/(name+'.command.json'),dict(argv=args,returncode=p.returncode))
        assert p.returncode==0,(name,p.stdout.decode(errors='replace'));return p.stdout
    def reject(name,fn,reason=None):
        try:fn()
        except (ValueError,AssertionError) as e:
            if reason:assert reason in str(e),(name,str(e))
            r['checks'].append(dict(name=name,rejected=True,error=str(e)));return
        raise AssertionError('wrongly accepted '+name)
    try:
        m=pc.image(pc.DEFAULT);model=reference.load(pc.MODEL)
        old=ROOT/'sim/cnn/board_diag_20261016_a/checks_02/review.json';old_result=json.loads(old.read_text())
        assert old_result['status']=='SOFTWARE_OFFLINE_CHECKS_PASS_NOT_HDL_NOT_BOARD'
        for n,h in old_result['input_sha256'].items():assert sha(ROOT/n)==h
        assert sha(ROOT/'tools/cnn_digits_diag/reference.py')==sha(ROOT/'tools/cnn_digits_photo/reference.py')
        r['reused_integer_reference_review']=dict(path=old.relative_to(ROOT).as_posix(),sha256=sha(old),reason='CNN math/model unchanged; seven-pattern C/Python checks not rerun')
        source=bytearray()
        for y in range(720):
            for x in range(1280):
                p=(((x*3+y*7)&31)<<11)|(((x*11+y*5)&63)<<5)|((x+13*y)&31)
                source+=struct.pack('<H',p)
        source=bytes(source);(out/'input.rgb565').write_bytes(source)
        rgb=pc.ppref.expected_from_source(source);assert rgb==pc.ppref.expected_second_implementation(source)
        (out/'input.rgb').write_bytes(rgb);inference=reference.infer(rgb,model);(out/'scores.bin').write_bytes(struct.pack('<10i',*inference['scores']))
        # Mismatched PP data still gets its own true CNN reference; only source->PP check can reject.
        changed=bytearray(rgb);changed[123]^=8;changed=bytes(changed);(out/'wrong_pp.rgb').write_bytes(changed)
        (out/'wrong_pp_scores.bin').write_bytes(struct.pack('<10i',*reference.infer(changed,model)['scores']))
        command('compile',['D:/mingw64/bin/gcc.exe','-O2','-std=c11','-Wall','-Wextra','-Werror','-Wno-int-to-pointer-cast',
            ROOT/'tests/cnn_digits_photo/native_flow.c',ROOT/'tests/cnn_digits_photo/pp01_wire.c','-o',out/'flow.exe'])
        plans=pc.loader_plan(m);load_rx=b''.join(bytes.fromhex(p['expected_hex']) for p in plans);load_tx=b''.join(bytes.fromhex(p['tx_hex']) for p in plans)
        class Fragmented(pc.Replay):
            def read(self,n):
                if self.rx_count==len(self.rx):raise ValueError('offline short raw RX')
                return super().read(min(73,n))
        flows={}
        for scenario in ('normal','no_tail','source_crc','source_ack','release','pp_mismatch','score'):
            f=out/scenario;f.mkdir();prefix=f/'run';badpp=scenario=='pp_mismatch'
            data=command(scenario,[out/'flow.exe',out/'input.rgb565',out/('wrong_pp.rgb' if badpp else 'input.rgb'),
                out/('wrong_pp_scores.bin' if badpp else 'scores.bin'),pc.MODEL/'load_words.bin',scenario,prefix])
            ledger=json.loads(data);flows[scenario]=ledger
            assert ledger['camera_starts']==ledger['pp_starts']==ledger['cnn_starts']==1
            assert ledger['model_words']==6222 and ledger['model_crc']==model['meta']['load_crc32']
            normal=scenario in ('normal','no_tail','pp_mismatch','score');assert ledger['status']==(2 if normal else 3)
            rx=load_rx+Path(str(prefix)+'.fw.tx.bin').read_bytes();tx=load_tx+Path(str(prefix)+'.fw.rx.bin').read_bytes()
            fpc=f/'pc';fpc.mkdir();w=Fragmented(rx,tx)
            if scenario in ('normal','no_tail'):
                session=pc.exchange(w,m,fpc,model)
                assert w.rx_count==len(rx) and w.tx_count==len(tx) and len(session['packets'])==1829
                assert ledger['releases']==(1 if scenario=='no_tail' else 2)
                assert (fpc/'source.rgb565').read_bytes()==source and (fpc/'rgb96.bin').read_bytes()==rgb
                assert pc.ppref.decode_png((fpc/'source.png').read_bytes())[:2]==(1280,720)
                # Independently expand every source pixel and compare decoded PNG RGB, not only file hashes.
                expanded=bytes(v for i in range(0,len(source),2) for v in pc.ppref.expand565(source[i]|source[i+1]<<8))
                assert pc.ppref.decode_png((fpc/'source.png').read_bytes())[2]==expanded
                (fpc/'uart.rx.bin').write_bytes(rx);(fpc/'uart.tx.bin').write_bytes(tx)
                shutil.copyfile(pc.DEFAULT,fpc/'manifest.json');shutil.copyfile(ROOT/m['bin_path'],fpc/'application.bin');shutil.copytree(pc.MODEL,fpc/'model')
                result=dict(status='CNN_DIAG_ONE_JOB_SCORES_PASS',evidence_origin='OFFLINE_SYNTHETIC_TEST',application=m,session=session,
                    manifest_sha256=sha(fpc/'manifest.json'),file_sha256={p.relative_to(fpc).as_posix():sha(p) for p in fpc.rglob('*') if p.is_file()})
                save(fpc/'result.json',result);save(fpc/'verified.json',pc.verify(fpc,'OFFLINE_SYNTHETIC_TEST'))
                reject('synthetic_not_board_'+scenario,lambda:pc.verify(fpc))
                if scenario=='normal':good_rx,good_tx=rx,tx
            else:
                reason='PP BYTE MISMATCH' if badpp else 'SCORE MISMATCH' if scenario=='score' else None
                reject(scenario,lambda:pc.exchange(w,m,fpc,model),reason)
                if badpp:
                    assert (fpc/'source.png').exists() and json.loads((fpc/'comparison.json').read_text())['all_10_scores_equal']
                    first=json.loads((fpc/'preprocess_comparison.json').read_text())['first_mismatch'];assert first['output_byte']==123
        packet=good_rx.index(b'CN02')+28*32+27*1024 # first source DATA after RGB DATA+END
        assert struct.unpack_from('<I',good_rx,packet+4)[0]==3
        def header(field,value):
            b=bytearray(good_rx);struct.pack_into('<I',b,packet+4+4*field,value);struct.pack_into('<I',b,packet+28,zlib.crc32(b[packet:packet+28])&0xffffffff);return bytes(b)
        mutants={'source_seq':header(1,2),'source_offset':header(2,1024),'source_kind':header(0,1),
            'source_total':header(4,27648),'source_short':good_rx[:packet+80],
            'source_payload_crc':good_rx[:packet+33]+bytes([good_rx[packet+33]^1])+good_rx[packet+34:]}
        for name,rx in mutants.items():
            folder=out/name;folder.mkdir();reject(name,lambda:pc.exchange(Fragmented(rx,good_tx),m,folder,model))
        r.update(status='SOURCE_EXPORT_SOFTWARE_CHECKS_PASS_NOT_HDL_NOT_BOARD',flows=flows,source_crc=f'{zlib.crc32(source)&0xffffffff:08x}',packets=1829,
            source_bytes=1843200,output_bytes=27648,reference_inputs='deterministic asymmetric full720p RGB565, never DUT-output derived')
    except BaseException as e:r.update(status='STOPPED_FIRST_OFFLINE_FAILURE',error=repr(e));raise
    finally:
        inputs=[Path(__file__),*list((ROOT/'tests/cnn_digits_photo').glob('*.*')),*list((ROOT/'tools/cnn_digits_photo').glob('*.py'))]
        r['input_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in inputs if p.is_file()}
        r['artifact_sha256']={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()};save(out/'review.json',r)
    print(json.dumps(dict(status=r['status'],scenarios=len(flows),rejections=len(r['checks']),packets=r['packets']),indent=2))
if __name__=='__main__':main()
