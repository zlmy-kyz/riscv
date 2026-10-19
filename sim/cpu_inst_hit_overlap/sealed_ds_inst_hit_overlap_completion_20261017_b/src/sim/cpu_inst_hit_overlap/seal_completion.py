"""Seal every dynamic input of the Task033 completion job.

Writes `sim/cpu_inst_hit_overlap/sealed_ds_inst_hit_overlap_completion_20261017_b/`

  src/      closed copy of the bridge, cache IP, model, testbench and harness
  inputs/   frozen plan
  manifest.json   role, source, sealed path, size and SHA256 per file
  tools.json      simulator / python / vendor identity

Nothing outside that directory is written and the formal build directory is
never created here. The original Task033 evidence is never modified; it is
listed as read-only and hashed for the before/after comparison.
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
TAG = 'ds_inst_hit_overlap_completion_20261017_b'
SEALED = HERE / ('sealed_' + TAG)

JOB = [
    PDS / 'GTP_GRS.v',
    PDS / 'GTP_DRM36K_E1.v',
    ROOT / 'ipcore/icache/rtl/ipm2l_sdpram_v1_10_icache.v',
    ROOT / 'ipcore/icache/icache.v',
    ROOT / 'ipcore/dcache/rtl/ipm2l_sdpram_v1_10_dcache.v',
    ROOT / 'ipcore/dcache/dcache.v',
    ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v',
    HERE / 'ddr_model_completion.sv',
    HERE / 'tb_inst_hit_completion.sv',
]

SCRIPTS = [HERE / n for n in ('prepare_completion.py', 'seal_completion.py',
                              'run_completion.py', 'check_completion.py',
                              'selftest_completion.py', 'inputs_completion.json')]

INPUTS = [HERE / 'completion_plan.txt']

DESIGN = ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v'
DESIGN_SHA = '7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933'

PROTECTED_DIRS = [HERE / n for n in (
    'build/ds_inst_hit_overlap_20261017_a',
    'aborted_run_20261017_a',
    'sealed_ds_inst_hit_overlap_20261017_a',
    'review_20261017_01',
    'preparation_20261017_a',
    'preparation_20261017_b',
)]

PROTECTED_DOCS = [ROOT / 'DeepSeek' / n for n in (
    '任务033_D读miss期间I缓存查询并行_关键仿真.md',
    '任务033_结果_ds_inst_hit_overlap_20261017_a.md',
    '任务033补齐_三个未触发场景与统计修正.md',
)]

SKIP_PARTS = {'work', 'socwork'}
INCLUDE_RE = re.compile(r'`include\s+"([^"]+)"')
READMEM_RE = re.compile(r'\$(readmem[hb])\s*\(\s*([A-Za-z_][\w$]*)')


def readmem_uses(files):
    """Runtime file reads; the DRM IP keeps INIT_FILE='NONE' in this design."""
    uses = []
    for f in files:
        f = Path(f)
        text = f.read_text(encoding='utf-8', errors='replace')
        for task, param in READMEM_RE.findall(text):
            try:
                name = str(f.relative_to(ROOT)).replace('\\', '/')
            except ValueError:
                name = str(f)
            uses.append(dict(file=name, task=task, param=param))
    return uses


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sealed_rel(path):
    path = Path(path).resolve()
    try:
        return Path('src') / path.relative_to(ROOT)
    except ValueError:
        return Path('src/external') / path.name


def include_closure(files):
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
                raise SystemExit('seal_completion: unresolved include %r from %s'
                                 % (name, cur))
            if cand not in order:
                order.append(cand)
            queue.append(cand)
    return order


def protected_list():
    rows = []

    def add(p, role, metadata_only=False):
        p = Path(p)
        rows.append(dict(source=str(p.relative_to(ROOT)).replace('\\', '/'),
                         role=role, metadata_only=metadata_only,
                         sha256=sha256(p), bytes=p.stat().st_size))

    for root in PROTECTED_DIRS:
        if not root.exists():
            continue
        for p in sorted(root.rglob('*')):
            if not p.is_file():
                continue
            parts = set(p.relative_to(root).parts)
            if parts & SKIP_PARTS:
                continue
            rel = p.relative_to(ROOT).parts
            if 'build' in rel and 'src' in rel:
                continue
            add(p, 'legacy_evidence')
    for p in PROTECTED_DOCS:
        if p.exists():
            add(p, 'legacy_document')
    ident = HERE / 'preparation_20261017_b/identity.json'
    if ident.exists():
        data = json.loads(ident.read_text(encoding='utf-8'))
        for rel, row in sorted(data.get('all_rows', {}).items()):
            p = ROOT / rel
            if not p.exists():
                continue
            rows.append(dict(source=rel.replace('\\', '/'), role='design_baseline',
                             metadata_only=bool(row.get('metadata_only')),
                             sha256=row['expected'], bytes=p.stat().st_size))
    return rows


def tool_identity():
    def ver(exe, args):
        try:
            r = subprocess.run([str(exe)] + args, capture_output=True, text=True,
                               errors='replace', timeout=60)
            return ((r.stdout or '') + (r.stderr or '')).strip().splitlines()[:4]
        except Exception as exc:                        # noqa: BLE001
            return ['<unavailable: %s>' % exc]

    tools = dict(simulator_root=str(MS), pango_vendor_root=str(PDS),
                 vsim=str(MS / 'vsim.exe'), vlog=str(MS / 'vlog.exe'),
                 vlib=str(MS / 'vlib.exe'),
                 vsim_version=ver(MS / 'vsim.exe', ['-version']),
                 python=sys.version.split()[0], python_executable=sys.executable,
                 platform=sys.platform)
    for key in ('vsim', 'vlog', 'vlib'):
        p = Path(tools[key])
        if p.exists():
            tools[key + '_sha256'] = sha256(p)
            tools[key + '_bytes'] = p.stat().st_size
    return tools


def main():
    if (HERE / 'build' / TAG).exists():
        raise SystemExit('seal_completion: %s already exists, refusing to seal'
                         % (HERE / 'build' / TAG))
    if sha256(DESIGN) != DESIGN_SHA:
        raise SystemExit('seal_completion: bridge SHA256 mismatch (%s)' % sha256(DESIGN))
    for p in JOB + SCRIPTS + INPUTS:
        if not p.exists():
            raise SystemExit('seal_completion: missing input %s' % p)

    includes = include_closure(JOB)
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

    for p in JOB:
        add(p, 'testbench' if p.name.startswith('tb_') else
            ('model' if p.name.startswith('ddr_model') else 'rtl'))
    for p in includes:
        add(p, 'include', 'rtl_include')
    for p in SCRIPTS:
        add(p, 'script')
    for p in INPUTS:
        add(p, 'input')

    incdirs = sorted({str(sealed_rel(p).parent) for p in includes})
    manifest = dict(
        tag=TAG, created_utc=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        root=str(ROOT), sealed_dir=str(SEALED),
        design=dict(source=str(DESIGN), sha256=DESIGN_SHA),
        job=[str(p) for p in JOB], incdirs=incdirs, files=rows,
        runtime_file_reads=readmem_uses(JOB),
        protected=protected_list(),
    )
    SEALED.mkdir(parents=True, exist_ok=True)
    (SEALED / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n',
                                         encoding='ascii')
    (SEALED / 'tools.json').write_text(json.dumps(tool_identity(), indent=2) + '\n',
                                      encoding='ascii')
    print('seal_completion: sealed %d files (%d rtl/model/tb, %d include, %d script, %d input)'
          % (len(rows), len(JOB), len(includes), len(SCRIPTS), len(INPUTS)))
    print('seal_completion: protected %d read-only files hashed' % len(manifest['protected']))
    print('seal_completion: dir %s' % SEALED)
    print('seal_completion: manifest sha256 %s' % sha256(SEALED / 'manifest.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
