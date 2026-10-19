"""Task019: one I32 DRM targeted test, real generated IP + Pango primitive; no PDS/serial."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET

from resume_inst_cache32 import project_configuration, pds_shell_count, command, git_snapshot
from run_inst_cache32 import planned_counts as baseline_counts

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / 'inst_drm_inputs.json'
MS = Path('D:/modelsim/win64pe')
VENDOR = Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def planned_counts():
    source = (HERE / 'tb_inst_drm_x32.sv').read_text(encoding='utf-8')
    weights = {n: 1 for n in ['fetch', 'load_word', 'store_word', 'cached_contention',
                              'sync_hit_address_change']}
    for name in ['queued_inst_fill', 'queued_data_fill', 'reset_during_hit']:
        body = re.search(r'task automatic ' + name + r'\b(.*?)endtask', source, re.S)[1]
        weights[name] = len(re.findall(r'\b(?:fetch|load_word|store_word)\(', body)) + \
                        len(re.findall(r'tests=tests\+1;', body))
    loop = re.compile(r'for\s*\(\s*(\w+)=0;\s*\1<([^;]+);\s*\1=\1\+1\s*\)\s*begin')
    def count(text):
        match = loop.search(text)
        if not match:
            return sum(weights[n] for n in re.findall(r'\b('+'|'.join(weights)+r')\(', text))
        depth = 1
        for token in re.finditer(r'\b(begin|end)\b', text[match.end():]):
            depth += 1 if token[1] == 'begin' else -1
            if depth == 0:
                start, stop = match.end()+token.start(), match.end()+token.end()
                break
        else:
            raise ValueError('Unbalanced TB loop')
        bound = match[2].strip()
        n = {'I_LINES': 32, 'D_LINES': 16}[bound] if bound in ('I_LINES', 'D_LINES') else int(bound)
        return count(text[:match.start()]) + n*count(text[match.end():start]) + count(text[stop:])
    main = source[source.index('    initial begin : run_tests'):]
    sections = re.split(r'\$display\("CHECK: (\S+) PASS"\);', main)
    assert len(sections) == 13
    rows = [dict(group=sections[i+1], checks=count(sections[i])) for i in range(0, 12, 2)]
    assert rows[:5] == baseline_counts(), 'Existing 834 checks changed'
    assert [r['checks'] for r in rows] == [325, 83, 111, 75, 240, 259]
    return rows


def review_rtl(m):
    old = (ROOT / m['baseline_bridge']).read_text(encoding='utf-8')
    new = (ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v').read_text(encoding='utf-8')
    # Reverse only the recorded I data implementation/response adaptation.
    restored = new.replace('//   * x32 指令数据用 icache DRM 同步读，tag/valid 仍在逻辑中；x16 保留原数组。\n', '')
    restored = restored.replace('    reg        response_from_inst_drm;\n', '')
    restored = restored.replace('    wire [31:0] inst_drm_rdata;\n    wire [31:0] inst_legacy_rdata;',
                                '    reg [8*MEM_DQ_WIDTH-1:0] inst_line_data [0:31];')
    begin = restored.index('    generate\n')
    end = restored.index('    endgenerate\n', begin) + len('    endgenerate\n')
    restored = restored[:begin] + restored[end+1:]
    restored = restored.replace('                inst_line_tag[reset_line]  <= {TAG_BITS{1\'b0}};\n',
        '                inst_line_tag[reset_line]  <= {TAG_BITS{1\'b0}};\n'
        '                inst_line_data[reset_line] <= {(8*MEM_DQ_WIDTH){1\'b0}};\n')
    restored = restored.replace('            inst_line_tag[fill_line_index]   <= request_line_tag;\n',
        '            inst_line_tag[fill_line_index]   <= request_line_tag;\n'
        '            inst_line_data[fill_line_index]  <= axi_rdata;\n')
    restored = restored.replace('    assign inst_rsp_rdata = response_from_inst_drm ? inst_drm_rdata : response_rdata;',
                                '    assign inst_rsp_rdata = response_rdata;')
    restored = re.sub(r'^\s*response_from_inst_drm <= .*;\n', '', restored, flags=re.M)
    restored = restored.replace('                            response_rdata <= inst_legacy_rdata;',
        '                            response_rdata <=\n'
        '                                inst_line_data[inst_line_index][inst_req_addr[BEAT_ADDR_BITS-1:2] * 32 +: 32];')
    assert restored == old, 'Unrelated RTL changed (D16/DDR FSM/tag/valid/priority must remain)'
    for text in ['.wr_data(axi_rdata)', ".wr_addr({1'b0, fill_line_index})",
                 '.wr_en(resetn && ddr_init_done && inst_line_fill)',
                 ".rd_addr({1'b0, inst_req_addr[9:2]})", '.wr_clk(clk)', '.rd_clk(clk)']:
        assert text in new, text


def require_inputs():
    m = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name, digest in m['sha256'].items():
        assert sha(ROOT / name) == digest, 'Protected input changed: '+name
    for name, digest in m['vendor_sha256'].items():
        assert sha(Path(name)) == digest, 'Vendor model changed: '+name
    config = project_configuration((ROOT / 'RISCV.pds').read_text(encoding='utf-8'))
    assert hashlib.sha256(config.encode()).hexdigest() == m['project_configuration_sha256']
    assert config.count('(_ip "ipcore/icache/icache.idf"') == 1
    assert 'ipcore/dcache/dcache.idf' not in config
    p = ET.parse(ROOT / 'ipcore/icache/icache.idf').getroot()
    params = {r.findtext('name'): r.findtext('value') for r in p.findall('./param_list/param')}
    assert all(params[n] == v for n, v in m['ip_configuration'].items())
    assert p.findtext('./header/device') == 'PG2L200H'
    assert p.findtext('./header/instance') == 'icache'
    assert planned_counts() == m['unit_plan'] and m['expected_checks'] == 1093
    review_rtl(m)
    # DDR model/transfer oracle and all previous tests preserved byte for byte.
    old_tb = (HERE / 'tb_inst_cache32_x32.sv').read_text(encoding='utf-8')
    new_tb = (HERE / 'tb_inst_drm_x32.sv').read_text(encoding='utf-8')
    a, b = '    assign rrdy=', '    initial begin : run_tests'
    old = old_tb[old_tb.index(a):old_tb.index(b)]
    new = new_tb[new_tb.index(a):new_tb.index('    // DRM-specific')]
    assert old == new
    a, b = '        for (k=0;k<128;', '        conservation();\n        if (tests!=834)'
    old = old_tb[old_tb.index(a):old_tb.index(b)]
    new = new_tb[new_tb.index(a):new_tb.index('        // New synchronous RAM checks')]
    assert old == new
    return m


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag')
    parser.add_argument('--check-inputs', action='store_true')
    args = parser.parse_args()
    m = require_inputs()
    if args.check_inputs:
        print('INPUTS_MATCH_NOT_SIMULATED', len(m['sha256']), 'vendor=2 checks=1093 ISA=0')
        return
    assert args.tag and re.fullmatch(r'[A-Za-z0-9_-]+', args.tag), 'Use a new simple tag'
    assert pds_shell_count() == 0, 'User PDS is running; stop before HDL'
    out = HERE / 'build' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    manifest_sha = sha(MANIFEST)
    before = git_snapshot()
    (out / 'git_before.json').write_text(json.dumps(before, indent=2)+'\n', encoding='utf-8')
    result = dict(status='RUNNING', input_manifest_sha256=manifest_sha, isa_cases=[],
        pds_started=False, serial_opened=False, formal_board='NOT_TESTED',
        model_scope='Generated ICache IP + real Pango DRM primitive; functional DDR user-port only')
    try:
        work = out / 'work'
        command([MS / 'vlib.exe', work], out, out / 'vlib')
        sources = [VENDOR / 'GTP_GRS.v', VENDOR / 'GTP_DRM36K_E1.v',
            ROOT / 'ipcore/icache/rtl/ipm2l_sdpram_v1_10_icache.v', ROOT / 'ipcore/icache/icache.v',
            ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v', HERE / 'tb_inst_drm_x32.sv']
        log = command([MS / 'vlog.exe', '-sv', '-work', work, *sources], out, out / 'compile')
        assert 'Errors: 0' in log
        assert not re.search(r'\bERROR:', log), 'Primitive/compiler error; preserve evidence'
        log = command([MS / 'vsim.exe', '-c', '-lib', work, 'tb_inst_drm_x32',
            '-do', 'run -all; quit -f'], out, out / 'simulation')
        assert 'Errors: 0' in log
        assert not re.search(r'\bERROR:', log), 'Primitive error; preserve evidence'
        assert re.findall(r'RESULT: PASS inst_drm_x32 tests=(\d+)', log) == ['1093']
        groups = re.findall(r'CHECK: (\S+) PASS', log)
        assert groups == [r['group'] for r in m['unit_plan']]
        specs = re.findall(r'IPSpecCheck: (\d+)', log)
        assert specs == ['04030130'], 'Unexpected IP parameter diagnostic; retain and stop'
        assert require_inputs() == m and sha(MANIFEST) == manifest_sha
        after = git_snapshot()
        (out / 'git_after.json').write_text(json.dumps(after, indent=2)+'\n', encoding='utf-8')
        assert after == before, 'Working tree changed during execution'
        for src in [sources[-2], sources[-1], Path(__file__), MANIFEST]:
            shutil.copy2(src, out / src.name)
        for src in sources[2:4]:
            shutil.copy2(src, out / src.name)
        result.update(status='MINI_INST_DRM_KEY_TEST_PASS', checks=1093, check_groups=groups,
            inputs_unchanged=True, git_snapshots_identical=True, ip_spec_diagnostics=specs)
        print('RESULT: PASS', out, 'checks=1093 ISA=0')
    except Exception as exc:
        result.update(status='FAIL', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
