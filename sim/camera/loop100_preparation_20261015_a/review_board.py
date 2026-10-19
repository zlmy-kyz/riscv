"""Review preserved real loop100 bytes and independently recompute CSV timing; no hardware activity."""
import csv,json,statistics,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/camera_uart'))
import loop100 as host
def main():
    folder=ROOT/'sim/camera/board/loop100_20261015_01'
    dest=folder/'sol_review.json'
    assert not dest.exists(),'preserve existing review'
    original={p.name:host.sha(p) for p in folder.iterdir() if p.is_file()}
    image=host.require_image(host.DEFAULT)
    r=json.loads((folder/'result.json').read_text(encoding='utf-8'))
    assert r['application']==image and r['retry_count']==0 and not r['PDS_started']
    assert all(host.sha(ROOT/'tools/camera_uart'/n)==d for n,d in r['tool_sha256'].items())
    assert all(host.sha(ROOT/n)==d for n,d in image['protected_sha256'].items())
    checked=host.verify(folder)
    assert checked==json.loads((folder/'verified.json').read_text())
    with (folder/'frames.csv').open(newline='',encoding='utf-8') as stream:rows=list(csv.DictReader(stream))
    assert len(rows)==100 and [int(f['seq']) for f in rows]==list(range(1,101))
    wait=[int(f['wait_ticks']) for f in rows];cpu=[int(f['check_ticks']) for f in rows]
    total=r['statistics']['total_ticks'];hz=93750000
    assert sum(wait)==r['statistics']['wait_sum'] and sum(cpu)==r['statistics']['check_sum']
    assert min(wait)==r['statistics']['wait_min'] and max(wait)==r['statistics']['wait_max']
    assert min(cpu)==r['statistics']['check_min'] and max(cpu)==r['statistics']['check_max']
    total_seconds=total/hz
    metrics=dict(total_seconds=total_seconds,successful_frames=100,effective_checked_frames_per_second=100/total_seconds,
        capture_wait=dict(total_seconds=sum(wait)/hz,mean_ms=statistics.mean(wait)*1000/hz,min_ms=min(wait)*1000/hz,
            max_ms=max(wait)*1000/hz,share_percent=sum(wait)*100/total,first_ms=wait[0]*1000/hz,
            following99_mean_ms=statistics.mean(wait[1:])*1000/hz,following99_min_ms=min(wait[1:])*1000/hz,
            following99_max_ms=max(wait[1:])*1000/hz),
        CPU_read_and_CRC=dict(total_seconds=sum(cpu)/hz,mean_ms=statistics.mean(cpu)*1000/hz,min_ms=min(cpu)*1000/hz,
            max_ms=max(cpu)*1000/hz,spread_us=(max(cpu)-min(cpu))*1e6/hz,share_percent=sum(cpu)*100/total,
            effective_MB_per_second=1843200/(statistics.mean(cpu)/hz)/1e6),
        other=dict(total_seconds=(total-sum(wait)-sum(cpu))/hz,share_percent=(total-sum(wait)-sum(cpu))*100/total),
        bytes_checked=184320000,words_checked=46080000,write_beats_reported_by_checked_firmware=5760000,
        distinct_crcs=len({f['crc32'] for f in rows}),adjacent_equal_crc=sum(a['crc32']==b['crc32'] for a,b in zip(rows,rows[1:])))
    assert all(host.sha(folder/n)==d for n,d in original.items())
    receipt=dict(status='CAMERA_LOOP100_BOARD_DATA_ACCEPTANCE_PASS',date='2026-10-15',
        method='Exact original Loader/TX/RX/summary/end replay plus independent CSV timing arithmetic',
        source_identity_match=True,protected_RTL_PDS_successful_firmware_unchanged=True,
        image_sha256=image['bin_sha256'],manifest_sha256=r['manifest_sha256'],
        loader_responses=len(r['loader_records']),loader_RUN_commands=sum(bool(p.get('run')) for p in host.loader_plan(image)),
        start_commands=1,sequence_range=[1,100],status_all='00000005',error_all='00000000',capture_CPU_CRC_matches=100,
        first_CRC=rows[0]['crc32'],last_CRC=rows[-1]['crc32'],retry_count=0,
        raw_replay=checked,independent_metrics=metrics,original_evidence_sha256=original,
        review_script_sha256=host.sha(Path(__file__)),serial_opened_by_reviewer=False,HDL_run=False,PDS_started=False,
        conclusions=['100 successive single-buffer ARM/BUSY/DONE/metadata/full CPU CRC checks passed on actual board',
            'Capture wait including 10 dropped startup frames is the largest measured phase; no new RTL fault evident',
            'First wait is 749.465 ms; remaining 99 waits and CPU CRC durations are stable',
            'No further RTL/PDS or repeat long simulation needed for this completed data check'],
        limits=['Same CRC is legal; 100 differing CRCs do not prove a human scene-change action; not separately confirmed in this log',
            'No frame export, PC whole-frame CRC or new visual inspection; reuse prior two-frame image acceptance',
            '0.8725 checked frames/s includes 10-drop wait, serial software sequence and CRC; it is not sensor FPS',
            '4.258 MB/s includes CPU CRC computation and metadata; it is not isolated DDR bandwidth',
            'Timing converted at configured 93.75 MHz; no independent host timestamps in this evidence',
            'Normal-path 100 frames do not imply arbitrary stress/fault/PHY/ISA coverage or completion of timed-out SoC simulation'])
    dest.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],review_sha256=host.sha(dest),metrics=metrics),indent=2))
if __name__=='__main__':main()
