"""Task038 minimal localisation runner.

Compiles one chosen mycpu_sync.v against tb_serial_drain.v and runs the four
modes (A/B/control-ALU/control-CSR) with the one-cycle instruction hit model.

Usage:
    python sim/br_ex_redirect/serial_drain_20261018_a/run.py \
        --tag ex_a --cpu <path/to/mycpu_sync.v> --ddelay 1

Never overwrites an existing tag directory. Records SHA256 of every compiled
input into result.json so the run is self-describing.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ASM = HERE.parent / "asm.py"
MUL = HERE.parent / "mul_behavioral.v"
IVERILOG = Path("D:/iverilog/bin/iverilog.exe")
VVP = Path("D:/iverilog/bin/vvp.exe")

FIXED = [
    ROOT / "myriscv" / "regfile.v",
    ROOT / "myriscv" / "alu.v",
    ROOT / "myriscv" / "l_alu.v",
    ROOT / "myriscv" / "br_alu.v",
    ROOT / "myriscv" / "csr_file.v",
    MUL,
]

MODES = {
    1: ("prog_a.S", "A_branch_then_csr"),
    2: ("prog_b.S", "B_drain_then_redirect"),
    3: ("prog_ctl_alu.S", "C_control_alu"),
    4: ("prog_ctl_csr.S", "D_control_csr_correct_path"),
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--cpu", required=True, help="mycpu_sync.v to compile")
    ap.add_argument("--ddelay", type=int, default=1)
    ap.add_argument("--modes", default="1,2,3,4")
    args = ap.parse_args()

    build = HERE / "build" / args.tag
    if build.exists():
        print(f"ERROR: {build} exists; pick a new tag")
        return 2
    build.mkdir(parents=True)

    cpu = Path(args.cpu).resolve()
    srcs = [HERE / "tb_serial_drain.v", cpu] + FIXED
    argv = [str(IVERILOG), "-g2012", "-Wall", "-Wno-timescale",
            "-I", str(ROOT / "myriscv"), "-o", str(build / "tb.vvp")] + [str(p) for p in srcs]
    r = subprocess.run(argv, capture_output=True, text=True, cwd=build)
    (build / "compile.log").write_text(r.stdout + r.stderr, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("COMPILE FAIL")
        print(r.stdout + r.stderr)
        return 4

    ident = {str(p): sha(p) for p in srcs}
    results = {}
    for m in [int(x) for x in args.modes.split(",") if x.strip()]:
        prog, name = MODES[m]
        sub = build / f"m{m}"
        sub.mkdir()
        r = subprocess.run([sys.executable, str(ASM), str(HERE / prog), str(sub)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout, r.stderr)
            return 3
        (sub / "dmem_init.hex").write_text("\n".join(["00000000"] * 256) + "\n", encoding="ascii")

        r = subprocess.run([str(VVP), str(build / "tb.vvp"),
                            f"+MODE={m}", f"+DDELAY={args.ddelay}"],
                           capture_output=True, text=True, cwd=sub)
        log = r.stdout + r.stderr
        (sub / "run.log").write_text(log, encoding="utf-8", errors="replace")
        verdict = [ln for ln in log.splitlines() if ln.startswith("RESULT:")]
        summary = [ln for ln in log.splitlines() if ln.startswith("----")]
        results[name] = {"verdict": verdict[-1] if verdict else "NO_VERDICT",
                         "summary": summary[-1] if summary else "", "log": str(sub / "run.log")}
        print(f"=== {name} (mode {m}) ===")
        for ln in summary + verdict:
            print("  " + ln)

    (build / "result.json").write_text(json.dumps({
        "tag": args.tag, "cpu": str(cpu), "cpu_sha256": sha(cpu),
        "ddelay": args.ddelay, "inputs_sha256": ident, "results": results,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
