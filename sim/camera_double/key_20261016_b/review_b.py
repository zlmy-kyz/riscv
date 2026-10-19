"""Sol read-only replay of frozen B evidence; never launches HDL or opens serial."""
import collections
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import check
import run
from seal import SEAL, VENDOR, closure, sha


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def main():
    out = HERE / 'build/ds_abi2_soc_resume_20261016_b'
    dest = HERE / 'review_b'
    assert not dest.exists(), 'preserve first review; use a new destination for repairs'
    identity = '5e262312b626ea8473db910f0372297ae79a3fc0321dd22a8fe30fc1415ce61a'
    m = run.require()
    assert sha(HERE/'inputs.json') == sha(SEAL/'inputs.json') == sha(out/'inputs.json') == identity
    for n, d in m['project_sha256'].items():
        assert sha(out/'inputs/project'/n) == d, n
    assert closure(out/'inputs/project', m['compile_sources']) == m['include_dependencies']
    for n, d in m['vendor_sha256'].items():
        assert sha(out/'inputs/vendor'/Path(n).relative_to(VENDOR)) == d, n
    assert sha(out/'modelsim.ini') == m['modelsim_ini']['sha256']
    evidence = load(out/'evidence_sha256.json')
    for n, d in evidence.items():
        assert sha(out/n) == d, n
    assert (out/'git_before.json').read_bytes() == (out/'git_after.json').read_bytes()
    assert load(out/'input_identity_after.json') == m['project_sha256']
    assert load(out/'protected_history_identity_after.json') == m['protected_history_sha256']
    result = load(out/'result.json')
    assert result == dict(status='ABI2_SOC_RESUME_CHECKED_PENDING_SOL_REVIEW', manifest_sha256=identity,
                         completed=['unit_recheck', 'soc'], PDS='NOT_RUN', board='NOT_RUN')
    commands = {n:load(out/(n+'.command.json')) for n in ('unit_recheck','vlib','compile','soc','soc_check')}
    for n, c in commands.items():
        assert c['returncode'] == 0 and not c['timed_out'], n
        assert 0 < c['elapsed_seconds'] < c['timeout_seconds'], n
        assert not any(s in (out/(n+'.stdout.log')).read_text(errors='replace')
                       for s in ('** Error','** Fatal','RESULT: FAIL','Error loading design')), n
    compile_text = (out/'compile.stdout.log').read_text()
    assert 'Errors: 0, Warnings: 0' in compile_text
    assert sorted(re.findall(r'-- Compiling module (\w+)',compile_text)) == sorted(m['modules']+['GTP_GRS','GTP_DRM36K_E1','GTP_APM_E2'])
    stdout = (out/'soc.stdout.log').read_text()
    assert 'RESULT: PASS ABI2_SMALL_REAL_CPU' in stdout
    assert re.findall(r'Errors:\s*(\d+)',stdout) == ['0']
    assert re.findall(r'Warnings:\s*(\d+)',stdout) == ['30']
    warning_codes = collections.Counter(re.findall(r'\*\* Warning: \(vsim-(\d+)\)',stdout))
    assert warning_codes == {'3017':2,'3722':28}
    # Same frozen checker, rerun from actual DVP, CPU and native bus bytes. Reports stay outside the run.
    unit_path = out/'inputs/project'/m['reuse_unit_path']
    unit = check.check_unit(unit_path)
    unit.update(status='ABI2_INDEPENDENT_RAW_CHECK_PASS', DVP_input_frames=check.data_input(unit_path/'unit.dvp.log','unit'))
    soc = check.check_soc(out)
    soc.update(status='ABI2_INDEPENDENT_RAW_CHECK_PASS', DVP_input_frames=check.data_input(out/'soc.dvp.log','soc'))
    assert json.loads(json.dumps(unit)) == load(out/'unit.checked.json')
    assert json.loads(json.dumps(soc)) == load(out/'soc.checked.json')
    assert sha(HERE/'review_a/review.json') == m['unit_reuse_review_sha256']
    # Bind the 16 actual startup retirements to the exact ELF-derived small BIN/DAT.
    sys.path.insert(0, str(ROOT/'tools/camera_uart'))
    import double100
    full = double100.image(double100.DEFAULT)
    small = double100.image(ROOT/'tests/camera_double100/build/abi2_small_20261016_d/manifest.json')
    assert full['source_sha256'] == small['source_sha256']
    small_bin = (ROOT/small['bin_path']).read_bytes()
    dat = out/'inputs/project/sim/camera_double/key_20261016_a/generated/cpu.dat'
    image = b''.join(int(s,16).to_bytes(4,'little') for s in dat.read_text().split())
    assert image == small_bin + bytes(16384-len(small_bin))
    rows = [s.split() for s in (out/'cpu.log').read_text().splitlines()]
    retired = [r for r in rows if r[0] == 'RETIRE']
    assert len(retired) == 16 and not any(r[0] == 'TRAP' for r in rows)
    for r in retired:
        off = int(r[2],16)-0x40000000
        assert off >= 0 and off % 4 == 0 and int(r[3],16) == int.from_bytes(small_bin[off:off+4],'little')
    pub = [dict(cycle=int(r[1]),buffer=int(r[2]),seq=int(r[3]),crc=r[4],last_actual_W=int(r[5])) for r in rows if r[0]=='PUB']
    assert [p['buffer'] for p in pub] == [0,1,0,1,0]
    reports = [int(r[2],16) for r in rows if r[0]=='REPORT']
    expected = [0xc0000001,pub[0]['crc'],0xd0000001,pub[1]['crc'],0xd0010002,0xc0000002,
                pub[2]['crc'],0xd0000003,pub[3]['crc'],0xd0010004,pub[4]['crc'],0xd0000005,0xc0000003]
    expected = [int(x,16) if isinstance(x,str) else x for x in expected]
    assert reports == expected, 'actual CPU CRC/slot/sequence reports'
    cover = [list(map(int,r[1:])) for r in rows if r[0]=='COVER']
    assert cover == [[5,1280,275,19,1,6904]]
    assert sum(r[0]=='CONTEND' for r in rows) == cover[0][-1]
    assert [int(r[2]) for r in rows if r[0]=='UART_STIMULUS'] == [1,2]
    a_result = load(ROOT/'sim/camera_double/key_20261016_a/build/ds_abi2_key_20261016_a/result.json')
    assert a_result['status'] == 'STOPPED_FIRST_FAILURE'
    # Ensure analysis has changed no sealed input, protected history or original evidence.
    run.require()
    for n,d in evidence.items():
        assert sha(out/n) == d
    receipt = dict(status='ABI2_KEY_RAW_REVIEW_PASS_BOARD_PROGRAM_RELEASED_BOARD_NOT_RUN',
        reviewed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        reviewer_source_sha256=sha(__file__), manifest_sha256=identity,
        parent_manifest_sha256=m['parent_manifest_sha256'],unit_review_sha256=m['unit_reuse_review_sha256'],
        project_files=len(m['project_sha256']),input_copies=3,protected_history_files=len(m['protected_history_sha256']),
        vendor_files=len(m['vendor_sha256']),tool_files=len(m['tool_sha256']),include_edges=len(m['include_dependencies']),
        inputs_includes_GRS_vendor_tools_INI_Git_match=True,evidence_sha256=evidence,
        commands={n:dict(returncode=c['returncode'],timed_out=c['timed_out'],elapsed_seconds=c['elapsed_seconds']) for n,c in commands.items()},
        compile=dict(modules=54,errors=0,warnings=0),soc_warnings=dict(total=30,codes=dict(warning_codes),
        disposition='Preserved: omitted observed/physical top outputs and unused DDR delay outputs; functional stimulus inputs explicitly connected'),
        unit_replay=unit,soc_replay=soc,publications=pub,actual_CPU_reports_hex=[f'{v:08x}' for v in reports],
        actual_startup_retirements=16,CPU_traps=0,cover=dict(publications=5,full_CPU_words=1280,
        CPU_requests_while_other_busy=275,DMA_completions_while_CPU_pending=19,release_mid_frame=1,simultaneous_CPU_camera_AW_cycles=6904),
        board_firmware=dict(path=full['bin_path'],bytes=full['bytes'],sha256=full['bin_sha256'],crc32=f"{full['crc32']:08x}",manifest_sha256=sha(double100.DEFAULT)),
        small_firmware=dict(path=small['bin_path'],bytes=small['bytes'],sha256=small['bin_sha256'],DAT_exact_BIN_padded=True),
        original_A_status='STOPPED_FIRST_FAILURE_UNCHANGED',RTL_modified=False,HDL_rerun_by_Sol=False,
        PDS='USER_CONFIRMED_TIMING_NO_REAUDIT',board='NOT_RUN',Full_Boot='NOT_RUN',PHY='NOT_RUN',
        scope='Small 64x8 real CPU plus reused 64x128 unit; no new 720p board/PHY/Full Boot PASS; board uses frozen full 720p100 BIN')
    dest.mkdir(exist_ok=False)
    (dest/'review.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],review_sha256=sha(dest/'review.json'),soc=soc,
                         publications=pub,firmware=receipt['board_firmware']),indent=2))


if __name__ == '__main__':
    main()
