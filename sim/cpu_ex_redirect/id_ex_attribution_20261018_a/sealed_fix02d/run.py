"""Task040 correction 02 runner.

Seals every input into sealed_<tag>/ and then compiles, assembles, builds the
reference and runs ONLY from that copy. Records every real command with cwd,
exit code and full stdout/stderr. Rejects the whole matrix on any FAIL /
INCOMPLETE / missing verdict / reference or audit mismatch, and checks every
RESULT line rather than the first one.
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
TASK = HERE.parent
ROOT = HERE.parents[3]
IVERILOG = Path("D:/iverilog/bin/iverilog.exe")
VVP = Path("D:/iverilog/bin/vvp.exe")
CPU_SEALED = ROOT / "sim/cpu_ex_redirect/target_fetch_20261018_a/after/myriscv/mycpu_sync.v"

DEPS = [
    "myriscv/regfile.v", "myriscv/alu.v", "myriscv/l_alu.v", "myriscv/br_alu.v",
    "myriscv/csr_file.v", "myriscv/simple_mmio.v", "myriscv/csr_defs.vh",
    "sim/br_ex_redirect/mul_behavioral.v", "sim/br_ex_redirect/asm.py",
]
OWN = ["tb_fix02.v", "p_fast.S", "p_oldmem.S", "p_nottaken.S", "p_serial.S",
       "ref.py", "run.py"]

RUNS = [
    ("fast",      "p_fast.S",     1, 1, False, 8),
    ("slowwrong", "p_fast.S",     1, 1, True,  8),
    ("oldmem_d1", "p_oldmem.S",   1, 1, False, 8),
    ("oldmem_d8", "p_oldmem.S",   1, 8, False, 8),
    ("nottaken",  "p_nottaken.S", 4, 1, False, 8),
    ("serial",    "p_serial.S",   1, 8, False, 8),
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def note_cmd(log, argv, cwd, rc, out, err):
    log.append({"argv": argv, "cwd": str(cwd), "exit": rc,
                "stdout": out[-4000:], "stderr": err[-4000:]})


def branch_addr(lst):
    for line in lst.read_text(encoding="utf-8").splitlines():
        if " beq " in line:
            return int(line.split(":")[0].strip(), 16)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    sealed = TASK / f"sealed_{args.tag}"
    if sealed.exists():
        raise SystemExit(f"ERROR: {sealed} exists; pick a new tag")
    (sealed / "myriscv").mkdir(parents=True)
    (sealed / "sim" / "br_ex_redirect").mkdir(parents=True)
    for name in OWN:
        shutil.copy2(HERE / name, sealed / name)
    shutil.copy2(CPU_SEALED, sealed / "myriscv" / "mycpu_sync.v")
    for rel in DEPS:
        dst = sealed / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    files = sorted(str(p.relative_to(sealed)).replace("\\", "/")
                   for p in sealed.rglob("*") if p.is_file())
    manifest = {f: sha(sealed / f) for f in files}
    (sealed / "manifest.json").write_text(
        json.dumps({"tag": args.tag, "files_sha256": manifest}, indent=2) + "\n", encoding="utf-8")
    print(f"sealed tree: {sealed} ({len(manifest)} files)")

    build = TASK / "build" / args.tag
    if build.exists():
        raise SystemExit(f"ERROR: {build} exists; pick a new tag")
    build.mkdir(parents=True)
    cmds, results = [], {}

    srcs = [sealed / "tb_fix02.v", sealed / "myriscv" / "mycpu_sync.v",
            sealed / "myriscv" / "regfile.v", sealed / "myriscv" / "alu.v",
            sealed / "myriscv" / "l_alu.v", sealed / "myriscv" / "br_alu.v",
            sealed / "myriscv" / "csr_file.v", sealed / "myriscv" / "simple_mmio.v",
            sealed / "sim" / "br_ex_redirect" / "mul_behavioral.v"]
    argv = [str(IVERILOG), "-g2012", "-Wall", "-Wno-timescale",
            "-I", str(sealed / "myriscv"), "-o", str(build / "tb.vvp")] + [str(p) for p in srcs]
    r = subprocess.run(argv, capture_output=True, text=True, cwd=build)
    note_cmd(cmds, argv, build, r.returncode, r.stdout, r.stderr)
    (build / "compile.log").write_text(r.stdout + r.stderr, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        (build / "commands.json").write_text(json.dumps(cmds, indent=2) + "\n", encoding="utf-8")
        print("COMPILE FAIL")
        print(r.stdout + r.stderr)
        return 4
    warnings = [ln for ln in (r.stdout + r.stderr).splitlines() if "warning" in ln.lower()]
    print(f"compiled from sealed tree; warnings={len(warnings)}")
    for ln in warnings:
        print("  W: " + ln)

    for name, prog, mode, ddelay, slow_after, slowdelay in RUNS:
        sub = build / name
        sub.mkdir()
        argv = [sys.executable, str(sealed / "sim/br_ex_redirect/asm.py"), str(sealed / prog), str(sub)]
        r = subprocess.run(argv, capture_output=True, text=True, cwd=build)
        note_cmd(cmds, argv, build, r.returncode, r.stdout, r.stderr)
        if r.returncode != 0:
            print(f"ASSEMBLE FAIL {name}")
            return 5
        (sub / "dmem_init.hex").write_text("\n".join(["00000000"] * 512) + "\n", encoding="ascii")

        stpc = int(branch_addr(sub / "program.lst")) + 4 if slow_after else None
        # completion store = last store in the listing (all six programs have one)
        probe = [sys.executable, str(sealed / "ref.py"), str(sub), str(sub / "program.lst"), "-1"]
        r = subprocess.run(probe, capture_output=True, text=True, cwd=build)
        note_cmd(cmds, probe, build, r.returncode, r.stdout, r.stderr)
        if r.returncode != 0:
            print(f"REF PROBE FAIL {name}: {r.stdout}{r.stderr}")
            return 6
        allrows = json.loads((sub / "ref_ret.json").read_text())
        # locate the completion store PC from the listing itself
        stpc_pc = None
        for line in (sub / "program.lst").read_text(encoding="utf-8").splitlines():
            if " sw " in line:
                stpc_pc = int(line.split(":")[0].strip(), 16)
        if stpc_pc is None:
            raise SystemExit(f"no store in {name}")
        argv = [sys.executable, str(sealed / "ref.py"), str(sub), str(sub / "program.lst"), hex(stpc_pc)]
        r = subprocess.run(argv, capture_output=True, text=True, cwd=build)
        note_cmd(cmds, argv, build, r.returncode, r.stdout, r.stderr)
        if r.returncode != 0:
            print(f"REF FAIL {name}: {r.stdout}{r.stderr}")
            return 6
        ref = json.loads((sub / "ref_ret.json").read_text())

        plus = [f"+MODE={mode}", f"+DDELAY={ddelay}", f"+SLOWDELAY={slowdelay}",
                f"+STPC={stpc_pc}", "+TRACE=1"]
        if slow_after:
            plus.append(f"+SLOWADDR={stpc}")
        argv = [str(VVP), str(build / "tb.vvp")] + plus
        r = subprocess.run(argv, capture_output=True, text=True, cwd=sub)
        note_cmd(cmds, argv, sub, r.returncode, r.stdout, r.stderr)
        log = r.stdout + r.stderr
        (sub / "run.log").write_text(log, encoding="utf-8", errors="replace")

        verdicts = [ln for ln in log.splitlines() if ln.startswith("RESULT:")]
        bad = [v for v in verdicts if not v.startswith("RESULT: PASS")]
        if not verdicts or bad or r.returncode != 0:
            print(f"STOP: {name} verdict={verdicts} rc={r.returncode}")
            (build / "commands.json").write_text(json.dumps(cmds, indent=2) + "\n", encoding="utf-8")
            return 7

        got = []
        for ln in log.splitlines():
            m = re.match(r"RET,(\d+),([0-9a-f]+),([0-9a-f]+),(\d+),(\d+),([0-9a-f]+),([0-9a-f]+)$", ln)
            if m:
                got.append({"pc": int(m.group(2), 16), "inst": int(m.group(3), 16),
                            "rd": int(m.group(4)), "we": int(m.group(5)),
                            "value": int(m.group(6), 16), "next_pc": int(m.group(7), 16)})
        mism = []
        for i, e in enumerate(ref):
            if i >= len(got):
                mism.append((i, "missing")); break
            g = got[i]
            if g["pc"] != e["pc"] or g["inst"] != e["inst"]:
                mism.append((i, f"pc/inst {g['pc']:#x}!={e['pc']:#x}"))
                break
            if e["we"] and (g["rd"] != e["rd"] or g["value"] != e["value"]):
                mism.append((i, f"we/rd/val {g['rd']},{g['value']:#x} != {e['rd']},{e['value']:#x}"))
                break
            if g["next_pc"] != e["next_pc"]:
                mism.append((i, f"next_pc {g['next_pc']:#x}!={e['next_pc']:#x}"))
                break
        key = [ln for ln in log.splitlines()
               if ln.startswith(("EVENT", "DELTA_EDGES", "WRONGPATH", "IAUDIT", "DAUDIT",
                                 "SLOWWIT", "ROI", "OTHER", "X31CHECK", "----"))]
        ok = not mism
        results[name] = {"plusargs": plus, "verdicts": verdicts, "ref_match": ok,
                         "ref_mismatch": mism, "lines": key, "log": str(sub / "run.log")}
        print(f"=== {name}  {' '.join(plus)} ===")
        for ln in key:
            print("  " + ln)
        print("  " + verdicts[-1] + ("  ref=OK" if ok else f"  ref=MISMATCH {mism}"))
        if not ok:
            print(f"STOP: {name} reference mismatch")
            (build / "commands.json").write_text(json.dumps(cmds, indent=2) + "\n", encoding="utf-8")
            return 7

    (build / "commands.json").write_text(json.dumps(cmds, indent=2) + "\n", encoding="utf-8")
    (build / "result.json").write_text(json.dumps(
        {"tag": args.tag, "sealed": str(sealed), "manifest": manifest, "runs": results},
        indent=2) + "\n", encoding="utf-8")
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
