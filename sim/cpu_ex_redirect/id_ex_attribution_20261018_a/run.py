"""Task040 runner: dynamic attribution for CPU 039.

Runs a small matrix of short programs against the frozen CPU and reports the
five-event timing plus the real OTHER classification.

Configurations (each a separate run directory, never overwritten):
  1  m1_fast      prog_m1, no slow address          -> baseline t0..t4
  2  m1_slowwrong prog_m1, sequential slot slow(8)   -> wrong-path occupancy
  3  m3_oldmem_d1 prog_m3, load 1 cycle              -> older-MEM wait
  4  m3_oldmem_d8 prog_m3, load 8 cycles             -> older-MEM wait (long)
  5  m4_nottaken  prog_m4                            -> not-taken control
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ASM = HERE.parents[1] / "br_ex_redirect" / "asm.py"
MUL = HERE.parents[1] / "br_ex_redirect" / "mul_behavioral.v"
IVERILOG = Path("D:/iverilog/bin/iverilog.exe")
VVP = Path("D:/iverilog/bin/vvp.exe")

DEPS = [
    ROOT / "myriscv" / "regfile.v",
    ROOT / "myriscv" / "alu.v",
    ROOT / "myriscv" / "l_alu.v",
    ROOT / "myriscv" / "br_alu.v",
    ROOT / "myriscv" / "csr_file.v",
    ROOT / "myriscv" / "simple_mmio.v",   # provides cpu_perf_counters
    MUL,
]

RUNS = [
    # name, program, mode, ddelay, slow_after_branch, slowdelay
    ("m1_fast",       "prog_m1.S", 1, 1, False, 8),
    ("m1_slowwrong",  "prog_m1.S", 1, 1, True,  8),
    ("m3_oldmem_d1",  "prog_m3.S", 1, 1, False, 8),
    ("m3_oldmem_d8",  "prog_m3.S", 1, 8, False, 8),
    ("m4_nottaken",   "prog_m4.S", 4, 1, False, 8),
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def branch_addr(lst_path):
    """Address of the first 'beq' in the listing (the taken branch under test)."""
    for line in lst_path.read_text(encoding="utf-8").splitlines():
        if " beq " in line:
            return int(line.split(":")[0].strip(), 16)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--cpu", default=str(ROOT / "myriscv" / "mycpu_sync.v"))
    args = ap.parse_args()

    build = HERE / "build" / args.tag
    if build.exists():
        print(f"ERROR: {build} exists; pick a new tag")
        return 2
    build.mkdir(parents=True)

    cpu = Path(args.cpu).resolve()
    srcs = [HERE / "tb_id_ex_attribution.v", cpu] + DEPS
    argv = [str(IVERILOG), "-g2012", "-Wall", "-Wno-timescale",
            "-I", str(ROOT / "myriscv"), "-o", str(build / "tb.vvp")] + [str(p) for p in srcs]
    r = subprocess.run(argv, capture_output=True, text=True, cwd=build)
    (build / "compile.log").write_text(r.stdout + r.stderr, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("COMPILE FAIL")
        print(r.stdout + r.stderr)
        return 4
    print(f"compiled cpu={cpu} sha={sha(cpu)}")

    ident = {str(p): sha(p) for p in srcs}
    summary = {}
    for name, prog, mode, ddelay, slow_after, slowdelay in RUNS:
        sub = build / name
        sub.mkdir()
        r = subprocess.run([sys.executable, str(ASM), str(HERE / prog), str(sub)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout, r.stderr)
            return 3
        (sub / "dmem_init.hex").write_text("\n".join(["00000000"] * 512) + "\n", encoding="ascii")

        plus = [f"+MODE={mode}", f"+DDELAY={ddelay}", f"+SLOWDELAY={slowdelay}"]
        if slow_after:
            ba = branch_addr(sub / "program.lst")
            plus.append(f"+SLOWADDR={ba + 4}")
        r = subprocess.run([str(VVP), str(build / "tb.vvp")] + plus,
                           capture_output=True, text=True, cwd=sub)
        log = r.stdout + r.stderr
        (sub / "run.log").write_text(log, encoding="utf-8", errors="replace")

        keep = [ln for ln in log.splitlines()
                if ln.startswith(("EVENT", "DELTA", "WRONGPATH", "CLASS", "OTHER", "IOPS",
                                  "----", "RESULT"))]
        summary[name] = {"plusargs": plus, "lines": keep,
                         "verdict": next((l for l in keep if l.startswith("RESULT")), "NO_VERDICT"),
                         "log": str(sub / "run.log")}
        print(f"=== {name}  {' '.join(plus)} ===")
        for ln in keep:
            print("  " + ln)

    (build / "result.json").write_text(json.dumps({
        "tag": args.tag, "cpu": str(cpu), "cpu_sha256": sha(cpu),
        "inputs_sha256": ident, "runs": summary,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
