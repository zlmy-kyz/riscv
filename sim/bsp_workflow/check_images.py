"""Negative ELF/BIN review fixtures, no board or serial evidence."""
from pathlib import Path
import json,shutil,struct,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
from application import audit
out=ROOT/'sim/bsp_workflow/build';folder=out/'image_fixtures';assert not folder.exists();folder.mkdir()
source=ROOT/'tests/bsp_workflow/build/hello';checks=[]
for name in ('entry','ABI_flags','BIN_mismatch','M_instruction','stack_overlap','ELF_arch'):
    case=folder/name;case.mkdir();elf=bytearray((source/'program.elf').read_bytes());binary=bytearray((source/'program.bin').read_bytes())
    if name=='entry':struct.pack_into('<I',elf,24,0)
    if name=='ABI_flags':struct.pack_into('<I',elf,36,1)
    if name=='ELF_arch':struct.pack_into('<H',elf,18,62)
    if name=='BIN_mismatch':binary[-1]^=1
    shoff=struct.unpack_from('<I',elf,32)[0];size,count,si=struct.unpack_from('<HHH',elf,46)
    heads=[struct.unpack_from('<10I',elf,shoff+i*size) for i in range(count)]
    strings=elf[heads[si][4]:heads[si][4]+heads[si][5]]
    if name=='M_instruction':
        h=next(h for h in heads if h[2]&4);struct.pack_into('<I',elf,h[4],0x02000033);struct.pack_into('<I',binary,h[3]-0x40000000,0x02000033)
    if name=='stack_overlap':
        index=next(i for i,h in enumerate(heads) if strings[h[0]:strings.index(0,h[0])]==b'.bss');struct.pack_into('<I',elf,shoff+index*size+12,0x4000fffc)
    (case/'program.elf').write_bytes(elf);(case/'program.bin').write_bytes(binary);shutil.copyfile(source/'symbols.txt',case/'symbols.txt')
    try:audit(case/'program.elf',case/'program.bin','hello')
    except (AssertionError,ValueError):checks.append(dict(name=name,result='PASS'));continue
    raise AssertionError('Invalid image accepted: '+name)
result=dict(status='UNIFIED_BSP_IMAGE_NEGATIVE_PASS',evidence_origin='OFFLINE_FIXTURE_NOT_BOARD',checks=checks,count=len(checks),serial_opened=False)
with (out/'pc_images.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print('RESULT: PASS',len(checks),'negative ELF/BIN checks')
