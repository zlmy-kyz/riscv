"""Task033 source snapshot and syntax/elaboration only; never runs HDL simulation."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BRIDGE = "myriscv/dual_sram_to_pango_ddr_bridge.v"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def inputs():
    paths = [p for p in (ROOT / "myriscv").rglob("*") if p.is_file()]
    for directory in ("ipcore/icache", "ipcore/dcache"):
        paths.extend(p for p in (ROOT / directory).rglob("*") if p.is_file())
    paths.extend(ROOT / name for name in (
        "RISCV.pds", "constraint_check/temp_constraint_file.fdc",
        "tests/cpu_performance_2b/build/measure_zmmul300_20261013_a/performance_300/program.bin",
        "tests/cpu_performance_2b/build/measure_zmmul300_20261013_a/validation_300/program.bin",
    ))
    return sorted(set(paths))


def git_record(name, args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    (HERE / name).write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"git failed: {args}")


def snapshot():
    dest = HERE / "before"
    dest.mkdir(exist_ok=False)
    manifest = {}
    for source in inputs():
        relative = source.relative_to(ROOT).as_posix()
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        manifest[relative] = sha(target)
    write_json(HERE / "before_manifest.json", manifest)
    git_record("git_before.txt", ["status", "--porcelain=v1", "-uall"])
    git_record("bridge_before_head.diff", ["diff", "--", BRIDGE])
    git_record("head.txt", ["rev-parse", "HEAD"])
    print(json.dumps({"snapshot_files": len(manifest), "bridge_sha256": manifest[BRIDGE]}))


def review():
    if (HERE / "review.json").exists():
        raise RuntimeError("review already exists; preserve it")
    before = json.loads((HERE / "before_manifest.json").read_text(encoding="utf-8"))
    after = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs()}
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    if changed != [BRIDGE]:
        raise RuntimeError(f"unexpected design changes: {changed}")
    for relative, digest in before.items():
        if sha(HERE / "before" / relative) != digest:
            raise RuntimeError(f"snapshot changed: {relative}")
    old = (HERE / "before" / BRIDGE).read_text(encoding="utf-8").splitlines(keepends=True)
    new = (ROOT / BRIDGE).read_text(encoding="utf-8").splitlines(keepends=True)
    (HERE / "bridge.patch").write_text("".join(difflib.unified_diff(old, new, "before/" + BRIDGE, "after/" + BRIDGE)), encoding="utf-8")
    write_json(HERE / "after_manifest.json", after)
    compiler = "D:/iverilog/bin/iverilog.exe"
    # Initial real-backend attempt is preserved in compile_failure.json and
    # bridge_x32_enabled.log: vendor unsized concatenation is rejected by
    # Icarus. Do not edit IP to accommodate this static-only frontend.
    # Use real port wrappers with the vendor backend left as a black box.
    check_dir = HERE / "checks_02"
    check_dir.mkdir(exist_ok=False)
    cache_sources = ["ipcore/icache/icache.v", "ipcore/dcache/dcache.v"]
    common = [compiler, "-g2005", "-tnull", "-i", "-I", "myriscv",
              "-I", "ipcore/icache/rtl", "-I", "ipcore/dcache/rtl"]
    top = "dual_sram_to_pango_ddr_bridge"
    configs = [
        ("bridge_x32_enabled", top, {"MEM_DQ_WIDTH": 32}),
        ("bridge_x32_disabled", top, {"MEM_DQ_WIDTH": 32, "INST_HIT_UNDER_DATA_MISS_ENABLE": 0}),
        ("bridge_x16", top, {"MEM_DQ_WIDTH": 16}),
        ("bridge_x32_no_icache", top, {"MEM_DQ_WIDTH": 32, "INST_LINE_BUFFER_ENABLE": 0}),
        ("bridge_x32_posted", top, {"MEM_DQ_WIDTH": 32, "POSTED_WRITE_ENABLE": 1}),
        ("board_top", "board_top", {}),
    ]
    checks = []
    for name, module, parameters in configs:
        command = common + ["-s", module]
        for key, value in parameters.items():
            command += ["-P", f"{module}.{key}={value}"]
        sources = [BRIDGE] if module == top else [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "myriscv").glob("*.v"))]
        command += sources + cache_sources
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60)
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        (check_dir / (name + ".log")).write_text(output, encoding="utf-8")
        check = {"name": name, "cwd": str(ROOT), "argv": command, "exit_code": result.returncode, "output": output}
        checks.append(check)
        if result.returncode:
            write_json(check_dir / "compile_failure.json", checks)
            raise RuntimeError(f"static elaboration failed: {name}")
    result = subprocess.run(["git", "diff", "--check", "--", BRIDGE], cwd=ROOT, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stdout.decode() + result.stderr.decode())
    git_record("git_after.txt", ["status", "--porcelain=v1", "-uall"])
    write_json(HERE / "review.json", {
        "status": "TASK033_STATIC_ELABORATION_ONLY_PENDING_USER_PDS",
        "changed_design_files": changed,
        "before_bridge_sha256": before[BRIDGE], "after_bridge_sha256": after[BRIDGE],
        "unchanged_tracked_inputs": len(after) - 1,
        "checks": checks,
        "limits": "Null-target syntax/elaboration with real cache port wrappers; vendor cache backends and other missing IP ignored with -i. Full vendor-backend Icarus attempt failed on existing unsized concatenation; original failure preserved. No HDL simulation, synthesis, timing or board verification.",
    })
    print(json.dumps({"status": "STATIC_ONLY_PENDING_USER_PDS", "checks": len(checks), "bridge_sha256": after[BRIDGE]}))


if __name__ == "__main__":
    {"snapshot": snapshot, "review": review}[sys.argv[1]]()
