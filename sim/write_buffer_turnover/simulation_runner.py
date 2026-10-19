"""Task031 single execution entry (DeepSeek): one frozen vlib/vlog, control and key.

Fixed commands only: no retry, no timeout change, no RPC/permission switch, no tag
change. The control job is the same TB with WRITE_BUFFER_TURNOVER_ENABLE=0 running
the short program; the key job is the full suite with the feature on.
"""
from pathlib import Path
import argparse
import json
import re
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'sim/mini_board_migration'))
from resume_inst_drm64 import command            # noqa: E402  verified native logging
from resume_inst_cache32 import git_snapshot, pds_shell_count  # noqa: E402

MS = Path('D:/modelsim/win64pe')
VENDOR = Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
MANIFEST = HERE / 'inputs.json'
DESIGN = HERE / 'simulation_inputs.json'
TAG = 'ds_write_buffer_turnover_20261014_a'
GROUPS = ['turnover_accept_eligibility', 'front_slot_priority', 'consecutive_turnover',
          'lane_strobe_dcache_ownership', 'forward_read_boundaries', 'reset_init_cancel',
          'non_ddr_order_gate', 'real_soc_turnover_fence_irq']
COVERAGE = ['OPPORTUNITIES', 'ACCEPTED', 'EARLY', 'I_OVERLAP', 'OVERLAP', 'GATE',
            'FENCE_WAIT', 'IRQ_WAIT', 'STOP_WAIT', 'UART', 'RAM', 'SOC_TURNOVER',
            'fills', 'updates', 'cancelled']
RESULT_FIELDS = (['tests', 'cpu_events', 'IRQ', 'OPPORTUNITIES', 'ACCEPTED', 'LATE', 'MLATE', 'EARLY',
                  'I_OVERLAP', 'OVERLAP', 'GATE', 'FENCE_WAIT', 'IRQ_WAIT', 'STOP_WAIT',
                  'UART', 'RAM', 'SOC_TURNOVER', 'fills', 'updates', 'cancelled'])
RESULT_KEY = ('RESULT: PASS write_buffer_turnover_x32 tests=(\\d+) cpu_events=(\\d+) IRQ=(\\d+) '
              'OPPORTUNITIES=(\\d+) ACCEPTED=(\\d+) LATE=(\\d+) MLATE=(\\d+) EARLY=(\\d+) I_OVERLAP=(\\d+) '
              'OVERLAP=(\\d+) GATE=(\\d+) FENCE_WAIT=(\\d+) IRQ_WAIT=(\\d+) STOP_WAIT=(\\d+) '
              'UART=(\\d+) RAM=(\\d+) SOC_TURNOVER=(\\d+) fills=(\\d+) updates=(\\d+) cancelled=(\\d+)')
RESULT_CTL = ('RESULT: PASS write_buffer_turnover_control tests=(\\d+) cycles=(\\d+) '
              'opportunities=(\\d+) late=(\\d+) AW=(\\d+) W=(\\d+)')
SHORT = ('SHORT: cycles=(\\d+) stores=(\\d+) opportunities=(\\d+) accepted=(\\d+) late=(\\d+) '
         'aw=(\\d+) w=(\\d+)')


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return Path(path).read_text(encoding='utf-8', errors='replace')


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def require_design():
    design = json.loads(read(DESIGN))
    assert design['input_manifest_sha256'] == sha(MANIFEST), 'Codex manifest changed'
    codex = json.loads(read(MANIFEST))
    for name, digest in codex['source_sha256'].items():
        assert sha(ROOT / name) == digest, 'RTL input changed: ' + name
    for name, digest in design['sha256'].items():
        assert sha(ROOT / name) == digest, 'design input changed: ' + name
    assert design['fixed_tag'] == TAG
    return design


def compile_argv(out, design):
    return [MS / 'vlog.exe', '-sv', '+incdir+' + (ROOT / 'myriscv').as_posix(),
            '+incdir+' + HERE.as_posix(), '+incdir+' + (ROOT / 'ipcore/inst_rom/rtl').as_posix(),
            '+incdir+' + (ROOT / 'ipcore/data_ram/rtl').as_posix(), '-work', out / 'work',
            *[VENDOR / n for n in design['vendor_compile_sources']],
            *[ROOT / n for n in design['compile_sources']]]


def job_argv(out, design, name):
    job = design['control'] if name == 'control' else design['key']
    args = ['-lib', out / 'work', 'tb_write_buffer_turnover_x32', *job['defines'],
            '+CPU_IMAGE=' + str(ROOT / design['cpu_image'])]
    for key, value in design['plusargs'].items():
        if key != 'CPU_IMAGE':
            args.append('+%s=%d' % (key, value))
    return [MS / 'vsim.exe', '-batch', *args, '-logfile', out / (name + '.transcript'),
            '-do', 'run -all; quit -f']


def short_line(console):
    rows = re.findall(SHORT, console)
    assert len(rows) == 1, 'expected exactly one SHORT line'
    return [int(v) for v in rows[0]]


def wlog(console):
    """Per-W-beat log of the short program (ModelSim prefixes console lines with '# ')."""
    rows = []
    for line in console.splitlines():
        words = line.replace('#', ' ').split()
        if words[:1] == ['WLOG']:
            rows.append(tuple(words[1:]))
    return rows


def check_job(out, design, name):
    console = read(out / (name + '.log'))
    transcript = read(out / (name + '.transcript'))
    assert console.strip() == transcript.strip(), 'console/transcript differ for ' + name
    assert '$finish' in console and 'Errors: 0, Warnings: 0' in console
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', console)
    if name == 'control':
        short = short_line(console)
        rows = re.findall(RESULT_CTL, console)
        assert len(rows) == 1, 'control result line'
        assert [int(v) for v in rows[0]][1:] == [short[0], short[2], short[4], short[5], short[6]]
        assert short[3] == 0, 'disabled feature accepted a turnover'
        assert short[2] > 0 and short[4] == short[2], 'control opportunity accounting'
        return dict(short=short, wlog=wlog(console))
    checks = re.findall(r'CHECK: (\w+) PASS checks=(\d+)', console)
    assert [n for n, _ in checks] == GROUPS, 'key group order/content: %s' % checks
    assert all(int(c) > 0 for _, c in checks)
    rows = re.findall(RESULT_KEY, console)
    assert len(rows) == 1, 'key result line'
    values = [int(v) for v in rows[0]]
    result = dict(zip(RESULT_FIELDS, values))
    assert result['IRQ'] == design['program_review']['irq']
    assert result['cpu_events'] == design['program_review']['events']
    for field in COVERAGE:
        assert result[field] > 0, 'key coverage %s is not positive' % field
    assert result['MLATE'] == 0, 'a manual opportunity was not accepted on its edge'
    assert result['ACCEPTED'] > 0, 'no turnover was accepted'
    result['groups'] = {n: int(c) for n, c in checks}
    result['short'] = short_line(console)
    result['wlog'] = wlog(console)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag')
    args = parser.parse_args()
    design = require_design()
    assert args.tag == TAG, 'use the assigned tag; no automatic retries'
    assert pds_shell_count() == 0, 'concurrent PDS is not allowed'
    out = HERE / 'build' / TAG
    assert not out.exists(), 'preserve the existing run directory'
    out.mkdir(parents=True)
    before = git_snapshot()
    write_json(out / 'git_before.json', before)
    result = dict(status='RUNNING', manifest_sha256=sha(MANIFEST), design_sha256=sha(DESIGN),
                  completed={}, CPU_changed=False, RTL_changed_by_design=False,
                  PDS_started=False, serial_opened=False, board_status='NOT_RUN')
    write_json(out / 'result.json', result)
    try:
        shutil.copyfile(MANIFEST, out / 'inputs.json')
        shutil.copyfile(DESIGN, out / 'simulation_inputs.json')
        for name, digest in design['sha256'].items():
            destination = out / 'inputs' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
            assert sha(destination) == digest
        command([MS / 'vlib.exe', out / 'work'], out, out / 'vlib', 60)
        log = command(compile_argv(out, design), out, out / 'compile', 60)
        modules = re.findall(r'-- Compiling module (\w+)', log)
        assert len(modules) == design['module_count'] and set(modules) == set(design['expected_modules'])
        assert 'Errors: 0, Warnings: 0' in log
        for name in ('control', 'key'):
            command(job_argv(out, design, name), out, out / name, 180)
            result['completed'][name] = check_job(out, design, name)
            write_json(out / 'result.json', result)
        key = result['completed']['key']
        control = result['completed']['control']
        assert key['wlog'] == control['wlog'], 'controlled short program memory traffic differs'
        assert key['short'][1] == control['short'][1], 'short program store count differs'
        assert key['short'][2] == control['short'][2], 'opportunity count differs between runs'
        saved = control['short'][0] - key['short'][0]
        assert saved == key['short'][2], \
            'controlled cycle saving %d != opportunities %d' % (saved, key['short'][2])
        result['controlled_cycles'] = dict(key=key['short'][0], control=control['short'][0],
                                           saved=saved, opportunities=key['short'][2])
        assert require_design() == design
        after = git_snapshot()
        write_json(out / 'git_after.json', after)
        assert before == after, 'git state changed during the run'
        result.update(status='WRITE_BUFFER_TURNOVER_KEY_AND_CONTROL_PASS',
                      inputs_unchanged=True, git_unchanged=True, board_status='NOT_RUN',
                      scope=design['scope'])
        print('RESULT: PASS write buffer turnover key + controlled short program; board NOT_RUN')
    except Exception as exc:                                  # noqa: BLE001
        result.update(status='STOPPED_FIRST_FAILURE', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        write_json(out / 'result.json', result)


if __name__ == '__main__':
    main()
