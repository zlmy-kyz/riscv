"""Portable MINI DDR3 application builder and RVLD serial runner.

No PDS, ModelSim, or serial device is touched by build/plan commands.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import re
import subprocess
import sys
import time
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BSP = ROOT / "tests/bsp_workflow"
sys.path.insert(0, str(ROOT / "tools/uart_loader/candidates/bsp_workflow"))
import application  # noqa: E402
import plan  # noqa: E402

HZ = 93_750_000
LIMIT = 61_440
SOURCES = [BSP / name for name in ("startup.S", "trap.S", "trap.c", "uart.c", "timer.c", "crc32.c")]
FROZEN = {
    "performance": ("677ee766fd0fc34d1558d778a343743a1cd9287ecdbbc182cb4681af3374517d", "5275"),
    "validation": ("461c635c46c86c8e719ced403b045bca468ded7299870bf2f87f8547ce11719b", "8803"),
}
SEED_CRC = {"performance": ("e9f5", "e714", "1fd7", "8e3a"),
            "validation": ("18f2", "e3c1", "0747", "8d84")}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def within(path: Path) -> Path:
    path = path.resolve()
    path.relative_to(ROOT)
    return path


def tool_dir(value: str | None) -> Path:
    import os
    import shutil

    candidate = value or os.environ.get("RISCV_TOOLCHAIN")
    if candidate:
        path = Path(candidate).resolve()
    else:
        bundled = ROOT / "xpack-riscv-none-elf-gcc-15.2.0-1/bin"
        path = bundled if bundled.exists() else Path(shutil.which("riscv-none-elf-gcc") or "").parent
    if not (path / ("riscv-none-elf-gcc.exe" if os.name == "nt" else "riscv-none-elf-gcc")).is_file():
        raise ValueError("Install RV32 GCC and pass --toolchain <directory containing riscv-none-elf-gcc>")
    return path


def run_tool(folder: Path, tool: Path, args: list[str | Path], log: str) -> str:
    result = subprocess.run([str(tool), *map(str, args)], cwd=folder, capture_output=True, text=True, check=False)
    (folder / log).write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"{tool.name} failed; see {folder / log}")
    return result.stdout


def audit_zmmul(elf: Path, binary: Path) -> dict:
    """Use the existing layout/ISA auditor with only the four Zmmul opcodes added."""
    code = inspect.getsource(application.audit)
    guard = "for i in range(0,len(code),4):assert isa.legal_instruction(int.from_bytes(code[i:i+4],'little')),(name,i)"
    if code.count(guard) != 1:
        raise ValueError("Base ISA auditor changed; review Zmmul extension before building")
    code = code.replace(guard, "for i in range(0,len(code),4):assert (isa.legal_instruction(int.from_bytes(code[i:i+4],'little')) or zmmul_legal(int.from_bytes(code[i:i+4],'little'))),(name,i)")
    def zmmul_legal(word: int) -> bool:
        return word & 127 == 0x33 and word >> 25 == 1 and ((word >> 12) & 7) < 4
    namespace = dict(application.__dict__, zmmul_legal=zmmul_legal)
    exec(compile(code, "<share_Zmmul_ELF_audit>", "exec"), namespace)
    return namespace["audit"](elf, binary, "hello")


def build(args: argparse.Namespace) -> None:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", args.tag):
        raise ValueError("--tag must contain only letters, digits, _ or -")
    is_coremark = args.command == "build-coremark"
    if is_coremark:
        if not 1 <= args.iterations <= 10000:
            raise ValueError("--iterations must be 1..10000; keep the timed run below the 32-bit cycle wrap")
        out = ROOT / "tests/cpu_performance_2b/build" / ("share_" + args.tag)
    else:
        out = ROOT / "tests/c_app/build" / ("share_" + args.tag)
    out.mkdir(parents=True, exist_ok=False)
    compiler = tool_dir(args.toolchain)
    suffix = ".exe" if sys.platform == "win32" else ""
    def exe(name: str) -> Path:
        return compiler / ("riscv-none-elf-" + name + suffix)
    common = ["-march=rv32i_zmmul" if is_coremark else "-march=rv32i", "-mabi=ilp32", "-Os", "-g", "-Wall", "-Wextra",
              "-ffreestanding", "-fno-builtin", "-fno-pic", "-fno-pie", "-msmall-data-limit=0",
              "-ffunction-sections", "-fdata-sections", "-I", str(BSP)]
    sources = SOURCES.copy()
    if is_coremark:
        port = (BSP / "core_portme.c").read_text(encoding="utf-8")
        port = port.replace('#include "bsp.h"', '#include "bsp.h"\n#include "perf.h"', 1)
        port = port.replace("    p->portable_id = 1;", "    p->portable_id = 1;\n    perf_arm_timer_pair();", 1)
        port = port.replace("    p->portable_id = 0;", "    perf_dump();\n    p->portable_id = 0;", 1)
        if "perf_arm_timer_pair();" not in port or "perf_dump();" not in port:
            raise ValueError("CoreMark port no longer matches the counter integration")
        copied_port = out / "core_portme.c"
        copied_port.write_text(port, encoding="utf-8")
        sources += [copied_port, BSP / "ee_printf.c", ROOT / "tests/cpu_performance_2b/perf.c"]
        sources += [ROOT / "coremark-main" / (name + ".c") for name in
                    ("core_main", "core_list_join", "core_matrix", "core_state", "core_util")]
        common += ["-I", str(ROOT / "coremark-main"), "-I", str(ROOT / "tests/cpu_performance_2b"),
                   "-DTOTAL_DATA_SIZE=2000", f"-DCLOCKS_PER_SEC={HZ}", f"-DITERATIONS={args.iterations}",
                   f"-D{args.mode.upper()}_RUN=1", '-DFLAGS_STR="-Os -march=rv32i_zmmul -mabi=ilp32; no LTO"']
    else:
        user = [within(Path(name)) for name in args.source]
        if not user or any(not path.is_file() or path.suffix.lower() != ".c" for path in user):
            raise ValueError("--source must name existing C files inside this repository")
        sources += [ROOT / "tests/c_app/wrapper.c", *user]
    objects: list[Path] = []
    for index, source in enumerate(sources):
        obj = out / f"{index:02}.o"
        extra = ["-Dmain=app_main"] if not is_coremark and source in user else []
        run_tool(out, exe("gcc"), [*common, "-I", source.parent, *extra, "-c", source, "-o", obj], f"compile_{index:02}.log")
        objects.append(obj)
    elf, binary = out / "program.elf", out / "program.bin"
    run_tool(out, exe("gcc"), [*common, "-nostdlib", "-nostartfiles", "-Wl,--no-relax", "-Wl,--build-id=none",
                                "-Wl,--gc-sections", "-T", BSP / "linker.ld", f"-Wl,-Map={out / 'program.map'}",
                                *objects, "-o", elf, "-lgcc"], "link.log")
    for name, options, log in (("objcopy", ["-O", "binary", elf, binary], "objcopy.log"),
                               ("nm", ["-n", elf], "symbols.txt"), ("readelf", ["-h", "-A", "-l", "-S", elf], "readelf.txt")):
        run_tool(out, exe(name), options, log)
    # The existing ELF/ISA/layout auditor is independent of the local board gate.
    layout = audit_zmmul(elf, binary) if is_coremark else application.audit(elf, binary, "hello")
    hashed_sources = (sources + [BSP / "core_portme.c", BSP / "core_portme.h", ROOT / "tests/cpu_performance_2b/perf.h"])
    if not is_coremark:
        hashed_sources = sources
    manifest = dict(layout, kind="coremark" if is_coremark else "c_app", mode=args.mode if is_coremark else None,
                    iterations=args.iterations if is_coremark else None, toolchain=str(compiler),
                    source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in hashed_sources},
                    build_script_sha256=sha(Path(__file__)))
    (out / "share_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"BUILT {binary} bytes={layout['bytes']} sha256={layout['bin_sha256']}")
    print("Board execution remains to be tested; use run with a new log path.")


def parse_output(raw: bytes, args: argparse.Namespace) -> dict:
    if args.kind == "c":
        text = raw.decode("utf-8", errors="strict")
        if not text.endswith("\nC_APP_DONE return=0\n") or text.count("C_APP_DONE") != 1:
            raise ValueError("C application did not return 0 exactly once")
        body = text[: -len("\nC_APP_DONE return=0\n")]
        if body.count(args.expect) != 1 or "C_APP_BSP_FAIL" in body or "TRAP_FAIL" in body:
            raise ValueError("C application output/expected text mismatch")
        return {"kind": "c", "output": body}
    text = raw.decode("ascii", errors="strict")
    if not text.endswith("PERF2B_DONE\n") or text.count("PERF2B_DONE") != 1:
        raise ValueError("CoreMark counter dump did not finish")
    def one(pattern: str) -> str:
        matches = re.findall(pattern, text, re.M)
        if len(matches) != 1:
            raise ValueError("Missing/duplicate CoreMark field: " + pattern)
        return matches[0]
    if one(r"^2K (performance|validation) run parameters for coremark\.$") != args.mode:
        raise ValueError("CoreMark mode mismatch")
    ticks = int(one(r"^Total ticks\s*:\s*(\d+)$"))
    iterations = int(one(r"^Iterations\s*:\s*(\d+)$"))
    done = re.search(r"^PORT_DONE ticks=(\d+) iterations=(\d+) hz=(\d+)$", text, re.M)
    if not done or tuple(map(int, done.groups())) != (ticks, iterations, HZ) or iterations != args.iterations:
        raise ValueError("CoreMark timer/iteration mismatch")
    seconds = ticks / HZ
    whole_seconds = int(one(r"^Total time \(secs\)\s*:\s*(\d+)$"))
    if whole_seconds != ticks // HZ:
        raise ValueError("CoreMark printed time mismatch")
    labels = ("seedcrc", "[0]crclist", "[0]crcmatrix", "[0]crcstate")
    observed = tuple(one(r"^" + re.escape(label) + r"\s*:\s*0x([0-9a-f]{4})$") for label in labels)
    if observed != SEED_CRC[args.mode]:
        raise ValueError("CoreMark algorithm CRC mismatch")
    time_error = "ERROR! Must execute for at least 10 secs for a valid result!"
    if seconds >= 10:
        if "Correct operation validated." not in text or "Errors detected" in text or "ERROR!" in text:
            raise ValueError("CoreMark self-validation failed")
    elif text.count(time_error) != 1 or text.count("Errors detected") != 1 or "Correct operation validated." in text:
        raise ValueError("Unexpected short CoreMark output")
    crc = one(r"^\[0\]crcfinal\s*:\s*0x([0-9a-f]{4})$")
    if args.iterations == 300 and crc != FROZEN[args.mode][1]:
        raise ValueError("Frozen P/V300 final CRC mismatch")
    start, stop = re.search(r"^PERF2B version=1 state=3 start=(\d+) stop=(\d+)$", text, re.M).groups()
    counts = {key: int(value, 16) for key, value in re.findall(r"^PERF2B (\w+)=([0-9a-fA-F]{16})$", text, re.M)}
    if len(counts) != 13 or counts.get("cycles") != ticks or ((int(stop) - int(start)) & 0xffffffff) != ticks:
        raise ValueError("CoreMark counter/timer mismatch")
    if sum(counts[key] for key in ("if_stall_cycles", "mem_stall_cycles", "branch_flush_cycles",
                                      "control_redirect_cycles", "control_hold_cycles", "load_use_cycles", "other_cycles")) != ticks:
        raise ValueError("Cycle classification mismatch")
    return {"kind": "coremark", "mode": args.mode, "iterations": iterations, "ticks": ticks,
            "seconds": seconds, "iterations_per_second": iterations / seconds, "crcfinal": crc,
            "formal_10s": seconds >= 10, "counters": counts}


def run(args: argparse.Namespace) -> None:
    binary = within(Path(args.bin))
    raw = binary.read_bytes()
    if not 4 <= len(raw) <= LIMIT:
        raise ValueError("BIN length must be 4..61440 bytes")
    if args.kind == "c" and not args.expect:
        raise ValueError("C application requires --expect")
    if args.kind == "coremark" and (not args.mode or not args.iterations):
        raise ValueError("CoreMark requires --mode and --iterations")
    if args.kind == "coremark" and args.iterations == 300 and binary.name in ("performance_300.bin", "validation_300.bin"):
        if sha(binary) != FROZEN[args.mode][0] or binary.name != args.mode + "_300.bin":
            raise ValueError("Frozen P/V300 BIN identity mismatch")
    info = {"bin_path": binary.relative_to(ROOT).as_posix(), "bytes": len(raw), "crc32": zlib.crc32(raw) & 0xffffffff}
    rows = plan.make_plan(info)
    if args.plan_only:
        print(f"PLAN {len(rows)} RVLD responses, one RUN; BIN sha256={sha(binary)}; serial unopened")
        return
    log = Path(args.log).resolve()
    if log.exists():
        raise ValueError("Log exists; choose a fresh --log path")
    log.parent.mkdir(parents=True, exist_ok=True)
    result = {"status": "RUNNING", "bin": str(binary), "bin_sha256": sha(binary), "port": args.port,
              "kind": args.kind, "mode": args.mode, "iterations": args.iterations,
              "records": [], "application_rx_hex": "", "no_automatic_retry": True}
    with log.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    try:
        import serial
        input("Download the supplied bitstream on the matching MINI board, close serial monitors, press/release KEY0, wait for DDR ready; then Enter: ")
        with serial.Serial(args.port, 115200, timeout=.05, write_timeout=2, xonxoff=False, rtscts=False, dsrdtr=False) as port:
            if port.in_waiting:
                raise ValueError("Unexpected startup RX; reset before a new run")
            for want in rows:
                tx = bytes.fromhex(want["tx_hex"])
                entry = {"name": want["name"], "tx_hex": want["tx_hex"], "expected_hex": want["expected_hex"]}
                result["records"].append(entry)
                if port.write(tx) != len(tx):
                    raise ValueError("Short serial write")
                rx = bytearray()
                deadline = time.monotonic() + 5
                while len(rx) < 60 and time.monotonic() < deadline:
                    rx += port.read(60 - len(rx))
                entry["rx_hex"] = rx.hex()
                if len(rx) != 60:
                    raise ValueError(f"RVLD short response {len(rx)}/60 at {want['name']}")
                entry["decoded"] = plan.rvld.decode(bytes(rx), bytes.fromhex(want["expected_hex"]))
                entry["result"] = "PASS"
            output = bytearray()
            deadline = time.monotonic() + args.timeout
            end = b"\nC_APP_DONE return=0\n" if args.kind == "c" else b"PERF2B_DONE\n"
            while not output.endswith(end) and time.monotonic() < deadline:
                output += port.read(port.in_waiting or 1)
                result["application_rx_hex"] = output.hex()
                if len(output) > 65536:
                    raise ValueError("Application output exceeds 64 KiB")
            if not output.endswith(end):
                raise ValueError("Application output timeout or completion marker missing")
            result["parsed"] = parse_output(bytes(output), args)
            time.sleep(.1)
            if port.in_waiting:
                raise ValueError("Unexpected trailing UART data")
        result["status"] = "BOARD_PASS"
        print(output.decode("utf-8", errors="replace"), end="")
        print("RESULT: PASS; log:", log)
    except BaseException as error:
        result.update(status="FAIL", error=str(error))
        raise
    finally:
        log.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build-c", "build-coremark"):
        sub = commands.add_parser(name)
        sub.add_argument("--tag", required=True)
        sub.add_argument("--toolchain", help="Directory containing riscv-none-elf-gcc")
        if name == "build-c":
            sub.add_argument("--source", action="append", required=True)
        else:
            sub.add_argument("--mode", choices=("performance", "validation"), required=True)
            sub.add_argument("--iterations", type=int, required=True)
    sub = commands.add_parser("run")
    sub.add_argument("--bin", required=True)
    sub.add_argument("--kind", choices=("c", "coremark"), required=True)
    sub.add_argument("--mode", choices=("performance", "validation"))
    sub.add_argument("--iterations", type=int)
    sub.add_argument("--expect", help="Required text appearing once in C output")
    sub.add_argument("--port", default="COM9")
    sub.add_argument("--log")
    sub.add_argument("--timeout", type=int, default=90)
    sub.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    if args.command == "run":
        if not args.plan_only and not args.log:
            parser.error("run requires --log unless --plan-only is used")
        run(args)
    else:
        build(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("RESULT: FAIL", error, file=sys.stderr)
        sys.exit(1)
