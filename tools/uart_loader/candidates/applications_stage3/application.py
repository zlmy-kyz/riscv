"""Audit DDR ELF/BIN and parse actual application output independently of Loader."""
from pathlib import Path
import hashlib,importlib.util,json,re,struct,zlib
ROOT=Path(__file__).resolve().parents[4]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BASE=0x40000000;LIMIT=61440;HZ=93750000
EXPECTED={'performance':('e9f5','e714','1fd7','8e3a'), 'validation':('18f2','e3c1','0747','8d84')}
TIME_ERROR='ERROR! Must execute for at least 10 secs for a valid result!'
SECOND=b'SECOND_PROGRAM_PASS sum=11440\r\n'

def audit(elf,bin_file,kind,mode=None,iterations=None):
    elf=Path(elf).resolve();bin_file=Path(bin_file).resolve();raw=elf.read_bytes();payload=bin_file.read_bytes()
    assert raw[:6]==b'\x7fELF\x01\x01' and struct.unpack_from('<H',raw,18)[0]==243
    assert struct.unpack_from('<I',raw,24)[0]==BASE and struct.unpack_from('<I',raw,36)[0]==0
    assert 4<=len(payload)<=LIMIT
    shoff=struct.unpack_from('<I',raw,32)[0];shsize,count,si=struct.unpack_from('<HHH',raw,46)
    headers=[struct.unpack_from('<10I',raw,shoff+i*shsize) for i in range(count)]
    names=raw[headers[si][4]:headers[si][4]+headers[si][5]];sections={};expected=bytearray(len(payload))
    spec=importlib.util.spec_from_file_location('isa',ROOT/'tests/uart_loader/candidates/verify_run_hello/image_to_dat.py')
    isa=importlib.util.module_from_spec(spec);spec.loader.exec_module(isa)
    insns=0
    for h in headers:
        name=names[h[0]:names.index(0,h[0])].decode()
        if not h[2]&2 or not h[5]:continue
        assert name in ('.text','.rodata','.data','.image_tail','.bss'),name
        assert BASE<=h[3]<h[3]+h[5]<=BASE+LIMIT
        sections[name]=dict(address=h[3],size=h[5],type=h[1])
        if h[1]!=8:
            offset=h[3]-BASE;assert offset+h[5]<=len(payload)
            expected[offset:offset+h[5]]=raw[h[4]:h[4]+h[5]]
        if h[2]&4:
            code=raw[h[4]:h[4]+h[5]];assert len(code)%4==0
            for i in range(0,len(code),4):assert isa.legal_instruction(int.from_bytes(code[i:i+4],'little')),(name,i)
            insns+=len(code)//4
    assert expected==payload and sections['.data']['size']>0 and sections['.bss']['type']==8
    assert sections['.bss']['address']>=((BASE+len(payload)+3)&~3)
    phoff=struct.unpack_from('<I',raw,28)[0];phsize,phnum=struct.unpack_from('<HH',raw,42)
    for i in range(phnum):
        p=struct.unpack_from('<8I',raw,phoff+i*phsize)
        if p[0]==1:assert p[2]==p[3] and BASE<=p[2] and p[2]+p[5]<=BASE+LIMIT
    symbols={n:int(a,16) for a,_,n in re.findall(r'^([0-9a-f]+)\s+(\w)\s+(\S+)$',elf.with_name('symbols.txt').read_text(),re.M)}
    assert symbols['__stack_top']==BASE+65536 and symbols['__stack_bottom']==BASE+LIMIT
    sp=[]
    for i in range(0,64,4):
        w=int.from_bytes(payload[i:i+4],'little')
        if w&0xfff==0x117:sp.append(dict(pc=BASE+i,value=(BASE+i+(w&0xfffff000))&0xffffffff))
    assert len(sp)==1
    if kind=='coremark':assert mode in EXPECTED and iterations in (1,60)
    return dict(status='DDR_APPLICATION_AUDIT_PASS',kind=kind,mode=mode,iterations=iterations,
                base=BASE,entry=BASE,bytes=len(payload),crc32=zlib.crc32(payload)&0xffffffff,
                bin_path=bin_file.relative_to(ROOT).as_posix(),bin_sha256=sha(bin_file),
                elf_path=elf.relative_to(ROOT).as_posix(),elf_sha256=sha(elf),sections=sections,
                symbols=symbols,sp_auipc=sp[0],instructions_audited=insns,clock_hz=HZ)

def require_manifest(path):
    info=json.loads(Path(path).read_text());assert info['status']=='DDR_APPLICATION_AUDIT_PASS'
    assert sha(ROOT/info['bin_path'])==info['bin_sha256'] and sha(ROOT/info['elf_path'])==info['elf_sha256']
    assert audit(ROOT/info['elf_path'],ROOT/info['bin_path'],info['kind'],info['mode'],info['iterations'])==info
    return info

def parse_output(info,data,*,board=False,elapsed=None):
    if info['kind']=='second':
        assert data==SECOND,'second application exact output/data/BSS checks'
        return dict(status='SECOND_APPLICATION_PASS',output_hex=data.hex(),formal_benchmark=False)
    text=data.decode('ascii');assert '\r' not in text
    def one(pattern):
        found=re.findall(pattern,text,re.M);assert len(found)==1,(pattern,found);return found[0]
    label=one(r'^2K (performance|validation) run parameters for coremark\.$');assert label==info['mode']
    assert int(one(r'^CoreMark Size\s*:\s*(\d+)$'))==666
    n=int(one(r'^Iterations\s*:\s*(\d+)$'));assert n==info['iterations']
    ticks=int(one(r'^Total ticks\s*:\s*(\d+)$'));seconds=int(one(r'^Total time \(secs\)\s*:\s*(\d+)$'))
    assert 0<ticks<2**32 and seconds==ticks//HZ
    done=one(r'^PORT_DONE ticks=(\d+) iterations=(\d+) hz=(\d+)$');assert tuple(map(int,done))==(ticks,n,HZ)
    assert text.endswith(f'PORT_DONE ticks={ticks} iterations={n} hz={HZ}\n')
    crc=[one(r'^'+re.escape(prefix)+r'\s*:\s*0x([0-9a-f]{4})$') for prefix in ('seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal')]
    expected=EXPECTED[label];assert tuple(crc[:4])==expected
    final=expected[1] if n==1 else ('a14c' if label=='performance' else '6770');assert crc[4]==final
    assert one(r'^Compiler version\s*:\s*(.+)$')=='GCC15.2.0'
    assert one(r'^Compiler flags\s*:\s*(.+)$')=='-Os -march=rv32i -mabi=ilp32; no LTO'
    assert one(r'^Memory location\s*:\s*(.+)$')=='DDR code/data; static 2000-byte buffer'
    errors=re.findall(r'^ERROR!.*$',text,re.M)
    if n==1 or not board and seconds<10:
        assert errors==[TIME_ERROR] and text.count('Errors detected')==1 and 'Correct operation validated' not in text
        assert 'Iterations/Sec' not in text if seconds==0 else True
    else:
        assert not errors and 'Errors detected' not in text and text.count('Correct operation validated.')==1
        assert int(one(r'^Iterations/Sec\s*:\s*(\d+)$'))==n//seconds
    if board:
        assert elapsed is not None and 0<elapsed<40,'host deadline proves run shorter than 32-bit timer period'
        assert elapsed+.5>=ticks/HZ,'reported benchmark ticks exceed observed application interval'
        if n==60:assert ticks>=10*HZ and seconds>=10
    # These exact BINs have a fixed output format. Only timing numbers vary.
    reference=Path(__file__).parent/'references'/f'{label}_{n}.txt'
    template=reference.read_text()
    template=re.sub(r'(^Total ticks\s*:\s*)\d+',lambda m:m[1]+str(ticks),template,flags=re.M)
    template=re.sub(r'(^Total time \(secs\)\s*:\s*)\d+',lambda m:m[1]+str(seconds),template,flags=re.M)
    template=re.sub(r'(^Iterations/Sec\s*:\s*)\d+',lambda m:m[1]+str(n//seconds),template,flags=re.M) if seconds else template
    template=re.sub(r'PORT_DONE ticks=\d+',f'PORT_DONE ticks={ticks}',template)
    assert text==template,'unexpected/missing/duplicate application output lines'
    return dict(status='COREMARK_FORMAL_BOARD_PASS' if board and n==60 else 'COREMARK_CRC_FUNCTIONAL_PASS',
                mode=label,iterations=n,seedcrc=crc[0],crclist=crc[1],crcmatrix=crc[2],crcstate=crc[3],crcfinal=crc[4],
                ticks=ticks,seconds=ticks/HZ,seconds_integer=seconds,
                iterations_per_second=n*HZ/ticks,formal_benchmark=bool(board and n==60),
                benchmark_origin='ACTUAL_UART_LOADER_BOARD' if board else 'SIMULATION_OR_OFFLINE_FIXTURE')
