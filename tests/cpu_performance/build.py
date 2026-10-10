"""Build isolated RV32I DDR microbenchmarks; never replace board images."""
from pathlib import Path
import argparse
import hashlib
import json
import random
import re
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOL = ROOT / 'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
BASE = 0x40000000


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def symbols(path):
    return {name: int(addr, 16) for addr, kind, name in
            re.findall(r'^([0-9a-f]+)\s+(\w)\s+(\S+)$', path.read_text(), re.M)}


def build(tag):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', tag):
        raise ValueError('invalid tag')
    out = HERE / 'build' / tag
    out.mkdir(parents=True, exist_ok=False)
    permutation = list(range(64))
    random.Random(20261010).shuffle(permutation)
    next_node = [0] * 64
    for i, node in enumerate(permutation):
        next_node[node] = permutation[(i + 1) % 64]
    lines = ['.option norvc', '.option norelax', '.section .text', '.globl _start', '_start:']
    lines += [f'addi x{i}, x0, 0' for i in range(1, 32)]
    lines += ['li sp, 0x40010000', 'li s11, 0x10000008', 'li s8, 0x10000000',
              'li t0, 1', 'sw t0, 16(s8)']
    cases = []

    def case(name, setup, body, result, units, unit):
        number = len(cases) + 1
        lines.extend(setup)
        lines.extend([f'li s7, {number}', f'.globl start_{name}', f'start_{name}:',
                      'lw s10, 0(s11)', f'.globl body_{name}', f'body_{name}:'])
        lines.extend(body)
        lines.extend([f'.globl stop_{name}', f'stop_{name}:', 'lw s9, 0(s11)',
                      f'li t6, {result}', 'bne a0, t6, fail', 'sw a0, 0(s8)'])
        cases.append(dict(id=number, name=name, expected=result, units=units, unit=unit))

    case('sequential_alu', ['li a0, 0'], ['addi a0, a0, 1'] * 128, 128, 128, 'ALU instructions')
    case('small_loop', ['li a0, 0', 'li t0, 32'],
         ['1: addi a0, a0, 2', 'addi t0, t0, -1', 'bne t0, zero, 1b'], 64, 32, 'iterations')
    case('not_taken', ['li a0, 0'],
         sum(([f'beq zero, s11, fail', 'addi a0, a0, 1'] for _ in range(32)), []),
         32, 32, 'branches')
    # Each visited block is on a distinct 16-byte boundary; no RNG runs inside the window.
    order = list(range(32))
    random.Random(20261011).shuffle(order)
    body = [f'j block_{order[0]}']
    for block in range(32):
        nxt = order[order.index(block) + 1] if order.index(block) < 31 else 'done'
        body += ['.balign 16', f'block_{block}:', 'addi a0, a0, 1', f'j block_{nxt}']
    body += ['block_done:']
    case('random_fetch', ['li a0, 0'], body, 32, 32, 'blocks')
    case('sequential_load', ['la s0, values', 'li a0, 0'],
         sum(([f'lw t0, {i*4}(s0)', 'add a0, a0, t0'] for i in range(64)), []),
         2016, 64, 'words')
    case('random_load', ['la s0, values', 'li a0, 0'],
         sum(([f'lw t0, {i*4}(s0)', 'add a0, a0, t0'] for i in permutation), []),
         2016, 64, 'words')
    case('pointer_chase', [f'la s0, node_{permutation[0]}', 'li a0, 0'],
         sum((['lw t0, 4(s0)', 'add a0, a0, t0', 'lw s0, 0(s0)'] for _ in range(64)), []),
         2016, 64, 'nodes (two reads/node)')
    case('sequential_store', ['la s0, destination', 'li a0, 0'],
         sum((['addi a0, a0, 1', f'sw a0, {i*4}(s0)'] for i in range(64)), []),
         64, 64, 'words')
    lines += ['li a0, 0']
    for i in range(64):
        lines += [f'lw t0, {i*4}(s0)', 'add a0, a0, t0']
    lines += ['li t6, 2080', 'bne a0, t6, fail']
    case('subword_lanes', ['la s0, destination', 'li t0, 0x11223344', 'li a0, 0'],
         ['sw t0, 0(s0)', 'li t1, 0x80', 'sb t1, 1(s0)',
          'li t1, 0x8001', 'sh t1, 2(s0)', 'lw a0, 0(s0)',
          'lb t2, 1(s0)', 'lbu t3, 1(s0)', 'lh t4, 2(s0)', 'lhu t5, 2(s0)'],
         0x80018044, 8, 'data requests')
    lines += ['li t6, -128', 'bne t2, t6, fail', 'li t6, 128', 'bne t3, t6, fail',
              'li t6, -32767', 'bne t4, t6, fail', 'li t6, 32769', 'bne t5, t6, fail',
              'li t0, 2', 'sw t0, 16(s8)', '.globl program_return',
              'program_return: j program_return', 'fail: li t0, 3',
              'sw t0, 16(s8)', 'j fail', '.section .data', '.balign 16', 'values:']
    lines += [f'.word {i}' for i in range(64)]
    lines += ['.balign 16', 'nodes:']
    for i in range(64):
        lines += [f'node_{i}: .word node_{next_node[i]}, {i}']
    lines += ['.balign 16', 'destination:', '.zero 256']
    (out / 'main.S').write_text('\n'.join(lines) + '\n')
    (out / 'linker.ld').write_text('ENTRY(_start)\nSECTIONS { . = 0x40000000; .text : { *(.text*) } .data : { *(.data*) } /DISCARD/ : { *(.comment) } }\n')
    boot = ['.option norvc', '.option norelax', '.section .text', '.globl _start', '_start:',
            'li t0, 0', 'li t1, 0x40000000', 'li t2, 0x3ff0', 'lw t3, 0(t2)',
            '1: lw t4, 0(t0)', 'sw t4, 0(t1)', 'addi t0, t0, 4', 'addi t1, t1, 4',
            'addi t3, t3, -1', 'bne t3, zero, 1b', 'fence rw, rw',
            'li t1, 0x40000000', 'jalr zero, 0(t1)']
    (out / 'boot.S').write_text('\n'.join(boot) + '\n')
    commands = []

    def cmd(args, log):
        commands.append([str(a) for a in args])
        p = subprocess.run(list(map(str, args)), capture_output=True, text=True, cwd=out)
        (out / log).write_text(p.stdout + p.stderr)
        if p.returncode:
            raise RuntimeError(f'{log}: {p.stderr}')
        return p.stdout

    gcc = TOOL / 'riscv-none-elf-gcc.exe'
    flags = ['-march=rv32i', '-mabi=ilp32', '-nostdlib', '-nostartfiles', '-mno-relax', '-Wl,--no-relax']
    cmd([gcc, *flags, '-T', out / 'linker.ld', out / 'main.S', '-o', out / 'program.elf'], 'link.log')
    cmd([gcc, *flags, '-Wl,-Ttext=0', out / 'boot.S', '-o', out / 'boot.elf'], 'boot_link.log')
    for name in ['program', 'boot']:
        cmd([TOOL / 'riscv-none-elf-objcopy.exe', '-O', 'binary', out / (name + '.elf'), out / (name + '.bin')], name + '_objcopy.log')
    cmd([TOOL / 'riscv-none-elf-nm.exe', '-n', out / 'program.elf'], 'symbols.txt')
    cmd([TOOL / 'riscv-none-elf-objdump.exe', '-d', '-M', 'no-aliases', out / 'program.elf'], 'program.dis')
    attrs=cmd([TOOL / 'riscv-none-elf-readelf.exe', '-h', '-A', out / 'program.elf'], 'program.readelf.txt')
    assert 'rv32i2p1' in attrs
    for name in ['program','boot']:
        elf=(out/(name+'.elf')).read_bytes()
        assert elf[:6]==b'\x7fELF\x01\x01' and struct.unpack_from('<H',elf,18)[0]==243
        assert struct.unpack_from('<I',elf,24)[0]==(BASE if name=='program' else 0)
        assert struct.unpack_from('<I',elf,36)[0]==0
    encoded=re.findall(r'^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(\S+)',(out/'program.dis').read_text(),re.M)
    assert encoded
    for address,word,name in encoded:
        w=int(word,16); op=w&127; f3=(w>>12)&7; f7=w>>25
        legal=op in (0x37,0x17,0x6f) or (op==0x67 and f3==0) or \
            (op==0x63 and f3 in (0,1,4,5,6,7)) or \
            (op==0x03 and f3 in (0,1,2,4,5)) or (op==0x23 and f3 in (0,1,2)) or \
            (op==0x13 and (f3 in (0,2,3,4,6,7) or f3==1 and f7==0 or f3==5 and f7 in (0,32))) or \
            (op==0x33 and (f7==0 or f7==32 and f3 in (0,5))) or (op==0x0f and f3==0)
        if not legal: raise ValueError(f'unsupported ISA {address} {word} {name}')
    raw = (out / 'program.bin').read_bytes()
    if not 0 < len(raw) <= 16368:
        raise ValueError('isolated copy-loader payload exceeds RAM capacity')
    for source, target, metadata in [('boot.bin', 'boot_rom.dat', False), ('program.bin', 'data_ram.dat', True)]:
        binary = (out / source).read_bytes()
        binary += bytes((-len(binary)) % 4)
        words = list(struct.unpack('<' + 'I' * (len(binary)//4), binary))
        words += [0] * (4096 - len(words))
        if metadata:
            words[4092] = len(binary) // 4
        (out / target).write_text(''.join(f'{word:08x}\n' for word in words))
    syms = symbols(out / 'symbols.txt')
    for entry in cases:
        entry.update(start=syms['start_' + entry['name']], stop=syms['stop_' + entry['name']])
    manifest = dict(kind='micro', clock_hz=93750000, entry=BASE, payload_bytes=len(raw),
                    done=syms['program_return'], cases=cases, random_seeds=[20261010, 20261011],
                    instructions_audited=len(encoded), commands=commands, sha256={name: sha(out / name) for name in
                    ['program.elf', 'program.bin', 'boot_rom.dat', 'data_ram.dat']})
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(output=str(out), bytes=len(raw), cases=len(cases))))
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True)
    build(parser.parse_args().tag)
