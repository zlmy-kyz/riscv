#!/usr/bin/env python3
"""重放提交日志的独立 RV32I/M-mode 参考模型；逐次核对 trap/MRET 全状态。"""

import pathlib
import sys

from rvtool import MASK32, ROM_WORDS, imm_b, imm_i, imm_j, imm_s, s32, sext


class TrapNeeded(Exception):
    def __init__(self, cause, tval):
        self.cause = cause
        self.tval = tval & MASK32


class Machine:
    CSR_MSTATUS = 0x300
    CSR_MISA = 0x301
    CSR_MIE = 0x304
    CSR_MTVEC = 0x305
    CSR_MSTATUSH = 0x310
    CSR_MSCRATCH = 0x340
    CSR_MEPC = 0x341
    CSR_MCAUSE = 0x342
    CSR_MTVAL = 0x343
    CSR_MIP = 0x344
    IDS = {0xF11, 0xF12, 0xF13, 0xF14, 0xF15}
    CSRS = {CSR_MSTATUS, CSR_MISA, CSR_MIE, CSR_MTVEC, CSR_MSTATUSH,
            CSR_MSCRATCH, CSR_MEPC, CSR_MCAUSE, CSR_MTVAL, CSR_MIP} | IDS

    def __init__(self, rom):
        self.rom = rom
        self.ram = bytearray(ROM_WORDS * 4)
        self.rf = [0] * 32
        self.pc = 0
        self.csr = {self.CSR_MSTATUS: 0x1800, self.CSR_MIE: 0,
                    self.CSR_MTVEC: 0x100, self.CSR_MSCRATCH: 0,
                    self.CSR_MEPC: 0, self.CSR_MCAUSE: 0,
                    self.CSR_MTVAL: 0}
        self.counts = {"R": 0, "T": 0, "M": 0, "I": 0, "S": 0}

    def csr_read(self, address, raw_irq):
        if address == self.CSR_MISA:
            return 0x40000100
        if address == self.CSR_MIP:
            return raw_irq & 0x888
        if address == self.CSR_MSTATUSH or address in self.IDS:
            return 0
        return self.csr[address]

    def csr_write(self, address, value):
        value &= MASK32
        if address == self.CSR_MSTATUS:
            self.csr[address] = 0x1800 | (value & 0x88)
        elif address == self.CSR_MIE:
            self.csr[address] = value & 0x888
        elif address in (self.CSR_MTVEC, self.CSR_MEPC):
            self.csr[address] = value & ~3
        elif address == self.CSR_MCAUSE:
            self.csr[address] = value & 0x8000001F
        elif address in (self.CSR_MSCRATCH, self.CSR_MTVAL):
            self.csr[address] = value
        # misa、mstatush、mip 的已实现固定/硬件字段写入无效果。

    def trap(self, cause, tval, is_interrupt):
        old_status = self.csr[self.CSR_MSTATUS]
        self.csr[self.CSR_MEPC] = self.pc & ~3
        self.csr[self.CSR_MCAUSE] = (0x80000000 if is_interrupt else 0) | cause
        self.csr[self.CSR_MTVAL] = tval & MASK32
        self.csr[self.CSR_MSTATUS] = 0x1800 | (0x80 if old_status & 8 else 0)
        self.pc = self.csr[self.CSR_MTVEC]

    def interrupt(self, raw_irq):
        eligible = raw_irq & self.csr[self.CSR_MIE] & 0x888
        if not (self.csr[self.CSR_MSTATUS] & 8) or not eligible:
            raise AssertionError("masked or withdrawn interrupt was accepted")
        cause = 11 if eligible & 0x800 else 3 if eligible & 0x008 else 7
        self.trap(cause, 0, True)
        return cause

    def load(self, addr, size, signed):
        start = addr % len(self.ram)
        data = bytes(self.ram[(start + i) % len(self.ram)] for i in range(size))
        value = int.from_bytes(data, "little")
        return sext(value, size * 8) & MASK32 if signed else value

    def store(self, addr, size, value):
        for i in range(size):
            self.ram[(addr + i) % len(self.ram)] = (value >> (i * 8)) & 0xFF

    def step(self, raw_irq):
        pc = self.pc
        inst = self.rom[(pc >> 2) & (ROM_WORDS - 1)]
        op, rd = inst & 0x7F, (inst >> 7) & 31
        f3, rs1, rs2 = (inst >> 12) & 7, (inst >> 15) & 31, (inst >> 20) & 31
        f7 = (inst >> 25) & 0x7F
        a, b = self.rf[rs1], self.rf[rs2]
        nxt, wb = (pc + 4) & MASK32, None
        try:
            if (inst & 3) != 3:
                raise TrapNeeded(2, inst)
            if op == 0x33:
                if f7 == 0:
                    ops = {0: lambda: a + b, 1: lambda: a << (b & 31),
                           2: lambda: int(s32(a) < s32(b)), 3: lambda: int(a < b),
                           4: lambda: a ^ b, 5: lambda: a >> (b & 31),
                           6: lambda: a | b, 7: lambda: a & b}
                    wb = ops[f3]()
                elif f7 == 0x20 and f3 in (0, 5):
                    wb = a - b if f3 == 0 else s32(a) >> (b & 31)
                else:
                    raise TrapNeeded(2, inst)
            elif op == 0x13:
                immediate = imm_i(inst)
                if f3 in (0, 2, 3, 4, 6, 7):
                    wb = {0: lambda: a + immediate,
                          2: lambda: int(s32(a) < immediate),
                          3: lambda: int(a < (immediate & MASK32)),
                          4: lambda: a ^ immediate,
                          6: lambda: a | immediate,
                          7: lambda: a & immediate}[f3]()
                elif f3 == 1 and f7 == 0:
                    wb = a << rs2
                elif f3 == 5 and f7 in (0, 0x20):
                    wb = a >> rs2 if f7 == 0 else s32(a) >> rs2
                else:
                    raise TrapNeeded(2, inst)
            elif op in (0x37, 0x17):
                wb = (inst & 0xFFFFF000) + (pc if op == 0x17 else 0)
            elif op == 0x03:
                if f3 not in (0, 1, 2, 4, 5):
                    raise TrapNeeded(2, inst)
                address = (a + imm_i(inst)) & MASK32
                size = 4 if f3 == 2 else 2 if f3 in (1, 5) else 1
                if address & (size - 1):
                    raise TrapNeeded(4, address)
                wb = self.load(address, size, f3 in (0, 1, 2))
            elif op == 0x23:
                if f3 not in (0, 1, 2):
                    raise TrapNeeded(2, inst)
                address = (a + imm_s(inst)) & MASK32
                size = 4 if f3 == 2 else 2 if f3 == 1 else 1
                if address & (size - 1):
                    raise TrapNeeded(6, address)
                self.store(address, size, b)
            elif op == 0x63:
                if f3 not in (0, 1, 4, 5, 6, 7):
                    raise TrapNeeded(2, inst)
                taken = {0: lambda: a == b, 1: lambda: a != b,
                         4: lambda: s32(a) < s32(b),
                         5: lambda: s32(a) >= s32(b),
                         6: lambda: a < b, 7: lambda: a >= b}[f3]()
                if taken:
                    nxt = (pc + imm_b(inst)) & MASK32
                    if nxt & 3:
                        raise TrapNeeded(0, nxt)
            elif op == 0x6F:
                nxt = (pc + imm_j(inst)) & MASK32
                if nxt & 3:
                    raise TrapNeeded(0, nxt)
                wb = (pc + 4) & MASK32
            elif op == 0x67 and f3 == 0:
                nxt = (a + imm_i(inst)) & MASK32 & ~1
                if nxt & 3:
                    raise TrapNeeded(0, nxt)
                wb = (pc + 4) & MASK32
            elif op == 0x73:
                if inst in (0x00000073, 0x00100073):
                    raise TrapNeeded(11 if inst == 0x00000073 else 3, 0)
                if inst == 0x30200073:
                    old = self.csr[self.CSR_MSTATUS]
                    self.csr[self.CSR_MSTATUS] = 0x1800 | (8 if old & 0x80 else 0) | 0x80
                    self.pc = self.csr[self.CSR_MEPC]
                    return "M", None
                if inst == 0x10500073:  # 本核 WFI 作为串行 NOP
                    pass
                elif f3 in (1, 2, 3, 5, 6, 7):
                    address = (inst >> 20) & 0xFFF
                    if address not in self.CSRS:
                        raise TrapNeeded(2, inst)
                    read_en = f3 not in (1, 5) or rd != 0
                    write_en = f3 in (1, 5) or rs1 != 0
                    if write_en and address in self.IDS:
                        raise TrapNeeded(2, inst)
                    old = self.csr_read(address, raw_irq) if read_en else 0
                    source = rs1 if f3 >= 5 else a
                    if write_en:
                        value = (source if f3 in (1, 5) else
                                 old | source if f3 in (2, 6) else old & ~source)
                        self.csr_write(address, value)
                    wb = old
                else:
                    raise TrapNeeded(2, inst)
            elif op == 0x0F and f3 == 0:  # FENCE；本阶段串行 NOP
                pass
            else:
                raise TrapNeeded(2, inst)
        except TrapNeeded as fault:
            self.trap(fault.cause, fault.tval, False)
            return "T", (fault.cause, fault.tval)

        self.pc = nxt
        if wb is not None and rd != 0:
            wb &= MASK32
            self.rf[rd] = wb
            return "R", (rd, wb)
        return "R", None

    def compare_snapshot(self, values, context):
        if len(values) != 8 + 32 + 1024:
            raise AssertionError(f"{context}: snapshot fields={len(values)}")
        expected = [self.pc, self.csr[self.CSR_MSTATUS], self.csr[self.CSR_MIE],
                    self.csr[self.CSR_MTVEC], self.csr[self.CSR_MSCRATCH],
                    self.csr[self.CSR_MEPC], self.csr[self.CSR_MCAUSE],
                    self.csr[self.CSR_MTVAL]] + self.rf
        expected += [int.from_bytes(self.ram[4*i:4*i+4], "little") for i in range(1024)]
        for index, (actual, reference) in enumerate(zip(values, expected)):
            if actual != reference:
                label = ("PC/mstatus/mie/mtvec/mscratch/mepc/mcause/mtval".split("/")
                         + [f"x{i}" for i in range(32)]
                         + [f"ram[{i}]" for i in range(1024)])[index]
                raise AssertionError(f"{context}: {label} DUT={actual:08x} reference={reference:08x}")


def replay(directory):
    rom = [int(line, 16) for line in (directory / "rom.hex").read_text().splitlines()]
    machine = Machine(rom)
    path = directory / "arch_events.txt"
    awaiting_snapshot = False
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        fields = line.split()
        kind = fields[0]
        values = [int(field, 16) for field in fields[1:]]
        context = f"{directory.name}:{line_number}:{kind}"
        if kind == "S":
            if not awaiting_snapshot:
                raise AssertionError(f"{context}: unexpected snapshot")
            machine.compare_snapshot(values, context)
            awaiting_snapshot = False
            machine.counts[kind] += 1
            continue
        if awaiting_snapshot:
            raise AssertionError(f"{context}: missing snapshot after trap/MRET")
        if kind in ("R", "T", "M"):
            pc, inst, raw_irq = values[:3]
            expected_inst = machine.rom[(machine.pc >> 2) & (ROM_WORDS - 1)]
            if (pc, inst) != (machine.pc, expected_inst):
                raise AssertionError(f"{context}: PC/inst DUT={pc:08x}/{inst:08x} "
                                     f"reference={machine.pc:08x}/{expected_inst:08x}")
            actual_kind, payload = machine.step(raw_irq)
            if kind != actual_kind:
                raise AssertionError(f"{context}: DUT event {kind}, reference {actual_kind}")
            if kind == "R":
                we, rd, data = values[3:]
                expected_wb = payload
                if (we, rd, data) != ((1, *expected_wb) if expected_wb else (0, 0, 0)):
                    raise AssertionError(f"{context}: WB DUT={(we, rd, data)} reference={expected_wb}")
            elif kind == "T" and (values[3], values[4]) != payload:
                raise AssertionError(f"{context}: cause/tval DUT={values[3:5]} reference={payload}")
        elif kind == "I":
            raw_irq, cause = values
            expected_cause = machine.interrupt(raw_irq)
            if cause != expected_cause:
                raise AssertionError(f"{context}: IRQ cause DUT={cause} reference={expected_cause}")
        else:
            raise AssertionError(f"{context}: unknown event")
        awaiting_snapshot = kind in ("T", "I", "M")
        machine.counts[kind] += 1
    if awaiting_snapshot:
        raise AssertionError("trace ended before trap/MRET snapshot")
    if machine.counts["S"] != sum(machine.counts[k] for k in ("T", "I", "M")):
        raise AssertionError("snapshot count differs from trap/MRET events")
    print("RESULT: PASS independent ISS replay " +
          " ".join(f"{key}={value}" for key, value in machine.counts.items()))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: trap_iss.py <build-directory>")
    replay(pathlib.Path(sys.argv[1]))
