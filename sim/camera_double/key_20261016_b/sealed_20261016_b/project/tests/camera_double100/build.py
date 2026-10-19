"""Build a new fixed software image; preserve RTL, successful firmware and old runs."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PREV=ROOT/'tests/camera_uart'
TOOLS=ROOT/'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tag',default='abi2_20261016_d');ap.add_argument('--sim',action='store_true');a=ap.parse_args()
    assert re.fullmatch('[a-z0-9_]+',a.tag)
    out=HERE/'build'/a.tag;out.mkdir(parents=True,exist_ok=False)
    sources=[PREV/'startup.S',HERE/'main.c']
    inputs=[*sources,PREV/'linker.ld',Path(__file__),ROOT/'tools/camera_uart/double100.py',ROOT/'tools/camera_uart/loop100.py',ROOT/'tools/camera_uart/capture.py',
            ROOT/'tools/camera_uart/protocol.py',ROOT/'tools/uart_loader/candidates/bsp_workflow/application.py',
            ROOT/'tools/uart_loader/candidates/bsp_workflow/plan.py',ROOT/'tools/uart_loader/candidates/verify_run_hello/protocol.py',
            ROOT/'tests/uart_loader/candidates/verify_run_hello/image_to_dat.py']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    protected=[*(ROOT/'myriscv').glob('*.v'),ROOT/'RISCV.pds',*(ROOT/'tests/camera_uart/build/camera_uart_20261015_a').glob('*')]
    protect={p.relative_to(ROOT).as_posix():sha(p) for p in protected if p.is_file()}
    flags=['-march=rv32i','-mabi=ilp32','-O2','-std=c11','-g','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin',
           '-fno-pic','-fno-pie','-msmall-data-limit=0','-ffunction-sections','-fdata-sections','-fstack-usage',
           '-nostdlib','-nostartfiles','-Wl,--no-relax','-Wl,--build-id=none','-Wl,--gc-sections']
    def run(label,name,args):
        argv=[str(TOOLS/('riscv-none-elf-'+name+'.exe')),*map(str,args)]
        r=subprocess.run(argv,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
        (out/(label+'.log')).write_text(r.stdout,encoding='utf-8')
        (out/(label+'.command.json')).write_text(json.dumps(dict(argv=argv,cwd=str(out),returncode=r.returncode),indent=2)+'\n')
        if r.returncode:raise RuntimeError(r.stdout)
    if a.sim: flags += ['-DCAMERA_SIM','-DFRAME_WIDTH=64u','-DFRAME_HEIGHT=8u','-DTARGET_FRAMES=4u']
    elf=out/'program.elf';binary=out/'program.bin'
    run('compile','gcc',flags+sources+['-T',PREV/'linker.ld',f'-Wl,-Map={out}/program.map','-o',elf,'-lgcc'])
    for label,name,args in [('objcopy','objcopy',['-O','binary',elf,binary]),('readelf','readelf',['-h','-A','-l','-S',elf]),
                            ('disassembly','objdump',['-d',elf]),('symbols','nm',['-n',elf]),('size','size',[elf])]:run(label,name,args)
    sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
    from application import audit
    (out/'symbols.txt').write_bytes((out/'symbols.log').read_bytes());info=audit(elf,binary,'crc32')
    info.update(status='ABI2_SOFTWARE_STATIC_PASS',kind='camera_double100',source_sha256=hashes,protected_sha256=protect,flags=flags,
                frame=dict(base=0x41000000,width=1280,height=720,bytes=1843200,pixels=921600,beats=57600,drop_frames_first_stream=10),
                frames=4 if a.sim else 100,simulation=a.sim,ABI='43414d02',UART_baud=115200,CRC='IEEE reflected CRC32',timeouts_seconds=dict(config=5,capture=5,CPU_read=20,start=30),
                timing='32-bit CYCLE extended to 64-bit in software; sampled at least every 1024 frame words',
                board='NOT_RUN',full_CPU_HDL_simulation='NOT_RUN')
    if a.sim: info['frame'].update(width=64,height=8,bytes=1024,pixels=512,beats=32)
    raw=binary.read_bytes();padded=raw+b'\0'*((-len(raw))%4)
    (out/'program.dat').write_text(''.join(f'{int.from_bytes(padded[i:i+4],"little"):08x}\n' for i in range(0,len(padded),4)),encoding='ascii')
    for n,d in {**hashes,**protect}.items():assert sha(ROOT/n)==d,n
    (out/'manifest.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=info['status'],bytes=info['bytes'],bin_sha256=info['bin_sha256'],crc32=f"{info['crc32']:08x}",serial_opened=False,PDS_started=False),indent=2))
if __name__=='__main__':main()
