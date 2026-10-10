"""Replay existing regression logic with main RTL and isolated outputs."""
from pathlib import Path
import argparse,importlib.util,inspect,json,re,sys
from run import ROOT,HERE,base,source,protect,sha
def load(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def fast(folder):
    sys.path.insert(0,str(ROOT/'MyCpu_test'))
    b=load(ROOT/'MyCpu_test/build_ddr_stage.py','image_build');b.OUT=folder/'images';b.OUT.mkdir()
    sys.argv=['build_ddr_stage.py'];b.main()
    r=load(ROOT/'MyCpu_test/run_ddr_rv32i_fast.py','rv32i')
    paths=[source(ROOT/n) for n in r.SOURCES];binary=folder/'rv32i.vvp'
    base.command([r.IVERILOG,'-g2012',f'-I{ROOT/"myriscv"}','-s','tb_soc_ddr3_rv32i_fast','-o',binary,*paths],ROOT,folder/'compile.log')
    tohost=dict(line.split() for line in (b.OUT/'tohost.tsv').read_text().splitlines());results={}
    for name in (b.OUT/'cases.txt').read_text().split():
        log=folder/f'{name}.log';plus=[f'+BOOT={(b.OUT/"boot_rom.dat").as_posix()}',f'+IMAGE={(b.OUT/(name+".dat")).as_posix()}',f'+TEST={name}',f'+TOHOST={tohost[name]}']
        try:
            output,_=base.command([r.VVP,binary,*plus],ROOT,log,90)
            assert f'RESULT: PASS {name} DDR RV32I tohost=1' in output
            results[name]='PASS'
        except (RuntimeError,AssertionError):
            assert name in ('fence_i','ma_data'),name
            # Reproduce each gap with production RTL; don't simply whitelist a failure.
            baseline=folder/f'baseline_{name}.vvp'
            base.command([r.IVERILOG,'-g2012',f'-I{ROOT/"myriscv"}','-s','tb_soc_ddr3_rv32i_fast','-o',baseline,*[ROOT/n for n in r.SOURCES]],ROOT,folder/f'baseline_{name}_compile.log')
            try:base.command([r.VVP,baseline,*plus],ROOT,folder/f'baseline_{name}.log',90)
            except RuntimeError:pass
            else:raise AssertionError('candidate failure not present in baseline')
            # Equal failure diagnostics, allowing file-name/tool banners to differ.
            def failure(p):return re.findall(r'RESULT: FAIL[^\r\n]*',p.read_text())
            assert failure(log)==failure(folder/f'baseline_{name}.log')
            results[name]='KNOWN_BASELINE_GAP_REPRODUCED'
    # CPU-origin I/D arbitration and request hold under forced backpressure.
    overlap=load(ROOT/'MyCpu_test/run_cpu_ddr_overlap_fast.py','overlap')
    for back in [False,True]:
        paths=[source(ROOT/n) for n in overlap.SOURCES]
        paths[2]=ROOT/'source'/('tb_cpu_ddr_backpressure_fast.v' if back else 'tb_cpu_ddr_overlap_fast.v')
        top='tb_cpu_ddr_backpressure_fast' if back else 'tb_cpu_ddr_overlap_fast';binary=folder/(top+'.vvp')
        base.command([r.IVERILOG,'-g2012',f'-I{ROOT/"myriscv"}','-s',top,'-o',binary,*paths],ROOT,folder/(top+'_compile.log'))
        for name in ['ld_st'] if back else overlap.DEFAULT_CASES:
            output,_=base.command([r.VVP,binary,f'+BOOT={(b.OUT/"boot_rom.dat").as_posix()}',
                f'+IMAGE={(b.OUT/(name+".dat")).as_posix()}',f'+TEST={name}',f'+TOHOST={tohost[name]}'],ROOT,folder/f'{top}_{name}.log',90)
            assert 'RESULT: PASS' in output and 'CHECK: CPU-origin DDR overlap' in output if back else 'OBS: CPU origin' in output
            results[f'{top}_{name}']='PASS'
    return results
def irq(folder):
    m=load(ROOT/'sim/uart_irq/run_irq.py','irq')
    code=inspect.getsource(m.main).replace('build = ROOT / "sim/uart_irq/build"','build = candidate_output')
    code=code.replace('[ROOT / "myriscv" / f"{name}.v" for name in names]','[candidate_source(ROOT / "myriscv" / f"{name}.v") for name in names]')
    ns=dict(m.__dict__,candidate_output=folder,candidate_source=source);exec(code,ns)
    for stage in ['cpu','uart']:
        for ddr in [False,True]:
            sys.argv=['run_irq.py','--stage',stage]+(['--ddr-code'] if ddr else []);ns['main']()
    return dict(status='PASS',cpu_cases=32,uart_cases=2)
def tcl(folder,physical):
    scripts=['ipcore/ddr3/sim/modelsim/soc_ddr3_sim.tcl','ipcore/ddr3/sim/modelsim/soc_ddr3_regress_sim.tcl'] if physical else [
        'sim/uart_mmio/run_bus_regression.tcl','sim/uart_mmio/run_uart_mmio.tcl','sim/uart_mmio/run_soc_uart_cpu.tcl']
    results={}
    for rel in scripts:
        original=ROOT/rel;out=folder/original.stem;out.mkdir();text=original.read_text()
        if physical:
            text=text.replace('set script_dir [pwd]',f'set script_dir {{{original.parent.as_posix()}}}',1)
            library='soc_ddr3_regress_work' if 'regress' in rel else 'soc_ddr3_work'
            text=re.sub(r'^vmap.*\n','',text,flags=re.M)
            text=text.replace(library,'{'+(out/'work').as_posix()+'}')
            logname=original.stem+'.log';text=text.replace('-l '+logname,'-l {'+(out/logname).as_posix()+'}')
            helper=(ROOT/'sim/compile_ddr3_physical_model.tcl').read_text().replace(
                'set out_dir [file join $repo_dir sim ddr_physical_model]',f'set out_dir {{{(out/"physical_model").as_posix()}}}',1)
            (out/'physical_model.tcl').write_text(helper)
            text=text.replace('source [file join $repo_dir sim compile_ddr3_physical_model.tcl]',
                'source {'+(out/'physical_model.tcl').as_posix()+'}')
        else:
            text=text.replace('set script_dir [pwd]',f'set script_dir {{{out.as_posix()}}}',1)
            text=re.sub(r'set repo_dir .*',f'set repo_dir {{{ROOT.as_posix()}}}',text,count=1)
            if 'run_soc_uart_cpu' in rel:
                base.command([sys.executable,ROOT/'difftest/golden/rvtool.py','asm',ROOT/'sim/uart_mmio/uart_poll.S',out/'cpu_image'],ROOT,out/'assemble.log')
                text=text.replace('    lappend sources [file join $repo_dir myriscv ${name}.v]',
                    '    if {$name in {mycpu_sync soc_top simple_mmio}} {\n'+
                    f'        lappend sources [file join {{{(ROOT/"myriscv").as_posix()}}} ${{name}}.v]\n'+
                    '    } else {lappend sources [file join $repo_dir myriscv ${name}.v]}')
        for n in ['mycpu_sync','soc_top','simple_mmio']:
            text=text.replace(f'[file join $repo_dir myriscv {n}.v]','{'+(ROOT/'myriscv'/(n+'.v')).as_posix()+'}')
        assert not re.search(r'^vmap\s',text,re.M)
        script=out/'run.tcl';script.write_text(text+'\nquit -f\n')
        output,seconds=base.command([base.MS/'vsim.exe','-c','-l',out/'session.log','-do',f'do {{{script.as_posix()}}}'],out,out/'console.log',1200)
        assert 'RESULT: PASS' in output and 'Errors: 0' in output
        assert not re.search(r'\bERROR:',output)
        results[rel]=dict(status='PASS',seconds=seconds)
    return results
def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--suite',choices=['fast','irq','mmio','physical'],required=True);a=p.parse_args()
    assert re.fullmatch('[a-z0-9_-]+',a.tag);folder=HERE/'build'/a.tag;folder.mkdir(parents=True,exist_ok=False)
    before=protect();result={'status':'RUNNING','suite':a.suite,'protected_before':before}
    try:
        result['checks']=fast(folder) if a.suite=='fast' else irq(folder) if a.suite=='irq' else tcl(folder,a.suite=='physical')
        result['status']='PERF2B_REGRESSION_PASS'
    finally:
        result['protected_after']=protect();assert before==result['protected_after']
        (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('RESULT: PASS',folder)
if __name__=='__main__':main()
