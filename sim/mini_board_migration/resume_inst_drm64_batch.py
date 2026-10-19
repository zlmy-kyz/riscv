"""Task021 one documented batch-mode test; original single top/RTL/TB/2449 oracle."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
from run_inst_drm64 import HERE, ROOT, MS, VENDOR, require_inputs as original_inputs
from resume_inst_drm64 import command
from resume_inst_drm64_cli import evidence
from resume_inst_cache32 import pds_shell_count, git_snapshot

MANIFEST=HERE/'inst_drm64_batch_inputs.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require_inputs():
    old=original_inputs()
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name,h in m['sha256'].items():assert sha(ROOT/name)==h,'Changed protected input: '+name
    for name,h in m['external_tool_sha256'].items():assert sha(Path(name))==h,'Changed simulator tool: '+name
    for name,h in m['external_reference_sha256'].items():assert sha(Path(name))==h,'Changed tool reference/configuration: '+name
    assert m['original_manifest_sha256']==sha(HERE/'inst_drm64_inputs.json')
    assert m['cli_manifest_sha256']==sha(HERE/'inst_drm64_cli_inputs.json')
    assert m['unit_plan']==old['unit_plan'] and m['expected_checks']==2449
    assert m['timeouts']=={'vlib':60,'compile':60,'simulation':180}
    assert m['entry_contract']=='Documented -batch single top; original run -all; quit -f; no -c or Tcl vsim'
    return m


def simulation_argv(work,out):
    return [MS/'vsim.exe','-batch','-lib',work,'tb_inst_drm64_x32',
            '-logfile',out/'transcript','-do','run -all; quit -f']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag');parser.add_argument('--check-inputs',action='store_true')
    args=parser.parse_args();m=require_inputs()
    if args.check_inputs:
        print('INPUTS_MATCH_NOT_SIMULATED',len(m['sha256']),
            'original=179 vendor=2 tools=5 refs=2 checks=2449 ISA=0 vsim_limit=180s entry=BATCH_SINGLE_TOP');return
    assert args.tag and re.fullmatch(r'[A-Za-z0-9_-]+',args.tag)
    assert pds_shell_count()==0,'User PDS running; stop before HDL'
    out=HERE/'build'/args.tag;out.mkdir(parents=True,exist_ok=False)
    work=out/'work';before=git_snapshot();manifest_sha=sha(MANIFEST)
    (out/'git_before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
    result=dict(status='RUNNING',functional_status='INCOMPLETE',input_manifest_sha256=manifest_sha,
        original_input_manifest_sha256=m['original_manifest_sha256'],expected_checks=2449,
        isa_cases=[],pds_started=False,serial_opened=False,formal_board='NOT_TESTED',
        entry_contract=m['entry_contract'],stdout_direct_to_file=True,host_settings_changed=False)
    try:
        command([MS/'vlib.exe',work],out,out/'vlib',60)
        ip_sources=[ROOT/f'ipcore/{n}/rtl/ipm2l_sdpram_v1_10_{n}.v' for n in ['icache','dcache']]+\
                   [ROOT/f'ipcore/{n}/{n}.v' for n in ['icache','dcache']]
        sources=[VENDOR/'GTP_GRS.v',VENDOR/'GTP_DRM36K_E1.v',*ip_sources,
                 ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v',HERE/'tb_inst_drm64_x32.sv']
        log=command([MS/'vlog.exe','-sv','-work',work,*sources],out,out/'compile',60)
        assert 'Errors: 0' in log
        log=command(simulation_argv(work,out),out,out/'simulation',180)
        trans=(out/'transcript').read_text(encoding='utf-8',errors='replace')
        assert not re.search(r'RPC_Init:|RESULT: FAIL|\*\* (?:Error|Fatal)|\bERROR:|\bFATAL\b',log+'\n'+trans)
        assert 'Errors: 0' in log
        assert re.findall(r'RESULT: PASS inst_drm64_x32 tests=(\d+)',log)==['2449']
        groups=re.findall(r'CHECK: (\S+) PASS',log);assert groups==[r['group'] for r in m['unit_plan']]
        assert re.findall(r'IPSpecCheck: (\d+)',log)==['04030130','04030130']
        assert '$finish' in log and 'tb_inst_drm64_x32.sv' in log
        assert trans,'Missing native batch transcript'
        assert require_inputs()==m and sha(MANIFEST)==manifest_sha
        after=git_snapshot();(out/'git_after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf-8')
        assert after==before,'Worktree changed during execution'
        for src in [*sources[2:],Path(__file__),MANIFEST]:shutil.copy2(src,out/src.name)
        result.update(status='MINI_INST_DRM64_BATCH_RESUME_KEY_TEST_PASS',functional_status='PASS',checks=2449,
            check_groups=groups,inputs_unchanged=True,git_snapshots_identical=True,
            ip_spec_diagnostics=['04030130','04030130'])
        print('RESULT: PASS',out,'checks=2449 ISA=0')
    except Exception as exc:
        result.update(status='BATCH_RESUME_STOPPED',error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        result['evidence']=evidence(out)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
