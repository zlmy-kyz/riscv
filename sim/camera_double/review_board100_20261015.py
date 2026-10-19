"""Read original ABI2 board bytes and independently calculate timing; no serial/HDL/PDS."""
import csv
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/camera_uart'))
import double100


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def main():
    folder = ROOT/'sim/camera_double/board/abi2_100_20261015_01'
    target = folder/'sol_review.json'
    assert not target.exists(), 'do not overwrite a completed review'
    originals = {p.name:sha(p) for p in folder.iterdir() if p.is_file()}
    assert set(originals) == {'application.bin','manifest.json','result.json','verified.json','frames.csv','uart.rx.bin','uart.tx.bin'}
    replay = double100.verify(folder)
    assert replay == load(folder/'verified.json')
    result = load(folder/'result.json')
    manifest = double100.image(double100.DEFAULT)
    assert manifest == load(folder/'manifest.json') == result['application']
    assert result['tool_sha256'] == sha(ROOT/'tools/camera_uart/double100.py')
    assert result['retry_count'] == 0 and result['PDS_started'] is False
    gate = load(ROOT/'sim/camera_double/key_20261016_a/board_release.json')
    assert gate['status'] == 'SOL_KEY_REVIEW_PASS_BOARD_RELEASED'
    assert gate['firmware_sha256'] == manifest['bin_sha256'] == originals['application.bin']
    assert gate['firmware_manifest_sha256'] == sha(double100.DEFAULT) == originals['manifest.json']
    assert sha(ROOT/gate['review_path']) == gate['review_sha256']
    assert sha(ROOT/gate['key_manifest_path']) == gate['key_manifest_sha256']
    frozen = load(ROOT/gate['key_manifest_path'])
    # Recheck relevant RTL/IP, software and key inputs. User requested no PDS/bitstream re-audit.
    checked = {n:d for n,d in frozen['project_sha256'].items() if n != 'RISCV.pds'}
    for n,d in checked.items():
        assert sha(ROOT/n) == d, n
    for n,d in frozen['protected_history_sha256'].items():
        assert sha(ROOT/n) == d, n
    with (folder/'frames.csv').open(encoding='utf-8',newline='') as f:
        rows = list(csv.DictReader(f))
    main_rows = rows[:100]
    assert len(rows) == 101 and all(int(r['seq']) == i+1 for i,r in enumerate(rows))
    assert all(int(r['buffer']) == i%2 for i,r in enumerate(rows))
    hz = 93750000
    waits = [int(r['wait_ticks']) for r in main_rows]
    reads = [int(r['read_ticks']) for r in main_rows]
    # Decode final totals directly from raw ASCII, separately from parser statistics.
    raw = (folder/'uart.rx.bin').read_bytes()[60*len(result['loader_records']):].decode('ascii').splitlines()
    final = dict(item.split('=',1) for item in raw[-1].split()[1:])
    total_ticks = int(final['TOTAL_TICKS'])
    assert [int(final[k]) for k in ('WAIT_SUM','WAIT_MIN','WAIT_MAX','READ_SUM','READ_MIN','READ_MAX')] == [sum(waits),min(waits),max(waits),sum(reads),min(reads),max(reads)]
    assert len(result['loader_records']) == 101
    assert sum(r['name']=='RUN_once' for r in result['loader_records']) == 1
    tail_wait = int(rows[-1]['wait_ticks']); tail_read = int(rows[-1]['read_ticks'])
    remaining = total_ticks-sum(waits)-sum(reads)-tail_wait-tail_read
    assert remaining > 0
    old_path = ROOT/'sim/camera/board/loop100_20261015_01/sol_review.json'
    old = load(old_path)['independent_metrics']
    seconds = total_ticks/hz
    metrics = dict(total_seconds=seconds,formal_frames=100,STOP_tail_frames=1,
        effective_formal_checked_frames_per_second=100/seconds,
        wait=dict(total_seconds=sum(waits)/hz,mean_ms=sum(waits)/100/hz*1000,
                  first_ms=waits[0]/hz*1000,following99_mean_us=sum(waits[1:])/99/hz*1e6,
                  following99_min_us=min(waits[1:])/hz*1e6,following99_max_us=max(waits[1:])/hz*1e6),
        CPU_read_CRC=dict(total_seconds=sum(reads)/hz,mean_ms=sum(reads)/100/hz*1000,
                          min_ms=min(reads)/hz*1000,max_ms=max(reads)/hz*1000,
                          spread_us=(max(reads)-min(reads))/hz*1e6,share_of_total_percent=sum(reads)/total_ticks*100,
                          effective_MB_per_second=1843200/(sum(reads)/100/hz)/1e6,
                          successive25_frame_mean_ms=[sum(reads[i:i+25])/25/hz*1000 for i in range(0,100,25)]),
        tail=dict(wait_us=tail_wait/hz*1e6,read_CRC_ms=tail_read/hz*1000),
        metadata_printing_loop_other_seconds=remaining/hz,
        WAIT_FREE=dict(cycles=int(final['WAIT_CYCLES']),seconds=int(final['WAIT_CYCLES'])/hz,
                       saturated=False,overlaps_CPU_time=True),
        formal_bytes_checked=184320000,all101_bytes_checked=186163200,all101_words_checked=46540800,
        distinct_formal_CRCs=len({r['crc32'] for r in main_rows}),distinct_all_CRCs=len({r['crc32'] for r in rows}),
        comparison_to_single_buffer=dict(old_total_seconds=old['total_seconds'],speed_ratio=old['total_seconds']/seconds,
                                        elapsed_reduction_percent=(1-seconds/old['total_seconds'])*100,
                                        old_CPU_mean_ms=old['CPU_read_and_CRC']['mean_ms'],
                                        old_wait_mean_ms=old['capture_wait']['mean_ms'],
                                        includes_software_flow_and_tail_difference=True))
    assert int(final['WAIT_CYCLES']) < 0xffffffff
    assert originals == {n:sha(folder/n) for n in originals}
    receipt = dict(status='CAMERA_ABI2_DOUBLE100_BOARD_DATA_ACCEPTANCE_PASS',
        reviewed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        method='Exact original Loader/RX/TX/end/CSV replay plus independent timing arithmetic and frozen input identity',
        original_evidence_sha256=originals,review_script_sha256=sha(__file__),raw_replay=replay,
        key_manifest_sha256=gate['key_manifest_sha256'],key_review_sha256=gate['review_sha256'],
        firmware_sha256=manifest['bin_sha256'],manifest_sha256=originals['manifest.json'],
        relevant_frozen_files_checked=len(checked),protected_history_files_checked=len(frozen['protected_history_sha256']),
        source_tool_BIN_ELF_identity_match=True,loader_responses=101,loader_RUN_commands=1,application_G_commands=1,
        retry_count=0,sequence_range=[1,101],buffer_counts_formal=[50,50],buffer_counts_with_tail=[51,50],
        capture_CPU_full_frame_CRC_matches=101,error_all='00000000',
        first_CRC=rows[0]['crc32'],formal_last_CRC=rows[99]['crc32'],tail_CRC=rows[100]['crc32'],
        firmware_guarded_metadata_per_frame=dict(pixels=921600,bytes=1843200,native256bit_write_beats=57600),
        STOP_final_state='Frozen firmware verifies stream stopped, both buffers FREE and GLOBAL_SEQ equals last released SEQ before DB_END PASS',
        independent_metrics=metrics,single_buffer_comparison_receipt_sha256=sha(old_path),
        serial_opened_by_reviewer=False,HDL_run=False,PDS_started=False,PDS_bitstream_reaudited=False,
        conclusions=['100 formal full-720p frames plus 1 in-flight STOP tail passed actual-board full CPU CRC with A/B reuse',
                     'Reduced capture wait is consistent with pipelining and skipping repeated 10-frame warmup; CPU read and CRC now dominates',
                     'WAIT_FREE growth is intended no-overwrite backpressure while software holds the two buffers; no new RTL defect evident'],
        limits=['No raw frame export, PC full-frame CRC or new image inspection in this run',
                'CRC variation does not independently prove a human changed the scene; equal CRC would also be legal',
                'Serial summaries do not provide cycle-level native DMA/CPU interleaving; reuse reviewed key simulation for that',
                'Timing is firmware ticks at configured 93.75 MHz; checked-frame throughput is not sensor FPS or isolated DDR bandwidth',
                'No new Full Boot, PHY or arbitrary stress PASS; original A first-failure evidence stays unchanged'])
    target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],review_sha256=sha(target),metrics=metrics),indent=2))


if __name__ == '__main__':
    main()
