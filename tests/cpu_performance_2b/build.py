"""Independent measurement BINs; preserve all successful BSP binaries/sources."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,re
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]; BSP=ROOT/'tests/bsp_workflow'
TOOL=ROOT/'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
from application import audit
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def build(name,tag):
    out=HERE/'build'/tag/name;out.mkdir(parents=True,exist_ok=False)
    port=(BSP/'core_portme.c').read_text()
    port=port.replace('#include "bsp.h"','#include "bsp.h"\n#include "perf.h"',1)
    port=port.replace('    p->portable_id = 1;', '    p->portable_id = 1;\n    perf_arm_timer_pair();',1)
    port=port.replace('    p->portable_id = 0;', '    perf_dump();\n    p->portable_id = 0;',1)
    (out/'core_portme.c').write_text(port)
    mode,n=name.rsplit('_',1);n=int(n)
    sources=[BSP/x for x in ('startup.S','trap.S','trap.c','uart.c','timer.c','crc32.c')]
    sources += [out/'core_portme.c',BSP/'ee_printf.c',HERE/'perf.c']
    sources += [ROOT/'coremark-main'/(x+'.c') for x in ('core_main','core_list_join','core_matrix','core_state','core_util')]
    flags=['-march=rv32i','-mabi=ilp32','-Os','-g','-Wall','-Wextra','-ffreestanding','-fno-builtin','-fno-pic','-fno-pie',
        '-msmall-data-limit=0','-ffunction-sections','-fdata-sections','-fstack-usage','-nostdlib','-nostartfiles',
        '-Wl,--no-relax','-Wl,--build-id=none','-Wl,--gc-sections','-I',str(BSP),'-I',str(HERE),'-I',str(ROOT/'coremark-main'),
        '-DTOTAL_DATA_SIZE=2000','-DCLOCKS_PER_SEC=93750000',f'-DITERATIONS={n}',f'-D{mode.upper()}_RUN=1',
        '-DFLAGS_STR="-Os -march=rv32i -mabi=ilp32; no LTO"']
    inputs=sources+[BSP/'core_portme.c',BSP/'core_portme.h',BSP/'bsp.h',BSP/'linker.ld',HERE/'perf.h',Path(__file__)]
    before={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    def run(tool,args,log):
        p=subprocess.run([str(TOOL/f'riscv-none-elf-{tool}.exe'),*map(str,args)],cwd=out,capture_output=True,text=True)
        (out/log).write_text(p.stdout+p.stderr); assert p.returncode==0,p.stdout+p.stderr
    elf=out/'program.elf';binary=out/'program.bin'
    run('gcc',flags+sources+['-T',BSP/'linker.ld',f'-Wl,-Map={out}/program.map','-o',elf,'-lgcc'],'compile.log')
    for tool,args,log in [('objcopy',['-O','binary',elf,binary],'objcopy.log'),('readelf',['-h','-A','-l','-S',elf],'program.readelf.txt'),
        ('objdump',['-d',elf],'program.dis'),('nm',['-n',elf],'symbols.txt'),('size',[elf],'size.txt')]:run(tool,args,log)
    info=audit(elf,binary,'coremark',mode,n)
    (out/'manifest.json').write_text(json.dumps(info,indent=2)+'\n')
    assert all(sha(ROOT/p)==h for p,h in before.items())
    (out/'build_receipt.json').write_text(json.dumps(dict(status='PERF2B_BUILD_PASS',source_sha256=before,info=info),indent=2)+'\n')
    print('RESULT: PASS',name,info['bytes'],info['crc32'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--application',choices=['all','performance_1','validation_1','performance_60','validation_60'],default='all');a=p.parse_args()
    assert re.fullmatch('[a-z0-9_-]+',a.tag)
    for name in ['performance_1','validation_1','performance_60','validation_60'] if a.application=='all' else [a.application]:build(name,a.tag)
