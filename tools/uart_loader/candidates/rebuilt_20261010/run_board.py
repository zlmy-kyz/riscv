"""User-operated six-application revalidation, explicitly bound to the rebuilt bitstream."""
from pathlib import Path
import argparse, datetime, hashlib, json, subprocess, sys

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'sim/bsp_workflow/rebuilt_20261010'
GATE = OUT / 'deployment_gate.json'
BIT = ROOT / 'generate_bitstream/board_top.sbit'
SEQUENCE = ('hello', 'crc32', 'performance_1', 'validation_1', 'performance_60', 'validation_60')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def require_gate(manifest):
    gate = json.loads(GATE.read_text())
    assert gate['status'] == 'REBUILT_LOADER_PRE_BOARD_AUDIT_PASS'
    rel = Path(manifest).resolve().relative_to(ROOT).as_posix()
    assert rel in gate['manifests'] and sha(manifest) == gate['manifests'][rel]
    for path, expected in gate['input_sha256'].items():
        assert sha(ROOT / path) == expected, 'Candidate input changed: ' + path
    assert sha(BIT) == gate['successful_bitstream_sha256']
    return sha(GATE)

def configure():
    # Reuse unchanged, validated transport and strict output parser, with new identity.
    sys.path.insert(0, str(ROOT / 'tools/uart_loader/candidates/bsp_workflow'))
    import upload
    upload.BIT, upload.GATE, upload.require_gate = BIT, GATE, require_gate
    sys.path.insert(0, str(ROOT / 'sim/bsp_workflow'))
    import check_board
    assert check_board.BIT == BIT and check_board.require_gate is require_gate
    return upload, check_board

def audit(folder, checker):
    journal = json.loads((folder / 'suite.json').read_text())
    assert journal['status'] in ('AWAITING_AUDIT', 'REBUILT_SIX_APPLICATION_BOARD_PASS')
    assert journal['evidence_origin'] == 'USER_OPERATED_REBUILT_ACTUAL_SERIAL_SUITE'
    assert tuple(journal['sequence']) == SEQUENCE and len(journal['records']) == 6
    runs, hashes, short = [], set(), {}
    last_end = None
    for i, (name, row) in enumerate(zip(SEQUENCE, journal['records']), 1):
        assert row['round'] == i and row['application'] == name
        assert row['result'] == 'PASS' and row['user_KEY0_confirmation']
        start = datetime.datetime.fromisoformat(row['start_utc'])
        end = datetime.datetime.fromisoformat(row['end_utc'])
        assert start <= end and (last_end is None or last_end <= start)
        last_end = end
        path = folder / f'round_{i:02}_{name}.json'
        assert row['log_path'] == path.as_posix() and row['log_sha256'] == sha(path)
        assert sha(path) not in hashes
        hashes.add(sha(path))
        raw = json.loads(path.read_text())
        assert Path(raw['manifest_path']).resolve() == ROOT / f'tests/bsp_workflow/build/{name}/manifest.json'
        checked = checker.verify(path)
        assert raw['records'][0]['seq'] == 1 and raw['records'][0]['received'] == 0
        assert raw['records'][0]['complete'] == raw['records'][0]['verified'] == 0
        assert checked['run_count'] == 1
        if name.endswith('_60'):
            assert raw['crc_prerequisite']['path'] == short[name.rsplit('_', 1)[0]].as_posix()
            assert checked['application']['formal_benchmark']
        if name.endswith('_1'):
            short[name.rsplit('_', 1)[0]] = path
        runs.append(dict(round=i, application_name=name, **checked))
    return dict(status='REBUILT_SIX_APPLICATION_ACTUAL_BOARD_VERIFIED', runs=runs,
                successful_rounds=6, responses=sum(r['responses'] for r in runs),
                successful_RUN_count=6, bitstream_identity=dict(path=BIT.as_posix(), sha256=sha(BIT)),
                gate_sha256=sha(GATE), source_journal_sha256=sha(folder / 'suite.json'),
                KEY0_independently_observed=False, JTAG_programming_independently_observed=False)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, default=OUT / 'board/first')
    p.add_argument('--application', choices=SEQUENCE)
    p.add_argument('--log', type=Path)
    p.add_argument('--crc-log', type=Path)
    p.add_argument('--plan-only', action='store_true')
    p.add_argument('--audit', action='store_true')
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    upload, checker = configure()
    if a.application:
        assert a.log is not None and not a.audit
        require_gate(ROOT / f'tests/bsp_workflow/build/{a.application}/manifest.json')
        sys.argv = [sys.argv[0], '--application', a.application, '--port', 'COM11', '--log', str(a.log)]
        if a.crc_log:
            sys.argv += ['--crc-log', str(a.crc_log)]
        if a.plan_only:
            sys.argv += ['--plan-only']
        upload.main()
        return
    assert not a.plan_only and a.log is None and a.crc_log is None
    folder = a.directory.resolve()
    if a.audit:
        assert a.output is not None and not a.output.exists()
        result = audit(folder, checker)
        with a.output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
        print('RESULT: PASS rebuilt bitstream independent board audit')
        return
    for name in SEQUENCE:
        require_gate(ROOT / f'tests/bsp_workflow/build/{name}/manifest.json')
    assert not folder.exists(), 'Preserve logs; choose another --directory'
    folder.mkdir(parents=True)
    journal = folder / 'suite.json'
    result = dict(status='RUNNING', evidence_origin='USER_OPERATED_REBUILT_ACTUAL_SERIAL_SUITE',
                  sequence=list(SEQUENCE), bitstream_identity=dict(path=BIT.as_posix(), sha256=sha(BIT)),
                  KEY0_independently_observed=False, JTAG_programming_independently_observed=False, records=[])
    save = lambda: journal.write_text(json.dumps(result, indent=2) + '\n')
    save()
    short = {}
    print('Program D:/riscv/RISCV/generate_bitstream/board_top.sbit; close serial terminal. COM11, 115200 8N1.')
    try:
        for i, name in enumerate(SEQUENCE, 1):
            input(f'[{i}/6 {name}] Press KEY0, release, wait for DDR initialization, then Enter: ')
            row = dict(round=i, application=name, user_KEY0_confirmation=True, result='RUNNING',
                       start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            result['records'].append(row)
            save()
            path = folder / f'round_{i:02}_{name}.json'
            cmd = [sys.executable, str(Path(__file__).resolve()), '--application', name, '--log', str(path)]
            if name.endswith('_60'):
                cmd += ['--crc-log', str(short[name.rsplit('_', 1)[0]])]
            completed = subprocess.run(cmd)
            row.update(log_path=path.as_posix(), log_sha256=sha(path) if path.exists() else None,
                       end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            if completed.returncode:
                row['result'] = 'FAIL'
                raise RuntimeError(f'Round {i} failed; preserve logs; no retry')
            row['result'] = 'PASS'
            save()
            if name.endswith('_1'):
                short[name.rsplit('_', 1)[0]] = path
        result['status'] = 'AWAITING_AUDIT'
        save()
        report = audit(folder, checker)
        output = folder / 'board_result.json'
        with output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
        result.update(status='REBUILT_SIX_APPLICATION_BOARD_PASS', independent_result_sha256=sha(output))
        save()
        print('RESULT: PASS rebuilt bitstream Hello/CRC32/CoreMark; logs:', folder)
    except BaseException as error:
        result.update(status='FAIL', error=str(error))
        save()
        raise

if __name__ == '__main__':
    main()
