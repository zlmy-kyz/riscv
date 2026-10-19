"""Task033 step 1: verify current design/IP/BIN identity against the read-only preparation manifest."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path('D:/riscv/RISCV')
HERE = ROOT / 'sim/cpu_inst_hit_overlap'
PREP_A = HERE / 'preparation_20261017_a'
OUT = HERE / 'preparation_20261017_b'

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

# PDS-generated engineering metadata: differences must be recorded, not used as a gate.
METADATA = ('RISCV.pds', 'constraint_check/', '.last_generated', '.settings',
            'generate.log', '/rtl/', '_init_param.v', '_Reset_Value.v', 'idf')


def is_metadata(name):
    return any(token in name for token in METADATA)


def main():
    ref = json.loads((PREP_A / 'after_manifest.json').read_text(encoding='utf-8'))
    rows = {}
    for name, digest in ref.items():
        path = ROOT / name
        now = sha(path) if path.exists() else None
        rows[name] = {'expected': digest, 'now': now, 'match': now == digest,
                      'metadata_only': is_metadata(name)}
    design = {k: v for k, v in rows.items() if not v['metadata_only']}
    fatal = {k: v for k, v in design.items() if not v['match']}
    meta = {k: v for k, v in rows.items() if v['metadata_only'] and not v['match']}
    bridge = sha(ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v')
    result = {
        'head': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True,
                               text=True).stdout.strip(),
        'bridge_sha256': bridge,
        'bridge_expected': '7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933',
        'bridge_match': bridge == '7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933',
        'design_mismatch': fatal,
        'metadata_changed': {k: v['now'] for k, v in meta.items()},
        'verified_files': len(design),
        'all_rows': rows,
    }
    (OUT / 'identity.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('bridge_match', result['bridge_match'], 'head', result['head'])
    print('design_verified', len(design), 'mismatch', len(fatal))
    for k, v in fatal.items():
        print('MISMATCH', k, v['expected'], '->', v['now'])
    print('metadata_changed', len(meta))
    for k in meta:
        print('META', k)


if __name__ == '__main__':
    main()
