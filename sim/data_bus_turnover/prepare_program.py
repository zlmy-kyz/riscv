"""Task032 independent program and architectural reference, no HDL execution."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
BASE = 0x40000000
MASK = 0xffffffff


def sext(v, bits):
    return (v & ((1 << bits) - 1)) - ((1 << bits) if v & (1 << (bits - 1)) else 0)


def addi(rd, rs, imm):
    return ((imm & 4095) << 20) | (rs << 15) | (rd << 7) | 0x13


def load(rd, rs, imm):
    return ((imm & 4095) << 20) | (rs << 15) | (2 << 12) | (rd << 7) | 3


def store(rs, base, imm, size=2):
    return (((imm & 4095) >> 5) << 25) | (rs << 20) | (base << 15) | (size << 12) | ((imm & 31) << 7) | 0x23


def program():
    words = [0xa5a5a5a5] * 4096
    code = [(0x40000 << 12) | (12 << 7) | 0x37, addi(12, 12, 0x300),
        (0x305 << 20) | (12 << 15) | (1 << 12) | 0x73,
        (0x40000 << 12) | (7 << 7) | 0x37, addi(1, 7, -2048),
        (0x10000 << 12) | (2 << 7) | 0x37, addi(3, 0, 1), store(3, 2, 16),
        addi(3, 0, 3), store(3, 2, 0x108),
        (0x11223 << 12) | (4 << 7) | 0x37, addi(4, 4, 0x344), addi(13, 0, 8)]
    # x1 must address BASE+0x800, despite signed 12-bit immediate range.
    code[4:5] = [(0x40001 << 12) | (1 << 7) | 0x37, addi(1, 1, -2048)]
    loop = len(code)
    code += [load(5, 1, 0), load(6, 7, 0), load(8, 1, 32), load(9, 7, 32), addi(13, 13, -1)]
    displacement = (loop - len(code)) * 4 & 8191
    code += [((displacement >> 12) << 31) | (((displacement >> 5) & 63) << 25) |
        (13 << 15) | (1 << 12) | (((displacement >> 1) & 15) << 8) |
        (((displacement >> 11) & 1) << 7) | 0x63]
    code += [store(4, 1, 0), store(4, 1, 1, 0), store(4, 1, 2, 1), load(14, 1, 0),
        store(4, 1, 4), load(15, 1, 4), store(4, 2, 0), load(16, 2, 0),
        store(4, 0, 0x40), load(17, 0, 0x40),
        (0x10001 << 12) | (18 << 7) | 0x37, store(4, 18, 0), store(4, 1, 12), 0x0ff0000f,
        addi(3, 0, 4), store(3, 2, 0x108),
        (0x20000 << 12) | (11 << 7) | 0x37, load(10, 11, 0),
        store(4, 1, 8), 0x0000006f]
    assert len(code) < 0x300 // 4
    words[:len(code)] = code
    words[0x300 // 4:0x300 // 4 + 3] = [addi(3, 0, 2), store(3, 2, 16), 0x0000006f]
    words[4092] = 1024  # Existing x32 model's preload word count.
    return words


def reference(words):
    regs = [0] * 32
    mem = {BASE + i * 4: word for i, word in enumerate(words[:1024])}
    mem[0x40] = 0
    mem[0x10000000] = 0
    events, requests = [], []
    pc, mtvec = BASE, 0
    for _ in range(1000):
        ins = mem[pc]
        op, rd, f3 = ins & 127, ins >> 7 & 31, ins >> 12 & 7
        a, b = ins >> 15 & 31, ins >> 20 & 31
        nxt, value, address = pc + 4, None, None
        if op == 0x37:
            value = ins & 0xfffff000
        elif op == 0x13:
            assert f3 == 0
            value = (regs[a] + sext(ins >> 20, 12)) & MASK
        elif op == 3:
            address = (regs[a] + sext(ins >> 20, 12)) & MASK
            error = address == 0x20000000
            requests.append(dict(write=0, size=2, addr=address, error=int(error), value=0 if error else mem[address]))
            if error:
                events.append([len(events), 'T', pc, ins, 0, 0, 0, 5, address, mtvec])
                pc = mtvec
                continue
            value = mem[address]
        elif op == 0x23:
            address = (regs[a] + sext((ins >> 25 << 5) | (ins >> 7 & 31), 12)) & MASK
            strobe = ((1 << (1 << f3)) - 1) << (address & 3)
            data = regs[b] << ((address & 3) * 8) & MASK
            requests.append(dict(write=1, size=f3, addr=address, data=data, strobe=strobe, error=0, value=0))
            if address in (0x10000010, 0x10000108, 0x10001000):
                pass
            else:
                old = mem.get(address & ~3, 0)
                mask = sum(255 << (lane * 8) for lane in range(4) if strobe >> lane & 1)
                mem[address & ~3] = old & ~mask | data & mask
        elif op == 0x63:
            assert f3 == 1
            offset = sext((ins >> 31 << 12) | ((ins >> 7 & 1) << 11) |
                ((ins >> 25 & 63) << 5) | ((ins >> 8 & 15) << 1), 13)
            if regs[a] != regs[b]:
                nxt = pc + offset
        elif op == 0x73:
            assert f3 == 1 and ins >> 20 == 0x305 and rd == 0
            mtvec = regs[a]
        elif op == 0x0f:
            assert ins == 0x0ff0000f
        else:
            raise ValueError('Unexpected instruction %08x' % ins)
        we = 15 if value is not None and rd else 0
        events.append([len(events), 'N', pc, ins, we, rd if we else 0, value if we else 0, 0, 0, nxt])
        if we:
            regs[rd] = value & MASK
        pc = nxt
        if op == 0x23 and address == 0x10000010 and regs[b] == 2:
            break
    else:
        raise ValueError('Program did not terminate')
    assert regs[14] == 0x33444444 and regs[15] == regs[16] == regs[17] == 0x11223344
    assert sum(e[1] == 'T' for e in events) == 1
    assert not any(r['write'] and r['addr'] == BASE + 0x808 for r in requests)
    return dict(events=events, requests=requests, final_words={str(a): mem[a] for a in (BASE+0x800, BASE+0x804, BASE+0x808, BASE+0x80c, 0x40, 0x10000000)})


def event_line(e):
    i, kind, pc, ins, we, rd, value, cause, tval, nxt = e
    return f'EV {i} {kind} {pc:08x} {ins:08x} {we:x} {rd} {value:08x} {cause:08x} {tval:08x} {nxt:08x}'


if __name__ == '__main__':
    words = program()
    ref = reference(words)
    for name, data in [('program.dat', '\n'.join(f'{w:08x}' for w in words)+'\n'),
        ('reference.json', json.dumps(ref, indent=2)+'\n'),
        ('reference.trace', '\n'.join(event_line(e) for e in ref['events'])+'\n')]:
        with (HERE / name).open('x', encoding='utf-8') as f:
            f.write(data)
    print(f'RESULT: PASS independent reference EV={len(ref["events"])} requests={len(ref["requests"])}; HDL NOT_RUN')
