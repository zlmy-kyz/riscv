"""Offline two-round stage8 r2 evidence audit; never opens a serial port."""
from pathlib import Path
import argparse, collections, hashlib, json, re, sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'sim/uart_loader/stage8'))
from check_board_r2 import verify, EXPECTED_IMAGE
from cases import cases

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf8'))

def audit(console, output):
    output = output.resolve()
    board = ROOT/'sim/uart_loader/board'
    frozen_console = output.with_name(output.stem+'_console_verified.txt')
    sources_dir = output.with_name(output.stem+'_sources')
    assert not output.exists() and not frozen_console.exists() and not sources_dir.exists(), 'Use new archive names'
    raw_console = console.read_bytes()
    lines = raw_console.decode('utf-8-sig').splitlines()
    pattern = re.compile(r'^(\d{3})/108 ([a-zA-Z0-9_]+): (ACK|NACK 0x[0-9A-Fa-f]{4}) PASS (\d+\.\d{3})s$')
    rows = [pattern.fullmatch(s).groups() for s in lines if pattern.fullmatch(s)]
    assert len(rows)==216 and not any('RESULT: FAIL' in s for s in lines)
    assert sum(s=='RESULT: PASS Stage8 host-injectable paths; UART frame/overflow board NOT_TESTED' for s in lines)==2
    command_lines = [s for s in lines if '--port COM11 --log' in s]
    assert len(command_lines)==2
    assert 'ack_nack_stage8_first_pc_r2.json' in command_lines[0]
    assert 'ack_nack_stage8_after_reset_pc_r2.json' in command_lines[1]
    matrix = cases(uart_faults=False)
    rounds=[]
    for round_index, label in enumerate(('first','after_reset')):
        path=board/f'ack_nack_stage8_{label}_pc_r2.json'
        result=verify(path)
        result_path=path.with_name(path.stem+'_result.json')
        frozen=path.with_name(path.stem+'_result_verified.json')
        assert read(result_path)==result and sha(frozen)==sha(path)
        log=read(path)
        assert log['port']=='COM11' and log['baud']==115200
        assert log['no_automatic_retry'] is True and log['load_verify_run_implemented'] is False
        assert log['uart_frame_error_board']=='NOT_TESTED' and log['uart_overflow_board']=='NOT_TESTED'
        assert log['stage8_full_board_result']=='NOT_COMPLETE'
        for name, expected in log['input_sha256'].items():
            assert sha(ROOT/'tools/uart_loader/candidates/ack_nack_stage8_r2'/name)==expected
        for name, expected in EXPECTED_IMAGE.items():
            for directory in ('tests/uart_loader/build/ddr_crc','tests/uart_loader/verified/ddr_crc_stage7/build','tests/uart_loader/candidates/ack_nack_stage8/build'):
                assert sha(ROOT/directory/name)==expected
        for i,(r,c) in enumerate(zip(log['records'],matrix)):
            index,name,status,time=rows[round_index*108+i]
            assert int(index)==i+1 and name==r['name']
            expected='ACK' if c['status']==0 else f'NACK 0x{c["status"]:04X}'
            assert status==expected and time==f'{r["seconds"]:.3f}'
        records=log['records']
        assert records[0]['seq']==1 and records[0]['status']==0
        assert records[-1]['seq']==73 and records[-1]['status']==0
        nack_histogram=collections.Counter(f'0x{c["status"]:04X}' for c in matrix if c['status'])
        timeouts={c['name']:r['seconds']*1000 for c,r in zip(matrix,records) if c.get('negative') and c['status']==0x8004}
        recovery=[r['seconds']*1000 for c,r in zip(matrix,records) if '_recover_' in c['name']]
        rounds.append(dict(round=label,**result,verified_evidence=frozen.relative_to(ROOT).as_posix(),
                           verification_result=result_path.relative_to(ROOT).as_posix(),
                           tx_bytes=sum(len(bytes.fromhex(r['tx_hex'])) for r in records),
                           rx_bytes=sum(len(bytes.fromhex(r['rx_hex'])) for r in records),
                           start_sequence=1,final_sequence=73,nack_histogram=dict(sorted(nack_histogram.items())),
                           truncated_nack_ms=timeouts,recovery_ack_ms_min=min(recovery),recovery_ack_ms_max=max(recovery),
                           input_sha256=log['input_sha256']))
    checked={}
    receipts=[('sim/uart_loader/build/ddr_crc_stage7_sources/archive_receipt.json','archive_entries',('source','archive')),
              ('sim/uart_loader/stage8/candidate_receipt.json','entries',('source','candidate')),
              ('sim/uart_loader/build/ack_nack_stage8_pc_r2/source_receipt.json','entries',('source','archive'))]
    for name, key, fields in receipts:
        receipt=read(ROOT/name)
        for entry in receipt[key]:
            for field in fields:
                assert sha(ROOT/entry[field])==entry['sha256'], f'{name}: {entry[field]}'
        checked[name]=dict(sha256=sha(ROOT/name),entries=len(receipt[key]))
    full=ROOT/'sim/uart_loader/build/ack_nack_stage8_repaired/full/results.json'
    simulation=read(full)
    assert simulation['status']=='STAGE8_FULL_SIM_PASS'
    for key in ('protected_sha256','input_sha256'):
        for name, expected in simulation[key].items():
            assert sha(Path(name))==expected, f'{key}: {name}'
    historical=board/'ack_nack_stage8_board_result.json'
    assert read(historical)['board_result']=='INCOMPLETE_RETEST_REQUIRED_PC_TIMING_FIX'
    result=dict(date='2026-10-08',status='STAGE8_HOST_INJECTABLE_TWO_ROUND_BOARD_PASS',board_result='PASS_HOST_INJECTABLE_ONLY',
                stage8_full_board_result='NOT_COMPLETE',port='COM11',baud=115200,serial_operated_by='USER',
                frames=216,ack_count=146,nack_count=70,crc_ack_count=74,negative_cases_per_round=35,
                fixed_ddr_base='0x40000000',fixed_ddr_bytes=64,actual_crc32='0x23C3E508',
                tx_bytes=sum(r['tx_bytes'] for r in rounds),rx_bytes=sum(r['rx_bytes'] for r in rounds),
                uart_frame_error_board='NOT_TESTED',uart_overflow_board='NOT_TESTED',
                reset_evidence='User submitted requested first and after_reset rounds; both accepted fresh SEQ1',
                reset_independently_observed=False,downloaded_bitstream_identity=None,
                scope='Host-injectable diagnostic exceptions and recovery; fixed64 DDR CRC preservation only',
                load_verify_run_implemented=False,stage9_started=False,
                image_sha256=EXPECTED_IMAGE,rounds=rounds,receipts_checked=checked,
                preserved_simulation=dict(path=full.relative_to(ROOT).as_posix(),sha256=sha(full),
                                          protected_files_checked=len(simulation['protected_sha256']),input_files_checked=len(simulation['input_sha256'])),
                historical_failure_summary=dict(path=historical.relative_to(ROOT).as_posix(),sha256=sha(historical),preserved=True),
                console=dict(path=frozen_console.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(raw_console).hexdigest(),pass_rows=216,final_pass_count=2),
                source_receipt=[])
    sources_dir.mkdir()
    for source in (Path(__file__),ROOT/'sim/uart_loader/stage8/check_board_r2.py'):
        archive=sources_dir/source.name
        with archive.open('xb') as stream: stream.write(source.read_bytes())
        result['source_receipt'].append(dict(source=source.relative_to(ROOT).as_posix(),archive=archive.relative_to(ROOT).as_posix(),sha256=sha(source)))
    with frozen_console.open('xb') as stream:stream.write(raw_console)
    with output.open('x',encoding='utf8') as stream:stream.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('RESULT: PASS two rounds; 216 frames, 146 ACK, 70 expected NACK, 74 CRC ACK')
    print(json.dumps({'tx_bytes':result['tx_bytes'],'rx_bytes':result['rx_bytes'],'rounds':[{'round':r['round'],'timeouts_ms':r['truncated_nack_ms'],'recovery_ack_ms':[r['recovery_ack_ms_min'],r['recovery_ack_ms_max']]} for r in rounds]},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--console',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    audit(args.console,args.output)
