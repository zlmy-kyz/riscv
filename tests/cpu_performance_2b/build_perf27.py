"""Build independent PERF27 P/V300 software only. No HDL/PDS/serial."""
from pathlib import Path
import argparse
import inspect
import json
import re
from perf27_software import ROOT, HERE, DEFAULT_TAG, audit, require_manifest, sha
from zmmul_software import load

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag', default=DEFAULT_TAG)
    a = p.parse_args()
    assert re.fullmatch('[a-z0-9_-]+', a.tag)
    out = HERE/'build'/a.tag
    assert not out.exists(), 'Preserve prior build; choose a new tag'
    protected = {str(p.relative_to(ROOT).as_posix()):sha(p)
        for p in (HERE/'build/measure_zmmul300_20261013_a').rglob('*') if p.is_file()}
    protected.update({p.relative_to(ROOT).as_posix():sha(p) for p in
        [HERE/'perf.c', HERE/'perf.h', ROOT/'myriscv/mycpu_sync.v', ROOT/'myriscv/simple_mmio.v',
         ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v', ROOT/'myriscv/soc_top.v']})
    recipe = load('perf27_legacy_builder', HERE/'build.py')
    code = inspect.getsource(recipe.build)
    assert code.count('-march=rv32i') == 2 and code.count("HERE/'perf.c'") == 1
    code = code.replace('-march=rv32i', '-march=rv32i_zmmul').replace("HERE/'perf.c'", "HERE/'perf27.c'")
    ns = dict(recipe.__dict__, audit=audit, __file__=str(Path(__file__).resolve()))
    exec(compile(code, '<independent_PERF27_build_recipe>', 'exec'), ns)
    outputs = {}
    for name in ['performance_300', 'validation_300']:
        ns['build'](name, a.tag)
        info = require_manifest(out/name/'manifest.json')
        outputs[name] = info
    assert all(sha(ROOT/n) == h for n,h in protected.items()), 'Protected old BIN/source or RTL changed'
    report = dict(status='PERF27_BUILD_AND_ELF_ISA_AUDIT_PASS_DYNAMIC_AND_BOARD_PENDING',
        outputs=outputs, protected_sha256=protected,
        reader_sha256=sha(HERE/'perf27.c'), parser_sha256=sha(HERE/'perf27_software.py'),
        HDL_started=False, PDS_started=False, serial_opened=False,
        note='New BIN identity and layout; frozen P/V300 kept. CRC references reused, not yet executed on CPU.')
    (out/'build_review.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(report['status'])
if __name__ == '__main__': main()
