"""Sol compile-only check. No vsim/vvp/run command."""
import argparse,json,subprocess
from pathlib import Path
from seal import HERE,ROOT,MS,VENDOR,sources,INCDIRS,sha,save,closure
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=HERE/'preparation/static_a');a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    src=sources();inc=closure(ROOT,src)
    jobs=[('vlib',[MS/'vlib.exe',out/'work']),('compile',[MS/'vlog.exe','-sv','-work',out/'work',*['+incdir+'+(ROOT/d).as_posix() for d in INCDIRS],
        *[VENDOR/n for n in ('GTP_GRS.v','GTP_DRM36K_E1.v','GTP_APM_E2.v')],*[ROOT/n for n in src]])]
    for name,argv in jobs:
        r=subprocess.run(list(map(str,argv)),cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
        (out/(name+'.log')).write_bytes(r.stdout);save(out/(name+'.command.json'),dict(argv=list(map(str,argv)),cwd=str(out),returncode=r.returncode))
        assert r.returncode==0,r.stdout.decode(errors='replace')
        assert b'** Error' not in r.stdout,r.stdout.decode(errors='replace')
    assert b'Errors: 0, Warnings: 0' in r.stdout
    save(out/'review.json',dict(status='ABI2_COMPLETE_MODELSIM_COMPILE_PASS_HDL_NOT_RUN',sources=len(src),include_edges=inc,
          input_sha256={n:sha(ROOT/n) for n in set(src)|set(inc.values())},HDL_executed=False))
    print('ABI2_COMPLETE_MODELSIM_COMPILE_PASS_HDL_NOT_RUN')
if __name__=='__main__':main()
