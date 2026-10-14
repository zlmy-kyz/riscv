"""Check the exact source/constraint/IP closure used by the MINI PDS project."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PDS = ROOT / "RISCV.pds"
MANIFEST = Path(__file__).resolve().parent / "pds_inputs.json"
EXTRA = (
    "ipcore/inst_rom/rtl/inst_rom_init_param.v",
    "ipcore/data_ram/rtl/data_ram_init_param.v",
    "ipcore/icache/rtl/icache_init_param.v",
    "ipcore/dcache/rtl/dcache_init_param.v",
    "ipcore/ddr3/define.vh",
    "ipcore/ddr3/rtl/ddrphy/localparam.vh",
    "tests/uart_loader/candidates/verify_run_hello/build/loader_rom.dat",
    "tests/uart_loader/candidates/verify_run_hello/build/loader_ram.dat",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect() -> dict:
    project = PDS.read_text(encoding="utf-8")
    paths = set(re.findall(r'\(_(?:file|ip|ip_source_item)\s+"([^"]+)"', project))
    paths = {path for path in paths if path.startswith(("myriscv/", "ipcore/", "constraint_check/"))}
    if not paths or len(paths) < 100:
        raise ValueError("PDS source list unexpectedly small")
    if '(_device PG2L200H)' not in project or '(_package FBB676)' not in project:
        raise ValueError("Unexpected target device/package")
    paths.update(EXTRA)
    missing = [path for path in sorted(paths) if not (ROOT / path).is_file()]
    if missing:
        raise ValueError("Missing PDS inputs: " + ", ".join(missing))
    # The loader data paths are absolute in the generated IP metadata. A clone
    # at another location needs the IP paths rebound before PDS regeneration.
    for name, image in (("inst_rom", "loader_rom.dat"), ("data_ram", "loader_ram.dat")):
        idf = (ROOT / f"ipcore/{name}/{name}.idf").read_text(encoding="utf-8")
        if f"D:/riscv/RISCV/tests/uart_loader/candidates/verify_run_hello/build/{image}" not in idf:
            raise ValueError(f"{name} INIT_FILE differs from the shared Loader image")
    return {
        "device": "PG2L200H-6FBB676",
        "pds_sha256": sha(PDS),
        "source_count": len(paths),
        "files_sha256": {path: sha(ROOT / path) for path in sorted(paths)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Create the handoff manifest from this checkout")
    args = parser.parse_args()
    actual = collect()
    if args.write:
        MANIFEST.write_text(json.dumps(actual, indent=2) + "\n", encoding="utf-8")
        print("WROTE", MANIFEST, "inputs=", actual["source_count"])
    else:
        expected = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if actual != expected:
            changed = [name for name, digest in expected["files_sha256"].items()
                       if actual["files_sha256"].get(name) != digest]
            raise ValueError("PDS input identity changed: " + ", ".join(changed[:12]))
        print("PDS INPUTS PASS", actual["device"], "inputs=", actual["source_count"])


if __name__ == "__main__":
    main()
