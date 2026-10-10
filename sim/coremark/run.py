"""Audit existing CoreMark ELF/BIN/DAT, then validate Full Boot UART CRCs."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUILD = HERE / 'build'
MS = Path('D:/modelsim/win64pe')
TOOL = ROOT / 'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
NAMES = 'alu br_alu l_alu regfile csr_file mycpu_sync inst_bus_interconnect data_bus_interconnect inst_bram_adapter data_bram_adapter simple_mmio dual_sram_to_pango_ddr_bridge uart_tx uart_rx uart_rx_fifo uart_mmio soc_top'.split()
SOURCES = [ROOT / 'myriscv' / (n+'.v') for n in NAMES] + [HERE / n for n in ['bram.v','ddr_model.v','tb_coremark.v']]
EXPECTED = {'performance': ('e9f5','e714','1fd7','8e3a'), 'validation': ('18f2','e3c1','0747','8d84')}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def command(args, folder, log, timeout=120):
    started = time.monotonic()
    p = subprocess.run(list(map(str,args)), cwd=folder, capture_output=True,
                       text=True, errors='replace', timeout=timeout)
    output = p.stdout+p.stderr
    log.write_text(output, encoding='utf-8')
    if p.returncode:
        raise RuntimeError(f'exit={p.returncode}: {log}\n{output[-3000:]}')
    return output, round(time.monotonic()-started,2)

def audit(mode, iterations=1):
    name = mode if iterations==1 else f'{mode}_{iterations}'
    test = ROOT / 'tests/coremark_baremetal/build' / name
    config = json.loads((test/'config.json').read_text())
    if config['mode']!=mode or config['iterations']!=iterations or config['data_size']!=2000:
        raise ValueError('acceptance requires matching mode/iterations and 2000 data bytes')
    raw = (test/'main.elf').read_bytes()
    payload = (test/'main.bin').read_bytes()
    image = [int(x,16) for x in (test/'main.dat').read_text().split()]
    if raw[:6]!=b'\x7fELF\x01\x01' or struct.unpack_from('<H',raw,18)[0]!=243:
        raise ValueError('expected ELF32 little-endian RISC-V')
    entry, phoff = struct.unpack_from('<II',raw,24)
    flags = struct.unpack_from('<I',raw,36)[0]
    phsize, phcount = struct.unpack_from('<HH',raw,42)
    if entry!=0x40000000 or flags!=0 or not 0<len(payload)<=16368:
        raise ValueError('entry/soft-float ABI/load size invalid')
    packed = bytearray(len(payload))
    for i in range(phcount):
        kind,off,va,pa,fs,mem,fl,align = struct.unpack_from('<8I',raw,phoff+i*phsize)
        if kind==1:
            if va!=pa or va<entry or va+mem>0x4000f000 or va+fs>entry+len(payload):
                raise ValueError('invalid load span or program/stack overlap')
            packed[va-entry:va-entry+fs]=raw[off:off+fs]
    words = (len(payload)+3)//4
    padded = payload+bytes((-len(payload))%4)
    if bytes(packed)!=payload or len(image)!=4096 or image[-4:]!=[words,0,0,0] or any(image[words:4092]) or b''.join(x.to_bytes(4,'little') for x in image[:words])!=padded:
        raise ValueError('ELF/BIN/DAT/manifest mismatch')
    syms = {name:int(addr,16) for addr,kind,name in re.findall(r'^([0-9a-f]+)\s+(\w)\s+(\S+)$',(test/'symbols.txt').read_text(),re.M)}
    if syms['__stack_top']!=0x40010000 or syms['__stack_bottom']!=0x4000f000:
        raise ValueError('unexpected stack layout')
    folder = BUILD / name
    folder.mkdir(parents=True,exist_ok=True)
    undefined,_ = command([TOOL/'riscv-none-elf-nm.exe','-u',test/'main.elf'],folder,folder/'undefined.log')
    if undefined.strip(): raise ValueError('unresolved symbols')
    attrs = (test/'main.readelf.txt').read_text()
    arch = re.search(r'Tag_RISCV_arch:\s+"([^"]+)"',attrs)
    if not arch or arch[1]!='rv32i2p1': raise ValueError('ISA attributes not pure RV32I')
    instructions = re.findall(r'^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(\S+)',(test/'main.dis').read_text(),re.M)
    if not instructions: raise ValueError('no disassembly')
    # Independently reject M/C/A/F opcodes in all linked executable sections,
    # including libgcc (not just the attribute string on the main object).
    for addr,encoded,mnemonic in instructions:
        word=int(encoded,16); op=word&127; f3=(word>>12)&7; f7=word>>25
        legal = op in (0x37,0x17,0x6f) or (op==0x67 and f3==0) or \
            (op==0x63 and f3 in (0,1,4,5,6,7)) or \
            (op==0x03 and f3 in (0,1,2,4,5)) or (op==0x23 and f3 in (0,1,2)) or \
            (op==0x13 and ((f3 in (0,2,3,4,6,7)) or (f3==1 and f7==0) or (f3==5 and f7 in (0,32)))) or \
            (op==0x33 and (f7==0 or (f7==32 and f3 in (0,5))))
        if not legal: raise ValueError(f'unsupported instruction {addr}: {encoded} {mnemonic}')
    return test,folder,{'config':config,'payload_bytes':len(payload),'payload_words':words,
        'entry':entry,'main':syms['main'],'done':syms['program_return'],
        'bss_start':syms['__bss_start'],'bss_end':syms['__bss_end'],
        'stack_bottom':syms['__stack_bottom'],'stack_top':syms['__stack_top'],
        'instructions_audited':len(instructions),
        'sha256':{n:sha(test/n) for n in ['main.elf','main.bin','main.dat','boot_rom.dat']}}

def accept_uart(mode,uart,info,output):
    iterations = info['config']['iterations']
    crc = []
    for label in ['seedcrc','crclist','crcmatrix','crcstate','crcfinal']:
        found = re.findall(rf'{label}\s*:\s*0x([0-9a-f]{{4}})',uart)
        if len(found)!=1: raise ValueError(f'missing/duplicate {label}')
        crc.append(found[0])
    if tuple(crc[:4])!=EXPECTED[mode] or (iterations==1 and crc[4]!=crc[1]):
        raise ValueError(f'CRC mismatch: {crc}')
    ticks = int(re.search(r'Total ticks\s*:\s*(\d+)',uart)[1])
    measured = int(re.search(r'timer_ticks=(\d+)',output)[1])
    seconds = int(re.search(r'Total time \(secs\):\s*(\d+)',uart)[1])
    if ticks!=measured or not 0<ticks<2**32 or seconds!=ticks//93750000:
        raise ValueError('timer mismatch or invalid tick count')
    if int(re.search(r'Iterations\s*:\s*(\d+)',uart)[1])!=iterations or \
       f'2K {mode} run parameters for coremark.' not in uart or \
       int(re.search(r'CoreMark Size\s*:\s*(\d+)',uart)[1])!=666:
        raise ValueError('wrong benchmark parameters')
    errors = [line for line in uart.splitlines() if 'ERROR' in line]
    if seconds<10:
        if errors!=['ERROR! Must execute for at least 10 secs for a valid result!'] or \
           uart.count('Errors detected')!=1 or 'Correct operation validated' in uart:
            raise ValueError(f'unexpected short-run validation status: {errors}')
    elif errors or 'Errors detected' in uart or uart.count('Correct operation validated.')!=1:
        raise ValueError(f'unexpected timed-run validation status: {errors}')
    if f'PORT_DONE ticks={ticks} iterations={iterations} hz=93750000\n' not in uart or \
       'GCC15.2.0' not in uart or f"-{info['config']['optimization']} -march=rv32i -mabi=ilp32; no LTO" not in uart:
        raise ValueError('missing port/build evidence')
    return {'seedcrc':crc[0],'crclist':crc[1],'crcmatrix':crc[2],'crcstate':crc[3],
            'crcfinal':crc[4],'ticks':ticks,'seconds_integer':seconds,
            'duration_rule_met_in_model':seconds>=10,'valid_score':False}

def run(options):
    if not 1<=options.iterations<=100:
        raise ValueError('this RTL runner supports 1..100 iterations (bounded signed cycle counter)')
    BUILD.mkdir(parents=True,exist_ok=True)
    protected = [*ROOT.joinpath('myriscv').glob('*.v'), *ROOT.joinpath('coremark-main').glob('core*.c'),
        ROOT/'coremark-main/coremark.h',ROOT/'coremark-main/coremark.md5',ROOT/'RISCV.pds',
        ROOT/'ipcore/data_ram/data_ram.idf',ROOT/'ipcore/data_ram/data_ram.v',
        ROOT/'ipcore/data_ram/rtl/data_ram_init_param.v',ROOT/'ipcore/inst_rom/rtl/inst_rom_init_param.v',
        ROOT/'MyCpu_test/board_selftest/boot_rom.dat',ROOT/'constraint_check/temp_constraint_file.fdc',
        ROOT/'tests/fpga_uart_pc_output_30/main.dat',ROOT/'tests/pc_uart_fpga_uart_pc/main.dat',
        ROOT/'tests/pc_uart_fpga_uart_pc/build/main.dat']
    before = {str(p):sha(p) for p in protected}
    results=[]
    for mode in (EXPECTED if options.mode=='all' else [options.mode]):
        test,folder,info=audit(mode,options.iterations)
        print(f"AUDIT {mode}: BIN={info['payload_bytes']} bytes; RV32I={info['instructions_audited']} instructions; PASS",flush=True)
        if options.audit_only:
            (folder/'audit.json').write_text(json.dumps(info,indent=2)+'\n')
            continue
        print(f'{mode}: starting Full Boot',flush=True)
        work=folder/'work'
        if not work.exists(): command([MS/'vlib.exe',work],folder,folder/'vlib.log')
        compile_text,_=command([MS/'vlog.exe','-sv','-work',work,f'+incdir+{ROOT/"myriscv"}',*SOURCES],folder,folder/'compile.log')
        if 'Errors: 0' not in compile_text: raise RuntimeError('compiler missing Errors: 0')
        plus=[f'+DAT={test.joinpath("main.dat").as_posix()}',f'+ROM={ROOT.joinpath("MyCpu_test/board_selftest/boot_rom.dat").as_posix()}',
              f'+MAIN={info["main"]:x}',f'+DONE={info["done"]:x}',f'+BSS_START={info["bss_start"]:x}',f'+BSS_END={info["bss_end"]:x}']
        # Prove the candidate loader is byte-identical to the active ROM loader.
        if (test/'boot_rom.dat').read_bytes()!=(ROOT/'MyCpu_test/board_selftest/boot_rom.dat').read_bytes():
            raise ValueError('candidate loader differs from active boot ROM')
        max_cycles=20000000*options.iterations
        # ModelSim 10.6c rejects fractional seconds; use an integer us duration.
        sim_microseconds=((max_cycles+10000)*1000000+93750000-1)//93750000
        script='onerror {quit -f -code 1}\n'+f'vsim -t 1ps -lib {{{work.as_posix()}}} -gMAX_CYCLES={max_cycles} tb_coremark {" ".join(plus)}\n'+\
            f'onfinish stop\nrun {sim_microseconds}us\n'+\
            'if {[examine -radix unsigned /tb_coremark/test_pass] != 1} {\necho {RESULT: FAIL incomplete CoreMark}\nquit -f -code 1\n}\nquit -f -code 0\n'
        (folder/'run.tcl').write_text(script,encoding='ascii')
        output,wall=command([MS/'vsim.exe','-c','-do','do run.tcl'],folder,folder/'modelsim.log',timeout=1800 if options.iterations==1 else 300*options.iterations)
        if 'Errors: 0' not in output or 'RESULT: FAIL' in output or len(re.findall(r'RESULT: PASS coremark_full_boot',output))!=1:
            raise RuntimeError(f'Full Boot acceptance failed: {folder}')
        uart=(folder/'uart.txt').read_text()
        crc=accept_uart(mode,uart,info,output)
        evidence=re.search(r'RESULT: PASS coremark_full_boot[^\r\n]*',output)[0]
        results.append({'mode':mode,'result':'CRC_FUNCTIONAL_PASS','image':info,'crc':crc,
                        'crcfinal_reference':'UART output from this exact DAT in the DDR user-port model; compare with board output',
                        'evidence':evidence,'wall_seconds':wall})
        print(f'{mode}: CRC_FUNCTIONAL_PASS {crc}; {evidence}',flush=True)
        if {str(p):sha(p) for p in protected}!=before: raise RuntimeError('protected sources/images changed')
        (folder/'validated_image.json').write_text(json.dumps(results[-1],indent=2)+'\n')
    report={'results':results,'protected_sha256':before,'board_result':'NOT_TESTED',
            'score':'NOT_VALID_SHORT_RUN' if options.iterations==1 else 'NOT_A_BOARD_SCORE'}
    report_name='results.json' if options.iterations==1 else f'results_{options.iterations}.json'
    if not options.audit_only: (BUILD/report_name).write_text(json.dumps(report,indent=2)+'\n')

def status(options):
    for mode in (EXPECTED if options.mode=='all' else [options.mode]):
        name=mode if options.iterations==1 else f'{mode}_{options.iterations}'
        folder=BUILD/name
        transcript=folder/'transcript'
        if not transcript.exists():
            print(f'{name}: no transcript yet',flush=True)
            continue
        rows=transcript.read_text(encoding='utf-8',errors='replace').splitlines()
        evidence=[row for row in rows if any(tag in row for tag in ['CHECK:', 'PROGRESS ', 'RESULT:', 'Errors:'])]
        print(name+':\n'+'\n'.join(evidence[-3:]),flush=True)
        receipt=folder/'validated_image.json'
        if receipt.exists():
            saved=json.loads(receipt.read_text())
            print(f"accepted: {saved['result']}; CRC={saved['crc']}",flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['all',*EXPECTED],default='all')
    parser.add_argument('--iterations',type=int,default=1,
                        help='1 uses original mode folders; N uses build/<mode>_N, e.g. performance_60')
    parser.add_argument('--audit-only',action='store_true')
    parser.add_argument('--status',action='store_true',help='read current transcripts without building or running')
    try:
        options=parser.parse_args()
        status(options) if options.status else run(options)
    except Exception as e:
        print(f'RESULT: FAIL coremark: {e}',file=sys.stderr,flush=True)
        sys.exit(1)
