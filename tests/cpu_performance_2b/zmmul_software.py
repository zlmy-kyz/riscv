"""Independent Zmmul ELF/output audit; old RV32I software/parser remains frozen."""
from pathlib import Path
import importlib.util
import inspect
import json
import re
import struct
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BUILD_DIR=HERE/'build/measure_zmmul_20261013_a'
FLAGS='-Os -march=rv32i_zmmul -mabi=ilp32; no LTO'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


legacy=load('zmmul_legacy_application',ROOT/'tools/uart_loader/candidates/bsp_workflow/application.py')
sha=legacy.sha


def zmmul_legal(word):
    return word&127==0x33 and word>>25==1 and ((word>>12)&7)<4


code=inspect.getsource(legacy.audit)
guard="for i in range(0,len(code),4):assert isa.legal_instruction(int.from_bytes(code[i:i+4],'little')),(name,i)"
assert code.count(guard)==1 and code.count('iterations in (1,60)')==1
code=code.replace(guard,"for i in range(0,len(code),4):assert (isa.legal_instruction(int.from_bytes(code[i:i+4],'little')) or zmmul_legal(int.from_bytes(code[i:i+4],'little'))),(name,i)")
code=code.replace('iterations in (1,60)','iterations in (1,120)')
namespace=dict(legacy.__dict__,zmmul_legal=zmmul_legal)
exec(compile(code,'<zmmul_ELF_layout_and_ISA_audit>','exec'),namespace)
layout_audit=namespace['audit']


def multiply_sites(elf):
    raw=Path(elf).read_bytes();shoff=struct.unpack_from('<I',raw,32)[0];shsize,count,si=struct.unpack_from('<HHH',raw,46)
    headers=[struct.unpack_from('<10I',raw,shoff+i*shsize) for i in range(count)]
    sites=[]
    for h in headers:
        if h[2]&4:
            code=raw[h[4]:h[4]+h[5]]
            for offset in range(0,len(code),4):
                word=int.from_bytes(code[offset:offset+4],'little')
                if zmmul_legal(word):sites.append(dict(pc=h[3]+offset,word=f'{word:08x}',mnemonic=['mul','mulh','mulhsu','mulhu'][(word>>12)&7]))
    return sites


def audit(elf,bin_file,kind,mode=None,iterations=None):
    info=layout_audit(elf,bin_file,kind,mode,iterations)
    readelf=Path(elf).with_name('program.readelf.txt').read_text()
    architecture=re.findall(r'Tag_RISCV_arch:\s*"([^"]+)"',readelf)
    assert len(architecture)==1 and re.fullmatch(r'rv32i\d+p\d+_zmmul\d+p\d+',architecture[0]),architecture
    sites=multiply_sites(elf);assert sites,'No hardware MUL instruction in new software'
    payload=Path(bin_file).read_bytes();offset=info['symbols']['seed4_volatile']-info['base']
    assert int.from_bytes(payload[offset:offset+4],'little')==iterations
    return dict(info,isa='rv32i_zmmul',compiler_flags=FLAGS,elf_arch=architecture[0],multiply_sites=sites,
                scope='Zmmul only; all executable words whitelisted, DIV/REM/other extensions forbidden')


def require_manifest(path):
    info=json.loads(Path(path).read_text());assert info['isa']=='rv32i_zmmul' and info['status']=='DDR_APPLICATION_AUDIT_PASS'
    assert sha(ROOT/info['bin_path'])==info['bin_sha256'] and sha(ROOT/info['elf_path'])==info['elf_sha256']
    assert audit(ROOT/info['elf_path'],ROOT/info['bin_path'],info['kind'],info['mode'],info['iterations'])==info
    return info


# Preserve the old exact UART/13-counter parser, changing only the new reference path.
measurement=load('zmmul_legacy_measurement',ROOT/'tools/uart_loader/candidates/perf_2b/run_measurement.py')
code=inspect.getsource(measurement.parse_measurement)
reference="reference = (FORMAL_DIR / f'{mode}_120/reference.txt' if iterations == 120 else\n                 ROOT / f'tools/uart_loader/candidates/bsp_workflow/references/{mode}_{iterations}.txt')"
assert code.count(reference)==1
code=code.replace(reference,"reference = BUILD_DIR / f'{mode}_{iterations}/reference.txt'")
namespace=dict(measurement.__dict__,BUILD_DIR=BUILD_DIR)
exec(compile(code,'<zmmul_exact_CRC_and_counter_output>','exec'),namespace)
_parse=namespace['parse_measurement']


def parse_measurement(info,data,*,board=False,elapsed=None):
    assert info['isa']=='rv32i_zmmul' and info['compiler_flags']==FLAGS
    result=_parse(info,data,board=board,elapsed=elapsed)
    return dict(result,isa='rv32i_zmmul',comparison_kind='Same algorithm/iterations/flags except ISA, different BIN',
                crc_functional_only=not board)
