"""Read the final FPGA DAT and run four gated UART Echo layers; never rebuild it."""
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
BUILD = HERE / "build"
TEST = ROOT / "tests/pc_uart_fpga_uart_pc/build"
MS = Path("D:/modelsim/win64pe")
IV = Path("D:/iverilog/bin")
TOOL = ROOT / "xpack-riscv-none-elf-gcc-15.2.0-1/bin"
LAYERS = ["uart_module", "uart_mmio", "cpu_echo", "full_boot"]
NAMES = "alu br_alu l_alu regfile csr_file mycpu_sync inst_bus_interconnect data_bus_interconnect inst_bram_adapter data_bram_adapter simple_mmio dual_sram_to_pango_ddr_bridge uart_tx uart_rx uart_rx_fifo uart_mmio soc_top".split()
SOURCES = [ROOT / "myriscv" / (n + ".v") for n in NAMES] + list((HERE / "tb").glob("*.v"))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def command(args, folder, log, timeout=180):
    started = time.monotonic()
    try:
        p = subprocess.run(list(map(str, args)), cwd=folder, capture_output=True,
                           text=True, errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired as error:
        log.write_text("RESULT: FAIL process timeout\n", encoding="utf-8")
        raise RuntimeError(f"process timeout: {log}") from error
    text = p.stdout + p.stderr
    log.write_text(text, encoding="utf-8")
    if p.returncode:
        raise RuntimeError(f"exit={p.returncode}: {log}\n{text[-3000:]}")
    return text, round(time.monotonic()-started, 2)

def image_info():
    dat, binary, elf = (TEST / ("main." + suffix) for suffix in ("dat", "bin", "elf"))
    if not all(p.is_file() for p in (dat, binary, elf)):
        raise RuntimeError("Build once first: ./tests/pc_uart_fpga_uart_pc/build.ps1")
    image = [int(x, 16) for x in dat.read_text().split()]
    payload = binary.read_bytes()
    words = (len(payload)+3)//4
    padded = payload + bytes((-len(payload)) % 4)
    if len(image) != 4096 or image[-4:] != [words, 0, 0, 0] or \
       b"".join(x.to_bytes(4, "little") for x in image[:words]) != padded or any(image[words:4092]):
        raise RuntimeError("final DAT does not match BIN/loader manifest")
    raw = elf.read_bytes()
    if raw[:6] != b"\x7fELF\x01\x01" or struct.unpack_from("<H", raw, 18)[0] != 243:
        raise RuntimeError("expected ELF32 little-endian RISC-V")
    entry, phoff = struct.unpack_from("<II", raw, 24)
    phsize, phcount = struct.unpack_from("<HH", raw, 42)
    loaded = bytearray(len(payload))
    for i in range(phcount):
        kind, off, va, pa, fs, mem, flags, align = struct.unpack_from("<8I", raw, phoff+i*phsize)
        if kind==1 and fs:
            if va!=pa or va<0x40000000 or va+mem>0x4000f000 or va+fs>0x40000000+len(payload):
                raise RuntimeError("ELF load span outside program area")
            loaded[va-0x40000000:va-0x40000000+fs] = raw[off:off+fs]
    if entry!=0x40000000 or bytes(loaded)!=payload:
        raise RuntimeError("ELF entry/BIN mismatch")
    BUILD.mkdir(parents=True, exist_ok=True)
    text, _ = command([TOOL / "riscv-none-elf-nm.exe", "-n", elf], BUILD, BUILD / "symbols.log")
    syms = {name:int(addr,16) for addr,kind,name in re.findall(r"^([0-9a-f]+)\s+(\w)\s+(\S+)$", text, re.M)}
    if syms["__stack_top"]!=0x40010000: raise RuntimeError("bad stack top")
    loads = [0x40000000+4*i for i,word in enumerate(image[:words])
             if syms["uart_getchar"]<=0x40000000+4*i<syms["uart_putchar"]
             and word & 0x707f == 0x4003]
    if len(loads)!=1: raise RuntimeError("expected one LBU in uart_getchar")
    return {"dat": str(dat), "dat_sha256": sha(dat), "elf_sha256": sha(elf),
            "bin_sha256": sha(binary), "payload_words": words, "main": syms["main"],
            "bss_start": syms["__bss_start"], "bss_end": syms["__bss_end"],
            "rx_load_pc":loads[0], "count_addr":syms["echo_count"], "error_addr":syms["echo_error"]}

def run(options):
    info = image_info()
    protected = [TEST / "main.dat", ROOT / "tests/fpga_uart_pc_output_30/main.dat",
                 ROOT / "RISCV.pds", ROOT / "constraint_check/temp_constraint_file.fdc",
                 ROOT / "ipcore/data_ram/data_ram.idf", ROOT / "ipcore/data_ram/data_ram.v",
                 ROOT / "ipcore/data_ram/rtl/data_ram_init_param.v",
                 ROOT / "ipcore/inst_rom/rtl/inst_rom_init_param.v"] + [p for p in (ROOT / "myriscv").glob("*.v")]
    before = {str(p):sha(p) for p in protected}
    results = []
    for layer, name in enumerate(LAYERS):
        folder = BUILD / name
        folder.mkdir(parents=True, exist_ok=True)
        plus = [f"+DAT={TEST.joinpath('main.dat').as_posix()}",
                f"+ROM={ROOT.joinpath('MyCpu_test/board_selftest/boot_rom.dat').as_posix()}",
                f"+MAIN={info['main']:x}", f"+BSS_START={info['bss_start']:x}", f"+BSS_END={info['bss_end']:x}",
                f"+RX_LOAD_PC={info['rx_load_pc']:x}", f"+COUNT_ADDR={info['count_addr']:x}", f"+ERROR_ADDR={info['error_addr']:x}"]
        if options.simulator == "modelsim":
            work = folder / "work"
            if not work.exists(): command([MS / "vlib.exe", work], folder, folder / "vlib.log")
            compile_text, _ = command([MS / "vlog.exe", "-sv", "-work", work,
                f"+incdir+{ROOT / 'myriscv'}", *SOURCES], folder, folder / "compile.log")
            if "Errors: 0" not in compile_text: raise RuntimeError("ModelSim compile missing Errors: 0")
            script = folder / "run.tcl"
            script.write_text("onerror {quit -f -code 1}\n" +
                f"vsim -t 1ps -lib {{{work.as_posix()}}} -gLAYER={layer} tb_uart_echo {' '.join(plus)}\n" +
                "onfinish stop\nrun 20ms\n" +
                "if {[examine -radix unsigned /tb_uart_echo/test_pass] != 1} {\n" +
                "echo {RESULT: FAIL incomplete echo simulation}\nquit -f -code 1\n}\nquit -f -code 0\n", encoding="ascii")
            output, seconds = command([MS / "vsim.exe", "-c", "-do", "do run.tcl"], folder, folder / "modelsim.log")
            if "Errors: 0" not in output: raise RuntimeError("ModelSim missing Errors: 0")
        else:
            exe = folder / "echo.vvp"
            command([IV / "iverilog.exe", "-g2012", "-I", ROOT / "myriscv", "-s", "tb_uart_echo",
                     f"-Ptb_uart_echo.LAYER={layer}", "-o", exe, *SOURCES], folder, folder / "compile.log")
            output, seconds = command([IV / "vvp.exe", exe, *plus], folder, folder / "iverilog.log")
        matches = re.findall(r"^(?:# )?RESULT: PASS uart_echo.*$", output, re.M)
        if len(matches)!=1 or "RESULT: FAIL" in output or "$fatal" in output:
            raise RuntimeError(f"{name} acceptance failed: {folder}")
        if {str(p):sha(p) for p in protected}!=before:
            raise RuntimeError("protected source/image changed during simulation")
        print(f"{name}: {matches[0].removeprefix('# ')} ({seconds}s)", flush=True)
        results.append({"layer":name,"result":"PASS","evidence":matches[0],"seconds":seconds})
    report = {"simulator":options.simulator,"image":info,"results":results,
              "protected_sha256":before,"board_result":"NOT_TESTED"}
    (BUILD / f"{options.simulator}_results.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    # This receipt binds deployment to the exact validated DAT, not a rebuild.
    (BUILD / f"{options.simulator}_validated_image.json").write_text(json.dumps(info,indent=2)+"\n",encoding="utf-8")
    print("RESULT: PASS uart_echo all layers 4/4; final DAT unchanged; board NOT_TESTED",flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator",choices=["modelsim","iverilog"],default="modelsim")
    args=parser.parse_args()
    try: run(args)
    except Exception as error:
        print(f"RESULT: FAIL uart_echo: {error}",file=sys.stderr,flush=True)
        sys.exit(1)
