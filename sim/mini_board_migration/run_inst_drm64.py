"""Task021: one I64/D32 targeted real-DRM test; no CPU/PHY/PDS/serial operations."""
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
MANIFEST=HERE/'inst_drm64_inputs.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def project_identity(text):
    tokens=re.findall(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()]+',project_configuration(text))
    return hashlib.sha256(json.dumps(tokens,separators=(',',':')).encode()).hexdigest()


def i64_transform(old):
    changes={
        '//   * 指令缓存和数据读缓冲均为 32 行直接映射。': '//   * 指令缓存为 64 行、数据读缓冲为 32 行直接映射。',
        '//     x16 保留数组实现；x32 I32/D32 各为 1 KiB。': '//     x16 保留数组实现；x32 I64 为 2 KiB、D32 为 1 KiB。',
        '// 32 行直接映射指令缓存': '// 64 行直接映射指令缓存',
        'reg [31:0]  inst_line_valid;': 'reg [63:0]  inst_line_valid;',
        'inst_line_tag [0:31];': 'inst_line_tag [0:63];',
        'wire [4:0]  inst_line_index;': 'wire [5:0]  inst_line_index;',
        'wire [4:0]  data_line_index;': 'wire [5:0]  data_line_index;',
        'wire [4:0]  fill_line_index;': 'wire [5:0]  fill_line_index;',
        'assign inst_line_index = inst_req_addr[BEAT_ADDR_BITS+4:BEAT_ADDR_BITS];':
            'assign inst_line_index = inst_req_addr[BEAT_ADDR_BITS+5:BEAT_ADDR_BITS];',
        'assign data_line_index = data_req_addr[BEAT_ADDR_BITS+4:BEAT_ADDR_BITS];':
            'assign data_line_index = data_req_addr[BEAT_ADDR_BITS+5:BEAT_ADDR_BITS];',
        'assign fill_line_index = request_line_tag[4:0];': 'assign fill_line_index = request_line_tag[5:0];',
        '// 仅使用低 32 行：写地址 0:index，读地址 0:index:word。':
            '// 使用全部 64 行：写地址 index[5:0]，读地址 index[5:0]:word[2:0]。',
        ".wr_addr({1'b0, fill_line_index})": '.wr_addr(fill_line_index)',
        ".rd_addr({1'b0, inst_req_addr[9:2]})": '.rd_addr(inst_req_addr[10:2])',
        'inst_line_data [0:31];': 'inst_line_data [0:63];',
        'reset_inst_data < 32;': 'reset_inst_data < 64;',
        "inst_line_valid <= 32'b0;": "inst_line_valid <= 64'b0;",
        'reset_line < 32;': 'reset_line < 64;',
    }
    for a,b in changes.items():
        assert a in old,a
        old=old.replace(a,b)
    return old


def planned_counts():
    source=(HERE/'tb_inst_drm64_x32.sv').read_text(encoding='utf-8')
    weights={n:1 for n in ['fetch','load_word','store_word','cached_contention',
                            'sync_hit_address_change','sync_data_address_change']}
    for name in ['queued_inst_fill','queued_data_fill','reset_during_hit','reset_during_data_hit']:
        body=re.search(r'task automatic '+name+r'\b(.*?)endtask',source,re.S)[1]
        weights[name]=len(re.findall(r'\b(?:fetch|load_word|store_word)\(',body))+len(re.findall(r'tests=tests\+1;',body))
    loop=re.compile(r'for\s*\(\s*(\w+)=0;\s*\1<([^;]+);\s*\1=\1\+1\s*\)\s*begin')
    def count(text):
        match=loop.search(text)
        if not match:
            return sum(weights[n] for n in re.findall(r'\b('+'|'.join(weights)+r')\(',text))+len(re.findall(r'tests=tests\+1;',text))
        depth=1
        for token in re.finditer(r'\b(begin|end)\b',text[match.end():]):
            depth+=1 if token[1]=='begin' else -1
            if depth==0:
                start,stop=match.end()+token.start(),match.end()+token.end();break
        else:raise ValueError('Unbalanced loop')
        bound=match[2].strip();n={'I_LINES':64,'D_LINES':32}[bound] if bound in ['I_LINES','D_LINES'] else int(bound)
        return count(text[:match.start()])+n*count(text[match.end():start])+count(text[stop:])
    main=source[source.index('    initial begin : run_tests'):]
    parts=re.split(r'\$display\("CHECK: (\S+) PASS"\);',main);assert len(parts)==17
    rows=[dict(group=parts[i+1],checks=count(parts[i])) for i in range(0,16,2)]
    assert [r['checks'] for r in rows]==[645,147,207,139,480,515,294,22]
    assert sum(r['checks'] for r in rows)==2449
    return rows


def require_inputs():
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name,digest in m['sha256'].items():assert sha(ROOT/name)==digest,'Changed input: '+name
    for name,digest in m['vendor_sha256'].items():assert sha(Path(name))==digest,name
    assert project_identity((ROOT/'RISCV.pds').read_text())==m['project_configuration_sha256']
    old=(ROOT/m['baseline_bridge']).read_text(encoding='utf-8')
    new=(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v').read_text(encoding='utf-8')
    assert new==i64_transform(old),'Unexpected change beyond I64 capacity/mapping/reset'
    for name in ['icache','dcache']:
        root=ET.parse(ROOT/f'ipcore/{name}/{name}.idf').getroot()
        params={r.findtext('name'):r.findtext('value') for r in root.findall('./param_list/param')}
        assert all(params[k]==v for k,v in m['ip_configuration'].items()),name
        assert root.findtext('./header/device')=='PG2L200H' and root.findtext('./header/instance')==name
    assert planned_counts()==m['unit_plan'] and m['expected_checks']==2449
    oldtb=(HERE/'tb_data_drm32_x32.sv').read_text(encoding='utf-8')
    newtb=(HERE/'tb_inst_drm64_x32.sv').read_text(encoding='utf-8')
    a,b='    assign rrdy=','    task automatic queued_inst_fill('
    assert oldtb[oldtb.index(a):oldtb.index(b)]==newtb[newtb.index(a):newtb.index(b)],'DDR model/transfer/latency oracle changed'
    a,b='    // D32 DRM accepted address','    initial begin : run_tests'
    assert oldtb[oldtb.index(a):oldtb.index(b)]==newtb[newtb.index(a):newtb.index(b)],'D32 task/monitor changed'
    a,b='        // D32: all rows/words','        conservation();\n        if (tests!='
    assert oldtb[oldtb.index(a):oldtb.index(b)]==newtb[newtb.index(a):newtb.index(b)],'D32 test sequence changed'
    return m


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag');parser.add_argument('--check-inputs',action='store_true')
    args=parser.parse_args();m=require_inputs()
    if args.check_inputs:
        print('INPUTS_MATCH_NOT_SIMULATED',len(m['sha256']),'vendor=2 checks=2449 ISA=0');return
    assert args.tag and re.fullmatch(r'[A-Za-z0-9_-]+',args.tag)
    assert pds_shell_count()==0,'User PDS running; stop before HDL'
    out=HERE/'build'/args.tag;out.mkdir(parents=True,exist_ok=False)
    before=git_snapshot();manifest_sha=sha(MANIFEST)
    (out/'git_before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
    result=dict(status='RUNNING',input_manifest_sha256=manifest_sha,isa_cases=[],pds_started=False,
                serial_opened=False,formal_board='NOT_TESTED',model_scope='Real I/D DRM + unchanged functional DDR user-port')
    try:
        work=out/'work';command([MS/'vlib.exe',work],out,out/'vlib')
        ip_sources=[ROOT/f'ipcore/{n}/rtl/ipm2l_sdpram_v1_10_{n}.v' for n in ['icache','dcache']]+\
                   [ROOT/f'ipcore/{n}/{n}.v' for n in ['icache','dcache']]
        sources=[VENDOR/'GTP_GRS.v',VENDOR/'GTP_DRM36K_E1.v',*ip_sources,
                 ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v',HERE/'tb_inst_drm64_x32.sv']
        log=command([MS/'vlog.exe','-sv','-work',work,*sources],out,out/'compile')
        assert 'Errors: 0' in log and not re.search(r'\bERROR:',log)
        log=command([MS/'vsim.exe','-c','-lib',work,'tb_inst_drm64_x32','-do','run -all; quit -f'],out,out/'simulation')
        assert 'Errors: 0' in log and not re.search(r'\bERROR:',log)
        assert re.findall(r'RESULT: PASS inst_drm64_x32 tests=(\d+)',log)==['2449']
        groups=re.findall(r'CHECK: (\S+) PASS',log);assert groups==[r['group'] for r in m['unit_plan']]
        assert re.findall(r'IPSpecCheck: (\d+)',log)==['04030130','04030130']
        assert require_inputs()==m and sha(MANIFEST)==manifest_sha
        after=git_snapshot();(out/'git_after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf-8')
        assert after==before,'Worktree changed during execution'
        for src in [*sources[2:],Path(__file__),MANIFEST]:shutil.copy2(src,out/src.name)
        result.update(status='MINI_INST_DRM64_KEY_TEST_PASS',checks=2449,check_groups=groups,
                      inputs_unchanged=True,git_snapshots_identical=True,ip_spec_diagnostics=['04030130','04030130'])
        print('RESULT: PASS',out,'checks=2449 ISA=0')
    except Exception as exc:
        result.update(status='FAIL',error=f'{type(exc).__name__}: {exc}');raise
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
