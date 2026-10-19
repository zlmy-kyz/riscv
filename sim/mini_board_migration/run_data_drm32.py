"""Task020: one targeted real I32/D32 DRM bridge simulation; no PDS/board operations."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from resume_inst_cache32 import project_configuration, pds_shell_count, command, git_snapshot

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MS=Path('D:/modelsim/win64pe')
VENDOR=Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
MANIFEST=HERE/'data_drm32_inputs.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def planned_counts():
    source=(HERE/'tb_data_drm32_x32.sv').read_text(encoding='utf-8')
    weights={n:1 for n in ['fetch','load_word','store_word','cached_contention',
                            'sync_hit_address_change','sync_data_address_change']}
    for name in ['queued_inst_fill','queued_data_fill','reset_during_hit','reset_during_data_hit']:
        body=re.search(r'task automatic '+name+r'\b(.*?)endtask',source,re.S)[1]
        weights[name]=len(re.findall(r'\b(?:fetch|load_word|store_word)\(',body))+len(re.findall(r'tests=tests\+1;',body))
    loop=re.compile(r'for\s*\(\s*(\w+)=0;\s*\1<([^;]+);\s*\1=\1\+1\s*\)\s*begin')
    def count(text):
        match=loop.search(text)
        if not match:
            return sum(weights[n] for n in re.findall(r'\b('+'|'.join(weights)+r')\(',text)) + \
                   len(re.findall(r'tests=tests\+1;',text))
        depth=1
        for token in re.finditer(r'\b(begin|end)\b',text[match.end():]):
            depth+=1 if token[1]=='begin' else -1
            if depth==0:
                start,stop=match.end()+token.start(),match.end()+token.end()
                break
        else: raise ValueError('Unbalanced loop')
        bound=match[2].strip()
        n=32 if bound in ['I_LINES','D_LINES'] else int(bound)
        return count(text[:match.start()])+n*count(text[match.end():start])+count(text[stop:])
    main=source[source.index('    initial begin : run_tests'):]
    parts=re.split(r'\$display\("CHECK: (\S+) PASS"\);',main)
    assert len(parts)==17
    rows=[dict(group=parts[i+1],checks=count(parts[i])) for i in range(0,16,2)]
    assert [r['checks'] for r in rows]==[325,83,143,75,320,259,294,22]
    assert sum(r['checks'] for r in rows)==1521
    return rows


def review_rtl(m):
    old=(ROOT/m['baseline_bridge']).read_text(encoding='utf-8')
    new=(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v').read_text(encoding='utf-8')
    restored=new.replace('//   * 指令缓存和数据读缓冲均为 32 行直接映射。',
                         '//   * 指令缓存为 32 行直接映射，数据读缓冲为 16 行直接映射。')
    restored=restored.replace('//   * x32 I/D 数据分别用 icache/dcache DRM 同步读，tag/valid 仍在逻辑中。\n'
        '//     x16 保留数组实现；x32 I32/D32 各为 1 KiB。',
        '//   * x32 指令数据用 icache DRM 同步读，tag/valid 仍在逻辑中；x16 保留原数组。')
    restored=restored.replace('    reg        response_from_data_drm;\n','')
    restored=restored.replace('    // 32 行数据读缓冲','    // 16 行数据读缓冲')
    restored=restored.replace('reg [31:0]  data_line_valid;','reg [15:0]  data_line_valid;')
    restored=restored.replace('data_line_tag [0:31];','data_line_tag [0:15];')
    restored=restored.replace('    wire [31:0] data_drm_rdata;\n    wire [31:0] data_legacy_rdata;',
                            '    reg [8*MEM_DQ_WIDTH-1:0] data_line_data [0:15];')
    restored=restored.replace('wire [4:0]  data_read_line_index;','wire [3:0]  data_read_line_index;')
    restored=restored.replace('wire [4:0]  data_fill_line_index;','wire [3:0]  data_fill_line_index;')
    restored=restored.replace('assign data_read_line_index = data_req_addr[BEAT_ADDR_BITS+4:BEAT_ADDR_BITS];',
        'assign data_read_line_index = data_req_addr[BEAT_ADDR_BITS+3:BEAT_ADDR_BITS];')
    restored=restored.replace('assign data_fill_line_index = request_line_tag[4:0];',
                             'assign data_fill_line_index = request_line_tag[3:0];')
    a=restored.index('    generate\n',restored.index('    assign data_line_fill ='))
    b=restored.index('    endgenerate\n',a)+len('    endgenerate\n')
    restored=restored[:a]+restored[b+1:]
    restored=restored.replace("data_line_valid <= 32'b0;","data_line_valid <= 16'b0;")
    restored=restored.replace('reset_data_line < 32;','reset_data_line < 16;')
    restored=restored.replace("                data_line_tag[reset_data_line]  <= {TAG_BITS{1'b0}};\n",
        "                data_line_tag[reset_data_line]  <= {TAG_BITS{1'b0}};\n"
        "                data_line_data[reset_data_line] <= {(8*MEM_DQ_WIDTH){1'b0}};\n")
    restored=restored.replace('            data_line_tag[data_fill_line_index]   <= request_line_tag;\n',
        '            data_line_tag[data_fill_line_index]   <= request_line_tag;\n'
        '            data_line_data[data_fill_line_index]  <= axi_rdata;\n')
    restored=restored.replace('    assign data_rsp_rdata = response_from_data_drm ? data_drm_rdata : response_rdata;',
                             '    assign data_rsp_rdata = response_rdata;')
    restored=re.sub(r'^\s*response_from_data_drm <= .*;\n','',restored,flags=re.M)
    restored=restored.replace('                            response_rdata <= data_legacy_rdata;',
        '                            response_rdata <=\n'
        '                                data_line_data[data_read_line_index][data_req_addr[BEAT_ADDR_BITS-1:2] * 32 +: 32];')
    assert restored==old,'Unexpected change beyond D32 data/IP/response; I/DDR/priority must remain'
    for text in [".wr_addr({1'b0, data_fill_line_index})",'.wr_en(resetn && ddr_init_done && data_line_fill)',
                 ".rd_addr({1'b0, data_req_addr[9:2]})",'data_line_tag [0:31];']:
        assert text in new,text


def require_inputs():
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name,digest in m['sha256'].items(): assert sha(ROOT/name)==digest,'Changed input: '+name
    for name,digest in m['vendor_sha256'].items(): assert sha(Path(name))==digest,name
    config=project_configuration((ROOT/'RISCV.pds').read_text(encoding='utf-8'))
    assert hashlib.sha256(config.encode()).hexdigest()==m['project_configuration_sha256']
    for name in ['icache','dcache']:
        assert config.count(f'(_ip "ipcore/{name}/{name}.idf"')==1
        root=ET.parse(ROOT/f'ipcore/{name}/{name}.idf').getroot()
        params={r.findtext('name'):r.findtext('value') for r in root.findall('./param_list/param')}
        assert all(params[k]==v for k,v in m['ip_configuration'].items()),name
        assert root.findtext('./header/device')=='PG2L200H' and root.findtext('./header/instance')==name
    assert planned_counts()==m['unit_plan'] and m['expected_checks']==1521
    review_rtl(m)
    old=(HERE/'tb_inst_drm_x32.sv').read_text(encoding='utf-8')
    new=(HERE/'tb_data_drm32_x32.sv').read_text(encoding='utf-8')
    a,b='    assign rrdy=','    task automatic transfer('
    assert old[old.index(a):old.index(b)]==new[new.index(a):new.index(b)],'DDR model changed'
    a,b='    task automatic transfer(','    task automatic queued_data_fill;'
    assert old[old.index(a):old.index(b)]==new[new.index(a):new.index(b)],'Protocol/latency oracle changed'
    return m


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag');parser.add_argument('--check-inputs',action='store_true')
    args=parser.parse_args();m=require_inputs()
    if args.check_inputs:
        print('INPUTS_MATCH_NOT_SIMULATED',len(m['sha256']),'vendor=2 checks=1521 ISA=0');return
    assert args.tag and re.fullmatch(r'[A-Za-z0-9_-]+',args.tag)
    assert pds_shell_count()==0,'User PDS running; stop before HDL'
    out=HERE/'build'/args.tag;out.mkdir(parents=True,exist_ok=False)
    before=git_snapshot();manifest_sha=sha(MANIFEST)
    (out/'git_before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
    result=dict(status='RUNNING',input_manifest_sha256=manifest_sha,isa_cases=[],pds_started=False,
                serial_opened=False,formal_board='NOT_TESTED',model_scope='Real I/D DRM + functional DDR user-port')
    try:
        work=out/'work';command([MS/'vlib.exe',work],out,out/'vlib')
        ip_sources=[ROOT/f'ipcore/{n}/rtl/ipm2l_sdpram_v1_10_{n}.v' for n in ['icache','dcache']]+\
                   [ROOT/f'ipcore/{n}/{n}.v' for n in ['icache','dcache']]
        sources=[VENDOR/'GTP_GRS.v',VENDOR/'GTP_DRM36K_E1.v',*ip_sources,
                 ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v',HERE/'tb_data_drm32_x32.sv']
        log=command([MS/'vlog.exe','-sv','-work',work,*sources],out,out/'compile')
        assert 'Errors: 0' in log and not re.search(r'\bERROR:',log)
        log=command([MS/'vsim.exe','-c','-lib',work,'tb_data_drm32_x32','-do','run -all; quit -f'],out,out/'simulation')
        assert 'Errors: 0' in log and not re.search(r'\bERROR:',log)
        assert re.findall(r'RESULT: PASS data_drm32_x32 tests=(\d+)',log)==['1521']
        groups=re.findall(r'CHECK: (\S+) PASS',log)
        assert groups==[r['group'] for r in m['unit_plan']]
        assert re.findall(r'IPSpecCheck: (\d+)',log)==['04030130','04030130']
        assert require_inputs()==m and sha(MANIFEST)==manifest_sha
        after=git_snapshot();(out/'git_after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf-8')
        assert after==before,'Worktree changed during execution'
        for src in [*sources[2:],Path(__file__),MANIFEST]: shutil.copy2(src,out/src.name)
        result.update(status='MINI_DATA_DRM32_KEY_TEST_PASS',checks=1521,check_groups=groups,
                      inputs_unchanged=True,git_snapshots_identical=True,ip_spec_diagnostics=['04030130','04030130'])
        print('RESULT: PASS',out,'checks=1521 ISA=0')
    except Exception as exc:
        result.update(status='FAIL',error=f'{type(exc).__name__}: {exc}');raise
    finally: (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': main()
