"""Combine two independently audited stage9 diagnostic board rounds without serial I/O."""
from pathlib import Path
import argparse,json
from check_board import verify

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--first',type=Path,required=True)
    parser.add_argument('--after-reset',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    assert args.first.resolve()!=args.after_reset.resolve() and not args.output.exists()
    rounds=[dict(round=label,**verify(p)) for label,p in [('first',args.first),('after_reset',args.after_reset)]]
    assert rounds[0]['sha256']!=rounds[1]['sha256'] and rounds[0]['image_sha256']==rounds[1]['image_sha256']
    assert rounds[0]['corpus_sha256']==rounds[1]['corpus_sha256']
    result=dict(status='STAGE9_TWO_ROUND_DIAGNOSTIC_BOARD_PASS',board_result='PASS_RANDOM_DIAGNOSTIC_ONLY',rounds=rounds,
                images=sum(r['images'] for r in rounds),frames=sum(r['frames'] for r in rounds),
                payload_bytes=sum(r['payload_bytes'] for r in rounds),zero_error_zero_retry=True,
                reset_independently_observed=False,formal_load_verify_run_implemented=False,random_execute=False,stage10_started=False)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    copies=[args.output.with_name(args.output.stem+'_'+label+'_verified.json') for label in ('first','after_reset')]
    assert all(not p.exists() for p in copies)
    for source,target in zip((args.first,args.after_reset),copies):
        with target.open('xb') as f:f.write(source.read_bytes())
    with args.output.open('x',encoding='utf8') as f:f.write(json.dumps(result,indent=2)+'\n')
    print('RESULT: PASS stage9 two diagnostic board rounds;',result['images'],'images; zero errors/retries; no RUN')

if __name__=='__main__':main()
