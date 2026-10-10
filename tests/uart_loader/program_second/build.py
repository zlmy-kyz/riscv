"""Build the second DDR application once, retaining successful Hello/Loader."""
from pathlib import Path
import json,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'build'
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/applications_stage3'))
from application import audit
TOOL=ROOT/'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
assert not (OUT/'program.elf').exists();OUT.mkdir(exist_ok=True)
def command(name,args,log):
    p=subprocess.run([str(TOOL/('riscv-none-elf-'+name+'.exe')),*map(str,args)],capture_output=True,text=True)
    (OUT/log).write_text(p.stdout+p.stderr)
    assert p.returncode==0,p.stdout+p.stderr
command('gcc',['-march=rv32i','-mabi=ilp32','-Os','-g','-Wall','-Wextra','-Werror','-ffreestanding',
               '-fno-builtin','-fno-pic','-fno-pie','-msmall-data-limit=0','-nostdlib','-nostartfiles',
               '-Wl,--no-relax','-Wl,--build-id=none','-T',HERE/'linker.ld',f'-Wl,-Map={OUT}/program.map',
               '-o',OUT/'program.elf',HERE/'startup.S',HERE/'main.c','-lgcc'],'compile.log')
command('objcopy',['-O','binary',OUT/'program.elf',OUT/'program.bin'],'objcopy.log')
command('readelf',['-h','-A','-l','-S',OUT/'program.elf'],'program.readelf.txt')
command('objdump',['-d',OUT/'program.elf'],'program.dis')
command('nm',['-n',OUT/'program.elf'],'symbols.txt')
info=audit(OUT/'program.elf',OUT/'program.bin','second')
(OUT/'manifest.json').write_text(json.dumps(info,indent=2)+'\n')
print('RESULT: PASS second application built and audited',info['bytes'],'bytes',f'CRC32={info["crc32"]:08X}')
