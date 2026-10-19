"""Independent architectural reference from the unchanged hex; never reads RTL."""
from pathlib import Path
import json

BASE = 0x40000000
MASK = 0xffffffff


def sext(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def build_reference(image):
    words = [int(line, 16) for line in Path(image).read_text().split()]
    regs = [0] * 32
    mem = {BASE + i * 4: word for i, word in enumerate(words)}
    events, requests = [], []
    pc, mtvec, mepc = BASE, 0, 0
    irq = False
    loads = stores = 0
    for _ in range(2000):
        ins = words[(pc - BASE) // 4]
        op, rd, f3 = ins & 127, ins >> 7 & 31, ins >> 12 & 7
        rs1, rs2 = ins >> 15 & 31, ins >> 20 & 31
        nxt, value, kind = (pc + 4) & MASK, None, 'N'
        address = None
        if op == 0x37:
            value = ins & 0xfffff000
        elif op == 0x13:
            assert f3 == 0
            value = regs[rs1] + sext(ins >> 20, 12)
        elif op == 0x33:
            assert f3 == 0 and ins >> 25 == 0
            value = regs[rs1] + regs[rs2]
        elif op == 3:
            assert f3 == 2
            address = (regs[rs1] + sext(ins >> 20, 12)) & MASK
            value = mem[address]
            requests.append(dict(write=0, size=2, addr=address, value=value))
            loads += 1
        elif op == 0x23:
            address = (regs[rs1] + sext((ins >> 25 << 5) | (ins >> 7 & 31), 12)) & MASK
            assert f3 in (0, 1, 2)
            mask = {0: 1, 1: 3, 2: 15}[f3] << (address & 3)
            data = (regs[rs2] << ((address & 3) * 8)) & MASK
            requests.append(dict(write=1, size=f3, addr=address, data=data, strobe=mask))
            if BASE <= address < BASE + 4096:
                old = mem.get(address & ~3, 0)
                byte_mask = sum(255 << (8 * lane) for lane in range(4) if mask >> lane & 1)
                mem[address & ~3] = (old & ~byte_mask) | (data & byte_mask)
                stores += 1
        elif op == 0x63:
            assert f3 == 4
            displacement = sext((ins >> 31 << 12) | ((ins >> 7 & 1) << 11) |
                                ((ins >> 25 & 63) << 5) | ((ins >> 8 & 15) << 1), 13)
            if sext(regs[rs1], 32) < sext(regs[rs2], 32):
                nxt = (pc + displacement) & MASK
        elif op == 0x0f:
            assert f3 == 0
        elif op == 0x73:
            if ins == 0x30200073:
                kind, nxt = 'M', mepc
            elif ins >> 20 == 0x305:
                assert rd == 0 and f3 == 1
                mtvec = regs[rs1]
            else:
                assert ins in (0x30461073, 0x30046073)
        else:
            raise ValueError('Unsupported reference instruction %08x' % ins)
        we = 15 if value is not None and rd else 0
        events.append([len(events), kind, pc, ins, we, rd if we else 0,
                       (value & MASK) if we else 0, 0, 0, nxt])
        if we:
            regs[rd] = value & MASK
        pc = nxt
        if op == 0x23 and address == BASE + 0x800 and not irq:
            irq, mepc, pc = True, pc, mtvec
            events.append([len(events), 'I', mepc, 0, 0, 0, 0, 11, 0, mtvec])
        if op == 0x23 and address == 0x10000010 and regs[rs2] == 2:
            break
    else:
        raise ValueError('Reference did not terminate at TEST_STATUS PASS')
    assert len(events) == 430 and loads == 64 and stores == 73
    assert regs[20] == 1 and regs[4] == 2080 and mepc == BASE + 92
    final = {hex(address): mem[address] for address in (BASE + 0x800, BASE + 0x804, BASE + 0x820, BASE + 0x824)}
    assert list(final.values()) == [8060992, 2080, 23057, 17]
    return dict(events=events, requests=requests, final_words=final, loads=loads,
                DDR_stores=stores, irq_pc=mepc, mtvec=mtvec)


def event_line(event):
    seq, kind, pc, ins, we, rd, data, cause, tval, nxt = event
    return f'EV {seq} {kind} {pc:08x} {ins:08x} {we:x} {rd:d} {data:08x} {cause:08x} {tval:08x} {nxt:08x}'
