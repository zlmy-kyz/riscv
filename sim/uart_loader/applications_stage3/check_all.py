"""Audit the requested five actual-board application runs on one Loader bitstream."""
from pathlib import Path
import argparse,json
from check_board import verify,sha,ROOT

NAMES=('second','performance_1','validation_1','performance_60','validation_60')

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists(),'Preserve existing result'
    runs={name:verify(a.directory/(name+'.json')) for name in NAMES}
    first=runs['second']
    assert first['board_result']=='SECOND_APPLICATION_PASS'
    for name,row in runs.items():
        assert row['gate_sha256']==first['gate_sha256'] and row['successful_bitstream_identity']==first['successful_bitstream_identity']
        if name!='second':
            mode,n=name.rsplit('_',1);assert row['application_info']['mode']==mode and row['application_info']['iterations']==int(n)
            assert row['board_result']==('COREMARK_CRC_FUNCTIONAL_PASS' if n=='1' else 'COREMARK_FORMAL_BOARD_PASS')
    assert len({row['application_info']['bin_sha256'] for row in runs.values()})==5
    baseline_path=ROOT/'sim/uart_loader/board/verify_run_hello_board_result.json'
    baseline=json.loads(baseline_path.read_text());assert baseline['status']=='COMBINED_ACTUAL_BOARD_VERIFIED'
    assert baseline['downloaded_bitstream_identity']==first['successful_bitstream_identity']
    hello=ROOT/'tests/uart_loader/program_hello/build/program.bin'
    assert first['application_info']['bin_sha256']!=sha(hello)
    result=dict(status='SECOND_PROGRAM_AND_COREMARK_ACTUAL_BOARD_PASS',runs=runs,
                same_loader_bitstream_sha256=first['successful_bitstream_identity']['sha256'],
                baseline_hello_evidence_sha256=sha(baseline_path),
                additional_ten_reset_test='NOT_TESTED_IN_THIS_REQUEST',
                reset_and_FPGA_programming_independently_observed=False)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print('RESULT: PASS second program, both CoreMark CRC checks, both formal runs; same Loader bitstream')

if __name__=='__main__':main()
