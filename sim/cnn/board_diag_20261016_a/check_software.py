"""Offline software checks only. Native MMIO device is not RTL or a real CPU."""
import argparse,hashlib,json,shutil,struct,subprocess,sys,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/cnn_digits_diag'))
import reference,run as pc
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',default='checks_01');args=parser.parse_args()
    out=HERE/args.tag;out.mkdir(exist_ok=False);report=dict(status='RUNNING',evidence_origin='OFFLINE_SYNTHETIC_TEST',
        real_CPU=False,HDL=False,serial_opened=False,PDS=False,board=False,checks=[])
    def command(label,argv):
        p=subprocess.run(list(map(str,argv)),cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
        (out/(label+'.log')).write_bytes(p.stdout);js(out/(label+'.command.json'),dict(argv=list(map(str,argv)),returncode=p.returncode))
        assert p.returncode==0,(label,p.stdout.decode(errors='replace'));return p.stdout
    def reject(label,fn,contains=None):
        try:fn()
        except (ValueError,AssertionError) as e:
            if contains:assert contains in str(e),(label,str(e))
            report['checks'].append(dict(name=label,rejected=True,error=str(e)));return
        raise AssertionError('wrongly accepted '+label)
    try:
        m=pc.image(pc.DEFAULT);model=reference.load(pc.MODEL)
        command('compile_reference',['D:/mingw64/bin/gcc.exe','-O2','-std=c11','-Wall','-Wextra','-Werror',ROOT/'tests/cnn_digits_diag/native_reference.c','-o',out/'reference.exe'])
        command('compile_actual_firmware_native',['D:/mingw64/bin/gcc.exe','-O2','-std=c11','-Wall','-Wextra','-Werror','-Wno-int-to-pointer-cast',ROOT/'tests/cnn_digits_diag/native_flow.c',ROOT/'tests/cnn_digits_diag/pp01_wire.c','-o',out/'flow.exe'])
        command('wide_RHA', [out/'reference.exe','vectors'])
        for a,s,want in [(-1,1,-1),(1,1,1),(-3,1,-2),(3,1,2),(-2**31,31,-1),(2**31-1,31,1),(-17,0,-17)]:assert reference.rha(a,s)==want
        assert len(model['words'])==6222 and all(model['biases']) and all(model['weights']) and min(model['weights'])<0<max(model['weights'])
        gradient=bytes(v for y in range(96) for x in range(96) for v in ((x*3+y*5+7)&255,(x*11+y*7+31)&255,(x*x+13*y+79)&255))
        patterns={name:bytes(rgb)*9216 for name,rgb in [('black',(0,0,0)),('white',(255,255,255)),('mid',(128,128,128)),('red',(255,0,0)),('green',(0,255,0)),('blue',(0,0,255))]}
        patterns['asymmetric']=gradient;results={}
        for name,rgb in patterns.items():
            folder=out/name;folder.mkdir();(folder/'rgb96.bin').write_bytes(rgb)
            result=reference.infer(rgb,model);reference.save_trace(folder,result)
            for y,x in [(0,0),(0,31),(31,0),(31,31),(7,19)]:
                p=3*((3*y+1)*96+3*x+1);r,g,b=rgb[p:p+3]
                assert result['layers']['gray32'][32*y+x]==(77*r+150*g+29*b+128)//256-128
            command('reference_'+name,[out/'reference.exe',folder/'rgb96.bin',pc.MODEL/'load_words.bin',folder/'native.trace'])
            expected=b''.join(bytes(v&255 for v in a) for a in result['layers'].values())+struct.pack('<10i',*result['scores'])
            assert len(expected)==4680 and expected==(folder/'native.trace').read_bytes(),name
            results[name]=dict(scores=result['scores'],prediction=result['prediction'],stats=result['stats'],tensor_sha256={k:sha(folder/(k+'.bin')) for k in result['layers']})
        assert len({tuple(r['scores']) for r in results.values()})>=4,'diagnostic model insensitive'
        report['reference_patterns']=results;report['max_accumulator_bound']=model['max_bound'];report['model']=model['meta']
        # Corruption with recomputed container hashes must still violate ABI/contract checks.
        def bad_model(name,mutate):
            folder=out/('bad_model_'+name);shutil.copytree(pc.MODEL,folder);meta=json.loads((folder/'model.json').read_text())
            mutate(folder,meta)
            meta['sha256']={n:sha(folder/n) for n in meta['sha256']};js(folder/'model.json',meta)
            reject('model_'+name,lambda:reference.load(folder))
        bad_model('minus128',lambda f,m:(f/'weights.bin').write_bytes(bytes([128])+(f/'weights.bin').read_bytes()[1:]))
        bad_model('signextended_word',lambda f,m:(f/'load_words.bin').write_bytes(b'\xfd\xff\xff\xff'+(f/'load_words.bin').read_bytes()[4:]))
        bad_model('shift32',lambda f,m:m['shifts'].__setitem__(0,32))
        bad_model('scale_chain',lambda f,m:m['scales'][1].__setitem__('Fin',4))
        bad_model('crc',lambda f,m:m.__setitem__('load_crc32',m['load_crc32']^1))
        bad_model('short',lambda f,m:(f/'load_words.bin').write_bytes((f/'load_words.bin').read_bytes()[:-4]))
        bad_model('model_id',lambda f,m:m.__setitem__('model_id',m['model_id']^1))
        scenarios=['normal','no_tail','model_valid','count','cnn_error','timeout','identity','reads','gray_count','ack','release','score']
        flow={}
        for name in scenarios:
            folder=out/('flow_'+name);folder.mkdir();prefix=folder/'run'
            raw=command('flow_'+name,[out/'flow.exe',out/'asymmetric/rgb96.bin',out/'asymmetric/scores.bin',pc.MODEL/'load_words.bin',name,prefix])
            ledger=json.loads(raw);flow[name]=ledger
            assert ledger['model_words']==6222 and ledger['model_crc']==model['meta']['load_crc32']
            assert ledger['camera_starts']<=1 and ledger['pp_starts']<=1 and ledger['cnn_starts']<=1
            tx=Path(str(prefix)+'.fw.tx.bin').read_bytes()
            if name in ('normal','no_tail','score'):
                assert ledger['status']==2 and b'CNN_DIAG_DONE JOBS=1' in tx
                assert ledger['releases']==(1 if name=='no_tail' else 2)
            else:assert ledger['status']==3 and b'CNN_FAIL REASON=' in tx and b'CNN_DIAG_DONE' not in tx
        report['native_firmware_scenarios']=flow
        loader=pc.loader_plan(m);loader_rx=b''.join(bytes.fromhex(p['expected_hex']) for p in loader);loader_tx=b''.join(bytes.fromhex(p['tx_hex']) for p in loader)
        def wire_for(name):
            prefix=out/('flow_'+name)/'run'
            return loader_rx+Path(str(prefix)+'.fw.tx.bin').read_bytes(),loader_tx+Path(str(prefix)+'.fw.rx.bin').read_bytes()
        # Exercise exact/line with fragmented binary reads, not an in-memory summary API.
        class Fragmented(pc.Replay):
            def read(self,n):
                if self.rx_count==len(self.rx):raise ValueError('offline short raw RX')
                return super().read(min(n,7))
        for name in ('normal','no_tail'):
            folder=out/('pc_'+name);folder.mkdir();rx,tx=wire_for(name);w=Fragmented(rx,tx)
            session=pc.exchange(w,m,folder,model);assert w.rx_count==len(rx) and w.tx_count==len(tx)
            (folder/'uart.rx.bin').write_bytes(rx);(folder/'uart.tx.bin').write_bytes(tx)
            shutil.copyfile(pc.DEFAULT,folder/'manifest.json');shutil.copyfile(ROOT/m['bin_path'],folder/'application.bin');shutil.copytree(pc.MODEL,folder/'model')
            r=dict(status='CNN_DIAG_ONE_JOB_SCORES_PASS',evidence_origin='OFFLINE_SYNTHETIC_TEST',application=m,session=session,
                manifest_sha256=sha(folder/'manifest.json'),file_sha256={p.relative_to(folder).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()})
            js(folder/'result.json',r);verified=pc.verify(folder,'OFFLINE_SYNTHETIC_TEST');js(folder/'verified.json',verified)
            reject('synthetic_cannot_be_board_'+name,lambda:pc.verify(folder))
        for name in scenarios[2:]:
            rx,tx=wire_for(name);folder=out/('pc_reject_'+name);folder.mkdir()
            reject('PC_'+name,lambda:pc.exchange(Fragmented(rx,tx),m,folder,model), 'SCORE MISMATCH' if name=='score' else None)
        rx,tx=wire_for('normal');packet=rx.index(b'CN01');end=packet+27*(32+1024)
        def mutate_header(offset,field,value):
            b=bytearray(rx);struct.pack_into('<I',b,offset+4+4*field,value);struct.pack_into('<I',b,offset+28,zlib.crc32(b[offset:offset+28])&0xffffffff);return bytes(b)
        mutations={'header_crc':rx[:packet+28]+bytes([rx[packet+28]^1])+rx[packet+29:],
            'payload_crc':rx[:packet+32]+bytes([rx[packet+32]^1])+rx[packet+33:],
            'seq':mutate_header(packet,1,2),'offset':mutate_header(packet,2,1024),
            'short':rx[:packet+99],'end_crc':mutate_header(end,5,0),
            'unclosed_ledger':rx.replace(b'CNN_RELEASED CLAIMS=2',b'CNN_RELEASED CLAIMS=1'),
            'wrong_class':rx.replace(b'CLASS='+str(results['asymmetric']['prediction']).encode(),b'CLASS=9'),
            'error_status':rx.replace(b'ERROR=00000000 CLASS=',b'ERROR=00000001 CLASS=')}
        for name,data in mutations.items():
            folder=out/('pc_mutate_'+name);folder.mkdir()
            reject('wire_'+name,lambda:pc.exchange(Fragmented(data,tx),m,folder,model))
        report['checks'].append(dict(name='independent_C_int64_vs_Python_wide',patterns=len(patterns),all_layer_bytes_and_scores_equal=True))
        report['status']='SOFTWARE_OFFLINE_CHECKS_PASS_NOT_HDL_NOT_BOARD'
    except BaseException as e:report.update(status='STOPPED_FIRST_OFFLINE_FAILURE',error=repr(e));raise
    finally:
        report['input_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),*list((ROOT/'tests/cnn_digits_diag').glob('*.*')),*list((ROOT/'tools/cnn_digits_diag').glob('*.py'))] if p.is_file()}
        report['artifact_sha256']={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
        js(out/'review.json',report)
    print(json.dumps(dict(status=report['status'],patterns=len(results),native_scenarios=len(flow),rejections=len(report['checks'])-1,folder=str(out)),indent=2))
if __name__=='__main__':main()
