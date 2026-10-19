"""Seal every dynamic input of the Task033 key simulation.

Writes `sim/cpu_inst_hit_overlap/sealed_ds_inst_hit_overlap_20261017_a/` with

  src/      closed copy of the RTL, testbenches and DDR model
  toolsrc/  vendor simulation primitives (external absolute library)
  scripts/  the harness itself (prepare/seal/run/check/selftest + inputs.json)
  inputs/   frozen plan and program images
  manifest.json   role, source path, sealed path, size and SHA256 per file
  tools.json      simulator/python identity

Nothing outside this directory is written and the formal build directory is
never created here.
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MS = Path(r'D:/modelsim/win64pe')
PDS = Path(r'C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
SEALED = HERE / ('sealed_' + 'ds_inst_hit_overlap_20261017_a')
TAG = 'ds_inst_hit_overlap_20261017_a'

# ------------------------------------------------------------------- inventor
BRIDGE_JOB = [
    PDS / 'GTP_GRS.v',
    PDS / 'GTP_DRM36K_E1.v',
    ROOT / 'ipcore/icache/rtl/ipm2l_sdpram_v1_10_icache.v',
    ROOT / 'ipcore/icache/icache.v',
    ROOT / 'ipcore/dcache/rtl/ipm2l_sdpram_v1_10_dcache.v',
    ROOT / 'ipcore/dcache/dcache.v',
    ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v',
    HERE / 'ddr_model.sv',
    HERE / 'tb_inst_hit_overlap.sv',
]

SOC_JOB = [
    PDS / 'GTP_GRS.v',
    PDS / 'GTP_DRM36K_E1.v',
    PDS / 'GTP_APM_E2.v',
    ROOT / 'ipcore/icache/rtl/ipm2l_sdpram_v1_10_icache.v',
    ROOT / 'ipcore/icache/icache.v',
    ROOT / 'ipcore/dcache/rtl/ipm2l_sdpram_v1_10_dcache.v',
    ROOT / 'ipcore/dcache/dcache.v',
    ROOT / 'ipcore/inst_rom/rtl/ipm2l_spram_v1_8_inst_rom.v',
    ROOT / 'ipcore/inst_rom/rtl/ipm2l_rom_v1_8_inst_rom.v',
    ROOT / 'ipcore/inst_rom/inst_rom.v',
    ROOT / 'ipcore/data_ram/rtl/ipm2l_spram_v1_8_data_ram.v',
    ROOT / 'ipcore/data_ram/data_ram.v',
    ROOT / 'ipcore/mul/rtl/ipm2l_apm_data_pipeline/ipm2l_apm_distributed_sdpram.v',
    ROOT / 'ipcore/mul/rtl/ipm2l_apm_data_pipeline/ipm2l_apm_distributed_shiftregister.v',
    ROOT / 'ipcore/mul/rtl/ipm2l_apm_data_pipeline/ipm2l_apm_data_pipeline.v',
    ROOT / 'ipcore/mul/rtl/ipm2l_mult_v1_3_mul.v',
    ROOT / 'ipcore/mul/mul.v',
] + [ROOT / 'myriscv' / (n + '.v') for n in
     ('alu br_alu l_alu regfile csr_file mycpu_sync inst_bus_interconnect '
      'data_bus_interconnect inst_bram_adapter data_bram_adapter simple_mmio '
      'dual_sram_to_pango_ddr_bridge uart_tx uart_rx uart_rx_fifo uart_mmio '
      'soc_top').split()] + [
    HERE / 'ddr_model.sv',
    HERE / 'tb_inst_hit_overlap_soc.sv',
]

SCRIPTS = [HERE / n for n in ('prepare_program.py', 'seal_inputs.py', 'run.py',
                              'check_evidence.py', 'selftest.py', 'inputs.json')]

INPUTS = [HERE / n for n in ('plan_bridge.txt', 'soc_program.hex',
                             'soc_fault_camera.hex', 'soc_fault_pp.hex')]

# read-only history that must not change during the run
PROTECTED_ROOTS = [HERE / 'preparation_20261017_a', HERE / 'preparation_20261017_b']

ROLE = {}
for _p in BRIDGE_JOB:
    ROLE[_p] = 'testbench' if _p.name.startswith('tb_') else (
        'model' if _p.name == 'ddr_model.sv' else 'rtl')
for _p in SOC_JOB:
    ROLE.setdefault(_p, 'testbench' if _p.name.startswith('tb_') else (
        'model' if _p.name == 'ddr_model.sv' else 'rtl'))
for _p in SCRIPTS:
    ROLE[_p] = 'script'
for _p in INPUTS:
    ROLE[_p] = 'input'

DESIGN = ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v'
DESIGN_SHA = '7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933'

INCLUDE_RE = re.compile(r'`include\s+"([^"]+)"')
READMEM_RE = re.compile(r'\$(readmem[hb])\s*\(\s*([A-Za-z_][\w$]*)')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sealed_rel(path):
    path = Path(path).resolve()
    try:
        rel = path.relative_to(ROOT)
        return Path('src') / rel
    except ValueError:
        return Path('src/external') / path.name


def include_closure(files):
    """Resolve every `include the compiler would follow, recursively."""
    seen, order = set(), []
    queue = [Path(f).resolve() for f in files]
    while queue:
        cur = queue.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        text = cur.read_text(encoding='utf-8', errors='replace')
        for name in INCLUDE_RE.findall(text):
            cand = (cur.parent / name).resolve()
            if not cand.exists():
                raise SystemExit('seal_inputs: unresolved include %r from %s'
                                 % (name, cur))
            if cand not in order:
                order.append(cand)
            queue.append(cand)
    return order


def readmem_uses(files):
    """Report any runtime file read; INIT_FILE stays "NONE" in this design."""
    uses = []
    for f in files:
        f = Path(f)
        text = f.read_text(encoding='utf-8', errors='replace')
        for task, param in READMEM_RE.findall(text):
            try:
                name = str(f.relative_to(ROOT))
            except ValueError:
                name = str(f)
            uses.append(dict(file=name, task=task, param=param))
    return uses


def tool_identity():
    def ver(exe, args):
        try:
            r = subprocess.run([str(exe)] + args, capture_output=True, text=True,
                               errors='replace', timeout=60)
            return ((r.stdout or '') + (r.stderr or '')).strip().splitlines()[:4]
        except Exception as exc:                    # noqa: BLE001
            return ['<unavailable: %s>' % exc]

    tools = dict(
        simulator_root=str(MS),
        pango_vendor_root=str(PDS),
        vsim=str(MS / 'vsim.exe'),
        vlog=str(MS / 'vlog.exe'),
        vlib=str(MS / 'vlib.exe'),
        vsim_version=ver(MS / 'vsim.exe', ['-version']),
        python=sys.version.split()[0],
        python_executable=sys.executable,
        platform=sys.platform,
    )
    for key in ('vsim', 'vlog', 'vlib'):
        p = Path(tools[key])
        if p.exists():
            tools[key + '_sha256'] = sha256(p)
            tools[key + '_bytes'] = p.stat().st_size
    return tools


def protected_list():
    rows = []
    for root in PROTECTED_ROOTS:
        if not root.exists():
            continue
        for p in sorted(root.rglob('*')):
            if p.is_file():
                rows.append(dict(source=str(p.relative_to(ROOT)),
                                 sha256=sha256(p), bytes=p.stat().st_size))
    return rows


def main():
    if (HERE / 'build' / TAG).exists():
        raise SystemExit('seal_inputs: %s already exists, refusing to seal'
                         % (HERE / 'build' / TAG))
    if sha256(DESIGN) != DESIGN_SHA:
        raise SystemExit('seal_inputs: bridge SHA256 mismatch (%s)' % sha256(DESIGN))
    for p in BRIDGE_JOB + SOC_JOB + SCRIPTS + INPUTS:
        if not p.exists():
            raise SystemExit('seal_inputs: missing input %s' % p)

    sources = []
    for p in BRIDGE_JOB + SOC_JOB:
        if p not in sources:
            sources.append(p)
    includes = include_closure(sources)
    if SEALED.exists():
        shutil.rmtree(SEALED)

    rows = []

    def add(path, role, kind='file'):
        path = Path(path).resolve()
        rel = sealed_rel(path)
        dst = SEALED / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(path.read_bytes())
        rows.append(dict(role=role, kind=kind, source=str(path),
                         sealed=str(rel).replace('\\', '/'),
                         sha256=sha256(dst), bytes=dst.stat().st_size))
        return dst

    for p in sources:
        add(p, ROLE.get(Path(p).resolve(), 'rtl'))
    for p in includes:
        add(p, 'include', 'rtl_include')
    for p in SCRIPTS:
        add(p, 'script')
    for p in INPUTS:
        add(p, 'input')

    incdirs = sorted({str(sealed_rel(p).parent) for p in includes})
    manifest = dict(
        tag=TAG,
        created_utc=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        root=str(ROOT),
        sealed_dir=str(SEALED),
        design=dict(source=str(DESIGN), sha256=DESIGN_SHA),
        bridge_job=[str(p) for p in BRIDGE_JOB],
        soc_job=[str(p) for p in SOC_JOB],
        incdirs=incdirs,
        runtime_file_reads=readmem_uses(sources),
        files=rows,
        protected=protected_list(),
    )
    SEALED.mkdir(parents=True, exist_ok=True)
    (SEALED / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n',
                                         encoding='ascii')
    tools = tool_identity()
    (SEALED / 'tools.json').write_text(json.dumps(tools, indent=2) + '\n',
                                      encoding='ascii')

    files = [r for r in rows if r['kind'] == 'file']
    print('seal_inputs: sealed %d files: %d rtl/testbench/model, %d include, %d script, %d input'
          % (len(rows),
             sum(1 for r in rows if r['role'] in ('rtl', 'testbench', 'model')),
             len(includes), len(SCRIPTS), len(INPUTS)))
    print('seal_inputs: protected %d read-only files hashed' % len(manifest['protected']))
    print('seal_inputs: runtime init-file reads: %s'
          % (manifest['runtime_file_reads'] or 'none'))
    print('seal_inputs: dir %s' % SEALED)
    print('seal_inputs: manifest sha256 %s'
          % sha256(SEALED / 'manifest.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
