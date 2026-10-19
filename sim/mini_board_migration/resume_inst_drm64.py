"""One Task021 diagnostic continuation; original RTL/TB/checks untouched, no PDS/serial."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from run_inst_drm64 import HERE, ROOT, MS, VENDOR, require_inputs as original_inputs
from resume_inst_cache32 import pds_shell_count, git_snapshot

MANIFEST=HERE/'inst_drm64_resume_inputs.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read_text=lambda p:p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''


def require_inputs():
    old=original_inputs()
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name,h in m['sha256'].items():assert sha(ROOT/name)==h,'Changed protected input: '+name
    for name,h in m['external_tool_sha256'].items():assert sha(Path(name))==h,'Changed simulator tool: '+name
    assert m['original_manifest_sha256']==sha(HERE/'inst_drm64_inputs.json')
    assert m['expected_checks']==2449 and m['unit_plan']==old['unit_plan']
    assert m['timeouts']=={'vlib':60,'compile':60,'simulation':180}
    return m


def script(work):
    return '''proc phase {name} {
    set file [open "phases.log" a]
    puts $file "$name wall_ms=[clock milliseconds]"
    flush $file
    close $file
    puts "DIAG_PHASE $name"
    catch {flush stdout}
}
phase TCL_ENTERED
onerror {phase TCL_ERROR; quit -f -code 2}
transcript on
phase BEFORE_LOAD
vsim -lib {'''+work.as_posix()+'''} tb_inst_drm64_x32 tb_inst_drm64_progress_probe
phase AFTER_LOAD
onfinish stop
phase BEFORE_RUN
run -all
phase AFTER_RUN
phase BEFORE_QUIT
quit -f -code 0
'''


def command(argv,cwd,prefix,timeout):
    assert os.name=='nt','This runner is bound to the verified Windows ModelSim installation'
    start=time.monotonic();timed_out=False;cleanup=None
    # Native stdout goes directly to disk; no pipe held open by child processes.
    with prefix.with_suffix('.log').open('wb') as stream:
        proc=subprocess.Popen(list(map(str,argv)),cwd=cwd,stdin=subprocess.DEVNULL,
            stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            code=proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True;code=-1
            # Stop only this invocation's known live process tree, never existing sessions.
            try:
                if proc.poll() is None:
                    kill=subprocess.run(['taskkill.exe','/PID',str(proc.pid),'/T','/F'],capture_output=True,
                        text=True,errors='replace',timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
                    cleanup=dict(argv=['taskkill.exe','/PID',str(proc.pid),'/T','/F'],
                        exit_code=kill.returncode,output=kill.stdout+kill.stderr)
            except Exception as exc:
                cleanup=dict(error=f'{type(exc).__name__}: {exc}')
            try:
                if proc.poll() is None:proc.kill()
                proc.wait(timeout=15)
            except Exception as exc:
                cleanup=cleanup or {}
                cleanup['parent_cleanup_error']=f'{type(exc).__name__}: {exc}'
    meta=dict(argv=list(map(str,argv)),cwd=str(cwd),exit_code=code,native_exit_after_wait=proc.returncode,
        seconds=time.monotonic()-start,timeout_seconds=timeout,timed_out=timed_out,pid=proc.pid,
        stdout_direct_to_file=True,cleanup=cleanup)
    prefix.with_suffix('.command.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    if timed_out:
        with prefix.with_suffix('.log').open('a',encoding='utf-8') as stream:stream.write('\nRUNNER TIMEOUT\n')
    output=read_text(prefix.with_suffix('.log'))
    assert code==0 and not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|\bERROR:|\bFATAL\b|RUNNER TIMEOUT',output),str(prefix)
    return output


def diagnosis(out):
    phases=read_text(out/'phases.log');probe=read_text(out/'hdl_progress.log')
    console=read_text(out/'simulation.log');trans=read_text(out/'transcript')
    seen=re.findall(r'^(\S+) wall_ms=',phases,re.M)
    last_probe=probe.splitlines()[-1] if probe.splitlines() else None
    combined=console+'\n'+trans
    if re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|\bERROR:|\bFATAL\b',combined):location='ERROR_RECORDED_INSPECT_RAW_LOG'
    elif 'BEFORE_QUIT' in seen:location='QUIT_OR_PROCESS_EXIT_STAGE'
    elif 'AFTER_RUN' in seen:location='POST_RUN_SCRIPT_STAGE'
    elif 'BEFORE_RUN' in seen:
        location='RUN_STARTED_WITH_TIME_PROBE' if probe else 'RUN_COMMAND_ENTERED_NO_HDL_PROBE'
    elif 'AFTER_LOAD' in seen:location='POST_LOAD_SCRIPT_STAGE'
    elif 'BEFORE_LOAD' in seen:location='DESIGN_LOAD_NOT_COMPLETED'
    elif 'TCL_ENTERED' in seen:location='FRONTEND_SCRIPT_STAGE'
    else:location='FRONTEND_STARTUP_NO_SCRIPT_MARKER'
    return dict(location=location,phase_markers=seen,last_probe=last_probe,
        functional_pass_line_seen=bool(re.search(r'RESULT: PASS inst_drm64_x32 tests=2449',combined)),
        finish_line_seen='$finish' in combined,root_cause='Infer from raw stages; marker alone is not a functional verdict')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag');parser.add_argument('--check-inputs',action='store_true')
    args=parser.parse_args();m=require_inputs()
    if args.check_inputs:
        print('INPUTS_MATCH_NOT_SIMULATED',len(m['sha256']),'original=179 vendor=2 checks=2449 ISA=0 vsim_limit=180s');return
    assert args.tag and re.fullmatch(r'[A-Za-z0-9_-]+',args.tag)
    assert pds_shell_count()==0,'User PDS running; stop before HDL'
    out=HERE/'build'/args.tag;out.mkdir(parents=True,exist_ok=False)
    work=out/'work';manifest_sha=sha(MANIFEST);before=git_snapshot()
    (out/'git_before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
    (out/'diagnostic.do').write_text(script(work),encoding='utf-8')
    result=dict(status='RUNNING',functional_status='INCOMPLETE',input_manifest_sha256=manifest_sha,
        original_input_manifest_sha256=m['original_manifest_sha256'],expected_checks=2449,isa_cases=[],
        pds_started=False,serial_opened=False,formal_board='NOT_TESTED',
        diagnostic_scope='Unchanged RTL/TB/model/oracle + read-only second top, direct log/phase/probe files')
    try:
        command([MS/'vlib.exe',work],out,out/'vlib',60)
        ip_sources=[ROOT/f'ipcore/{n}/rtl/ipm2l_sdpram_v1_10_{n}.v' for n in ['icache','dcache']]+\
                   [ROOT/f'ipcore/{n}/{n}.v' for n in ['icache','dcache']]
        sources=[VENDOR/'GTP_GRS.v',VENDOR/'GTP_DRM36K_E1.v',*ip_sources,
                 ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v',HERE/'tb_inst_drm64_x32.sv',
                 HERE/'tb_inst_drm64_progress_probe.sv']
        log=command([MS/'vlog.exe','-sv','-work',work,*sources],out,out/'compile',60)
        assert 'Errors: 0' in log
        command([MS/'vsim.exe','-c','-l',out/'transcript','-do','do diagnostic.do'],out,out/'simulation',180)
        # The explicit native transcript is the authoritative simulation log.
        log=read_text(out/'transcript')
        assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|\bERROR:|\bFATAL\b',log)
        assert 'Errors: 0' in log
        assert re.findall(r'RESULT: PASS inst_drm64_x32 tests=(\d+)',log)==['2449']
        groups=re.findall(r'CHECK: (\S+) PASS',log);assert groups==[r['group'] for r in m['unit_plan']]
        assert re.findall(r'IPSpecCheck: (\d+)',log)==['04030130','04030130']
        assert '$finish' in log and 'tb_inst_drm64_x32.sv' in log
        d=diagnosis(out)
        assert d['phase_markers']==['TCL_ENTERED','BEFORE_LOAD','AFTER_LOAD','BEFORE_RUN','AFTER_RUN','BEFORE_QUIT']
        assert read_text(out/'hdl_progress.log').startswith('PROBE_START ')
        assert require_inputs()==m and sha(MANIFEST)==manifest_sha
        after=git_snapshot();(out/'git_after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf-8')
        assert after==before,'Worktree changed during execution'
        for src in [*sources[2:],Path(__file__),MANIFEST]:shutil.copy2(src,out/src.name)
        result.update(status='MINI_INST_DRM64_DIAGNOSTIC_RESUME_KEY_TEST_PASS',functional_status='PASS',checks=2449,
            check_groups=groups,inputs_unchanged=True,git_snapshots_identical=True,diagnosis=d)
        print('RESULT: PASS',out,'checks=2449 ISA=0')
    except Exception as exc:
        result.update(status='DIAGNOSTIC_STOPPED',error=f'{type(exc).__name__}: {exc}',diagnosis=diagnosis(out))
        raise
    finally:
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
