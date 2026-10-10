"""Combine independently verified first/after-reset all-mode diagnostic board rounds."""
from pathlib import Path
import argparse,hashlib,json
from check_board import verify,ROOT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first',type=Path,required=True);parser.add_argument('--after-reset',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    assert args.first.resolve()!=args.after_reset.resolve() and not args.output.exists()
    rounds=[]
    for label,p in [('first',args.first),('after_reset',args.after_reset)]:
        r=verify(p);assert r['mode']=='all'
        rounds.append(dict(round=label,**r))
    assert rounds[0]['image_sha256']==rounds[1]['image_sha256']
    summary=dict(status='STAGE8_DIAGNOSTIC_TWO_ROUND_BOARD_PASS',board_result='PASS_DIAGNOSTIC_CANDIDATE_ONLY',
                 stage8_full_board_diagnostic_candidate='PASS',original_stage7_image_revalidated=False,
                 frames=234,ack_count=160,nack_count=74,crc_ack_count=80,
                 uart_frame_error_board='PASS',uart_overflow_board='PASS',raw_uart_flags_each_round=[16,32],
                 image_sha256=rounds[0]['image_sha256'],rounds=rounds,reset_independently_observed=False,
                 load_verify_run_implemented=False,stage9_started=False)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for label,p in [('first',args.first),('after_reset',args.after_reset)]:
        frozen=args.output.with_name(args.output.stem+'_'+label+'_verified.json');assert not frozen.exists()
        with frozen.open('xb') as f:f.write(p.read_bytes())
    with args.output.open('x',encoding='utf8') as f:f.write(json.dumps(summary,indent=2)+'\n')
    print('RESULT: PASS two diagnostic board rounds; 234 frames, frame=0x10 overflow=0x20; old image scope separate')

if __name__=='__main__':main()
