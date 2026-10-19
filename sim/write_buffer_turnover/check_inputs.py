"""Task031 read-only input identity check; this never runs HDL or board tools."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'inputs.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_inputs():
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for section in ('source_sha256', 'software_sha256', 'preparation_sha256', 'baseline_evidence_sha256'):
        for name, digest in data[section].items():
            if sha(ROOT / name) != digest:
                raise ValueError('Input changed: ' + name)
    return data


if __name__ == '__main__':
    manifest = require_inputs()
    print('RESULT: PASS Task031 inputs match; HDL NOT_RUN; ISA=0; serial not opened')
