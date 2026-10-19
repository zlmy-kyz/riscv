"""Task010: only the missing CPU lw case with echoed DDR read ID and hit proof."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from run_data_read_buffer import command, git_snapshot, load

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / 'data_read_cpu_resume_input_manifest.json'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require_inputs():
    m = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert m['cases'] == ['lw']
    for name, digest in m['sha256'].items():
        assert sha(ROOT / name) == digest, 'INPUT_CHANGED: ' + name
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag')
    p.add_argument('--check-inputs', action='store_true')
    a = p.parse_args()
    m = require_inputs()
    if a.check_inputs:
        assert not a.tag
        print('INPUTS_MATCH_NOT_SIMULATED CPU lw only')
        return
    assert a.tag and re.fullmatch('[a-z0-9_-]+', a.tag)
    out = HERE / 'build' / a.tag
    out.mkdir(parents=True, exist_ok=False)
    result = dict(status='RUNNING', input_manifest_sha256=sha(MANIFEST),
                  cases=['lw'], formal_board='NOT_TESTED', pds_started=False,
                  serial_opened=False, functional_only_not_DDR_performance=True)
    result['git_before'] = git_snapshot(out / 'git_before.json')
    try:
        sys.path.insert(0, str(ROOT / 'MyCpu_test'))
        builder = load(ROOT / 'MyCpu_test/build_ddr_stage.py', 'resume_lw_image')
        builder.OUT = out / 'images'
        sys.argv = ['build_ddr_stage.py', 'lw']
        builder.main()
        runner = load(ROOT / 'MyCpu_test/run_ddr_rv32i_fast.py', 'resume_lw_driver')
        binary = out / 'selected.vvp'
        command([runner.IVERILOG, '-g2012', '-I' + str(ROOT / 'myriscv'),
                 '-s', 'tb_soc_ddr3_rv32i_fast', '-o', binary,
                 *[ROOT / n for n in runner.SOURCES]], ROOT, out / 'compile.log')
        tohost = dict(line.split() for line in
                      (builder.OUT / 'tohost.tsv').read_text().splitlines())
        output = command([runner.VVP, binary,
                          '+BOOT=' + (builder.OUT / 'boot_rom.dat').as_posix(),
                          '+IMAGE=' + (builder.OUT / 'lw.dat').as_posix(),
                          '+TEST=lw', '+TOHOST=' + tohost['lw'], '+EXPECT_D_HITS=1'],
                         ROOT, out / 'lw.log')
        passes = re.findall(r'^RESULT: (?:PASS|FAIL).*$', output, re.M)
        assert len(passes) == 1 and passes[0].startswith('RESULT: PASS lw DDR RV32I tohost=1')
        loaded = re.findall(r'^CHECK: lw CPU loaded (\d+) words into DDR$', output, re.M)
        expected = (builder.OUT / 'lw.dat').read_text().split()
        assert loaded == [str(int(expected[-4], 16) + int(expected[-2], 16))]
        hits = re.findall(r'^CHECK: lw D_READS=(\d+) D_AR=(\d+) D_HITS=(\d+)$', output, re.M)
        assert len(hits) == 1
        reads, ar, hit = map(int, hits[0])
        assert reads > ar > 0 and hit == reads - ar > 0
        result.update(status='DATA_READ_BUFFER_CPU_LW_RESUME_PASS', loaded_words=int(loaded[0]),
                      data_reads=reads, data_ar_commands=ar, data_hits=hit)
    except BaseException as exc:
        result.update(status='FAIL', error=str(exc))
        raise
    finally:
        try:
            result['git_after'] = git_snapshot(out / 'git_after.json')
            require_inputs()
            assert sha(MANIFEST) == result['input_manifest_sha256']
            result['inputs_unchanged'] = True
        except BaseException as exc:
            result.update(status='FAIL', inputs_unchanged=False, input_error=str(exc))
            raise
        finally:
            (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('RESULT: PASS CPU lw data-hit coverage; no unit or historical ISA rerun', out)


if __name__ == '__main__':
    main()
