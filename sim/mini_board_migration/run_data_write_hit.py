"""Task025: one x32 write-hit group on real I/D DRM, no PDS or serial."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from resume_inst_drm64 import command
from resume_inst_cache32 import pds_shell_count, git_snapshot

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
MS=Path('D:/modelsim/win64pe')
VENDOR=Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
MANIFEST=HERE/'data_write_hit_inputs.json'
TAG='ds_mini_data_write_hit_20261013_a'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:Path(p).read_text(encoding='utf-8',errors='replace')
write=lambda p,x:Path(p).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')


def require_inputs():
    m=json.loads(read(MANIFEST))
    for n,h in m['sha256'].items(): assert sha(ROOT/n)==h,n
    for n,h in m['external_sha256'].items(): assert sha(n)==h,n
    assert m['expected_checks']==945 and m['cpu_changed'] is False
    ip=ET.parse(ROOT/'ipcore/dcache/dcache.idf')
    values={p.findtext('name'):p.findtext('value') for p in ip.findall('./param_list/param')}
    for k,v in m['dcache_parameters'].items(): assert values[k]==v,k
    assert ip.findtext('./header/device')=='PG2L200H'
    old=read(HERE/'tb_data_drm64_x32.sv')
    prefix=old[:old.index('    task automatic queued_inst_fill')].replace('module tb_data_drm64_x32;','module tb_data_write_hit_x32;')
    prefix=prefix.replace('            if (data_port) dv=0; else iv=0;',
        "            if (data_port) begin dv=0;da='hfe4;wd=32'hdeadbeef;ws=0;dw=0;end\n            else begin iv=0;ia='hfd0;end")
    tb=read(HERE/'tb_data_write_hit_x32.sv')
    assert tb.startswith(prefix),'Existing DDR model/transfer changed beyond post-accept request-wire poison'
    assert re.findall(r'CHECK: (\S+) PASS',tb)==[g['name'] for g in m['groups']]
    assert [g['checks'] for g in m['groups']]==[64*8,8*16*3,8,4*4,12,3*3,4]
    assert sum(g['checks'] for g in m['groups'])==945
    assert tb.count('wr_byte_en')>=2 and 'backend_write && pending_store && pending_hit' in tb
    bridge=read(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v')
    assert ".wr_byte_en(data_line_fill ? 32'hffff_ffff : axi_wstrb)" in bridge
    assert '((state == STATE_WADDR) && axi_awready && axi_wready)' in bridge
    assert '((state == STATE_WDATA) && axi_wready)' in bridge
    baseline=read(ROOT/m['baseline_bridge'])
    # The shared arbitration, state transitions and external AXI-like wiring are unchanged.
    controller=lambda s:s[s.index('    always @(posedge clk) begin\n        if (!resetn) begin\n            state'):s.index('    // 首版不根据')]
    current=controller(bridge)
    rows=current.splitlines(keepends=True)
    for line in ['            request_data_write_hit <= 1\'b0;\n',
                 '                        request_data_write_hit <= data_line_write_hit;\n',
                 '                        request_data_write_hit <= 1\'b0;\n']:
        assert rows.count(line)==1;rows.remove(line)
    current=''.join(rows)
    assert current==controller(baseline),'DDR controller transitions changed'
    for a,b in [('    assign idle_ready','    assign data_line_index'),
                ('    assign selected_addr','    always @(posedge clk) begin\n        if (!resetn) begin\n            state')]:
        assert bridge[bridge.index(a):bridge.index(b,bridge.index(a))]==baseline[baseline.index(a):baseline.index(b,baseline.index(a))]
    assert '.DDR_MEM_DQ_WIDTH(32)' in read(ROOT/'myriscv/soc_ddr3_top.v')
    assert '.MEM_DQ_WIDTH(DDR_MEM_DQ_WIDTH)' in read(ROOT/'myriscv/soc_top.v')
    ast.parse(read(Path(__file__)))
    return m


def check_evidence(folder,m):
    console=read(folder/'simulation.log');transcript=read(folder/'transcript')
    assert console.replace('\r\n','\n').strip()==transcript.replace('\r\n','\n').strip()
    for text in [console,transcript]:
        assert '$finish' in text and 'Errors: 0, Warnings: 0' in text
        assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT',text)
        assert re.findall(r'IPSpecCheck: (\d+)',text)==['04030130','04030130']
        assert re.findall(r'CHECK: (\S+) PASS',text)==[g['name'] for g in m['groups']]
    rows=re.findall(r'RESULT: PASS data_write_hit_x32 tests=(\d+) fills=(\d+) updates=(\d+)',console)
    assert len(rows)==1 and int(rows[0][0])==945 and all(int(v)>0 for v in rows[0][1:])
    return dict(tests=int(rows[0][0]),fills=int(rows[0][1]),updates=int(rows[0][2]))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check-inputs',action='store_true');p.add_argument('--tag')
    a=p.parse_args();m=require_inputs()
    if a.check_inputs:
        print('INPUTS_MATCH_WRITE_HIT_NOT_SIMULATED checks=945 groups=7 real I/D DRM; CPU/DDR controller unchanged');return
    assert a.tag==TAG and pds_shell_count()==0
    out=HERE/'build'/TAG;out.mkdir(parents=True,exist_ok=False);work=out/'work'
    before=git_snapshot();write(out/'git_before.json',before)
    result=dict(status='RUNNING',expected_checks=945,manifest_sha256=sha(MANIFEST),
                CPU_changed=False,PDS_started=False,serial_opened=False,board='NOT_RUN',scope='Real I/D DRM and x32 bridge only')
    write(out/'result.json',result)
    try:
        shutil.copyfile(MANIFEST,out/'inputs.json')
        for n in m['snapshot_files']:
            dest=out/'inputs'/n;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/n,dest);assert sha(dest)==m['sha256'][n]
        command([MS/'vlib.exe',work],out,out/'vlib',60)
        sources=[VENDOR/'GTP_GRS.v',VENDOR/'GTP_DRM36K_E1.v',
                 *[ROOT/n for n in m['compile_sources']]]
        log=command([MS/'vlog.exe','-sv','-work',work,*sources],out,out/'compile',60)
        assert 'Errors: 0, Warnings: 0' in log
        command([MS/'vsim.exe','-batch','-lib',work,'tb_data_write_hit_x32','-logfile',out/'transcript',
                 '-do','run -all; quit -f'],out,out/'simulation',180)
        counts=check_evidence(out,m)
        assert require_inputs()==m
        after=git_snapshot();write(out/'git_after.json',after);assert after==before
        result.update(status='DATA_WRITE_HIT_KEY_TEST_PASS',functional_status='PASS',**counts,
                      inputs_unchanged=True,git_unchanged=True,groups=m['groups'])
        print('RESULT: PASS data_write_hit key group; board/timing NOT_RUN')
    except Exception as exc:
        result.update(status='STOPPED_FIRST_FAILURE',error=f'{type(exc).__name__}: {exc}');raise
    finally:
        if not (out/'git_after.json').exists():write(out/'git_after.json',git_snapshot())
        write(out/'result.json',result)


if __name__=='__main__':main()
