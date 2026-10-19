"""Task031 dispatch only. DeepSeek supplies and freezes simulation_runner.py."""
import argparse
import json
import subprocess
import sys
from check_inputs import ROOT, HERE, MANIFEST, sha, require_inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-inputs', action='store_true')
    parser.add_argument('--tag', default='ds_write_buffer_turnover_20261014_a')
    args = parser.parse_args()
    inputs = require_inputs()
    assert args.tag == inputs['fixed_tag'], 'Use the assigned tag; no automatic retries'
    design_manifest = HERE / 'simulation_inputs.json'
    if not design_manifest.is_file():
        if args.check_inputs:
            print('RESULT: PASS RTL inputs; DeepSeek simulation design PENDING; HDL NOT_RUN')
            return
        raise ValueError('DeepSeek must first design and freeze simulation_inputs.json and simulation_runner.py')
    design = json.loads(design_manifest.read_text(encoding='utf-8'))
    assert design['input_manifest_sha256'] == sha(MANIFEST)
    runner = HERE / 'simulation_runner.py'
    required = {'sim/write_buffer_turnover/run.py', 'sim/write_buffer_turnover/simulation_runner.py'}
    assert required <= set(design['sha256'])
    for name, digest in design['sha256'].items():
        assert sha(ROOT / name) == digest, name
    for name, digest in design.get('external_sha256', {}).items():
        assert sha(name) == digest, name
    if args.check_inputs:
        print('RESULT: PASS Task031 RTL and frozen simulation inputs; HDL NOT_RUN')
        return
    assert not (HERE / 'build' / args.tag).exists(), 'Preserve existing run directory'
    result = subprocess.run([sys.executable, '-B', str(runner), '--tag', args.tag], cwd=ROOT)
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
