"""2B hardware counter verification using the current myriscv design."""
from pathlib import Path
import argparse,hashlib,importlib.util,inspect,json,re,struct,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];CAND=ROOT/'myriscv'
sys.path.insert(0,str(ROOT/'sim/cpu_performance'))
spec=importlib.util.spec_from_file_location('perf_base',ROOT/'sim/cpu_performance/run.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
from check_output import check,NAMES
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def source(path):
    candidate=CAND/path.name
    return candidate if path.parent==ROOT/'myriscv' and candidate.is_file() else path
def protect():
    paths=[*ROOT.joinpath('myriscv').glob('*.v'),ROOT/'RISCV.pds',ROOT/'generate_bitstream/board_top.sbit',
        *ROOT.joinpath('ipcore/inst_rom').rglob('*.v'),*ROOT.joinpath('ipcore/data_ram').rglob('*.v'),
        ROOT/'ipcore/inst_rom/inst_rom.idf',ROOT/'ipcore/data_ram/data_ram.idf',
        *ROOT.joinpath('tests/bsp_workflow/build').glob('*/program.bin'),
        *ROOT.joinpath('coremark-main').glob('core*.c'),ROOT/'coremark-main/coremark.h',ROOT/'coremark-main/coremark.md5']
    # A fresh source checkout has no generated board bitstream yet. Protect
    # existing artifacts, and include a newly generated bit in later runs.
    return {p.relative_to(ROOT).as_posix():sha(p) for p in paths if p.is_file()}
def compile_candidate(folder,engine,micro=False):
    tb=(ROOT/'sim/cpu_performance/tb_performance.sv').read_text()
    # Counter verification only: data and instruction traffic still use real CPU/bridge.
    extra='''
    integer hw_index, hw_checks=0;
    reg [63:0] hw_expected[0:12];
    always @(posedge clk) if(resetn && stop_event && '''+('marker_id==1' if micro else '1')+''') begin
        for(integer c=0;c<13;c=c+1) hw_expected[c]=monitor.count[c<11?c:c+4];
        #1;
        if(`SOC.u_simple_mmio.g_perf.u_perf.state!=3) $fatal(1,"hardware snapshot did not freeze");
        for(hw_index=0;hw_index<13;hw_index=hw_index+1)
            if(`SOC.u_simple_mmio.g_perf.u_perf.count[hw_index]!==hw_expected[hw_index])
                $fatal(1,"hardware/observer mismatch index=%d hardware=%d expected=%d",hw_index,
                    `SOC.u_simple_mmio.g_perf.u_perf.count[hw_index],hw_expected[hw_index]);
        hw_checks=hw_checks+1;
        $display("CHECK: 13 hardware counters match independent 2A observer");
    end
'''
    if micro:
        extra+='''
    defparam `SOC.PERF_START_PC=0;
    defparam `SOC.PERF_STOP_PC=0;
'''
    declarations='    integer hw_index, hw_checks=0;\n    reg [63:0] hw_expected[0:12];\n'
    extra=extra.replace(declarations,'',1)
    tb=tb.replace('module tb_performance;','module tb_performance;\n'+declarations,1)
    tb=tb.replace('    initial begin #1000000000;',extra+'\n    initial begin #1000000000;',1)
    tb=tb.replace('            $fflush(trace_file); $fflush(uart_file);',
        '            if(hw_checks!=1) $fatal(1,"missing hardware window check");\n            $fflush(trace_file); $fflush(uart_file);',1)
    tbpath=folder/'tb_performance_2b.sv';tbpath.write_text(tb)
    code=inspect.getsource(base.compile_design)
    code=code.replace("[ROOT/'myriscv'/(n+'.v') for n in RTL]", "[candidate_source(ROOT/'myriscv'/(n+'.v')) for n in RTL]")
    code=code.replace("HERE/'tb_performance.sv'",'candidate_tb')
    namespace=dict(base.__dict__,candidate_source=source,candidate_tb=tbpath)
    exec(code,namespace)
    return namespace['compile_design'](folder,engine)
def oracle(folder):
    work=folder/'work';base.command([base.MS/'vlib.exe',work],folder,folder/'vlib.log')
    base.command([base.MS/'vlog.exe','-sv','-work',work,CAND/'simple_mmio.v',ROOT/'sim/cpu_performance/perf_monitor.sv',HERE/'tb_counter.sv'],folder,folder/'compile.log')
    seconds=base.simulate(folder,work,'tb_counter',[],60)
    return dict(status='PERF2B_MMIO_ORACLE_PASS',seconds=seconds)
def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True)
    p.add_argument('--suite',choices=['oracle','micro','coremark','original-coremark'],default='oracle')
    p.add_argument('--engine',choices=['functional','physical','physical-copy'],default='functional')
    p.add_argument('--software-build',default='tests/cpu_performance_2b/build/measure_20261010_c')
    p.add_argument('--timeout',type=int,default=2400);a=p.parse_args();assert re.fullmatch('[a-z0-9_-]+',a.tag)
    out=HERE/'build'/a.tag;out.mkdir(parents=True,exist_ok=False)
    before=protect();(out/'protected_before.json').write_text(json.dumps(before,indent=2)+'\n')
    results={}
    try:
        if a.suite=='oracle':results=oracle(out)
        else:
            compile_dir=out/'compile';compile_dir.mkdir();work=compile_candidate(compile_dir,a.engine,a.suite=='micro')
            for name in ['micro'] if a.suite=='micro' else ['performance_1','validation_1']:
                folder=out/name;folder.mkdir()
                micro=ROOT/'tests/cpu_performance/build/measure_20261010_c'
                if name=='micro' or a.suite=='original-coremark':info,plus=base.prepare(folder,name,micro)
                else:
                    app=base.module(ROOT/'tools/uart_loader/candidates/bsp_workflow/application.py','bsp_audit')
                    original=app.require_manifest(ROOT/a.software_build/name/'manifest.json')
                    raw=(ROOT/original['bin_path']).read_bytes();raw+=bytes((-len(raw))%4)
                    words=list(struct.unpack('<'+'I'*(len(raw)//4),raw)); assert len(words)<4092
                    words += [0]*(4096-len(words));words[4092]=len(raw)//4
                    dat=folder/'data_ram.dat';dat.write_text(''.join(f'{w:08x}\n' for w in words))
                    info=dict(kind='coremark',original=original,done=original['symbols']['program_return'],
                        cases=[dict(id=1,name=name,units=1,unit='iteration')])
                    plus=['+MICRO=0',f'+ROM={(micro/"boot_rom.dat").as_posix()}',f'+DAT={dat.as_posix()}',
                        f'+DONE={info["done"]:x}',f'+START_FN={original["symbols"]["start_time"]:x}',f'+STOP_FN={original["symbols"]["stop_time"]:x}']
                    (folder/'input_manifest.json').write_text(json.dumps(info,indent=2)+'\n')
                print('START',a.engine,name,flush=True)
                seconds=base.simulate(folder,work,'tb_performance',[*plus,'+MAX_CYCLES=60000000'],a.timeout)
                summary=base.summarize(folder,info,a.engine)
                log=(folder/'simulation.log').read_text()
                assert log.count('CHECK: 13 hardware counters match independent 2A observer')==1
                if a.suite=='coremark':
                    parsed=check(info['original'],(folder/'uart.txt').read_bytes())
                    assert all(parsed['counters'][n]==summary['windows'][0][n] for n in NAMES)
                    summary['uart_counter_readout']=parsed
                elif a.suite=='original-coremark':
                    summary['crc']=app.parse_output(info['original'],(folder/'uart.txt').read_bytes()) if 'app' in locals() else base.module(ROOT/'tools/uart_loader/candidates/bsp_workflow/application.py','bsp_parser').parse_output(info['original'],(folder/'uart.txt').read_bytes())
                summary.update(seconds=seconds,hardware_counters_match_observer=True,board_result='NOT_TESTED')
                (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');results[name]=summary
                print('PASS',name,seconds,flush=True)
        (out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    finally:
        after=protect();(out/'protected_after.json').write_text(json.dumps(after,indent=2)+'\n');assert before==after
    print('RESULT: PASS',out,flush=True)
if __name__=='__main__':main()
