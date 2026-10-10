"""Audit a Harvard ELF and extract ROM .text and RAM .rodata independently."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def legal_instruction(word):
    op, f3, f7 = word & 127, (word >> 12) & 7, word >> 25
    if op in (0x37, 0x17, 0x6f): return True
    if op == 0x67: return f3 == 0
    if op == 0x63: return f3 in (0, 1, 4, 5, 6, 7)
    if op == 0x03: return f3 in (0, 1, 2, 4, 5)
    if op == 0x23: return f3 in (0, 1, 2)
    if op == 0x13:
        return (f7 == 0 if f3 == 1 else f7 in (0, 32) if f3 == 5 else True)
    if op == 0x33: return f7 == 0 or (f7 == 32 and f3 in (0, 5))
    if op == 0x0f: return f3 == 0
    if op == 0x73: return f3 in (1, 2, 3, 5, 6, 7) or word in (0x73, 0x100073, 0x30200073, 0x10500073)
    return False


def audit(elf):
    raw = elf.read_bytes()
    if raw[:6] != b'\x7fELF\x01\x01' or struct.unpack_from('<H', raw, 18)[0] != 243:
        raise ValueError('expected ELF32 little-endian RISC-V')
    if struct.unpack_from('<I', raw, 24)[0] != 0 or struct.unpack_from('<I', raw, 36)[0] != 0:
        raise ValueError('entry must be zero; no compressed/float ABI ELF flags')
    shoff = struct.unpack_from('<I', raw, 32)[0]
    shsize, count, strings_index = struct.unpack_from('<HHH', raw, 46)
    headers = [struct.unpack_from('<10I', raw, shoff + i * shsize) for i in range(count)]
    strings = headers[strings_index]
    names = raw[strings[4]:strings[4] + strings[5]]
    sections = {}
    for h in headers:
        end = names.find(b'\0', h[0])
        name = names[h[0]:end].decode('ascii')
        sections[name] = {'type': h[1], 'flags': h[2], 'address': h[3], 'offset': h[4], 'size': h[5]}
        if h[2] & 2 and h[5] and name not in ('.text', '.rodata', '.bss', '.rx_buffer', '.diagnostics'):
            raise ValueError(f'unexpected allocated section {name}')
    expected = {'.text': (0, 0x4000, 1), '.rodata': (0x100, 0x1000, 1),
                '.bss': (0x1000, 0x2000, 8), '.rx_buffer': (0x2000, 0x3000, 8),
                '.diagnostics': (0x20, 0x100, 8)}
    for name, (start, end, kind) in expected.items():
        s = sections[name]
        if s['address'] != start or s['address'] + s['size'] > end or s['type'] != kind:
            raise ValueError(f'bad partition/type: {name}: {s}')
    text = sections['.text']
    code = raw[text['offset']:text['offset'] + text['size']]
    if len(code) % 4 or not code:
        raise ValueError('ROM code must contain 32-bit instructions')
    for i in range(0, len(code), 4):
        word = int.from_bytes(code[i:i + 4], 'little')
        if not legal_instruction(word):
            raise ValueError(f'unsupported instruction at {i:08x}: {word:08x}')
    symbols_text = elf.with_name('symbols.txt').read_text()
    symbols = {name: int(address, 16) for address, kind, name in
               re.findall(r'^([0-9a-f]+)\s+(\w)\s+(\S+)$', symbols_text, re.M)}
    if symbols['__stack_top'] != 0x3ff0 or symbols['__stack_bottom'] != 0x3000:
        raise ValueError('bad Loader stack')
    rx_loads = [(i, (int.from_bytes(code[i:i + 4], 'little') >> 7) & 31)
                for i in range(symbols['uart_read_byte'], symbols['uart_write_byte'], 4)
                if int.from_bytes(code[i:i + 4], 'little') & 0x707f == 0x4003]
    if len(rx_loads) != 1:
        raise ValueError(f'expected exactly one UART RX LBU: {rx_loads}')
    recover_loads = [(i, (int.from_bytes(code[i:i + 4], 'little') >> 7) & 31)
                     for i in range(symbols['uart_recover'], min(symbols['loader_crc32'], symbols.get('loader_crc32_update', symbols['loader_crc32'])), 4)
                     if int.from_bytes(code[i:i + 4], 'little') & 0x707f == 0x4003]
    if len(recover_loads) != 1:
        raise ValueError('expected one recovery RX LBU')
    return raw, sections, symbols, rx_loads[0], recover_loads[0], len(code) // 4


def ddr_instructions(raw, sections, symbols):
    if 'loader_ddr_read_start' not in symbols: return {}
    s = sections['.text']
    code = raw[s['offset']:s['offset'] + s['size']]
    result = {}
    modes = [('write', 0x2023), ('read', 0x2003)]
    if 'loader_ddr_crc_read_start' in symbols: modes.append(('crc_read', 0x2003))
    for name, opcode in modes:
        matches = [(i, int.from_bytes(code[i:i + 4], 'little'))
                   for i in range(symbols[f'loader_ddr_{name}_start'], symbols[f'loader_ddr_{name}_end'], 4)
                   if int.from_bytes(code[i:i + 4], 'little') & 0x707f == opcode]
        if len(matches) != 1: raise ValueError(f'expected one DDR {name} instruction: {matches}')
        result[f'ddr_{name}_pc'] = matches[0][0]
        if name != 'write': result[f'ddr_{name}_rd'] = (matches[0][1] >> 7) & 31
    return result


def extract(elf, output):
    raw, sections, symbols, rx_load, recover_load, instructions = audit(elf)
    rom = bytearray((0x0000006f).to_bytes(4, 'little') * 4096)
    ram = bytearray(16384)
    for name, image in (('.text', rom), ('.rodata', ram)):
        s = sections[name]
        image[s['address']:s['address'] + s['size']] = raw[s['offset']:s['offset'] + s['size']]
    output.mkdir(parents=True, exist_ok=True)
    for name, image in (('loader_rom.dat', rom), ('loader_ram.dat', ram)):
        file = output / name
        file.write_text(''.join(f'{int.from_bytes(image[i:i + 4], "little"):08x}\n'
                                for i in range(0, 16384, 4)), encoding='ascii')
        decoded = b''.join(int(w, 16).to_bytes(4, 'little') for w in file.read_text().split())
        if decoded != image: raise ValueError('DAT round-trip failed')
    info = {'stage': 'ROM_RESIDENT_RANDOM_STAGE9', 'entry': 0, 'sections': sections,
            'symbols': symbols, 'rx_load_pc': rx_load[0], 'rx_load_rd': rx_load[1],
            'recover_rx_load_pc': recover_load[0], 'recover_rx_load_rd': recover_load[1],
            'instructions_audited': instructions, 'isa': 'rv32i', 'abi': 'ilp32',
            'sha256': {name: sha(output / name) for name in
                       ('loader.elf', 'loader_rom.dat', 'loader_ram.dat')}}
    info.update(ddr_instructions(raw, sections, symbols))
    (output / 'manifest.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf-8')
    print(f'AUDIT PASS: ROM={sections[".text"]["size"]} RAM_CONST={sections[".rodata"]["size"]} '
          f'BSS={sections[".bss"]["size"]} instructions={instructions} entry=0 stack=0x3ff0')
    return info


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    extract(args.elf, args.output)
