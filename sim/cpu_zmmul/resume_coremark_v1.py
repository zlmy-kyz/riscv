"""Task024 V1-only continuation. Start a detached native-file worker; poll status."""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from run_coremark_crc import ROOT, HERE, MS, command, read, write, sha, git_snapshot, pds_shell_count
import run_coremark_crc as original

TAG = 'ds_cpu_zmmul_coremark_v1_resume_20261013_a'
MANIFEST = HERE/'coremark_v1_resume_inputs.json'
OLD = HERE/'build'/original.TAG
OUT = HERE/'build'/TAG
sys.path.insert(0, str(ROOT/'tests/cpu_performance_2b'))
from zmmul_software import BUILD_DIR, require_manifest, parse_measurement
from zmmul300_software import BUILD_DIR as BUILD300, require_manifest as require300


def evidence(folder, mode):
    info = require_manifest(BUILD_DIR/(mode+'_1')/'manifest.json')
    console, transcript = read(folder/'simulation.log'), read(folder/'transcript')
    for text in [console, transcript]:
        assert text.count('RESULT: PASS coremark_zmmul_direct') == 1 and '$finish' in text
        assert 'Errors: 0, Warnings: 0' in text
        assert text.count('04030130') == 2
        assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', text)
    assert console.replace('\r\n','\n').strip() == transcript.replace('\r\n','\n').strip()
    fields = re.findall(r'RESULT: PASS coremark_zmmul_direct cycles=(\d+) retired=(\d+) AR=(\d+) AW=(\d+) UART=(\d+) MUL=(\d+) MATRIX_MUL=(\d+)', console)
    assert len(fields)==1 and all(int(x)>0 for x in fields[0])
    counts = dict(zip(['cycles','retired','AR','AW','UART','MUL','MATRIX_MUL'], map(int,fields[0])))
    uart = (folder/'uart.txt').read_bytes()
    assert len(uart)==counts['UART']
    parsed = parse_measurement(info, uart, board=False)
    return dict(status='RAW_CRC_COUNTERS_REAL_MUL_PASS', parsed=parsed, actual_simulation_counts=counts,
                evidence_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in
                                 [folder/'simulation.log',folder/'transcript',folder/'uart.txt']})


def require_inputs():
    original.require_inputs()
    m = json.loads(read(MANIFEST))
    assert m['original_manifest_sha256']==sha(original.MANIFEST)
    assert m['simulation_timeout_seconds']==3600 and m['new_jobs']==['validation_1']
    for name, digest in m['sha256'].items(): assert sha(ROOT/name)==digest, name
    for name, digest in m['original_artifact_sha256'].items(): assert sha(ROOT/name)==digest, name
    compile_meta = json.loads(read(OLD/'compile.command.json'))
    assert compile_meta['exit_code']==compile_meta['native_exit_after_wait']==0 and not compile_meta['timed_out']
    assert 'Errors: 0, Warnings: 0' in read(OLD/'compile.log')
    old_inputs = json.loads(read(original.MANIFEST))
    expected = [str(MS/'vlog.exe'), '-sv', '-work', str(OLD/'work'), '+incdir+'+(ROOT/'myriscv').as_posix(),
                *[str(Path(n)) for n in old_inputs['vendor_compile_sources']],
                *[str(ROOT/n) for n in old_inputs['compile_sources']]]
    assert compile_meta['argv']==expected
    p1 = evidence(OLD/'performance_1', 'performance')
    assert p1['actual_simulation_counts']['MUL']==9618 and p1['actual_simulation_counts']['MATRIX_MUL']==9396
    for mode in ['performance','validation']: require300(BUILD300/(mode+'_300')/'manifest.json')
    return m, p1


def worker():
    result = json.loads(read(OUT/'result.json'))
    assert result['status']=='STARTED' and not (OUT/'worker_entered.json').exists()
    write(OUT/'worker_entered.json', dict(pid=os.getpid(), wall_time=time.time()))
    before = git_snapshot(); write(OUT/'git_before.json', before)
    result.update(status='RUNNING',phase='INPUTS',worker_pid=os.getpid())
    write(OUT/'result.json',result)
    try:
        m,p1 = require_inputs(); assert pds_shell_count()==0
        shutil.copyfile(MANIFEST, OUT/'inputs.json')
        for name in m['snapshot_new_files']:
            dest = OUT/'new_inputs'/name; dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,dest); assert sha(dest)==m['sha256'][name]
        write(OUT/'original_observation.json', dict(result=json.loads(read(OLD/'result.json')),
              original_process_metadata='P1 command/native exit and git_after absent; not reconstructed',
              original_interruption_cause='UNKNOWN', raw_P1=p1,
              known_old_workspace_delta='ipcore/mul/.settings added after old git_before; current continuation includes it in baseline'))
        work = OUT/'work'; shutil.copytree(OLD/'work',work)
        for name,digest in m['original_artifact_sha256'].items():
            path = ROOT/name
            if path.is_relative_to(OLD/'work'): assert sha(work/path.relative_to(OLD/'work'))==digest
        folder = OUT/'validation_1'; folder.mkdir()
        info = require_manifest(BUILD_DIR/'validation_1/manifest.json')
        plus = ['+ROM='+str(ROOT/old_inputs_rom()), '+DAT='+str(HERE/'fixtures/coremark_validation_1.dat'),
                f'+DONE={info["symbols"]["program_return"]:08x}', '+OUT='+str(folder), '+MAX_CYCLES=60000000',
                '+HOT_PC_FILE='+str(HERE/'fixtures/coremark_validation_mul_pcs.hex')]
        argv = [MS/'vsim.exe','-batch','-lib',work,'tb_coremark_zmmul',*plus,
                '-logfile',folder/'transcript','-do','run -all; quit -f']
        write(OUT/'planned_simulation.json',dict(argv=list(map(str,argv)),timeout_seconds=3600,cwd=str(folder)))
        result.update(phase='V1_SIMULATION',reused_P1=p1); write(OUT/'result.json',result)
        command(argv,folder,folder/'simulation',3600)
        v1 = evidence(folder,'validation')
        meta = json.loads(read(folder/'simulation.command.json'))
        assert meta['exit_code']==meta['native_exit_after_wait']==0 and not meta['timed_out']
        write(folder/'crc_review.json',v1)
        result.update(phase='FINAL_INPUT_AND_WORKSPACE_CHECK',V1=v1,functional_status='P1_REUSED_V1_NEW_P_V_SHORT_CRC_PASS')
        write(OUT/'result.json',result)
        require_inputs()
        after = git_snapshot(); write(OUT/'git_after.json',after)
        assert before==after, 'Current continuation Git snapshot changed; inspect separately from functional result'
        receipt_path = HERE/'build/preparation_20261013_a/pds_review_20261013/receipt.json'
        receipt = json.loads(read(receipt_path))
        gate = dict(status='ZMMUL_P_V_SHORT_CRC_GATE_PASS_300_READY_FOR_USER_BOARD',
                    original_orchestration='Preserved incomplete historical metadata; native P1 exit unknown',
                    original_tag=original.TAG,continuation_tag=TAG,
                    P1=p1,V1=v1,V1_command=meta,formal_benchmark=False,
                    registered_input_sha256=receipt['registered_input_sha256'],
                    continuation_input_sha256=m['sha256'],
                    bitstream_sha256=sha(ROOT/'generate_bitstream/board_top.sbit'),
                    software_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in BUILD300.rglob('*') if p.is_file()},
                    old_artifacts_unchanged=True,current_git_unchanged=True,
                    serial_opened=False,PDS_started=False,board_300='NOT_RUN')
        write(OUT/'software_gate.json',gate)
        result.update(status='PASS',phase='DONE',software_gate_sha256=sha(OUT/'software_gate.json'),
                      old_run_result_not_modified=True,board_300='NOT_RUN')
        print('RESULT: PASS V1-only continuation; P1 reused; Zmmul300 ready for user board',flush=True)
    except Exception as exc:
        result.update(status='STOPPED_FIRST_FAILURE',error=f'{type(exc).__name__}: {exc}')
        print(result['error'],flush=True)
    finally:
        if not (OUT/'git_after.json').exists(): write(OUT/'git_after.json',git_snapshot())
        write(OUT/'result.json',result)
    return 0 if result['status']=='PASS' else 1


def old_inputs_rom(): return json.loads(read(original.MANIFEST))['unused_ROM_simulation_image']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check-inputs',action='store_true'); p.add_argument('--start',action='store_true')
    p.add_argument('--status',action='store_true'); p.add_argument('--worker',action='store_true'); p.add_argument('--tag')
    a = p.parse_args(); assert sum([a.check_inputs,a.start,a.status,a.worker])==1
    if a.status:
        assert a.tag==TAG
        print(read(OUT/'result.json') if (OUT/'result.json').exists() else 'NOT_STARTED'); return
    if a.worker:
        assert a.tag==TAG; sys.exit(worker())
    m,p1 = require_inputs()
    if a.check_inputs:
        print('INPUTS_MATCH_V1_ONLY_NOT_SIMULATED; reused compile/P1; timeout=3600s; 300 software ready'); return
    assert a.tag==TAG and pds_shell_count()==0
    active = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
               '(Get-Process -Name vsim,vsimk -ErrorAction SilentlyContinue | Measure-Object).Count'],
               capture_output=True,text=True,check=True,timeout=15)
    assert int(active.stdout.strip())==0, 'Existing ModelSim process: preserve it and stop'
    OUT.mkdir(parents=True,exist_ok=False)
    write(OUT/'result.json',dict(status='STARTED',phase='WORKER_LAUNCH',functional_status='INCOMPLETE',
          input_manifest_sha256=sha(MANIFEST),old_P1_native_exit='UNKNOWN',new_jobs=['validation_1'],
          pds_started=False,serial_opened=False,board_300='NOT_RUN'))
    argv = [sys.executable,'-B',str(Path(__file__).resolve()),'--worker','--tag',TAG]
    with (OUT/'worker.log').open('xb') as stream:
        proc = subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,
                 creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
    write(OUT/'worker_launch.json',dict(argv=argv,pid=proc.pid,stdout_native_to_file=True,
          parent_returns_without_wait=True,wall_time=time.time(),simulation_timeout_seconds=3600))
    print('STARTED V1 worker pid='+str(proc.pid)+'; use --status; do not start again')


if __name__ == '__main__': main()
