"""Task040 correction runner (fix01).

Seals every input into sealed_fix01/ first, then compiles and runs ONLY from
that copy, so nothing is silently pulled from the main worktree afterwards.
Any compile/run failure, FAIL/INCOMPLETE verdict, audit mismatch or reference
mismatch makes the process exit non-zero and stops the matrix.

Runs (6): fast, slowwrong, oldmem_d1, oldmem_d8, nottaken, serial.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SRC = HERE
TASK = HERE.parent
IVERILOG = Path("D:/iverilog/bin/iverilog.exe")
VVP = Path("D:/iverilog/bin/vvp.exe")

CPU_SEALED = ROOT / "sim/cpu_ex_redirect/target_fetch_20261018_a/after/myriscv/mycpu_sync.v"

# files copied from the main worktree (dependencies only)
DEPS = [
    "myriscv/regfile.v", "myriscv/alu.v", "myriscv/l_alu.v", "myriscv/br_alu.v",
    "myriscv/csr_file.v", "myriscv/simple_mmio.v", "myriscv/csr_defs.vh",
    "sim/br_ex_redirect/mul_behavioral.v", "sim/br_ex_redirect/asm.py",
]
OWN = ["tb_fix01.v", "p_fast.S", "p_oldmem.S", "p_nottaken.S", "p_serial.S",
       "ref.py", "run.py"]

RUNS = [
    # name, program, mode, ddelay, slow_after, slowdelay
    ("fast",      "p_fast.S",     1, 1, False, 8),
    ("slowwrong", "p_fast.S",     1, 1, True,  8),
    ("oldmem_d1", "p_oldmem.S",   1, 1, False, 8),
    ("oldmem_d8", "p_oldmem.S",   1, 8, False, 8),
    ("nottaken",  "p_nottaken.S", 4, 1, False, 8),
    ("serial",    "p_serial.S",   1, 8, False, 8),
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def seal(tag):
    sealed = TASK / f"sealed_{tag}"
    if sealed.exists():
        raise SystemExit(f"ERROR: {sealed} exists; pick a new tag")
    (sealed / "myriscv").mkdir(parents=True)
    (sealed / "sim" / "br_ex_redirect").mkdir(parents=True)
    for name in OWN:
        shutil.copy2(SRC / name, sealed / name)
    shutil.copy2(CPU_SEALED, sealed / "myriscv" / "mycpu_sync.v")
    for rel in DEPS:
        dst = sealed / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    files = sorted(str(p.relative_to(sealed)).replace("\\", "/")
                   for p in sealed.rglob("*") if p.is_file())
    manifest = {f: sha(sealed / f) for f in files}
    (sealed / "manifest.json").write_text(
        json.dumps({"tag": tag, "files_sha256": manifest}, indent=2) + "\n", encoding="utf-8")
    return sealed, manifest


def branch_addr(lst):
    for line in lst.read_text(encoding="utf-8").splitlines():
        if " beq " in line:
            return int(line.split(":")[0].strip(), 16)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--sealed", default=None, help="reuse an existing sealed tree")
    args = ap.parse_args()

    if args.sealed:
        sealed = Path(args.sealed).resolve()
        manifest = json.loads((sealed / "manifest.json").read_text())["files_sha256"]
        for f, h in manifest.items():
            if sha(sealed / f) != h:
                raise SystemExit(f"SEALED TAMPERED: {f}")
    else:
        sealed, manifest = seal(args.tag)
    print(f"sealed tree: {sealed}  ({len(manifest)} files)")

    build = TASK / "build" / args.tag
    if build.exists():
        raise SystemExit(f"ERROR: {build} exists; pick a new tag")
    build.mkdir(parents=True)

    srcs = [sealed / "tb_fix01.v", sealed / "myriscv" / "mycpu_sync.v",
            sealed / "myriscv" / "regfile.v", sealed / "myriscv" / "alu.v",
            sealed / "myriscv" / "l_alu.v", sealed / "myriscv" / "br_alu.v",
            sealed / "myriscv" / "csr_file.v", sealed / "myriscv" / "simple_mmio.v",
            sealed / "sim" / "br_ex_redirect" / "mul_behavioral.v"]
    argv = [str(IVERILOG), "-g2012", "-Wall", "-Wno-timescale",
            "-I", str(sealed / "myriscv"), "-o", str(build / "tb.vvp")] + [str(p) for p in srcs]
    r = subprocess.run(argv, capture_output=True, text=True, cwd=build)
    (build / "compile.log").write_text(r.stdout + r.stderr, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("COMPILE FAIL")
        print(r.stdout + r.stderr)
        return 4
    warn = [ln for ln in (r.stdout + r.stderr).splitlines() if "warning" in ln.lower()]
    print(f"compiled from sealed tree; warnings={len(warn)}")
    for ln in warn:
        print("  W: " + ln)

    results = {}
    for name, prog, mode, ddelay, slow_after, slowdelay in RUNS:
        sub = build / name
        sub.mkdir()
        r = subprocess.run([sys.executable, str(sealed / "sim/br_ex_redirect/asm.py"),
                            str(sealed / prog), str(sub)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"ASSEMBLE FAIL {name}: {r.stdout}{r.stderr}")
            return 5
        (sub / "dmem_init.hex").write_text("\n".join(["00000000"] * 512) + "\n", encoding="ascii")

        stpc = None
        if mode != 4:
            rr = subprocess.run([sys.executable, str(sealed / "ref.py"), str(sub), str(sub / "program.lst")],
                                capture_output=True, text=True)
            if rr.returncode != 0:
                print(f"REF FAIL {name}: {rr.stdout}{rr.stderr}")
                return 6
            meta = json.loads((sub / "ref_meta.json").read_text())
            stpc = meta["stpc"]

        plus = [f"+MODE={mode}", f"+DDELAY={ddelay}", f"+SLOWDELAY={slowdelay}"]
        if slow_after:
            plus.append(f"+SLOWADDR={branch_addr(sub / 'program.lst') + 4}")
        if stpc is not None:
            plus.append(f"+STPC={stpc}")

        r = subprocess.run([str(VVP), str(build / "tb.vvp")] + plus,
                           capture_output=True, text=True, cwd=sub)
        log = r.stdout + r.stderr
        (sub / "run.log").write_text(log, encoding="utf-8", errors="replace")

        verdict = next((ln for ln in log.splitlines() if ln.startswith("RESULT:")), "NO_VERDICT")
        key = [ln for ln in log.splitlines()
               if ln.startswith(("EVENT", "DELTA", "WRONGPATH", "IAUDIT", "DAUDIT",
                                 "SLOWWIT", "ROI", "OTHER", "X31CHECK", "----"))]
        ref_ok = True
        if mode != 4:
            ref = [int(x, 16) for x in (sub / "ref_pc.txt").read_text().split()]
            got = [int(m.group(1), 16) for m in
                   (re.match(r"RET,\d+,([0-9a-f]+),", ln) for ln in log.splitlines() if ln.startswith("RET,"))
                   if m]
            ref_ok = got[:len(ref)] == ref
            if not ref_ok:
                first = next((i for i, (a, b) in enumerate(zip(got, ref)) if a != b),
                             min(len(got), len(ref)))
                gv = got[first] if first < len(got) else "none"
                ev = ref[first] if first < len(ref) else "none"
                print(f"  REF MISMATCH at retire #{first}: got={gv} exp={ev}")
        ok = verdict.startswith("RESULT: PASS") and ref_ok
        results[name] = {"plusargs": plus, "verdict": verdict, "ref_match": ref_ok,
                         "lines": key, "log": str(sub / "run.log")}
        print(f"=== {name}  {' '.join(plus)} ===")
        for ln in key:
            print("  " + ln)
        print("  " + verdict)
        if not ok:
            print(f"STOP: {name} did not pass (verdict or reference)")
            (build / "result.json").write_text(json.dumps(
                {"tag": args.tag, "sealed": str(sealed), "manifest": manifest,
                 "runs": results, "stopped_at": name}, indent=2) + "\n", encoding="utf-8")
            return 7

    (build / "result.json").write_text(json.dumps(
        {"tag": args.tag, "sealed": str(sealed), "manifest": manifest, "runs": results},
        indent=2) + "\n", encoding="utf-8")
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
