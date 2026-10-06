"""Build independent C candidates, convert BIN to DAT and run real SoC/LED tests."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess

from bin_to_dat import convert

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUILD = HERE / "build"
TOOL = ROOT / "xpack-riscv-none-elf-gcc-15.2.0-1/bin"
MODELSIM = Path("D:/modelsim/win64pe")
NAMES = "alu br_alu l_alu regfile csr_file mycpu_sync inst_bus_interconnect data_bus_interconnect inst_bram_adapter data_bram_adapter simple_mmio dual_sram_to_pango_ddr_bridge uart_tx uart_rx uart_rx_fifo uart_mmio soc_top soc_ddr3_top".split()
SOURCES = [ROOT / "myriscv" / (n + ".v") for n in NAMES] + [
    ROOT / "difftest/model/inst_rom.v", ROOT / "difftest/model/data_ram.v", HERE / "tb_baremetal_c.v"]


def command(args: list, cwd: Path, log: Path) -> str:
    result = subprocess.run([str(x) for x in args], cwd=cwd, capture_output=True,
                            text=True, errors="replace", timeout=120)
    output = result.stdout + result.stderr
    log.write_text(output, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"exit={result.returncode}: {log}\n{output[-4000:]}")
    return output


def elf_info(elf: Path, binary: Path, folder: Path) -> dict:
    raw = elf.read_bytes()
    if raw[:6] != b"\x7fELF\x01\x01" or struct.unpack_from("<H", raw, 18)[0] != 243:
        raise ValueError("expected little-endian ELF32 RISC-V")
    entry, phoff = struct.unpack_from("<II", raw, 24)
    phsize, phcount = struct.unpack_from("<HH", raw, 42)
    spans = []
    for i in range(phcount):
        kind, offset, vaddr, paddr, filesz, memsz, flags, align = struct.unpack_from("<8I", raw, phoff+i*phsize)
        if kind == 1 and filesz:
            if vaddr != paddr or vaddr < 0x40000000 or vaddr+memsz > 0x4000F000:
                raise ValueError("ELF load span outside reserved program area or LMA != VMA")
            spans.append((vaddr, raw[offset:offset+filesz]))
    if entry != 0x40000000 or not spans or min(a for a, _ in spans) != entry:
        raise ValueError("loader requires entry/start at DDR base 0x40000000")
    packed = bytearray(max(a+len(b) for a, b in spans)-entry)
    for address, data in spans:
        packed[address-entry:address-entry+len(data)] = data
    if bytes(packed) != binary.read_bytes():
        raise ValueError("BIN differs from ELF loadable bytes")
    nm = command([TOOL / "riscv-none-elf-nm.exe", "-n", elf], ROOT, folder / "symbols.txt")
    symbols = {name: int(address, 16) for address, kind, name in re.findall(r"^([0-9a-fA-F]+)\s+(\w)\s+(\S+)$", nm, re.M)}
    command([TOOL / "riscv-none-elf-readelf.exe", "-h", "-A", "-l", elf], ROOT, folder / "main.readelf.txt")
    dis = command([TOOL / "riscv-none-elf-objdump.exe", "-d", elf], ROOT, folder / "main.dis")
    if "rv32i2p1" not in (folder / "main.readelf.txt").read_text():
        raise ValueError("expected RV32I attributes")
    if "c_done" in symbols:
        done = symbols["c_done"]
    else:
        loops = [int(a, 16) for a, target in re.findall(r"^([0-9a-f]+):\s+0000006f\s+j\s+([0-9a-f]+)", dis, re.M) if a == target]
        done = max(loops)
    return {"entry": entry, "main": symbols["main"], "done": done,
            "bss_start": symbols["__bss_start"], "bss_end": symbols["__bss_end"],
            "stack_top": symbols["__stack_top"], "results": symbols.get("results", symbols.get("uart_result", 0))}


def prepare(name: str, program_dir: Path) -> tuple[Path, dict]:
    folder = BUILD / name
    folder.mkdir(parents=True, exist_ok=True)
    elf, binary = folder / "main.elf", folder / "main.bin"
    if name == "uart_printf":
        shutil.copy2(program_dir / "build/main.elf", elf)
        shutil.copy2(program_dir / "build/main.bin", binary)
    else:
        c_source = HERE / ("original_main.c" if name in ("original", "timeout") else "led_main.c")
        flags = ["-march=rv32i", "-mabi=ilp32", "-O2", "-g", "-Wall", "-Wextra",
                 "-ffreestanding", "-fno-builtin", "-fno-pic", "-fno-pie", "-msmall-data-limit=0",
                 "-nostdlib", "-nostartfiles", "-Wl,--no-relax", "-Wl,--build-id=none",
                 f"-DINJECT_FAILURE={int(name == 'injected_fail')}", ROOT / "tests/fpga_uart_pc_output_30/startup.S",
                 c_source, "-T", ROOT / "tests/fpga_uart_pc_output_30/linker.ld",
                 f"-Wl,-Map={folder / 'main.map'}", "-o", elf, "-lgcc"]
        command([TOOL / "riscv-none-elf-gcc.exe", *flags], ROOT, folder / "compile.log")
        command([TOOL / "riscv-none-elf-objcopy.exe", "-O", "binary", elf, binary], ROOT, folder / "objcopy.log")
    info = elf_info(elf, binary, folder)
    info.update(convert(binary, folder))
    if info["stack_top"] != 0x40010000:
        raise ValueError("unexpected stack top")
    if name in ("original", "timeout") and (info["done"] != 0x40000060 or info["payload_bytes"] != 100):
        raise ValueError("original BIN changed; review stack/stop expectations before proceeding")
    shutil.copy2(folder / "boot_rom.dat", folder / "rom.hex")
    shutil.copy2(folder / "main.dat", folder / "ram.hex")
    (folder / "acceptance.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    return folder, info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator", choices=("modelsim", "iverilog"), default="modelsim")
    parser.add_argument("--case", choices=("all", "original", "led_pass", "injected_fail", "timeout", "uart_printf"), default="all")
    parser.add_argument("--wave", action="store_true")
    parser.add_argument("--program-dir", type=Path, default=ROOT / "tests/fpga_uart_pc_output_30",
                        help="UART printf program folder with build/main.elf and main.bin")
    options = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    # Guard live board sources/IP initialization against accidental promotion.
    protected = [ROOT / "MyCpu_test/board_selftest/boot_rom.dat", ROOT / "MyCpu_test/board_selftest/ddr_selftest.dat",
                 ROOT / "ipcore/inst_rom/inst_rom.idf", ROOT / "ipcore/data_ram/data_ram.idf",
                 ROOT / "ipcore/inst_rom/rtl/inst_rom_init_param.v", ROOT / "ipcore/data_ram/rtl/data_ram_init_param.v",
                 ROOT / "myriscv/soc_ddr3_top.v", ROOT / "RISCV.pds", ROOT / "constraint_check/temp_constraint_file.fdc",
                 ROOT / "tests/fpga_uart_pc_output_30/main.dat"]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    work = BUILD / "c_work"
    executable = BUILD / "c.vvp"
    if options.simulator == "modelsim":
        if not work.exists(): command([MODELSIM / "vlib.exe", work], ROOT, BUILD / "vlib.log")
        output = command([MODELSIM / "vlog.exe", "-sv", "-work", work, f"+incdir+{ROOT / 'myriscv'}", *SOURCES], ROOT, BUILD / "modelsim_compile.log")
        if "Errors: 0" not in output: raise RuntimeError("ModelSim compiler did not report Errors: 0")
    else:
        command(["D:/iverilog/bin/iverilog.exe", "-g2012", "-I", ROOT / "myriscv", "-s", "tb_baremetal_c", "-o", executable, *SOURCES], ROOT, BUILD / "iverilog_compile.log")
        if options.case in ("all", "uart_printf"):
            command(["D:/iverilog/bin/iverilog.exe", "-g2012", "-I", ROOT / "myriscv", "-s", "tb_baremetal_c",
                     "-Ptb_baremetal_c.LED_TIMEOUT=200000", "-Ptb_baremetal_c.MAX_CYCLES=220000",
                     "-o", BUILD / "uart_printf.vvp", *SOURCES], ROOT, BUILD / "iverilog_uart_compile.log")
    summary = []
    for name in (("original", "led_pass", "injected_fail", "timeout", "uart_printf") if options.case == "all" else (options.case,)):
        folder, info = prepare(name, options.program_dir.resolve())
        mode = {"original": 0, "led_pass": 1, "injected_fail": 2, "timeout": 3, "uart_printf": 4}[name]
        args = [f"+MODE={mode}", "+IMAGE=main.dat", f"+WORDS={info['payload_words']}",
                f"+MAIN={info['main']:x}", f"+DONE={info['done']:x}",
                f"+BSS_START={info['bss_start']:x}", f"+BSS_END={info['bss_end']:x}", f"+RESULTS={info['results']:x}"]
        if options.wave: args.append("+WAVE")
        if options.simulator == "modelsim":
            script = folder / "run.tcl"
            params = "-gLED_TIMEOUT=200000 -gMAX_CYCLES=220000" if mode == 4 else ""
            script.write_text("onerror {quit -f -code 1}\n" +
                              f"vsim -t 1ps -lib {{{work.as_posix()}}} {params} tb_baremetal_c {' '.join(args)}\n" +
                              "onfinish stop\nrun 3ms\n" +
                              "if {[examine -radix unsigned /tb_baremetal_c/test_pass] != 1} {\n" +
                              " echo {RESULT: FAIL incomplete C simulation}\n quit -f -code 1\n}\nquit -f -code 0\n", encoding="ascii")
            output = command([MODELSIM / "vsim.exe", "-c", "-do", "do run.tcl"], folder, folder / "modelsim.log")
            if "Errors: 0" not in output: raise RuntimeError(f"ModelSim Errors summary missing: {name}")
        else:
            binary_vvp = BUILD / "uart_printf.vvp" if mode == 4 else executable
            output = command(["D:/iverilog/bin/vvp.exe", binary_vvp, *args], folder, folder / "iverilog.log")
        matches = re.findall(r"^(?:# )?RESULT: PASS baremetal_c.*$", output, re.M)
        if len(matches) != 1 or "RESULT: FAIL" in output:
            raise RuntimeError(f"C acceptance failed: {folder}\n{output[-4000:]}")
        print(f"{name}: {matches[0].removeprefix('# ')}", flush=True)
        summary.append({"case": name, "result": "PASS", "acceptance": info, "log": str(folder / (options.simulator + ".log")), "evidence": matches[0]})
    after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    if before != after: raise RuntimeError("live board inputs changed during C validation")
    (BUILD / (options.simulator + "_results.json")).write_text(json.dumps({"cases": summary, "protected_sha256": after}, indent=2) + "\n", encoding="utf-8")
    print(f"TOTAL {len(summary)}/{len(summary)} PASS; live board inputs SHA256 unchanged", flush=True)


if __name__ == "__main__":
    main()
