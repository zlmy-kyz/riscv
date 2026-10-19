"""Task024: new Zmmul P/V one-iteration CRC on real CPU/I64-D64/IP + DDR model."""
from pathlib import Path
import argparse
import ast
import json
import re
import shutil
import sys
from resume_isa import ROOT, HERE, MS, VENDOR, command, pds_shell_count, git_snapshot, read, write, sha
sys.path.insert(0,str(ROOT/'tests/cpu_performance_2b'))
from zmmul_software import BUILD_DIR, require_manifest, parse_measurement

MANIFEST=HERE/'coremark_crc_inputs.json'
TAG='ds_cpu_zmmul_coremark_crc_20261013_a'


def require_inputs():
    m=json.loads(read(MANIFEST))
    for n,h in m['sha256'].items():assert sha(ROOT/n)==h,'Changed CRC input: '+n
    for n,h in m['external_sha256'].items():assert sha(n)==h,'Changed external input: '+n
    receipt=json.loads(read(ROOT/m['cpu_functional_review']))
    assert receipt['status']=='CPU_ZMMUL_KEY_FUNCTION_AND_TWO_ISA_RAW_EVIDENCE_REVIEW_PASS'
    assert receipt['cpu_sha256']==sha(ROOT/'myriscv/mycpu_sync.v')
    for n in ['performance_1','validation_1','performance_120','validation_120']:
        info=require_manifest(BUILD_DIR/n/'manifest.json')
        assert info['bytes']<16368
    assert m['unused_ROM_simulation_image'] in m['sha256']
    for mode in m['modes']:
        info=require_manifest(BUILD_DIR/(mode+'_1')/'manifest.json')
        payload=(ROOT/info['bin_path']).read_bytes()
        words=[int(w,16) for w in read(HERE/'fixtures'/f'coremark_{mode}_1.dat').split()]
        count=len(payload)//4
        assert len(payload)%4==0 and len(words)==4096 and words[4092]==count
        assert b''.join(w.to_bytes(4,'little') for w in words[:count])==payload
        assert all(w==0 for i,w in enumerate(words[count:],count) if i!=4092)
        hot=[int(w,16) for w in read(HERE/'fixtures'/f'coremark_{mode}_mul_pcs.hex').split()]
        assert len(hot)==len(set(hot))==5 and set(hot)<=set(s['pc'] for s in info['multiply_sites'])
    assert m['modes']==['performance','validation'] and m['simulation_timeout_seconds']==900
    assert m['max_cycles']==60000000 and m['isa_samples']==[]
    ast.parse(read(HERE/'run_coremark_crc.py'))
    return m


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag');p.add_argument('--check-inputs',action='store_true');a=p.parse_args();m=require_inputs()
    if a.check_inputs:
        print('INPUTS_MATCH_ZMMUL_COREMARK_CRC_NOT_SIMULATED',len(m['sha256']),'real_mul_I_D_IP P/V1 only; 900s vsim');return
    assert a.tag==TAG and pds_shell_count()==0
    out=HERE/'build'/TAG;out.mkdir(parents=True,exist_ok=False);work=out/'work'
    before=git_snapshot();write(out/'git_before.json',before)
    result=dict(status='RUNNING',completed=[],input_manifest_sha256=sha(MANIFEST),HDL_scope='New Zmmul CRC only',
                pds_started=False,serial_opened=False,formal_benchmark=False,board_status='NOT_TESTED')
    write(out/'result.json',result)
    try:
        # Prior design snapshots remain in 023; freeze only new TB/entry/software.
        shutil.copyfile(MANIFEST,out/'inputs.json')
        for n in m['new_snapshot_files']:
            target=out/'new_inputs'/n;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/n,target);assert sha(target)==m['sha256'][n]
        write(out/'source_identity.json',m['sha256'])
        command([MS/'vlib.exe',work],out,out/'vlib',60)
        output=command([MS/'vlog.exe','-sv','-work',work,'+incdir+'+(ROOT/'myriscv').as_posix(),
                        *[Path(n) for n in m['vendor_compile_sources']],*[ROOT/n for n in m['compile_sources']]],out,out/'compile',60)
        assert 'Errors: 0, Warnings: 0' in output
        for mode in m['modes']:
            name=mode+'_1';folder=out/name;folder.mkdir();info=require_manifest(BUILD_DIR/name/'manifest.json')
            plus=['+ROM='+str(ROOT/m['unused_ROM_simulation_image']),'+DAT='+str(HERE/'fixtures'/f'coremark_{mode}_1.dat'),
                  f'+DONE={info["symbols"]["program_return"]:08x}','+OUT='+str(folder),'+MAX_CYCLES=60000000',
                  '+HOT_PC_FILE='+str(HERE/'fixtures'/f'coremark_{mode}_mul_pcs.hex')]
            transcript=folder/'transcript'
            print('START new Zmmul',name,'CRC only',flush=True)
            output=command([MS/'vsim.exe','-batch','-lib',work,'tb_coremark_zmmul',*plus,
                            '-logfile',transcript,'-do','run -all; quit -f'],folder,folder/'simulation',900)
            for text in [output,read(transcript)]:
                assert text.count('RESULT: PASS coremark_zmmul_direct')==1 and '$finish' in text
                assert 'Errors: 0, Warnings: 0' in text and not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT',text)
            assert output.replace('\r\n','\n').strip()==read(transcript).replace('\r\n','\n').strip()
            parsed=parse_measurement(info,(folder/'uart.txt').read_bytes(),board=False)
            assert parsed['formal_benchmark']==False
            observed=re.findall(r'RESULT: PASS coremark_zmmul_direct cycles=(\d+) retired=(\d+) AR=(\d+) AW=(\d+) UART=(\d+) MUL=(\d+) MATRIX_MUL=(\d+)',output)
            assert len(observed)==1 and all(int(x)>0 for x in observed[0])
            record=dict(mode=mode,status='NEW_ZMMUL_ONE_ITERATION_CRC_AND_COUNTERS_PASS',parsed=parsed,
                        evidence=observed[0],bin_sha256=info['bin_sha256'],model_performance_not_board=True)
            write(folder/'crc_review.json',record);result['completed'].append(record);write(out/'result.json',result)
        require_inputs();after=git_snapshot();write(out/'git_after.json',after);assert after==before
        result.update(status='PASS',software_status='NEW_ZMMUL_P_V_SHORT_CRC_PASS',fixed_120_status='Not simulated; identical code to short BIN, original seed4=120 retained',
                      scope='Direct preloaded CPU/SoC and x32 DDR model; real MUL/I/D primitives, no Loader/PHY/board',formal_benchmark=False)
        print('RESULT: PASS new Zmmul P/V short CRC; DDR board performance NOT_TESTED',flush=True)
    except Exception as exc:
        result.update(status='STOPPED_FIRST_FAILURE',error=f'{type(exc).__name__}: {exc}');raise
    finally:write(out/'result.json',result)


if __name__=='__main__':main()
