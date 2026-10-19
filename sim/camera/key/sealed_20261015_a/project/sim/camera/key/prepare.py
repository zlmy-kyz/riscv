"""Sol: deterministic input generation only. Never executes HDL or edits design/IP."""
import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'difftest/golden'))
from rvtool import Assembler

W, H = 1280, 720
BASE = 0x40000000

def pixel(pattern, x, y):
    # Deliberately exercise both bytes, line/beat boundaries and frame identity.
    return ((x * 73 + y * 151 + (x ^ (y * 3)) * 19) ^
            (0x1357 if pattern == 1 else 0xeca8)) & 0xffff

def frame(pattern, width=W, height=H):
    return b''.join(struct.pack('<H', pixel(pattern, x, y))
                    for y in range(height) for x in range(width))

def imm(reg, value):
    value &= 0xffffffff
    upper = ((value + 0x800) >> 12) & 0xfffff
    lower = (value & 4095) - (4096 if value & 2048 else 0)
    return f'lui {reg},{upper}\naddi {reg},{reg},{lower}\n'

def cpu_source(crcs):
    s = '.org 0x40000000\n'
    s += imm('s0', 0x10002000) + imm('s1', 0x10000000)
    s += imm('s2', 0x40010000) + imm('s3', 0x41000000)
    # Generate CRC table through real CPU stores, rather than modifying RAM IP.
    s += imm('s4', 0x1000)
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ (0xedb88320 if c & 1 else 0)
        s += imm('t0', c) + f'sw t0,{i*4}(s4)\n'
    s += '''addi t0,x0,1
sw t0,16(s1)
config_wait: lw t0,8(s0)
andi t1,t0,16
bne t1,x0,fail
andi t0,t0,1
beq t0,x0,config_wait
'''
    # Prime reads before ARM, and reread after the first CRC. No cache force/flush.
    s += 'lw t0,0(s3)\nlw t1,32(s3)\nlw t2,0(s3)\n'
    for p in (1, 2):
        s += f'''addi a7,x0,{p}
addi t0,x0,1
sw t0,4(s0)
wait_{p}: sw a7,0(s2)
lw t0,8(s0)
andi t1,t0,16
bne t1,x0,fail
andi t1,t0,4
beq t1,x0,wait_{p}
andi t1,t0,2
bne t1,x0,fail
lw t0,20(s0)
bne t0,a7,fail
lw t0,16(s0)
'''
        s += imm('t1', W*H*2) + 'bne t0,t1,fail\nlw t0,24(s0)\n'
        s += imm('t1', W*H) + 'bne t0,t1,fail\nlw t0,36(s0)\n'
        s += imm('t1', W*H*2//32) + 'bne t0,t1,fail\n'
        s += 'addi a0,s3,0\naddi a1,x0,-1\n' + imm('a2', W*H//2)
        s += f'crc_{p}: lw a3,0(a0)\n'
        # Byte-table CRC, each frame word loaded exactly once by the CPU.
        for byte in range(4):
            s += f'''xor t0,a1,a3
andi t0,t0,255
slli t0,t0,2
add t0,s4,t0
lw t0,0(t0)
srli a1,a1,8
xor a1,a1,t0
'''
            if byte != 3:
                s += 'srli a3,a3,8\n'
        s += f'''addi a0,a0,4
addi a2,a2,-1
bne a2,x0,crc_{p}
xori a1,a1,-1
lw t0,40(s0)
bne t0,a1,fail
'''
        s += imm('t1', crcs[p-1]) + 'bne a1,t1,fail\n'
        # Durable observation via real MMIO, including independent expected CRC.
        s += f'sw a1,0(s1)\nsw a7,0(s1)\n'
        if p == 1:
            s += 'lw t0,0(s3)\nlw t1,32(s3)\nlw t2,0(s3)\n'
    s += '''addi t0,x0,2
sw t0,16(s1)
halt: jal x0,halt
fail: addi t0,x0,3
sw t0,16(s1)
bad: jal x0,bad
'''
    return s

def model_header():
    # Retain the exact reduced-mode port signature of the generated DDR wrapper.
    defines = set(re.findall(r'`define\s+(\w+)', (ROOT/'ipcore/ddr3/define.vh').read_text()))
    lines, stack, active = [], [], True
    for line in (ROOT/'ipcore/ddr3/ddr3.v').read_text().splitlines():
        m = re.match(r'\s*`(ifdef|ifndef|elsif|else|endif)\b\s*(\w*)', line)
        if m:
            op, name = m.groups()
            if op in ('ifdef', 'ifndef'):
                test = (name in defines) == (op == 'ifdef')
                stack.append([active, test]); active = active and test
            elif op == 'elsif':
                parent, taken = stack[-1]; test = not taken and name in defines
                stack[-1][1] |= test; active = parent and test
            elif op == 'else':
                parent, taken = stack[-1]; active = parent and not taken; stack[-1][1] = True
            else:
                active = stack.pop()[0]
        elif active and not line.lstrip().startswith('`include'):
            lines.append(line)
    text = '\n'.join(lines)
    start = text.index('module ddr3')
    end = text.index('\n);', start) + 3
    header = text[start:end]
    # Only model outputs assigned procedurally need variable declarations.
    for name in ('axi_rdata', 'axi_rid', 'axi_rlast', 'axi_rvalid'):
        header = re.sub(r'(output\s+)(\[[^\]]+\]\s+)?('+name+r'\b)',
                        lambda m: m[1]+'reg '+(m[2] or '')+m[3], header)
    return '`timescale 1ns/1ps\n// Test-only native user-port model; no PHY claims.\n'+header+'\n'

def main():
    (HERE/'generated').mkdir(exist_ok=True)
    crcs = []
    for p in (1, 2):
        data = frame(p)
        crcs.append(zlib.crc32(data))
        (HERE/f'generated/frame{p}.bin').write_bytes(data)
        # A byte array, deliberately different packing from DUT 256-bit words.
        (HERE/f'generated/frame{p}.hex').write_text(''.join(f'{b:02x}\n' for b in data))
    text = cpu_source(crcs)
    asm = Assembler(); code = asm.assemble(text)
    words = [0x13]*4096
    for addr, word in code.items():
        assert BASE <= addr < BASE+16384
        words[(addr-BASE)//4] = word
    (HERE/'generated/cpu.S').write_text(text)
    (HERE/'generated/cpu.dat').write_text(''.join(f'{w:08x}\n' for w in words))
    (HERE/'generated/cpu.lst').write_text(''.join(f'{a:08x} {v or "":8s} {s}\n' for a,v,s in asm.listing))
    table = re.findall(r"8'd(\d+): data=24'h([0-9a-fA-F_]+)", (ROOT/'myriscv/ov5640_config_rom.v').read_text())
    assert [int(i) for i,_ in table] == list(range(244))
    (HERE/'generated/config.hex').write_text(''.join(v.replace('_','')+'\n' for _,v in table))
    (HERE/'generated/ddr_header.svh').write_text(model_header())
    reference = dict(width=W,height=H,bytes=W*H*2,beats=W*H*2//32,words=W*H//2,
                     crc32=crcs,pattern_spec='(73*x+151*y+19*(x^(3*y))) XOR salt; modulo 65536; salts 1357/eca8',
                     labels=asm.sym,frame_sha256=[hashlib.sha256(frame(p)).hexdigest() for p in (1,2)])
    (HERE/'generated/reference.json').write_text(json.dumps(reference,indent=2)+'\n')
    print(json.dumps(dict(status='INPUTS_GENERATED_HDL_NOT_RUN',crc32=[f'{c:08x}' for c in crcs],instructions=len(code))))

if __name__ == '__main__': main()
