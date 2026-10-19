"""Create simulation-only programs and independent integer retirement oracles. No HDL run."""
from pathlib import Path
import json
import random
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'difftest/golden'))
from rvtool import enc_r, enc_i, enc_s, enc_b, enc_u, enc_j, s32, imm_i, imm_s, imm_b, imm_j

BASE = 0x80000000
HANDLER = BASE + 0x3c00
STATUS = BASE + 0x3ffc
DATA = BASE + 0x3000
MASK = 0xffffffff
SEED = 2026101323


class Program:
    def __init__(self):
        self.words = {}
        self.pc = BASE
        self.meta = {}

    def emit(self, word):
        pc = self.pc
        self.words[pc] = word
        self.pc += 4
        return pc

    def li(self, rd, value):
        value &= MASK
        self.emit(enc_u(((value + 0x800) >> 12) & 0xfffff, rd, 0x37))
        self.addi(rd, rd, ((value & 0xfff) ^ 0x800) - 0x800)

    def addi(self, rd, rs, value):
        return self.emit(enc_i(value, rs, 0, rd, 0x13))

    def mul(self, op, rd=3, a=1, b=2):
        return self.emit(enc_r(1, b, a, op, rd, 0x33))

    def csr(self, csr, rd=0, rs=0, op=2):
        return self.emit(enc_i(csr, rs, op, rd, 0x73))

    def lw(self, rd, rs=10, offset=0):
        return self.emit(enc_i(offset, rs, 2, rd, 3))

    def sw(self, rs, base=10, offset=0):
        return self.emit(enc_s(offset, rs, base, 2, 0x23))

    def setup_trap(self):
        self.li(20, HANDLER)
        self.csr(0x305, rs=20, op=1)

    def handler(self, skip=True):
        saved = self.pc
        self.pc = HANDLER
        self.csr(0x342, rd=21)
        self.csr(0x343, rd=22)
        self.csr(0x341, rd=23)
        if skip:
            self.addi(23, 23, 4)
            self.csr(0x341, rs=23, op=1)
        self.emit(0x30200073)
        self.pc = saved

    def finish(self):
        self.li(30, STATUS)
        self.addi(31, 0, 1)
        self.sw(31, 30)
        self.emit(enc_j(0, 0, 0x6f))


def oracle(p):
    """Reference architectural semantics; never reads DUT values or pipeline timing."""
    regs = [0] * 32
    mem = {DATA: 0x89abcdef}
    csrs = {0x300: 0x1800, 0x301: 0x40000100, 0x304: 0, 0x305: 0,
            0x340: 0, 0x341: 0, 0x342: 0, 0x343: 0}
    events = []
    pc = BASE
    faulted = False
    interrupted = False
    muls = 0

    def event(kind, at, inst, rd=0, value=0, cause=0, tval=0):
        events.append([kind, at, inst, int(rd != 0), rd, value & MASK, cause, tval])

    def trap(at, inst, cause, tval, irq=False):
        event(2 if irq else 1, at, 0 if irq else inst, cause=cause, tval=tval)
        csrs[0x341] = at
        csrs[0x342] = cause
        csrs[0x343] = tval
        csrs[0x300] = 0x1800 | (0x80 if csrs[0x300] & 8 else 0)
        return csrs[0x305]

    for _ in range(15000):
        inst = p.words[pc]
        op = inst & 127
        rd, f3, rs1, rs2 = (inst >> 7) & 31, (inst >> 12) & 7, (inst >> 15) & 31, (inst >> 20) & 31
        a, b = regs[rs1], regs[rs2]
        nxt, write, value = pc + 4, 0, 0
        if op == 0x37:
            write, value = rd, inst & 0xfffff000
        elif op == 0x13 and f3 == 0:
            write, value = rd, a + imm_i(inst)
        elif op == 0x33 and inst >> 25 == 1 and f3 < 4:
            aa = s32(a) if f3 in (1, 2) else a
            bb = s32(b) if f3 == 1 else b
            product = aa * bb
            write, value = rd, product if f3 == 0 else product >> 32
            muls += 1
        elif op == 3 and f3 == 2:
            address = (a + imm_i(inst)) & MASK
            if address == p.meta.get('fault_address') and not faulted:
                faulted = True
                pc = trap(pc, inst, 5, address)
                continue
            write, value = rd, mem.get(address, 0)
        elif op == 0x23 and f3 == 2:
            address = (a + imm_s(inst)) & MASK
            mem[address] = b
        elif op == 0x63 and f3 in (0, 1):
            taken = (a == b) if f3 == 0 else (a != b)
            if taken:
                nxt = pc + imm_b(inst)
        elif op == 0x6f:
            write, value, nxt = rd, pc + 4, pc + imm_j(inst)
        elif op == 0x67:
            write, value, nxt = rd, pc + 4, (a + imm_i(inst)) & ~1
        elif inst == 0x30200073:
            csrs[0x300] = 0x1880 | (8 if csrs[0x300] & 0x80 else 0)
            nxt = csrs[0x341]
        elif op == 0x73 and f3 in (1, 2):
            csr = inst >> 20
            write, value = rd, csrs[csr]
            if f3 == 1 or rs1:
                new = a if f3 == 1 else value | a
                if csr == 0x300:
                    new = 0x1800 | (new & 0x88)
                elif csr == 0x304:
                    new &= 0x888
                elif csr in (0x305, 0x341):
                    new &= ~3
                elif csr == 0x301:
                    new = 0x40000100
                csrs[csr] = new
        else:
            pc = trap(pc, inst, 2, inst)
            continue
        event(3 if inst == 0x30200073 else 0, pc, inst, write, value)
        if write:
            regs[write] = value & MASK
        if op == 0x23 and address == STATUS:
            assert b == 1
            return events, muls
        previous = pc
        pc = nxt & MASK
        if previous == p.meta.get('irq_mul_pc') and not interrupted:
            interrupted = True
            pc = trap(pc, 0, 0x8000000b, 0, irq=True)
    raise AssertionError('Oracle did not finish')


def make_programs():
    rng = random.Random(SEED)
    cases = []
    edges = [0, 1, 2, 0xffffffff, 0x80000000, 0x7fffffff, 0x80000001, 0xffff0001]
    pairs = [(a, b) for a in edges for b in edges] + [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(32)]
    p = Program()
    p.li(10, DATA)
    for op in range(4):
        for a, b in pairs:
            p.li(1, a)
            p.li(2, b)
            p.mul(op)
            p.addi(4, 3, 1)
            p.sw(4)
    # rd aliases rs1/rs2, x0, load-use, consecutive multiplies and branch/jalr consumers.
    p.li(1, 7); p.li(2, 9)
    p.mul(0, rd=1); p.mul(3, rd=2); p.mul(2, rd=0)
    p.li(2, 5); p.sw(1); p.lw(1); p.mul(0, rd=5); p.sw(5)
    p.mul(0, rd=7, a=0)
    p.li(1, 0); p.mul(0)
    p.emit(enc_b(8, 0, 3, 0, 0x63)); p.addi(9, 0, 99)
    target = p.pc + 7 * 4
    p.li(1, target); p.li(2, 1); p.mul(0)
    p.emit(enc_i(0, 3, 0, 6, 0x67)); p.addi(9, 0, 98)
    assert p.pc == target
    p.finish(); cases.append(('math_dependencies', p))

    p = Program(); p.li(10, DATA); p.li(1, 0xffffffff); p.li(2, 0x80000000)
    p.lw(8); p.mul(2); p.addi(4, 3, 5); p.sw(4); p.lw(9)
    p.meta['long_memory'] = True
    p.finish(); cases.append(('memory_backpressure', p))

    p = Program(); p.li(1, 3); p.li(2, 11); p.mul(0); p.addi(4, 3, 1)
    p.meta['reset_mid_mul'] = True
    p.finish(); cases.append(('reset_mid_mul', p))

    p = Program(); p.setup_trap(); p.li(10, DATA); p.li(1, 0xffffffff); p.li(2, 17)
    p.lw(8); p.mul(1); p.addi(4, 3, 1)
    p.meta.update(fault_address=DATA, long_memory=True)
    p.finish(); p.handler(); cases.append(('older_fault_cancel', p))

    p = Program(); p.setup_trap(); p.li(20, 0x800); p.csr(0x304, rs=20, op=1)
    p.li(20, 8); p.csr(0x300, rs=20, op=1)
    p.li(1, 0x80000000); p.li(2, 0xffffffff)
    p.meta['irq_mul_pc'] = p.mul(2)
    p.addi(4, 3, 1); p.finish(); p.handler(skip=False); cases.append(('irq_drain', p))

    p = Program(); p.setup_trap(); p.li(1, 7); p.li(2, 0xffffffff)
    p.csr(0x301, rd=7)
    for op in range(4, 8):
        p.mul(op)
    p.emit(enc_r(2, 2, 1, 0, 3, 0x33))
    p.csr(0x301, rs=1, op=1); p.csr(0x301, rd=7)
    p.mul(0); p.finish(); p.handler(); cases.append(('illegal_div_rem_misa', p))
    return cases, pairs


def main():
    out = HERE / 'fixtures'
    out.mkdir(exist_ok=True)
    cases, pairs = make_programs()
    plan = []
    for index, (name, p) in enumerate(cases):
        events, muls = oracle(p)
        rom = [p.words.get(BASE + i * 4, 0x13) for i in range(4096)]
        ram = [0] * 4096; ram[(DATA - BASE) // 4] = 0x89abcdef
        for kind, values in [('rom', rom), ('ram', ram)]:
            (out / f'{name}_{kind}.hex').write_text(''.join(f'{v:08x}\n' for v in values), encoding='ascii')
        (out / f'{name}_trace.txt').write_text(''.join(' '.join(f'{v:08x}' for v in row) + '\n' for row in events), encoding='ascii')
        plan.append(dict(index=index, name=name, events=len(events), mul_retirements=muls, **p.meta))
    # Raw 33x33 signed full product, with negative inputs and all 66 output bits checked.
    edges33 = [0, 1, 2, (1 << 32) - 1, -(1 << 32), -1, -2, -(1 << 32) + 1]
    raw = [(a, b) for a in edges33 for b in edges33] + [(random.Random(SEED+i).randrange(-(1<<32), 1<<32), random.Random(SEED+100+i).randrange(-(1<<32), 1<<32)) for i in range(64)]
    (out / 'ip_vectors.txt').write_text(''.join(f'{a & ((1<<33)-1):09x} {b & ((1<<33)-1):09x} {(a*b) & ((1<<66)-1):017x}\n' for a,b in raw), encoding='ascii')
    supported = sorted(p.name for p in (ROOT / 'MyCpu_test/dat').iterdir() if p.is_dir() and (p / (p.name+'_rom.dat')).exists() and p.name not in ('fence_i', 'ma_data'))
    sample = random.Random(SEED).sample(supported, 2)
    isa = []
    for name in sample:
        dump = ROOT / f'MyCpu_test/dump/rv32ui-p-{name}.dump'
        address = re.findall(r'#\s*([0-9a-fA-F]{8})\s*<tohost>', dump.read_text(encoding='utf-8', errors='replace'))
        assert address and len(set(address)) == 1, name
        rom = ROOT / f'MyCpu_test/dat/{name}/{name}_rom.dat'
        ram = ROOT / f'MyCpu_test/dat/{name}/{name}_ram.dat'
        isa.append(dict(name=name, rom=rom.relative_to(ROOT).as_posix(), ram=ram.relative_to(ROOT).as_posix() if ram.exists() else None, tohost=int(address[0],16), dump=dump.relative_to(ROOT).as_posix()))
    result = dict(seed=SEED, raw_ip_vectors=len(raw), multiply_math_vectors=4*len(pairs), cases=plan, isa_cases=isa, supported_population=supported)
    (HERE / 'test_plan.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
