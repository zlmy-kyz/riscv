"""Build and audit isolated one-photo fixed DDR firmware; no HDL/PDS/serial."""
import argparse,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
TOOLS=ROOT/'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',default='photo_20261015_d');a=p.parse_args();assert re.fullmatch('[a-z0-9_]+',a.tag)
    out=HERE/'build'/a.tag;out.mkdir(parents=True,exist_ok=False)
    def run(label,name,argv):
        cmd=[str(TOOLS/('riscv-none-elf-'+name+'.exe')),*map(str,argv)]
        r=subprocess.run(cmd,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
        (out/(label+'.log')).write_text(r.stdout,encoding='utf-8');(out/(label+'.command.json')).write_text(json.dumps(dict(argv=cmd,cwd=str(out),returncode=r.returncode),indent=2)+'\n')
        assert r.returncode==0,(label,r.stdout)
    flags=['-march=rv32i','-mabi=ilp32','-O2','-std=c11','-g','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin',
           '-fno-pic','-fno-pie','-msmall-data-limit=0','-ffunction-sections','-fdata-sections','-fstack-usage',
           '-nostdlib','-nostartfiles','-Wl,--no-relax','-Wl,--build-id=none','-Wl,--gc-sections']
    elf=out/'program.elf';binary=out/'program.bin'
    run('compile','gcc',flags+[HERE/n for n in ('startup.S','main.c','preprocess_ref.c','pp01_wire.c')]+['-T',HERE/'linker.ld',f'-Wl,-Map={out}/program.map','-o',elf,'-lgcc'])
    for label,name,args in [('objcopy','objcopy',['-O','binary',elf,binary]),('readelf','readelf',['-h','-A','-l','-S',elf]),
        ('disassembly','objdump',['-d',elf]),('symbols','nm',['-n',elf]),('size','size',[elf])]:run(label,name,args)
    sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'));from application import audit
    (out/'symbols.txt').write_bytes((out/'symbols.log').read_bytes());info=audit(elf,binary,'crc32')
    # Reuse the existing static stack analysis, without rebuilding/changing its software.
    origin=ROOT/'tests/camera_preprocess_uart/build.py';spec=importlib.util.spec_from_file_location('prior_photo_stack',origin)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    functions=helper.parse_symbols(out/'symbols.txt');frames,edges,calls=helper.frame_from_disassembly((out/'disassembly.log').read_text(),functions)
    # fail sets failing=1 before text; uart_put then returns on timeout instead
    # of calling fail again. Preserve that context when bounding the call graph.
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
    inputs += list((ROOT/'tools/camera_preprocess_photo').glob('*.py'))
    inputs += [origin,ROOT/'tools/camera_uart/capture.py',ROOT/'tools/camera_uart/protocol.py',
               ROOT/'tools/uart_loader/candidates/bsp_workflow/plan.py',ROOT/'tools/uart_loader/candidates/bsp_workflow/application.py',
               ROOT/'tools/uart_loader/candidates/verify_run_hello/protocol.py',ROOT/'tests/uart_loader/candidates/verify_run_hello/image_to_dat.py']
    info.update(status='PHOTO_BUILD_STATIC_AUDIT_PASS',kind='camera_preprocess_photo',groups=1,
       source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in inputs},flags=flags,
       stack_depth_bytes=depth,board='NOT_RUN',HDL='NOT_RUN_USER_BOARD_FIRST',
       source=dict(buf=0,base='41000000',bytes=1843200),output=dict(base='42000000',bytes=27648),
       frame_contract='center 720x720 -> 96x96 RGB888/HWC; integer center NN; bit replication',
       source_held_until_full_export=True,retry_count=0)
    raw=binary.read_bytes();raw+=bytes((-len(raw))%4)
    (out/'program.dat').write_text(''.join(f'{int.from_bytes(raw[i:i+4],"little"):08x}\n' for i in range(0,len(raw),4)))
    (out/'manifest.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=info['status'],bytes=info['bytes'],sha256=info['bin_sha256'],CRC=f"{info['crc32']:08x}",stack=depth),indent=2))
if __name__=='__main__':main()
