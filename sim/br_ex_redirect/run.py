"""Build and run the branch / EX-redirect regression with iverilog.

Usage:
    python sim/br_ex_redirect/run.py --tag <new_tag>
    python sim/br_ex_redirect/run.py --tag <tag> --rtl <path to mycpu_sync.v>
    python sim/br_ex_redirect/run.py --tag <tag> --only 2      # bench only

Modes:
    0  directed branch / jump / load-use program, checks DMEM results
    1  misaligned-jalr must trap instead of redirecting
    2  1000 taken-branch loop, prints BENCH_DONE cycles=<n> for A/B compare

Never overwrites an existing tag directory. build/ is git-ignored.
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IVERILOG = Path("D:/iverilog/bin/iverilog.exe")
VVP = Path("D:/iverilog/bin/vvp.exe")

FIXED_SRCS = [
    ROOT / "myriscv" / "regfile.v",
    ROOT / "myriscv" / "alu.v",
    ROOT / "myriscv" / "l_alu.v",
    ROOT / "myriscv" / "br_alu.v",
    ROOT / "myriscv" / "csr_file.v",
    HERE / "mul_behavioral.v",
]

PROGRAMS = {0: "program.S", 1: "program_trap.S", 2: "program_bench.S"}
SUBDIR = {0: "m0", 1: "m1", 2: "bench"}

DMEM_INIT = {
    0: {0x40: 0x00001234, 0x41: 0x00000000, 0x44: 0x00000000, 0x48: 0x00000000},
    1: {},
    2: {},
}


def write_dmem_init(path, words):
    lines = ["00000000"] * 512
    for idx, val in words.items():
        lines[idx] = f"{val:08x}"
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def run_mode(build, mode, delay=1):
    sub = build / SUBDIR[mode]
    sub.mkdir()
    r = subprocess.run([sys.executable, str(HERE / "asm.py"),
                        str(HERE / PROGRAMS[mode]), str(sub)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit(f"assemble failed for mode {mode}")
    print(f"mode {mode}: {r.stdout.strip()}")
    write_dmem_init(sub / "dmem_init.hex", DMEM_INIT[mode])

    r = subprocess.run([str(VVP), str(build / "tb.vvp"), f"+MODE={mode}", f"+DELAY={delay}"],
                       capture_output=True, text=True, cwd=sub)
    log = r.stdout + r.stderr
    (sub / "run.log").write_text(log, encoding="utf-8", errors="replace")
    print(log)

    ok = "RESULT: PASS" in log and "RESULT: FAIL" not in log
    cycles = None
    m = re.search(r"BENCH_DONE cycles=(\d+)", log)
    if m:
        cycles = int(m.group(1))
    return ok, cycles, str(sub / "run.log")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--rtl", default=str(ROOT / "myriscv" / "mycpu_sync.v"))
    ap.add_argument("--only", type=int, choices=[0, 1, 2], default=None)
    ap.add_argument("--delay", type=int, default=1,
                    help="memory response latency in cycles (1 = ideal)")
    args = ap.parse_args()

    build = HERE / "build" / args.tag
    if build.exists():
        print(f"ERROR: {build} already exists; pick a new --tag")
        return 2
    build.mkdir(parents=True)

    srcs = [HERE / "tb_br_ex_redirect.v", Path(args.rtl)] + FIXED_SRCS
    argv = [str(IVERILOG), "-g2012", "-Wall", "-Wno-timescale",
            "-I", str(ROOT / "myriscv"), "-o", str(build / "tb.vvp")] + [str(p) for p in srcs]
    r = subprocess.run(argv, capture_output=True, text=True, cwd=build)
    (build / "compile.log").write_text(r.stdout + r.stderr, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("COMPILE FAIL")
        print(r.stdout + r.stderr)
        return 4
    print(f"compiled with rtl={args.rtl}")

    modes = [args.only] if args.only is not None else [0, 1, 2]
    results, all_ok = {}, True
    for m in modes:
        ok, cycles, logpath = run_mode(build, m, args.delay)
        all_ok = all_ok and ok
        results[f"mode{m}"] = {"pass": ok, "bench_cycles": cycles, "log": logpath}

    (build / "result.json").write_text(
        json.dumps({"tag": args.tag, "rtl": args.rtl, "pass": all_ok,
                    "modes": results}, indent=2) + "\n", encoding="utf-8")
    print("PASS" if all_ok else "FAIL")
    return 0 if all_ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
