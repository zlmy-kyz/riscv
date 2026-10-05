"""SoC IRQ acceptance and pin-level UART IRQ tests; no board/IP image writes."""
import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "difftest/golden"))
from rvtool import Assembler, BRAM_WORDS, enc_i, parse_reg


class IRQAssembler(Assembler):
    def encode(self, text, cur):
        fields = text.replace(",", " ").split()
        op, args = fields[0].lower(), fields[1:]
        csr = {"mstatus": 0x300, "mie": 0x304, "mtvec": 0x305,
               "mepc": 0x341, "mcause": 0x342, "mtval": 0x343, "mip": 0x344}
        if op == "mret":
            return 0x30200073
        if op in ("csrr", "csrw"):
            if op == "csrr":
                return enc_i(csr[args[1]], 0, 2, parse_reg(args[0]), 0x73)
            return enc_i(csr[args[0]], parse_reg(args[1]), 1, 0, 0x73)
        return super().encode(text, cur)


def assemble(text, directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "test.S").write_text(text, encoding="utf-8")
    assembler = IRQAssembler()
    program = assembler.assemble(text)
    rom = [0] * BRAM_WORDS
    for address, word in program.items():
        rom[address // 4] = word
    (directory / "rom.hex").write_text("".join(f"{word:08x}\n" for word in rom))
    (directory / "ram.hex").write_text("00000000\n" * BRAM_WORDS)
    (directory / "prog.lst").write_text("".join(
        f"{addr:08x} {encoded or '        '} {raw}\n"
        for addr, encoded, raw in assembler.listing), encoding="utf-8")
    return assembler.sym


def cpu_program(case):
    masked = case in (1, 2)
    setup = "csrw mie,x0" if case == 2 else "csrw mie,x3"
    global_enable = "csrw mstatus,x0" if case == 1 else "csrw mstatus,x4"
    operations = {
        0: "addi x10,x0,85", 1: "csrw mstatus,x4", 2: "csrw mie,x3",
        3: "sw x7,0(x1)", 4: "lw x10,0(x1)",
        5: "sw x7,0(x1)", 6: "lw x10,0(x1)",
        7: "lw x10,8(x5)", 8: "lw x10,8(x5)",
        9: "lw x10,1(x1)", 10: "sw x7,4(x6)",
        11: "sw x7,0(x1)", 12: "addi x10,x0,85",
        13: "addi x10,x0,85", 14: "addi x10,x0,85", 15: "addi x10,x0,85",
    }
    # Serial CSR after the target bounds the independent resume address.
    return f""".org 0
addi x2,x0,1024
csrw mtvec,x2
lui x3,1
addi x3,x3,-1912
{setup}
addi x4,x0,8
{global_enable}
lui x1,0x40000
lui x5,0x10001
lui x6,0x10000
addi x7,x0,85
addi x8,x0,1
sw x8,16(x6)
{'csrr x9,mip' if masked else 'nop'}
target: {operations[case]}
resume: csrr x11,mip
addi x12,x12,1
addi x8,x0,2
sw x8,16(x6)
done: jal x0,done
.org 1024
handler: csrr x20,mcause
csrr x21,mepc
csrr x22,mtval
addi x23,x23,1
blt x20,x0,irq_return
addi x21,x21,4
csrw mepc,x21
irq_return: mret
"""


CPU_CASES = [
    "external", "global_mask", "local_mask", "ddr_store_wait", "ddr_load_wait",
    "store_response_boundary", "load_response_boundary", "mmio_wait",
    "mmio_response_boundary", "misaligned_exception_priority", "mmio_fault_priority",
    "withdrawn_during_wait", "sustained_level", "software", "timer", "three_source_priority",
]


def command(args, cwd, log):
    result = subprocess.run([str(a) for a in args], cwd=cwd,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    log.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        print(result.stdout)
        raise RuntimeError(f"command failed ({result.returncode}); {log}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("cpu", "uart"), default="cpu")
    parser.add_argument("--case", type=int)
    parser.add_argument("--wave", action="store_true")
    parser.add_argument("--ddr-code", action="store_true", help="execute foreground from DDR; ISR remains in ROM")
    options = parser.parse_args()
    build = ROOT / "sim/uart_irq/build"
    build.mkdir(parents=True, exist_ok=True)
    names = "alu br_alu l_alu regfile csr_file mycpu_sync inst_bus_interconnect data_bus_interconnect inst_bram_adapter data_bram_adapter simple_mmio dual_sram_to_pango_ddr_bridge uart_tx uart_rx uart_rx_fifo uart_mmio soc_top".split()
    sources = [ROOT / "myriscv" / f"{name}.v" for name in names]
    sources += [ROOT / "difftest/model/inst_rom.v", ROOT / "difftest/model/data_ram.v",
                ROOT / "source/tb_soc_irq.v"]
    suffix = "_ddr_code" if options.ddr_code else ""
    executable = build / f"irq{suffix}.vvp"
    command(["D:/iverilog/bin/iverilog.exe", "-g2012", f"-Ptb_soc_irq.EXEC_FROM_DDR={int(options.ddr_code)}", "-I", ROOT / "myriscv",
             "-I", ROOT / "sim/uart_irq", "-s", "tb_soc_irq", "-o", executable, *sources],
            ROOT, build / f"compile{suffix}.log")
    summary = []
    cases = range(len(CPU_CASES)) if options.case is None else [options.case]
    if options.stage == "uart":
        cases = [100]
    for case in cases:
        name = (CPU_CASES[case] if case < 100 else "uart_rx_closed_loop") + suffix
        directory = build / name
        text = cpu_program(case) if case < 100 else (ROOT / "sim/uart_irq/uart_irq.S").read_text()
        symbols = assemble(text, directory)
        if options.ddr_code:
            symbols = {label: address + (0x40001000 if address < 1024 else 0)
                       for label, address in symbols.items()}
        args = ["D:/iverilog/bin/vvp.exe", executable, f"+CASE={case}",
                f"+TARGET={symbols.get('target', 0):x}", f"+RESUME={symbols.get('resume', 0):x}"]
        for label in ("queue_load", "wait_mmio"):
            args.append(f"+{label.upper()}={symbols.get(label, 0):x}")
        if options.wave:
            args.append("+WAVE")
        output = command(args, directory, directory / "sim.log")
        if "RESULT: PASS" not in output or "RESULT: FAIL" in output:
            raise RuntimeError(f"missing PASS: {directory / 'sim.log'}")
        print(f"{name}: {next(line for line in output.splitlines() if line.startswith('RESULT: PASS'))}")
        summary.append({"case": name, "result": "PASS", "log": str(directory / "sim.log")})
    selection = f"_case{options.case}" if options.case is not None else ""
    (build / f"{options.stage}{suffix}{selection}_results.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
