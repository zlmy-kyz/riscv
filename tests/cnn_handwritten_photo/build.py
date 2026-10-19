"""Build and audit isolated digits10 diagnostic DDR firmware; no HDL/PDS/serial."""
import argparse,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
TOOLS=ROOT/'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',default='handwritten_20261017_a');a=p.parse_args();assert re.fullmatch('[a-z0-9_]+',a.tag)
    out=HERE/'build'/a.tag;out.mkdir(parents=True,exist_ok=False)
    def run(label,name,argv):
        cmd=[str(TOOLS/('riscv-none-elf-'+name+'.exe')),*map(str,argv)]
        r=subprocess.run(cmd,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
        (out/(label+'.log')).write_text(r.stdout,encoding='utf-8');(out/(label+'.command.json')).write_text(json.dumps(dict(argv=cmd,cwd=str(out),returncode=r.returncode),indent=2)+'\n')
        assert r.returncode==0,(label,r.stdout)
    sys.path.insert(0,str(ROOT/'tools/cnn_handwritten_photo'))
    import reference
    model=reference.load(ROOT/'sim/cnn/training/handwritten_run_20261017_a/model')
    words=model['words']
    text='#ifndef HANDWRITTEN_MODEL_DATA_H\n#define HANDWRITTEN_MODEL_DATA_H\n'
    text+=f"#define MODEL_ID 0x{model['meta']['model_id']:08x}u\n#define MODEL_CRC 0x{model['meta']['load_crc32']:08x}u\n#define MODEL_WORDS 6222u\n"
    text+='static const uint32_t model_words[6222] = {\n'
    text+=''.join('    '+','.join(f'0x{value:08x}u' for value in words[start:start+8])+',\n' for start in range(0,6222,8))
    text+='};\n#endif\n'
    (out/'model_data.h').write_text(text,encoding='ascii')
    flags=['-march=rv32i','-mabi=ilp32','-O2','-std=c11','-g','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin',
           '-fno-pic','-fno-pie','-msmall-data-limit=0','-ffunction-sections','-fdata-sections','-fstack-usage',
           '-nostdlib','-nostartfiles','-Wl,--no-relax','-Wl,--build-id=none','-Wl,--gc-sections']
    elf=out/'program.elf';binary=out/'program.bin'
    run('compile','gcc',flags+['-I',out]+[HERE/n for n in ('startup.S','main.c','pp01_wire.c')]+['-T',HERE/'linker.ld',f'-Wl,-Map={out}/program.map','-o',elf,'-lgcc'])
    for label,name,args in [('objcopy','objcopy',['-O','binary',elf,binary]),('readelf','readelf',['-h','-A','-l','-S',elf]),
        ('disassembly','objdump',['-d',elf]),('symbols','nm',['-n',elf]),('size','size',[elf])]:run(label,name,args)
    sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'));from application import audit
    (out/'symbols.txt').write_bytes((out/'symbols.log').read_bytes());info=audit(elf,binary,'crc32')
    origin=ROOT/'tests/camera_preprocess_uart/build.py';spec=importlib.util.spec_from_file_location('prior_photo_stack',origin)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    functions=helper.parse_symbols(out/'symbols.txt');frames,edges,calls=helper.frame_from_disassembly((out/'disassembly.log').read_text(),functions)
    def visit(name,diagnostic=False,path=()):
        diagnostic=diagnostic or name=='fail';key=(name,diagnostic)
        assert key not in path,('unbounded call cycle',path,key)
        children=[visit(n,diagnostic,path+(key,)) for n in edges.get(name,())
                  if not (diagnostic and name=='uart_put' and n=='fail')]
        value,chain=max(children,default=(0,[]),key=lambda x:x[0])
        return frames.get(name,0)+value,[name]+chain
    depth,chain=max((visit(n) for n in frames),key=lambda x:x[0]);assert depth<4096
    su={}
    for path in out.glob('*.su'):su.update(helper.stack_usage(path))
    assert all(frames.get(n,v)==v for n,v in su.items()),'stack usage/disassembly mismatch'
    (out/'stack_depth.json').write_text(json.dumps(dict(bytes=depth,chain=chain,frames=frames,call_edges=len(calls),
        diagnostic_guard='failing=1 disables uart_put -> fail recursion',su_matches_disassembly=True),indent=2)+'\n')
    inputs=[p for p in HERE.iterdir() if p.suffix in ('.c','.h','.S','.ld','.py')]
    inputs += list((ROOT/'tools/cnn_handwritten_photo').glob('*.py'))
    inputs += list((ROOT/'sim/cnn/training/handwritten_run_20261017_a/model').iterdir())
    inputs += [ROOT/'tools/camera_preprocess_photo/reference.py']
    inputs += [ROOT/'doc/cnn/digits10_int8_v1.json']
    inputs += [ROOT/'tools/cnn_digits_training/integer_reference.py',
               ROOT/'sim/cnn/training/handwritten_run_20261017_a/sealed_manifest.json',
               ROOT/'sim/cnn/training/handwritten_sol_review_20261017_01.json',
               ROOT/'sim/cnn/training/handwritten_sol_numeric_review_20261017_01.json']
    inputs += [origin,ROOT/'tools/camera_uart/capture.py',ROOT/'tools/camera_uart/protocol.py',
               ROOT/'tools/uart_loader/candidates/bsp_workflow/plan.py',ROOT/'tools/uart_loader/candidates/bsp_workflow/application.py',
               ROOT/'tools/uart_loader/candidates/verify_run_hello/protocol.py',ROOT/'tests/uart_loader/candidates/verify_run_hello/image_to_dat.py']
    sys.path.insert(0,str(ROOT/'tools/cnn_handwritten_photo'));import reference
    model=reference.load(ROOT/'sim/cnn/training/handwritten_run_20261017_a/model')
    info.update(status='CNN_HANDWRITTEN_BUILD_STATIC_AUDIT_PASS',kind='cnn_handwritten_photo',groups=1,trained_model=model['meta'],
       trained_digit_accuracy=False,timing='EXISTING_REPORT_MET_BOARD_PHASE_UNMEASURED',key_HDL='NOT_COMPLETED',
       source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in inputs},flags=flags,
       stack_depth_bytes=depth,board='NOT_RUN',HDL='NOT_RUN_USER_BOARD_FIRST',
       source=dict(buf=0,base='41000000',bytes=1843200),output=dict(base='42000000',bytes=27648),
       frame_contract='digits10_int8_v1; actual RGB96 -> 32 gray -> Conv8/16/32 -> GAP16 -> FC10',
       source_held_until_full_export=True,full_source_export='PC_SELECTABLE_D_OR_d',wire_magic='CN03',retry_count=0)
    raw=binary.read_bytes()
    offset=info['symbols']['model_words']-info['base']
    assert raw[offset:offset+24888]==(ROOT/'sim/cnn/training/handwritten_run_20261017_a/model/load_words.bin').read_bytes(),'ELF model words differ'
    info['embedded_model_words_equal']=True
    info['generated_header_sha256']=sha(out/'model_data.h')
    raw+=bytes((-len(raw))%4)
    (out/'program.dat').write_text(''.join(f'{int.from_bytes(raw[i:i+4],"little"):08x}\n' for i in range(0,len(raw),4)))
    (out/'manifest.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=info['status'],bytes=info['bytes'],sha256=info['bin_sha256'],CRC=f"{info['crc32']:08x}",stack=depth),indent=2))
if __name__=='__main__':main()

