"""Build a fixed DDR Loader application; no PDS, serial or HDL execution."""
import argparse,hashlib,importlib.util,json,re,subprocess,sys,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
TOOLS=ROOT/'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tag',default='camera_uart_20261015_a');a=ap.parse_args()
    assert re.fullmatch('[a-z0-9_]+',a.tag)
    out=HERE/'build'/a.tag;out.mkdir(parents=True,exist_ok=False)
    sources=[HERE/n for n in ['startup.S','main.c','crc32.c']]
    inputs=[*sources,HERE/'crc32.h',HERE/'linker.ld',Path(__file__),
            ROOT/'tools/camera_uart/capture.py',ROOT/'tools/camera_uart/protocol.py',
            ROOT/'tools/uart_loader/candidates/bsp_workflow/application.py',ROOT/'tools/uart_loader/candidates/bsp_workflow/plan.py',
            ROOT/'tools/uart_loader/candidates/verify_run_hello/protocol.py',ROOT/'tests/uart_loader/candidates/verify_run_hello/image_to_dat.py']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    # Bind current board contract and protect all design files from this software build.
    design={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'myriscv').glob('*.v')}
    flags=['-march=rv32i','-mabi=ilp32','-O2','-std=c11','-g','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin',
           '-fno-pic','-fno-pie','-msmall-data-limit=0','-ffunction-sections','-fdata-sections','-fstack-usage',
           '-nostdlib','-nostartfiles','-Wl,--no-relax','-Wl,--build-id=none','-Wl,--gc-sections']
    def run(label,name,args):
        argv=[str(TOOLS/('riscv-none-elf-'+name+'.exe')),*map(str,args)]
        r=subprocess.run(argv,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
        (out/(label+'.log')).write_text(r.stdout,encoding='utf-8')
        (out/(label+'.command.json')).write_text(json.dumps(dict(argv=argv,cwd=str(out),returncode=r.returncode),indent=2)+'\n')
        if r.returncode:raise RuntimeError(r.stdout)
    elf=out/'program.elf';binary=out/'program.bin'
    run('compile','gcc',flags+sources+['-T',HERE/'linker.ld',f'-Wl,-Map={out}/program.map','-o',elf,'-lgcc'])
    for label,name,args in [('objcopy','objcopy',['-O','binary',elf,binary]),('readelf','readelf',['-h','-A','-l','-S',elf]),
                            ('disassembly','objdump',['-d',elf]),('symbols','nm',['-n',elf]),('size','size',[elf])]:run(label,name,args)
    # Reuse the proven generic ELF/section/RV32I audit; the token does not run a CRC application.
    sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
    from application import audit
    (out/'symbols.txt').write_bytes((out/'symbols.log').read_bytes())
    info=audit(elf,binary,'crc32');info.update(status='CAMERA_UART_BUILD_STATIC_AUDIT_PASS',kind='camera_uart',
        source_sha256=hashes,design_contract_sha256=design,flags=flags,
        frame=dict(base=0x41000000,width=1280,height=720,bytes=1843200,pixels=921600,beats=57600),
        UART_baud=115200,chunk=1024,CRC='IEEE reflected CRC32',full_CPU_HDL_simulation='NOT_RUN')
    # DAT is a DDR program representation only, never a replacement ROM/RAM initialization image.
    raw=binary.read_bytes();padded=raw+b'\0'*((-len(raw))%4)
    (out/'program.dat').write_text(''.join(f'{int.from_bytes(padded[i:i+4],"little"):08x}\n' for i in range(0,len(padded),4)),encoding='ascii')
    for n,d in {**hashes,**design}.items():assert sha(ROOT/n)==d,n
    (out/'manifest.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=info['status'],bytes=info['bytes'],bin_sha256=info['bin_sha256'],crc32=f"{info['crc32']:08x}",serial_opened=False,PDS_started=False),indent=2))

if __name__=='__main__':main()
