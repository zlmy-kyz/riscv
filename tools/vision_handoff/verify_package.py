import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description='Verify a transferred vision package without opening serial or PDS')
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.out and args.out.exists():
        raise ValueError('new report path required')
    manifest = json.loads((ROOT / 'package_manifest.json').read_text(encoding='utf-8'))
    checked = 0
    for name, entry in manifest['files'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or path.stat().st_size != entry['bytes'] or sha(path) != entry['sha256']:
            raise ValueError('changed or missing package file: ' + name)
        checked += 1
    project = ROOT / 'project'
    setup = (project / 'RISCV.pds').read_text(encoding='utf-8').split('(_task tsk_compile', 1)[0]
    references = sorted(set(re.findall(r'\(_(?:file|ip|ip_source_item)\s+"([^"]+)"', setup)))
    for name in references:
        if not (project / name).is_file():
            raise ValueError('missing PDS setup input: ' + name)
    samples = json.loads((project / 'sim/cnn/training/handwritten_data_20261017_a/samples.json').read_text(encoding='utf-8'))
    for record in samples:
        if sha(ROOT / 'dataset_source' / record['path']) != record['sha256']:
            raise ValueError('source dataset mismatch ' + record['path'])
    result = dict(status='TRANSFERRED_PACKAGE_HASHES_AND_PDS_SETUP_INPUTS_VERIFIED', files_checked=checked,
                  source_images_checked=len(samples), PDS_setup_inputs=len(references),
                  serial_opened=False, PDS_started=False, model_retrained=False, replays={})

    def run(arguments):
        command = [sys.executable, '-X', 'utf8', str(project / 'tools/cnn_handwritten_perf46/run.py'), *arguments]
        process = subprocess.run(command, cwd=project, capture_output=True, timeout=120)
        if process.returncode:
            raise ValueError(process.stderr.decode('utf-8', errors='replace') + process.stdout.decode('utf-8', errors='replace'))
        return json.loads(process.stdout.decode('utf-8'))

    if args.plan:
        result['plan'] = run(['--plan-only'])
    if args.replay:
        for name in manifest['capture_directories']:
            result['replays'][name] = run(['--verify', str(project / name)])
        result['status'] = 'TRANSFERRED_PACKAGE_RAW_CAPTURES_REPLAYED_NOT_RECOGNITION_ACCURACY_PASS'
    if args.out:
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
