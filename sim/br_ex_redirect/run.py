"""Build and run the branch / EX-redirect regression with iverilog.

Usage:
    python sim/br_ex_redirect/run.py [--tag name]

Creates build/<tag>/ containing imem.hex, dmem_init.hex, program.lst,
compile.log and run.log. Never overwrites an existing tag directory.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IVERILOG = Path("D:/iverilog/bin/iverilog.exe")
VVP = Path("D:/iverilog/bin/vvp.exe")

SRCS = [
    HERE / "tb_br_ex_redirect.v",
    ROOT / "myriscv" / "mycpu_sync.v",
    ROOT / "myriscv" / "regfile.v",
    ROOT / "myriscv" / "alu.v",
    ROOT / "myriscv" / "l_alu.v",
    ROOT / "myriscv" / "br_alu.v",
    ROOT / "myriscv" / "csr_file.v",
    HERE / "mul_behavioral.v",
]


def write_dmem_init(path, words):
    lines = ["00000000"] * 512
    for idx, val in words.items():
        lines[idx] = f"{val:08x}"
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="br_ex_redirect_20261018_a")
    args = ap.parse_args()

    build = HERE / "build" / args.tag
    if build.exists():
        print(f"ERROR: {build} already exists; pick a new --tag")
        return 2
    build.mkdir(parents=True)

    r = subprocess.run([sys.executable, str(HERE / "asm.py"), str(HERE / "program.S"), str(build)],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr)
        return 3

    trap_build = build / "trap"
    trap_build.mkdir()
    r = subprocess.run([sys.executable, str(HERE / "asm.py"), str(HERE / "program_trap.S"), str(trap_build)],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr)
        return 3

    write_dmem_init(build / "dmem_init.hex", {
        0x40: 0x00001234,   # 0x100: non-zero word for the branch test
        0x41: 0x00000000,   # 0x104: zero word
        0x44: 0x00000000,   # 0x110: scratch for the jalr test
        0x48: 0x00000000,   # 0x120: zero word holding MEM in case 6
    })
    write_dmem_init(trap_build / "dmem_init.hex", {})

    argv = [str(IVERILOG), "-g2012", "-Wall", "-Wno-timescale", "-I", str(ROOT / "myriscv"),
            "-o", str(build / "tb.vvp")] + [str(p) for p in SRCS]
    r = subprocess.run(argv, capture_output=True, text=True, cwd=build)
    (build / "compile.log").write_text(r.stdout + r.stderr, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("COMPILE FAIL")
        print(r.stdout + r.stderr)
        return 4

    ok = True
    for mode, sub in ((0, build), (1, trap_build)):
        r = subprocess.run([str(VVP), str(build / "tb.vvp"), f"+MODE={mode}"],
                           capture_output=True, text=True, cwd=sub)
        log = r.stdout + r.stderr
        name = "run.log" if mode == 0 else "run_trap.log"
        (sub / name).write_text(log, encoding="utf-8", errors="replace")
        print(log)
        if not ("RESULT: PASS" in log and "RESULT: FAIL" not in log):
            ok = False

    (build / "result.json").write_text(
        json.dumps({"tag": args.tag, "pass": ok,
                    "modes": ["main", "trap"],
                    "logs": [str(build / "run.log"), str(trap_build / "run_trap.log")]}, indent=2) + "\n",
        encoding="utf-8")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
