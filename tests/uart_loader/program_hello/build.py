"""Build and independently bind one real DDR application ELF/BIN/manifest."""
from pathlib import Path
import hashlib,json,struct,subprocess,zlib,importlib.util
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BIN=ROOT/'xpack-riscv-none-elf-gcc-15.2.0-1/bin';OUT=HERE/'build'

def command(name,args,log):
    p=subprocess.run([str(BIN/('riscv-none-elf-'+name+'.exe')),*map(str,args)],capture_output=True,text=True)
    (OUT/log).write_text(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)

def audit():
    raw=(OUT/'program.elf').read_bytes();data=(OUT/'program.bin').read_bytes()
    assert raw[:6]==b'\x7fELF\x01\x01' and struct.unpack_from('<H',raw,18)[0]==243
    assert struct.unpack_from('<I',raw,24)[0]==0x40000000 and struct.unpack_from('<I',raw,36)[0]==0
    off=struct.unpack_from('<I',raw,32)[0];size,count,si=struct.unpack_from('<HHH',raw,46)
    headers=[struct.unpack_from('<10I',raw,off+i*size) for i in range(count)]
    names=raw[headers[si][4]:headers[si][4]+headers[si][5]];sections={}
    expected=bytearray(len(data));covered=bytearray(len(data))
    for h in headers:
        name=names[h[0]:names.index(0,h[0])].decode()
        if not h[2]&2 or not h[5]:continue
        assert name in ('.text','.rodata','.data','.image_tail','.bss'),name
        assert 0x40000000<=h[3]<h[3]+h[5]<=0x4000F000
        sections[name]=dict(address=h[3],size=h[5],type=h[1])
        if h[1]!=8:
            start=h[3]-0x40000000;assert start+h[5]<=len(data)
            expected[start:start+h[5]]=raw[h[4]:h[4]+h[5]];covered[start:start+h[5]]=b'\1'*h[5]
    assert expected==data and len(data)>256 and len(data)%4==3
    assert sections['.data']['size']>0 and sections['.bss']['type']==8 and sections['.bss']['size']>0
    assert sections['.bss']['address']>=(0x40000000+len(data)+3)&~3
    assert data[-3:]==bytes([0x5a,0xc3,0x7e])
    phoff=struct.unpack_from('<I',raw,28)[0];phsize,phnum=struct.unpack_from('<HH',raw,42)
    for i in range(phnum):
        p=struct.unpack_from('<8I',raw,phoff+i*phsize)
        if p[0]==1:assert p[2]==p[3] and 0x40000000<=p[2] and p[2]+p[5]<=0x4000F000
    spec=importlib.util.spec_from_file_location('isa',ROOT/'tests/uart_loader/candidates/load_stage10/image_to_dat.py')
    isa=importlib.util.module_from_spec(spec);spec.loader.exec_module(isa)
    text=sections['.text'];code=data[:text['size']]
    assert len(code)%4==0 and all(isa.legal_instruction(int.from_bytes(code[i:i+4],'little')) for i in range(0,len(code),4))
    files=[p for p in HERE.iterdir() if p.is_file()]+[p for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json']
    manifest=dict(status='HELLO_PROGRAM_ELF_BIN_AUDIT_PASS',entry=0x40000000,base=0x40000000,
                  bytes=len(data),crc32=zlib.crc32(data)&0xffffffff,bin_sha256=hashlib.sha256(data).hexdigest(),
                  sections=sections,bss_in_bin=False,execution_candidate=True,isa='rv32i',abi='ilp32',
                  sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('RESULT: PASS real program ELF/BIN',len(data),'bytes; data/bss nonempty; RV32I; no execution')

if __name__=='__main__':
    assert not (OUT/'program.elf').exists(), 'Do not rebuild an existing application ELF/BIN'
    OUT.mkdir(exist_ok=True)
    if (OUT/'compile.log').exists():
        failed=OUT/'compile_failed_initial.log'
        assert not failed.exists()
        failed.write_bytes((OUT/'compile.log').read_bytes())
    command('gcc',['-march=rv32i','-mabi=ilp32','-Os','-g','-Wall','-Wextra','-Werror','-ffreestanding',
                  '-fno-builtin','-fno-pic','-fno-pie','-msmall-data-limit=0','-nostdlib','-nostartfiles',
                  '-Wl,--no-relax','-Wl,--build-id=none','-T',HERE/'linker.ld',f'-Wl,-Map={OUT}/program.map',
                  '-o',OUT/'program.elf',HERE/'startup.S',HERE/'main.c','-lgcc'],'compile.log')
    command('objcopy',['-O','binary',OUT/'program.elf',OUT/'program.bin'],'objcopy.log')
    command('readelf',['-h','-A','-l','-S',OUT/'program.elf'],'program.readelf.txt')
    command('objdump',['-d',OUT/'program.elf'],'program.dis')
    command('nm',['-n',OUT/'program.elf'],'symbols.txt')
    audit()
