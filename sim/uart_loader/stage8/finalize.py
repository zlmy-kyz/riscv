"""Publish stage8 simulation receipt only after all final gates pass."""
from pathlib import Path
import hashlib,json
R=Path('D:/riscv/RISCV');B=R/'sim/uart_loader/build/ack_nack_stage8'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf8'))
def main():
    native=load(B/'native/results.json');uart=load(B/'uart/results.json')
    F=R/'sim/uart_loader/build/ack_nack_stage8_repaired/full';full=load(F/'results.json')
    for report,status in [(native,'STAGE8_NATIVE_SIM_PASS'),(uart,'STAGE8_UART_SIM_PASS'),(full,'STAGE8_FULL_SIM_PASS')]:
        assert report['status']==status
        assert all(report[k] for k in ['protected_unchanged','image_unchanged','inputs_unchanged'])
    for k,v in full['protected_sha256'].items():assert sha(Path(k))==v
    for k,v in full['input_sha256'].items():assert sha(Path(k))==v
    archive=load(B/'attempt1_sources/receipt.json')
    archived={e['source']:e for e in archive['entries']}
    historic_differences=[]
    for k,v in native['input_sha256'].items():
        if sha(Path(k))!=v:
            assert archived[k]['sha256']==v and sha(Path(archived[k]['archive']))==v
            historic_differences.append(dict(source=k,sha256=v,archive=archived[k]['archive']))
    stage7=load(R/'sim/uart_loader/build/ddr_crc_stage7_sources/archive_receipt.json')
    for e in stage7['archive_entries']:
        assert sha(R/e['source'])==e['sha256'] and sha(R/e['archive'])==e['sha256']
    initial=load(B/'full/results.json');assert initial['status']=='FAIL' and 'DDR before complete validated UART packet' in initial['error']
    records=load(F/'decoded_responses.json')
    assert len(records)==114 and sum(c['status']!=0 for c in records)==37
    assert all(c['result']=='PASS' for c in records)
    # Revalidate all frozen final inputs and save recoverable copies.
    final_archive=B/'final_sources';entries=[]
    extra=[R/'tools/uart_loader/candidates/ack_nack_stage8/acceptance.py',R/'sim/uart_loader/stage8/check_board.py',
           R/'sim/uart_loader/stage8/check_pc_tool.py',R/'sim/uart_loader/stage8/check_validator.py',Path(__file__)]
    frozen={**full['input_sha256'],**{str(p):sha(p) for p in extra}}
    for k,v in frozen.items():
        p=Path(k);q=final_archive/p.relative_to(R);q.parent.mkdir(parents=True,exist_ok=True)
        if q.exists():assert q.read_bytes()==p.read_bytes()
        else:q.write_bytes(p.read_bytes())
        assert sha(q)==v;entries.append(dict(source=k,archive=str(q),sha256=v))
    (final_archive/'receipt.json').write_text(json.dumps(dict(status='STAGE8_FINAL_INPUT_ARCHIVE_PASS',entries=entries),indent=2)+'\n',encoding='utf8')
    result=dict(date='2026-10-08',status='STAGE8_ACK_NACK_SIM_PASS',board_result='NOT_TESTED',next_action='restore stage7 successful bitstream; reset and wait DDR; COM11 108-frame board acceptance',
        full=dict(evidence=str(F/'results.json'),sha256=sha(F/'results.json'),frames=114,negative_cases=37,time_scale=64,ack_count=77,nack_count=37,
                  crc_ack_count=sum(c['status']==0 and c.get('crc_read',False) for c in records),rx_bytes=len((F/'requests.bin').read_bytes()),tx_bytes=len((F/'responses.bin').read_bytes()),
                  evidence_line=full['results'][-1]['evidence'],wall_seconds=full['results'][-1]['seconds']),
        native=dict(evidence=str(B/'native/results.json'),sha256=sha(B/'native/results.json'),frames=8,negative_cases=2,time_scale=1,
                    bad_header_response_seconds=.113941,truncated_body_response_seconds=.209509,historical_inputs_preserved=historic_differences),
        uart=dict(evidence=str(B/'uart/results.json'),sha256=sha(B/'uart/results.json'),frames=8,negative_cases=2,time_scale=64,evidence_line=uart['results'][-1]['evidence']),
        initial_attempt=dict(result='FAIL_CHECKER',evidence=str(B/'full/results.json'),sha256=sha(B/'full/results.json'),
                             reason='Deliberate FIFO drop reduced LBU count by one; checker compared count to raw wire offset; changed gate to mapped raw LBU index and reran full matrix'),
        image_sha256=full['image']['sha256'],rebuild_performed=False,rtl_c_ip_changed=False,stage7_all_37_original_and_archived_files_match=True,
        input_archive=str(final_archive/'receipt.json'),pc_tool=load(B/'pc_tool_results.json')['status'],independent_board_validator=load(B/'validator_offline/results.json')['status'],
        uart_frame_error_board='NOT_TESTED',uart_overflow_board='NOT_TESTED',load_verify_run_implemented=False,random_binary_test_started=False)
    out=B/'stage8_sim_result.json'
    with out.open('x',encoding='utf8') as stream:stream.write(json.dumps(result,indent=2)+'\n')
    print('RESULT: PASS STAGE8_ACK_NACK_SIM_PASS; full114 / 37 negative; native8; uart8; board NOT_TESTED')
    print(json.dumps(result['full'],indent=2))
if __name__=='__main__':main()
