"""Task011: UART wait-chain equivalence/latency and two DDR-path ISA cases."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / 'wait_chain_input_manifest.json'
sys.path.insert(0, str(ROOT / 'sim/inst_line_buffer'))
from run_data_read_buffer import command, git_snapshot, load

sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_inputs():
    m = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert m['unit_delays'] == [0, 1, 2, 6]
    assert m['isa_cases'] == random.Random(m['isa_seed']).sample(m['isa_pool'], 2)
    for name, digest in m['sha256'].items():
        assert sha(ROOT / name) == digest, 'INPUT_CHANGED: ' + name
    return m


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag')
    parser.add_argument('--check-inputs', action='store_true')
    args = parser.parse_args()
    manifest = require_inputs()
    if args.check_inputs:
        assert not args.tag
        print('INPUTS_MATCH_NOT_SIMULATED', len(manifest['sha256']),
              manifest['isa_seed'], manifest['isa_cases'])
        return
    assert args.tag and re.fullmatch('[a-z0-9_-]+', args.tag)
    out = HERE / 'build' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    result = dict(status='RUNNING', input_manifest_sha256=sha(MANIFEST),
                  isa_seed=manifest['isa_seed'], isa_cases=manifest['isa_cases'],
                  checks={}, pds_started=False, serial_opened=False,
                  simulation_started=True, formal_board='NOT_TESTED',
                  functional_only_not_DDR_performance=True)
    result['git_before'] = git_snapshot(out / 'git_before.json')
    try:
        iverilog = Path('D:/iverilog/bin/iverilog.exe')
        vvp = Path('D:/iverilog/bin/vvp.exe')
        unit = out / 'unit.vvp'
        command([iverilog, '-g2012', '-s', 'tb_wait_chain', '-o', unit,
                 *[ROOT / name for name in manifest['unit_sources']]],
                ROOT, out / 'unit_compile.log')
        output = command([vvp, unit], ROOT, out / 'unit.log')
        rows = re.findall(r'^RESULT: PASS uart_wait_chain delay=(\d+) '
                          r'transactions=(\d+) accepted=(\d+) responses=(\d+) '
                          r'decoded=(\d+) canceled=(\d+)$', output, re.M)
        assert len(rows) == 4 and {int(row[0]) for row in rows} == {0, 1, 2, 6}
        assert len(re.findall(r'^RESULT: PASS uart_wait_chain_all modes=4$', output, re.M)) == 1
        assert len(re.findall(r'^RESULT:', output, re.M)) == 5
        for delay, transactions, accepted, responses, decoded, canceled in rows:
            values = tuple(map(int, (transactions, accepted, responses, decoded, canceled)))
            assert values == (28, 29, 28, 1, 1)
            for group in ('latency/held-valid/TX/lanes', 'RX/order/no-repeat/empty/IRQ',
                          'access-fault/frame/W1C', 'reset/canceled=1'):
                assert output.count(f'CHECK: uart_wait_chain delay={delay} {group} PASS') == 1
            result['checks']['delay_' + delay] = dict(status='PASS', transactions=28,
                                                      accepted=29, responses=28,
                                                      decoded=1, canceled=1)

        sys.path.insert(0, str(ROOT / 'MyCpu_test'))
        builder = load(ROOT / 'MyCpu_test/build_ddr_stage.py', 'uart_wait_isa_images')
        builder.OUT = out / 'images'
        sys.argv = ['build_ddr_stage.py', *manifest['isa_cases']]
        builder.main()
        assert (builder.OUT / 'cases.txt').read_text().split() == manifest['isa_cases']
        for name, digest in manifest['prepared_images_sha256'].items():
            assert sha(builder.OUT / name) == digest, 'IMAGE_CHANGED: ' + name
        runner = load(ROOT / 'MyCpu_test/run_ddr_rv32i_fast.py', 'uart_wait_isa_driver')
        binary = out / 'isa.vvp'
        assert runner.SOURCES == manifest['isa_sources']
        command([iverilog, '-g2012', '-I' + str(ROOT / 'myriscv'),
                 '-s', 'tb_soc_ddr3_rv32i_fast', '-o', binary,
                 *[ROOT / name for name in runner.SOURCES]], ROOT, out / 'isa_compile.log')
        tohost = dict(line.split() for line in (builder.OUT / 'tohost.tsv').read_text().splitlines())
        for name in manifest['isa_cases']:
            output = command([vvp, binary, '+BOOT=' + (builder.OUT / 'boot_rom.dat').as_posix(),
                              '+IMAGE=' + (builder.OUT / (name + '.dat')).as_posix(),
                              '+TEST=' + name, '+TOHOST=' + tohost[name]],
                             ROOT, out / (name + '.log'))
            passes = re.findall(r'^RESULT: (?:PASS|FAIL).*$', output, re.M)
            assert len(passes) == 1 and re.fullmatch(
                r'RESULT: PASS ' + re.escape(name) + r' DDR RV32I tohost=1 cycles=\d+', passes[0])
            words = (builder.OUT / (name + '.dat')).read_text().split()
            count = int(words[-4], 16) + int(words[-2], 16)
            assert re.findall(r'^CHECK: ' + re.escape(name) + r' CPU loaded (\d+) words into DDR$',
                              output, re.M) == [str(count)]
            result['checks']['isa_' + name] = dict(status='PASS', loaded_words=count)
        result['status'] = 'UART_WAIT_CHAIN_KEY_TESTS_PASS'
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
    print('RESULT: PASS UART wait-chain key tests', out)


if __name__ == '__main__':
    main()
