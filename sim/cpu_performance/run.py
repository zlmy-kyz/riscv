"""Isolated monitor oracle, microbenchmarks, and existing CoreMark BIN observer."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import struct
import subprocess
import time
from analyze import check_partition, metrics, summarize

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MS=Path('D:/modelsim/win64pe')
LIB=Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
RTL='alu br_alu l_alu regfile csr_file mycpu_sync inst_bus_interconnect data_bus_interconnect inst_bram_adapter data_bram_adapter simple_mmio dual_sram_to_pango_ddr_bridge uart_tx uart_rx uart_rx_fifo uart_mmio soc_top'.split()


def setup_wrapper(folder):
    """Derive a simulation-only setup mux around the unmodified DDR wrapper.

    All payload beats are written and read back through Pango IP + PHY + DRAM
    before CPU reset release. During measurement the mux selects the real bridge.
    """
    original=(ROOT/'myriscv/soc_ddr3_top.v').read_text(encoding='utf-8').split('endmodule',1)[0]+'endmodule\n'
    text=original.replace('module soc_ddr3_top #(', 'module perf_ddr3_setup #(',1)
    text=text.replace('    wire pll_lock;', '    reg setup_done=0;\n    wire pll_lock;',1)
    text=text.replace('.RESET_PC(RESET_PC)', ".RESET_PC(32'h40000000), .INST_ROM_BASE(0), .DATA_RAM_BASE(0)",1)
    text=text.replace('ddr_init_done && pll_lock};','ddr_init_done && pll_lock && setup_done};',1)
    prep=r'''
    reg [31:0] setup_image[0:4095];
    integer setup_state=0, setup_index=0, setup_beats;
    string setup_path;
    wire [27:0] setup_addr=setup_index*8; // 16-bit user address units
    wire [127:0] setup_data={setup_image[setup_index*4+3],setup_image[setup_index*4+2],
                             setup_image[setup_index*4+1],setup_image[setup_index*4]};
    initial begin
        if(!$value$plusargs("DAT=%s",setup_path)) $fatal(1,"missing setup DAT");
        $readmemh(setup_path,setup_image);
        setup_beats=(setup_image[4092]+3)/4;
        if(setup_beats<1 || setup_beats>1023) $fatal(1,"setup size invalid");
    end
    task setup_read_complete;
        begin
            if(axi_rdata!==setup_data || !axi_rlast || axi_rid!=0)
                $fatal(1,"RESULT: FAIL physical DDR setup readback beat=%0d expected=%h got=%h",
                       setup_index,setup_data,axi_rdata);
            if(setup_index+1==setup_beats) begin
                setup_done<=1;
                $display("CHECK: Pango IP/PHY/physical DDR wrote and read back %0d payload beats",setup_beats);
            end else begin setup_index<=setup_index+1; setup_state<=2; end
        end
    endtask
    task setup_write_complete;
        begin
            if(!axi_wusero_last) $fatal(1,"setup W last missing");
            if(setup_index+1==setup_beats) begin setup_index<=0; setup_state<=2; end
            else begin setup_index<=setup_index+1; setup_state<=0; end
        end
    endtask
    always @(posedge core_clk) begin
        if(!resetn) begin setup_done<=0; setup_state<=0; setup_index<=0; end
        else if(ddr_init_done && pll_lock && !setup_done) begin
            case(setup_state)
                0: if(axi_awready) begin
                    if(axi_wready) setup_write_complete(); else setup_state<=1;
                end
                1: if(axi_wready) setup_write_complete();
                2: if(axi_arready) begin
                    if(axi_rvalid) setup_read_complete(); else setup_state<=3;
                end
                3: if(axi_rvalid) setup_read_complete();
            endcase
        end
    end
'''
    text=text.replace('    ddr3 u_ddr3 (',prep+'\n    ddr3 u_ddr3 (',1)
    expressions={
        'awaddr':'setup_addr','awuser_ap':"1'b0",'awuser_id':"4'd1",'awlen':"4'd0",
        'awvalid':'(ddr_init_done && pll_lock && setup_state==0)',
        'wdata':'setup_data','wstrb':"16'hffff",'araddr':'setup_addr',
        'aruser_ap':"1'b0",'aruser_id':"4'd0",'arlen':"4'd0",
        'arvalid':'(ddr_init_done && pll_lock && setup_state==2)'}
    for name,value in expressions.items():
        old=f'.axi_{name}(axi_{name})'
        assert text.count(old)==1,name
        text=text.replace(old,f'.axi_{name}(setup_done ? axi_{name} : {value})',1)
    path=folder/'perf_ddr3_setup.sv'; path.write_text(text,encoding='utf-8')
    return path


def setup_functional_stub(folder):
    # Only for setup-harness verification. Never mark this engine as performance evidence.
    header=(ROOT/'ipcore/ddr3/ddr3.v').read_text(encoding='utf-8').split(');',1)[0]+');\n'
    body=r'''
    reg fake_clock=0;
    always #(1.0e9/93750000.0/2.0) fake_clock=~fake_clock;
    assign core_clk=fake_clock;
    assign pll_lock=1'b1;
    assign ddr_init_done=resetn;
    assign axi_wusero_id=4'd1;
    assign axi_wusero_last=axi_wready;
    assign axi_rid=4'd0;
    assign axi_rlast=axi_rvalid;
    coremark_ddr_model fake_memory(.clk(core_clk),.resetn(resetn),
        .awaddr(axi_awaddr),.awvalid(axi_awvalid),.awready(axi_awready),
        .wdata(axi_wdata),.wstrb(axi_wstrb),.wready(axi_wready),
        .araddr(axi_araddr),.arvalid(axi_arvalid),.arready(axi_arready),
        .rdata(axi_rdata),.rvalid(axi_rvalid));
endmodule
module GTP_GRS(input GRS_N); endmodule
module ddr3_mem #(parameter DEBUG=0)(input rst_n,ck,ck_n,cs_n,ras_n,cas_n,we_n,odt,cke,
    input [14:0] addr,input [2:0] ba,inout [15:0] dq,inout [1:0] dqs,dqs_n,
    input [1:0] dm_tdqs,output tdqs_n); endmodule
'''
    path=folder/'setup_functional_stub.sv'; path.write_text(header+body,encoding='utf-8')
    return path


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args,cwd,log,timeout=180):
    started=time.monotonic()
    with log.open('w',encoding='utf-8') as stream:
        p=subprocess.Popen(list(map(str,args)),cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        try: p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Terminate only this command's process tree, including ModelSim kernel.
            subprocess.run(['taskkill.exe','/PID',str(p.pid),'/T','/F'],capture_output=True)
            raise RuntimeError(f'command timeout ({timeout}s), log retained: {log}')
    output=log.read_text(encoding='utf-8',errors='replace')
    if p.returncode or re.search(r'\*\* (?:Error|Fatal):|RESULT: FAIL',output):
        raise RuntimeError(f'{log}: exit={p.returncode}\n{output[-2500:]}')
    return output,round(time.monotonic()-started,3)


def compile_design(folder,engine,oracle=False):
    work=folder/'work'
    command([MS/'vlib.exe',work],folder,folder/'vlib.log')
    if oracle:
        sources=[HERE/'perf_monitor.sv',HERE/'tb_monitor_oracle.sv']
    else:
        sources=[ROOT/'myriscv'/(n+'.v') for n in RTL]+[ROOT/'sim/coremark/bram.v',HERE/'perf_monitor.sv',HERE/'tb_performance.sv']
        if engine.startswith('physical'):
            factory=ROOT/'ipcore/ddr3/sim/modelsim'
            command([MS/'vlog.exe','-work',work,*LIB.joinpath('modelsim10.2c/adc_e2_source_codes').glob('*.vp')],folder,folder/'vendor_primitives.log')
            command([MS/'vlog.exe','-sv','-work',work,'-mfcu','-incr','-suppress','2902',
                '-f','sim_file_list.f','-y',LIB,'+libext+.v','+incdir+../../example_design/bench/mem/'],
                factory,folder/'vendor_ip_compile.log')
            model=ROOT/'ipcore/ddr3/example_design/bench/mem/ddr3.v'
            text=model.read_text()
            text,n=re.subn(r'\bmodule\s+ddr3\b','module ddr3_mem',text,count=1)
            if n!=1: raise ValueError('unexpected vendor physical model module')
            derived=folder/'ddr3_mem.v'; derived.write_text(text)
            command([MS/'vlog.exe','-sv','-work',work,'+define+den4096Mb','+define+x16','+define+sg25E',
                f'+incdir+{model.parent.as_posix()}',derived],factory,folder/'physical_model_compile.log')
            sources += [ROOT/'myriscv/soc_ddr3_top.v']
            if engine=='physical': sources += [setup_wrapper(folder)]
        elif engine=='setup-functional':
            sources += [ROOT/'sim/coremark/ddr_model.v',ROOT/'myriscv/soc_ddr3_top.v',
                        setup_wrapper(folder),setup_functional_stub(folder)]
        else: sources += [ROOT/'sim/coremark/ddr_model.v']
    args=[MS/'vlog.exe','-sv','-work',work,f'+incdir+{(ROOT/"myriscv").as_posix()}']
    if engine.startswith('physical') and not oracle:
        args += ['+define+PERF_PHYSICAL','-y',LIB,'+libext+.v']
        if engine=='physical': args += ['+define+PERF_DIRECT']
    if engine=='setup-functional': args += ['+define+PERF_PHYSICAL','+define+PERF_DIRECT']
    snapshot=folder/'source_snapshot'; snapshot.mkdir()
    inputs=[*sources,HERE/'run.py',HERE/'analyze.py',ROOT/'tests/cpu_performance/build.py']
    if engine.startswith('physical') and not oracle:
        inputs += [model,model.parent/'ddr3_parameters.vh',factory/'sim_file_list.f']
    manifest={}
    for source in inputs:
        rel=source.relative_to(ROOT)
        dest=snapshot/rel; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(source.read_bytes())
        manifest[rel.as_posix()]=sha(source)
    (snapshot/'sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    output,_=command([*args,*sources],folder,folder/'compile.log')
    if 'Errors: 0' not in output: raise RuntimeError('compiler did not confirm Errors: 0')
    return work


def simulate(folder,work,top,plus,timeout):
    output,wall=command([MS/'vsim.exe','-c','-sva','-suppress','3486,3680,3781','+nowarn1',
        '-lib',work,top,f'+OUT={folder.as_posix()}',*plus,'-do','run -all; quit -f'],
        folder,folder/'simulation.log',timeout)
    if 'RESULT: PASS' not in output: raise RuntimeError('missing simulation PASS')
    if re.search(r'\bERROR:',output) or 'Errors: 0' not in output:
        raise RuntimeError(f'physical/model ERROR or missing Errors: 0: {folder}')
    return wall


def oracle(folder):
    # Priority intersections, old response/new acceptance, boundary requests,
    # MRET retirement, dropped response, and 64-bit carry are all explicit.
    names='start stop retire mret redirect hold mem load branch fetch delivered ireq iready irsp drop dreq dready drsp bi bd contention ar aw r w'.split()
    event_sets=[['ireq','iready'],
        ['start','retire','redirect','mem','branch','irsp','ireq','iready','ar','r'],
        ['retire','mem','hold'], ['hold','load','branch','fetch'],
        ['load','branch','fetch'], ['branch','fetch'], ['mem','ireq','contention'],
        ['fetch'], ['delivered'], ['fetch','mret'],
        ['retire','fetch','irsp','drop','ireq','iready','dreq','dready','aw','w','bd'],
        ['drsp'], ['stop','retire','irsp'], ['start'], [], [], ['stop']]
    states=[0,1,2,2,2,2,2,2,5,0,3,5,0,0,0,0,0]
    events=[]
    for i,(enabled,state) in enumerate(zip(event_sets,states)):
        bits=sum(1<<names.index(n) for n in enabled) | state<<25
        if i>=13: bits|=1<<32
        events.append(bits)
    (folder/'events.dat').write_text(''.join(f'{e:016x}\n' for e in events+[0]*(64-len(events))))
    work=compile_design(folder,'functional',oracle=True)
    wall=simulate(folder,work,'tb_monitor_oracle',[f'+EVENTS={(folder/"events.dat").as_posix()}',f'+EVENT_COUNT={len(events)}'],60)
    m=metrics(folder)
    for window in m.values(): check_partition(window)
    expected={'cycles':11,'instret':4,'control_redirect_cycles':1,'mem_stall_cycles':2,
        'control_hold_cycles':1,'load_use_cycles':1,'branch_flush_cycles':2,
        'if_stall_cycles':2,'other_cycles':2,'branch_redirects':4,
        'if_requests':2,'if_responses':2,'data_requests':1,'data_responses':1,
        'ddr_transactions':2,'ddr_ar_commands':1,'ddr_aw_commands':1,
        'ddr_r_beats':1,'ddr_w_beats':1,'if_dropped_responses':1,
        'pending_0_start':1,'pending_0_end':1,'pending_1_start':0,'pending_1_end':0}
    for key,value in expected.items():
        assert m[1][key]==value,(key,m[1][key],value)
    assert m[2]['cycles']==2**32+1 and m[2]['other_cycles']==2**32+1
    # Latencies are measured across boundaries, including turnover at the same edge.
    import csv
    hist={(int(r['channel']),int(r['latency_cycles'])):int(r['count'])
          for r in csv.DictReader((folder/'latency.csv').open()) if r['window']=='1'}
    assert hist=={(0,1):1,(0,9):1,(1,1):1},hist
    rejected=[]
    for name,sequence,message in [
        ('extra_response',[1<<13],'response without pending'),
        ('duplicate_request',[(1<<11)|(1<<12)]*2,'two outstanding requests'),
        ('stop_without_start',[1<<1],'stop without monitor window')]:
        bad=folder/name; bad.mkdir()
        (bad/'events.dat').write_text(''.join(f'{e:016x}\n' for e in sequence+[0]*(64-len(sequence))))
        try:
            simulate(bad,work,'tb_monitor_oracle',[f'+EVENTS={(bad/"events.dat").as_posix()}',f'+EVENT_COUNT={len(sequence)}'],60)
        except RuntimeError:
            assert message in (bad/'simulation.log').read_text(),name
            rejected.append(name)
        else: raise AssertionError(f'negative oracle accepted: {name}')
    result=dict(status='PASS',checks=list(expected)+['same_edge_turnover','latency_boundary','64_bit_carry'],
                correctly_rejected=rejected,wall_seconds=wall)
    (folder/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def prepare(folder,kind,micro_build):
    build_mod=module(ROOT/'tests/cpu_performance/build.py','micro_build')
    if kind=='micro':
        source=micro_build
        info=json.loads((source/'manifest.json').read_text())
        for name,digest in info['sha256'].items(): assert sha(source/name)==digest
        info['bin_path']=str(source/'program.bin')
        rom=source/'boot_rom.dat'; dat=source/'data_ram.dat'
        markers=[]
        for case in info['cases']: markers += [case['id'],case['start'],case['stop']]
        (folder/'markers.dat').write_text(''.join(f'{x:08x}\n' for x in markers+[0]*(48-len(markers))))
        plus=[f'+MICRO=1',f'+MARKERS={(folder/"markers.dat").as_posix()}',f'+WINDOWS={len(info["cases"])}']
    else:
        mode=kind.removesuffix('_1')
        source=ROOT/'tests/bsp_workflow/build'/kind
        app=module(ROOT/'tools/uart_loader/candidates/bsp_workflow/application.py','application')
        original=app.require_manifest(source/'manifest.json')
        raw=(source/'program.bin').read_bytes(); padded=raw+bytes((-len(raw))%4)
        words=list(struct.unpack('<'+'I'*(len(padded)//4),padded)); words += [0]*(4096-len(words)); words[4092]=len(padded)//4
        dat=folder/'data_ram.dat'; dat.write_text(''.join(f'{w:08x}\n' for w in words))
        rom=micro_build/'boot_rom.dat'
        info=dict(kind='coremark',original=original,done=original['symbols']['program_return'],
            cases=[dict(id=1,name=kind,units=1,unit='iteration')],sha256=original)
        plus=['+MICRO=0',f'+START_FN={original["symbols"]["start_time"]:x}',f'+STOP_FN={original["symbols"]["stop_time"]:x}']
    plus += [f'+ROM={rom.as_posix()}',f'+DAT={dat.as_posix()}',f'+DONE={info["done"]:x}']
    info['simulation_boot']='isolated CPU RAM-to-DDR copy loader; not production UART download protocol'
    info['simulation_input_sha256']={str(p):sha(p) for p in [rom,dat]}
    (folder/'input_manifest.json').write_text(json.dumps(info,indent=2)+'\n')
    return info,plus


def run(args):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',args.tag): raise ValueError('invalid tag')
    out=HERE/'build'/args.tag; out.mkdir(parents=True,exist_ok=False)
    protected=[*ROOT.joinpath('myriscv').glob('*.v'),ROOT/'RISCV.pds',
        *ROOT.joinpath('ipcore/inst_rom').rglob('*.v'),*ROOT.joinpath('ipcore/data_ram').rglob('*.v'),
        ROOT/'ipcore/inst_rom/inst_rom.idf',ROOT/'ipcore/data_ram/data_ram.idf',
        ROOT/'generate_bitstream/board_top.sbit',*ROOT.joinpath('tests/bsp_workflow/build').glob('*/program.bin'),
        *ROOT.joinpath('coremark-main').glob('core*.c'),ROOT/'coremark-main/coremark.h',ROOT/'coremark-main/coremark.md5']
    before={p.relative_to(ROOT).as_posix():sha(p) for p in protected if p.is_file()}
    (out/'protected_before.json').write_text(json.dumps(before,indent=2)+'\n')
    result={}
    try:
        if args.suite=='oracle': result['oracle']=oracle(out)
        else:
            micro=Path(args.micro_build).resolve() if args.micro_build else ROOT/'tests/cpu_performance/build'/args.tag
            if not micro.exists(): micro=module(ROOT/'tests/cpu_performance/build.py','micro_builder').build(args.tag)
            compile_folder=out/'compile'; compile_folder.mkdir()
            work=compile_design(compile_folder,args.engine)
            kinds=['micro'] if args.suite=='micro' else ['performance_1','validation_1'] if args.suite=='coremark' else ['micro','performance_1','validation_1']
            for kind in kinds:
                folder=out/kind; folder.mkdir()
                info,plus=prepare(folder,kind,micro)
                if args.engine in ('physical','setup-functional'):
                    info['simulation_boot']=('simulation-only 128-bit Pango port setup; full physical DDR write/readback; CPU starts from DDR after reset release'
                        if args.engine=='physical' else 'setup-harness functional test with delayed user-port model; no real IP/PHY/physical DDR')
                    (folder/'input_manifest.json').write_text(json.dumps(info,indent=2)+'\n')
                print(f'START {args.engine} {kind}',flush=True)
                if args.timer_wrap:
                    if args.engine!='functional' or kind!='micro': raise ValueError('timer wrap is a functional micro oracle only')
                    plus += ['+TIMER_WRAP']
                wall=simulate(folder,work,'tb_performance',[*plus,f'+MAX_CYCLES={args.max_cycles}'],args.timeout)
                summary=summarize(folder,info,args.engine); summary['wall_seconds']=wall
                if kind!='micro':
                    app=module(ROOT/'tools/uart_loader/candidates/bsp_workflow/application.py','coremark_output')
                    summary['crc']=app.parse_output(info['original'],(folder/'uart.txt').read_bytes())
                    assert summary['crc']['ticks']==summary['windows'][0]['cycles']
                (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
                result[kind]=summary
                print(f'PASS {kind} wall={wall}s windows={len(summary["windows"])}',flush=True)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:
        after={p:sha(ROOT/p) for p in before}
        (out/'protected_after.json').write_text(json.dumps(after,indent=2)+'\n')
        assert before==after,'protected RTL/IP/PDS/BIN/bitstream changed'
    print(f'RESULT: PASS {out}',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--tag',required=True)
    parser.add_argument('--suite',choices=['oracle','micro','coremark','all'],default='micro')
    parser.add_argument('--engine',choices=['physical','physical-copy','functional','setup-functional'],default='physical')
    parser.add_argument('--micro-build')
    parser.add_argument('--timeout',type=int,default=2400)
    parser.add_argument('--max-cycles',type=int,default=60000000)
    parser.add_argument('--timer-wrap',action='store_true')
    run(parser.parse_args())
