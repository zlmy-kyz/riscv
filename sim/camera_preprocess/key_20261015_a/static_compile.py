"""Compile-only check for the preprocess key group. No vsim/vvp/run command."""
import argparse,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
MS=Path('D:/modelsim/win64pe')
VENDOR=Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
INCDIRS=['myriscv','ipcore/inst_rom/rtl','ipcore/data_ram/rtl','sim/camera/key',
         'sim/camera_preprocess/key_20261015_a']
NEW=['ddr_model.sv','pp_aperture.sv','cam_boundary.sv','tb_unit.sv','tb_soc.sv']
def sources():
    prior=json.loads((ROOT/'sim/camera/key/inputs.json').read_text(encoding='utf-8'))
    base=[s for s in prior['compile_sources'] if not s.startswith('sim/')]
    for n in ('myriscv/preprocess_mmio.v','myriscv/preprocess_ddr_read_arbiter.v'):
        if n not in base:
            i=base.index('myriscv/dual_sram_to_pango_ddr_bridge.v')+1
            base.insert(i,n)
    return (base+['sim/camera/key/sensor.sv']
            +[f'sim/camera_preprocess/key_20261015_a/{n}' for n in NEW if (HERE/n).exists()])
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=HERE/'preparation/static_a');a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    src=sources()
    jobs=[('vlib',[MS/'vlib.exe',out/'work']),
          ('compile',[MS/'vlog.exe','-sv','-work',out/'work',*['+incdir+'+(ROOT/d).as_posix() for d in INCDIRS],
            *[VENDOR/n for n in ('GTP_GRS.v','GTP_DRM36K_E1.v','GTP_APM_E2.v')],*[ROOT/n for n in src]])]
    for name,argv in jobs:
        r=subprocess.run(list(map(str,argv)),cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
        (out/(name+'.log')).write_bytes(r.stdout)
        (out/(name+'.command.json')).write_text(json.dumps(dict(argv=list(map(str,argv)),cwd=str(out),returncode=r.returncode),indent=2)+'\n')
        if r.returncode or b'** Error' in r.stdout:
            print(r.stdout.decode(errors='replace')[-8000:]);sys.exit(1)
    tail=r.stdout.decode(errors='replace').strip().splitlines()[-1]
    print('STATIC_COMPILE_OK sources=%d %s'%(len(src),tail))
if __name__=='__main__':main()
