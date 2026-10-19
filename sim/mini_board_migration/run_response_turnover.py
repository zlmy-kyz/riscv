"""Task026: one manual+real-CPU x32 bridge suite; DeepSeek executes HDL."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import shutil
from resume_inst_drm64 import command
from resume_inst_cache32 import pds_shell_count,git_snapshot
from generate_response_turnover_tb import build_tb

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
MS=Path('D:/modelsim/win64pe')
VENDOR=Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
MANIFEST=HERE/'response_turnover_inputs.json'
TAG='ds_mini_response_turnover_20261013_a'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:Path(p).read_text(encoding='utf-8',errors='replace')
write=lambda p,x:Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def require_inputs():
    m=json.loads(read(MANIFEST))
    for n,h in m['sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in m['external_sha256'].items():assert sha(n)==h,n
    assert m['expected_checks']==1832 and not m['cpu_changed']
    assert m['timeouts']=={'vlib':60,'compile':60,'simulation':180}
    assert read(HERE/'tb_response_turnover_x32.sv')==build_tb()
    cases=read(HERE/'response_turnover_cases.svh')
    assert re.findall(r'checkpoint\("(\w+)",(\d+)\)',cases)==[(g['name'],str(g['checks'])) for g in m['groups']]
    assert sum(g['checks'] for g in m['groups'])==1832
    assert len(read(ROOT/m['cpu_image']).splitlines())==15
    current=read(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v')
    baseline=read(ROOT/m['baseline_bridge'])
    # Exact authorized patch: only readiness and the response/accept state block.
    transformed=baseline.replace('//     x16 保留原数组和写命中失效策略。\n',
        '//     x16 保留原数组和写命中失效策略。\n'
        '//   * 旧响应周期可同时接受下一请求；同步 DRM 输出在接受边沿后才更新，\n'
        '//     CPU 在该边沿仍消费旧响应。没有下一请求时回到 IDLE。\n')
    transformed=transformed.replace('    assign idle_ready = (state == STATE_IDLE) && ddr_init_done;',
        '    // RSP 表示旧 DDR 事务已完成，可在旧响应消费边沿交接下一请求。\n'
        '    // ready 不依赖 rsp 消费反馈；I/D 仍共用一个事务槽，数据仍优先。\n'
        '    assign idle_ready = ((state == STATE_IDLE) || (state == STATE_RSP)) && ddr_init_done;')
    transformed=transformed.replace('                STATE_IDLE: begin\n',
        "                STATE_IDLE, STATE_RSP: begin\n"
        "                    // 默认清旧响应来源；若接受新命中，下方重新置位。\n"
        "                    response_from_inst_drm <= 1'b0;\n"
        "                    response_from_data_drm <= 1'b0;\n"
        "                    state <= STATE_IDLE;\n")
    transformed=transformed.replace("                STATE_RSP: begin\n"
        "                    response_from_inst_drm <= 1'b0;\n"
        "                    response_from_data_drm <= 1'b0;\n"
        "                    state <= STATE_IDLE;\n                end\n\n",'')
    assert transformed==current,'Unexpected design change beyond RSP turnover'
    for n in m['snapshot_files']:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    return m


def compile_argv(out,m):
    return [MS/'vlog.exe','-sv','+incdir+'+str(ROOT/'myriscv'),'+incdir+'+str(HERE),'-work',out/'work',
            *[VENDOR/n for n in m['vendor_compile_sources']],*[ROOT/n for n in m['compile_sources']]]


def simulation_argv(out,m):
    return [MS/'vsim.exe','-batch','-lib',out/'work','tb_response_turnover_x32',
            '+CPU_IMAGE='+str(ROOT/m['cpu_image']),'-logfile',out/'transcript','-do','run -all; quit -f']


def check_evidence(folder,m):
    console=read(folder/'simulation.log');transcript=read(folder/'transcript')
    assert console.strip()==transcript.strip()
    for text in (console,transcript):
        assert '$finish' in text and 'Errors: 0, Warnings: 0' in text
        assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT',text)
        assert re.findall(r'IPSpecCheck: (\d+)',text)==['04030130','04030130']
        assert re.findall(r'CHECK: (\w+) PASS checks=(\d+)',text)==[(g['name'],str(g['checks'])) for g in m['groups']]
    rows=re.findall(r'RESULT: PASS response_turnover_x32 tests=(\d+) cpu_events=(\d+) turnovers=(\d+) I_TURN=(\d+) D_TURN=(\d+) CPU_TURN=(\d+) fills=(\d+) updates=(\d+)',console)
    assert len(rows)==1 and rows[0][:2]==('1832','392') and all(int(v)>0 for v in rows[0][2:])
    assert rows[0][-2:]==('71','97')
    return dict(zip(('tests','cpu_events','turnovers','I_TURN','D_TURN','CPU_TURN','fills','updates'),map(int,rows[0])))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check-inputs',action='store_true');p.add_argument('--tag')
    a=p.parse_args();m=require_inputs()
    if a.check_inputs:
        print('INPUTS_MATCH_RESPONSE_TURNOVER_HDL_NOT_RUN tests=1832 cpu_events=392 groups=7');return
    assert a.tag==TAG and pds_shell_count()==0
    out=HERE/'build'/TAG;out.mkdir(parents=True,exist_ok=False)
    before=git_snapshot();write(out/'git_before.json',before)
    result=dict(status='RUNNING',manifest_sha256=sha(MANIFEST),expected_checks=1832,CPU_changed=False,
                PDS_started=False,serial_opened=False,scope=m['scope'])
    write(out/'result.json',result)
    try:
        shutil.copyfile(MANIFEST,out/'inputs.json')
        for n in m['snapshot_files']:
            dest=out/'inputs'/n;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/n,dest);assert sha(dest)==m['sha256'][n]
        command([MS/'vlib.exe',out/'work'],out,out/'vlib',60)
        log=command(compile_argv(out,m),out,out/'compile',60)
        assert 'Errors: 0, Warnings: 0' in log
        command(simulation_argv(out,m),out,out/'simulation',180)
        counts=check_evidence(out,m)
        assert require_inputs()==m
        after=git_snapshot();write(out/'git_after.json',after);assert before==after
        result.update(status='RESPONSE_TURNOVER_KEY_TEST_PASS',functional_status='PASS',**counts,
                      inputs_unchanged=True,git_unchanged=True,groups=m['groups'])
        print('RESULT: PASS response turnover key suite; board performance NOT_RUN')
    except Exception as exc:
        result.update(status='STOPPED_FIRST_FAILURE',error=f'{type(exc).__name__}: {exc}');raise
    finally:
        write(out/'result.json',result)


if __name__=='__main__':main()
