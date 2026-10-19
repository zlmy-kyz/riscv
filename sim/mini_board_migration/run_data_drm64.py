"""Task022: D32 to D64 only, real DRM batch key test; no PDS/serial/CPU change."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from run_inst_drm64 import HERE, ROOT, MS, VENDOR, project_identity
from resume_inst_drm64 import command
from resume_inst_cache32 import pds_shell_count, git_snapshot

MANIFEST=HERE/'data_drm64_inputs.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def data64_transform(old):
    changes={
        '//   * 指令缓存为 64 行、数据读缓冲为 32 行直接映射。':'//   * 指令缓存和数据读缓冲均为 64 行直接映射。',
        '//     x16 保留数组实现；x32 I64 为 2 KiB、D32 为 1 KiB。':'//     x16 保留数组实现；x32 I64/D64 各为 2 KiB。',
        '// 32 行数据读缓冲':'// 64 行数据读缓冲',
        'reg [31:0]  data_line_valid;':'reg [63:0]  data_line_valid;',
        'data_line_tag [0:31];':'data_line_tag [0:63];',
        'wire [4:0]  data_read_line_index;':'wire [5:0]  data_read_line_index;',
        'wire [4:0]  data_fill_line_index;':'wire [5:0]  data_fill_line_index;',
        'assign data_read_line_index = data_req_addr[BEAT_ADDR_BITS+4:BEAT_ADDR_BITS];':
            'assign data_read_line_index = data_req_addr[BEAT_ADDR_BITS+5:BEAT_ADDR_BITS];',
        'assign data_fill_line_index = request_line_tag[4:0];':'assign data_fill_line_index = request_line_tag[5:0];',
        '// 与 I IP 同配置，D32 使用低 32 行，地址最高位为 0。':'// 与 I IP 同配置，D64 使用全部 64 行及 512 个 word。',
        ".wr_addr({1'b0, data_fill_line_index})":'.wr_addr(data_fill_line_index)',
        ".rd_addr({1'b0, data_req_addr[9:2]})":'.rd_addr(data_req_addr[10:2])',
        'data_line_data [0:31];':'data_line_data [0:63];',
        'reset_data_array < 32;':'reset_data_array < 64;',
        "data_line_valid <= 32'b0;":"data_line_valid <= 64'b0;",
        'reset_data_line < 32;':'reset_data_line < 64;',
    }
    for a,b in changes.items():
        assert a in old,a
        old=old.replace(a,b)
    return old


def planned_counts():
    source=(HERE/'tb_data_drm64_x32.sv').read_text(encoding='utf-8')
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
        bound=match[2].strip();n=64 if bound in ['I_LINES','D_LINES'] else int(bound)
        return count(text[:match.start()])+n*count(text[match.end():start])+count(text[stop:])
    main=source[source.index('    initial begin : run_tests'):]
    parts=re.split(r'\$display\("CHECK: (\S+) PASS"\);',main);assert len(parts)==17
    rows=[dict(group=parts[i+1],checks=count(parts[i])) for i in range(0,16,2)]
    assert [r['checks'] for r in rows]==[645,147,271,139,640,515,584,22]
    assert sum(r['checks'] for r in rows)==2963
    return rows


def require_inputs():
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name,h in m['sha256'].items():assert sha(ROOT/name)==h,'Changed protected input: '+name
    for key in ['vendor_sha256','external_tool_sha256','external_reference_sha256']:
        for name,h in m[key].items():assert sha(Path(name))==h,'Changed external input: '+name
    assert project_identity((ROOT/'RISCV.pds').read_text())==m['project_configuration_sha256']
    old=(ROOT/m['baseline_bridge']).read_text(encoding='utf-8')
    new=(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v').read_text(encoding='utf-8')
    assert new==data64_transform(old),'Unexpected change beyond D64 capacity/mapping/reset'
    for name in ['icache','dcache']:
        root=ET.parse(ROOT/f'ipcore/{name}/{name}.idf').getroot()
        params={r.findtext('name'):r.findtext('value') for r in root.findall('./param_list/param')}
        assert all(params[k]==v for k,v in m['ip_configuration'].items()),name
        assert root.findtext('./header/device')=='PG2L200H' and root.findtext('./header/instance')==name
    oldtb=(HERE/'tb_inst_drm64_x32.sv').read_text(encoding='utf-8')
    newtb=(HERE/'tb_data_drm64_x32.sv').read_text(encoding='utf-8')
    a,b='    assign rrdy=','    task automatic queued_inst_fill('
    assert oldtb[oldtb.index(a):oldtb.index(b)]==newtb[newtb.index(a):newtb.index(b)],'DDR model/transfer/latency oracle changed'
    a,b='    task automatic queued_inst_fill','    task automatic queued_data_fill'
    assert oldtb[oldtb.index(a):oldtb.index(b)]==newtb[newtb.index(a):newtb.index(b)],'I fill/data arbitration task changed'
    a,b='    integer fill_writes=0;','    // D'
    assert oldtb[oldtb.index(a):oldtb.index(b,oldtb.index(a))]==newtb[newtb.index(a):newtb.index(b,newtb.index(a))],'I synchronous monitor/task changed'
    assert planned_counts()==m['unit_plan'] and m['expected_checks']==2963
    return m


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag');p.add_argument('--check-inputs',action='store_true')
    args=p.parse_args();m=require_inputs()
    if args.check_inputs:
        print('INPUTS_MATCH_NOT_SIMULATED',len(m['sha256']),'vendor=2 tools=5 refs=2 checks=2963 ISA=0 entry=BATCH_SINGLE_TOP');return
    assert args.tag and re.fullmatch(r'[A-Za-z0-9_-]+',args.tag)
    assert pds_shell_count()==0,'User PDS running; stop before HDL'
    out=HERE/'build'/args.tag;out.mkdir(parents=True,exist_ok=False)
    work=out/'work';before=git_snapshot();manifest_sha=sha(MANIFEST)
    (out/'git_before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
    result=dict(status='RUNNING',functional_status='INCOMPLETE',input_manifest_sha256=manifest_sha,
        expected_checks=2963,isa_cases=[],pds_started=False,serial_opened=False,formal_board='NOT_TESTED',
        host_settings_changed=False,mode='-batch',scope='D32 to D64 only; I64/CPU/DDR timing/IP/software unchanged')
    try:
        command([MS/'vlib.exe',work],out,out/'vlib',60)
        ip_sources=[ROOT/f'ipcore/{n}/rtl/ipm2l_sdpram_v1_10_{n}.v' for n in ['icache','dcache']]+\
                   [ROOT/f'ipcore/{n}/{n}.v' for n in ['icache','dcache']]
        sources=[VENDOR/'GTP_GRS.v',VENDOR/'GTP_DRM36K_E1.v',*ip_sources,
                 ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v',HERE/'tb_data_drm64_x32.sv']
        log=command([MS/'vlog.exe','-sv','-work',work,*sources],out,out/'compile',60)
        assert 'Errors: 0' in log
        log=command([MS/'vsim.exe','-batch','-lib',work,'tb_data_drm64_x32','-logfile',out/'transcript',
            '-do','run -all; quit -f'],out,out/'simulation',180)
        trans=(out/'transcript').read_text(encoding='utf-8',errors='replace')
        assert log==trans and trans,'Native transcript differs after newline normalization'
        assert not re.search(r'RPC_Init:|RESULT: FAIL|\*\* (?:Error|Fatal)|\bERROR:|\bFATAL\b',log)
        assert 'Errors: 0' in log
        assert re.findall(r'RESULT: PASS data_drm64_x32 tests=(\d+)',log)==['2963']
        groups=re.findall(r'CHECK: (\S+) PASS',log);assert groups==[r['group'] for r in m['unit_plan']]
        assert re.findall(r'IPSpecCheck: (\d+)',log)==['04030130','04030130']
        assert '$finish' in log and 'tb_data_drm64_x32.sv' in log
        assert require_inputs()==m and sha(MANIFEST)==manifest_sha
        after=git_snapshot();(out/'git_after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf-8')
        assert after==before,'Worktree changed during execution'
        for src in [*sources[2:],Path(__file__),MANIFEST]:shutil.copy2(src,out/src.name)
        result.update(status='MINI_DATA_DRM64_KEY_TEST_PASS',functional_status='PASS',checks=2963,
            check_groups=groups,inputs_unchanged=True,git_snapshots_identical=True,
            ip_spec_diagnostics=['04030130','04030130'])
        print('RESULT: PASS',out,'checks=2963 ISA=0')
    except Exception as exc:
        result.update(status='STOPPED',error=f'{type(exc).__name__}: {exc}');raise
    finally:
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
