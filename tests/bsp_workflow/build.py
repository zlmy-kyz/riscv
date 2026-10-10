"""One GCC -> ELF -> BIN -> strict audit entry; never overwrite successful builds."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
from application import audit
NAMES=['hello','crc32','irq_probe','performance_1','validation_1','performance_60','validation_60']
TOOL=ROOT/'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(name,tag):
    out=HERE/('build' if tag is None else 'build_versions/'+tag)/name
    assert not out.exists(),'Preserve build; choose a new --tag'
    out.mkdir(parents=True)
    sources=[HERE/n for n in ('startup.S','trap.S','trap.c','uart.c','timer.c','crc32.c')]
    flags=['-march=rv32i','-mabi=ilp32','-Os','-g','-Wall','-Wextra','-ffreestanding','-fno-builtin','-fno-pic','-fno-pie','-msmall-data-limit=0',
           '-ffunction-sections','-fdata-sections','-fstack-usage','-nostdlib','-nostartfiles','-Wl,--no-relax','-Wl,--build-id=none','-Wl,--gc-sections','-I',str(HERE)]
    mode=n=None
    if name in ('hello','crc32','irq_probe'):
        sources.append(HERE/('main_irq.c' if name=='irq_probe' else 'main_'+name+'.c'));kind=name
    else:
        mode,n=name.rsplit('_',1);n=int(n);kind='coremark'
        flags+=['-DTOTAL_DATA_SIZE=2000','-DCLOCKS_PER_SEC=93750000',f'-DITERATIONS={n}',f'-D{mode.upper()}_RUN=1',
                '-DFLAGS_STR="-Os -march=rv32i -mabi=ilp32; no LTO"','-I',str(ROOT/'coremark-main')]
        sources += [HERE/'core_portme.c',HERE/'ee_printf.c']+[ROOT/'coremark-main'/(a+'.c') for a in ('core_main','core_list_join','core_matrix','core_state','core_util')]
    tracked=sources+[HERE/'bsp.h',HERE/'linker.ld',HERE/'build.py']
    if kind=='coremark':tracked += [HERE/'core_portme.h',ROOT/'coremark-main/coremark.h']
    before={p.relative_to(ROOT).as_posix():sha(p) for p in tracked}
    def command(tool,args,log):
        result=subprocess.run([str(TOOL/('riscv-none-elf-'+tool+'.exe')),*map(str,args)],cwd=out,capture_output=True,text=True)
        (out/log).write_text(result.stdout+result.stderr)
        assert result.returncode==0,result.stdout+result.stderr
    elf=out/'program.elf';binary=out/'program.bin'
    command('gcc',flags+list(map(str,sources))+['-T',str(HERE/'linker.ld'),f'-Wl,-Map={out}/program.map','-o',str(elf),'-lgcc'],'compile.log')
    for tool,args,log in [('objcopy',['-O','binary',elf,binary],'objcopy.log'),('readelf',['-h','-A','-l','-S',elf],'program.readelf.txt'),('objdump',['-d',elf],'program.dis'),('nm',['-n',elf],'symbols.txt'),('size',[elf],'size.txt')]:command(tool,args,log)
    info=audit(elf,binary,kind,mode,n)
    (out/'manifest.json').write_text(json.dumps(info,indent=2)+'\n')
    assert all(sha(ROOT/p)==h for p,h in before.items())
    (out/'build_receipt.json').write_text(json.dumps(dict(status='UNIFIED_BSP_BUILD_PASS',application=name,source_sha256=before,application_info=info),indent=2)+'\n')
    print('RESULT: PASS',name,info['bytes'],'bytes',f'CRC32={info["crc32"]:08X}')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--application',choices=NAMES+['all'],default='all');p.add_argument('--tag');a=p.parse_args()
    if a.tag:
        import re
        assert re.fullmatch('[a-z0-9_-]+',a.tag)
    for name in NAMES if a.application=='all' else [a.application]:build(name,a.tag)
