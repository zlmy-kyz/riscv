"""Read-only design/snapshot/history preflight; not a final test-seal check."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
IDENTITY = 'a21f061174e2e0bb1a56a25177c96e6de274d68455f273a7e8adfba6eeed5125'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = HERE/'design_inputs.json'
    assert sha(p) == IDENTITY, 'Sol design identity changed'
    m = json.loads(p.read_text(encoding='utf-8'))
    assert sha(HERE/'fix_design_inputs.py') == m['prep_script_sha256']
    for n,d in m['design_sha256'].items():
        assert sha(ROOT/n) == sha(ROOT/m['snapshot']/n) == d, n
    for group in ('reference_dependencies_sha256','protected_sha256'):
        for n,d in m[group].items():
            assert sha(ROOT/n) == d, n
    print(json.dumps(dict(status='SOL_DESIGN_CONTRACT_HISTORY_IDENTITY_PASS_TEST_SEAL_NOT_CREATED',
        design_manifest_sha256=IDENTITY,design_files=len(m['design_sha256']),
        protected_files=len(m['protected_sha256']),HDL_run=False,serial_opened=False),indent=2))


if __name__ == '__main__':
    main()
