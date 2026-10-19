"""Preserve the previous working UART entry/parser, checked against original log identities."""
from pathlib import Path
import hashlib
import json
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def main():
    target = HERE/'previous_sources'
    assert not target.exists(), 'Preserve previous archive'
    ident = json.loads((ROOT/'sim/cpu_cache_perf/board/perf27_v_parser_fix01_01/identity.json').read_text())
    earlier = json.loads((ROOT/'sim/cpu_cache_perf/software_20261018_a/review.json').read_text())
    names = ['tests/cpu_performance_2b/perf27_software.py',
             'tools/uart_loader/candidates/perf_2b/run_perf27_measurement.py',
             'tools/uart_loader/candidates/perf_2b/run_perf27_measurements.ps1']
    restored = {}
    for n in names:
        text = (ROOT/n).read_text(encoding='utf-8')
        if n.endswith('perf27_software.py'):
            text = text.replace("    if info.get('layout_schema') == 'FROZEN_LAYOUT_PLUS_PERF27_V1':\n        from perf27_fixed_software import require_manifest as require_fixed_manifest\n        return require_fixed_manifest(path)\n",'')
            text = text.replace("comparison_kind=info['comparison_kind'])", "comparison_kind='NEW_PERF27_BIN_NOT_THE_FROZEN_P300_V300_BIN')")
        elif n.endswith('.py'):
            text = text.replace('from perf27_software import require_manifest, parse_measurement, sha\nfrom perf27_fixed_software import DEFAULT_FIXED_TAG',
                                'from perf27_software import DEFAULT_TAG, require_manifest, parse_measurement, sha')
            text = text.replace("         'tests/cpu_performance_2b/perf27_fixed_software.py',\n         'tests/cpu_performance_2b/build_perf27_fixed.py',\n",'')
            text = text.replace("extra.add_argument('--build-tag')", "extra.add_argument('--build-tag', default=DEFAULT_TAG)")
            text = text.replace("    if options.build_tag is None and '--verify-log' in rest:\n        record = json.loads(Path(rest[rest.index('--verify-log')+1]).read_text(encoding='utf-8'))\n        options.build_tag = Path(record['manifest_path']).parent.parent.name\n    if options.build_tag is None:\n        options.build_tag = DEFAULT_FIXED_TAG\n",'')
            text = text.replace("            identity['layout_schema'] = info.get('layout_schema', 'UNFIXED_PERF27_LAYOUT')\n",'')
        else:
            text = text.replace('perf27_fixed_300_01','perf27_300_01').replace('measure_perf27_fixed_20261018_a','measure_perf27_20261018_a')
        expected = (ident['sha256'] if n in ident['sha256'] else earlier['source_sha256'])[n]
        matches = [b for b in [text.encode(),text.replace('\n','\r\n').encode()] if hashlib.sha256(b).hexdigest()==expected]
        assert matches, n
        restored[n] = (matches[0],expected)
    target.mkdir()
    for n,(data,_) in restored.items(): (target/Path(n).name).write_bytes(data)
    (target/'identity.json').write_text(json.dumps(dict(
        status='PREVIOUS_WORKING_SOURCE_BYTES_RECONSTRUCTED_AND_HASH_VERIFIED',
        note='Historical source archive only; original logs and hashes unchanged. Lowercase-only pre-fix parser is separately archived in parser_case_fix01.',
        sha256={n:h for n,(_,h) in restored.items()}),indent=2)+'\n',encoding='utf-8')
    print('Previous parser/tool/PowerShell source bytes archived; original identity hashes match')
if __name__ == '__main__': main()
