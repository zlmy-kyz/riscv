"""DeepSeek executes the sealed group exactly once; first failure is preserved."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from seal import HERE,ROOT,SEAL,TAG,MS,VENDOR,sha,closure,git_snapshot

MANIFEST=HERE/'inputs.json'
OUT=HERE/'build'/TAG

def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def require_inputs():
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert sha(SEAL/'inputs.json')==sha(MANIFEST),'Sealed manifest mismatch'
    for name,digest in manifest['project_sha256'].items():
        assert sha(ROOT/name)==digest,'Live input changed: '+name
        assert sha(SEAL/'project'/name)==digest,'Sealed input changed: '+name
    for name,digest in manifest['vendor_sha256'].items():
        assert sha(name)==digest,'Vendor changed: '+name
        assert sha(SEAL/'vendor'/Path(name).relative_to(VENDOR))==digest,'Sealed vendor changed'
    for name,digest in manifest['tool_sha256'].items():assert sha(name)==digest,'Tool changed: '+name
    assert sha(manifest['modelsim_ini']['path'])==manifest['modelsim_ini']['sha256']
    assert sha(SEAL/'tools/modelsim.ini')==manifest['modelsim_ini']['sha256']
    assert closure(SEAL/'project',manifest['compile_sources'])==manifest['include_dependencies']
    for top in ('tb_sccb.sv','tb_faults.sv','tb_soc.sv'):
        text=(SEAL/'project/sim/camera/key'/top).read_text()
        assert 'GTP_GRS GRS_INST' in text,'Missing required global reset instance'
    return manifest

def command(name,args,cwd,timeout):
    meta=dict(argv=[str(a) for a in args],cwd=str(cwd),timeout_seconds=timeout,start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    save(OUT/(name+'.command.json'),meta)
    start=time.monotonic()
    with (OUT/(name+'.stdout.log')).open('wb') as log:
        p=subprocess.Popen(meta['argv'],cwd=cwd,stdout=log,stderr=subprocess.STDOUT)
        try:
            code=p.wait(timeout=timeout);timed_out=False
        except subprocess.TimeoutExpired:
            # Kill child simulator processes as well, retaining the first failure log.
            subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=log,stderr=subprocess.STDOUT,check=False)
            p.wait();code=p.returncode;timed_out=True
    meta.update(returncode=code,timed_out=timed_out,elapsed_seconds=time.monotonic()-start)
    save(OUT/(name+'.command.json'),meta)
    assert not timed_out and code==0,f'{name}: native exit {code}; timeout={timed_out}'
    text=(OUT/(name+'.stdout.log')).read_text(encoding='utf-8',errors='replace')
    assert not any(s in text for s in ('** Error','** Fatal','Error loading design','RESULT: FAIL')),name+' raw error'
    return text

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check-inputs',action='store_true');ap.add_argument('--plan-only',action='store_true')
    a=ap.parse_args();m=require_inputs()
    assert not OUT.exists(),'Run directory exists: preserve first run, no retry'
    if a.check_inputs or a.plan_only:
        print(json.dumps(dict(status='INPUT_IDENTITY_INCLUDE_GRS_CHECK_PASS_HDL_NOT_RUN',tag=TAG,
                              manifest_sha256=sha(MANIFEST),jobs=['vlib','compile',*m['tops']],timeouts=m['timeouts'])))
        return
    OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',manifest_sha256=sha(MANIFEST),completed=[],HDL='NOT_RUN',PDS='NOT_RUN',board='NOT_RUN')
    before=git_snapshot();save(OUT/'git_before.json',before);save(OUT/'result.json',result)
    try:
        project=OUT/'inputs/project';vendor=OUT/'inputs/vendor'
        shutil.copytree(SEAL/'project',project);shutil.copytree(SEAL/'vendor',vendor)
        shutil.copyfile(MANIFEST,OUT/'inputs.json')
        shutil.copytree(SEAL/'tools',OUT/'inputs/tools')
        for n,d in m['project_sha256'].items():assert sha(project/n)==d
        for n,d in m['vendor_sha256'].items():assert sha(vendor/Path(n).relative_to(VENDOR))==d
        assert closure(project,m['compile_sources'])==m['include_dependencies']
        # Use a private modelsim.ini; never write into the repository or PDS installation.
        shutil.copyfile(OUT/'inputs/tools/modelsim.ini',OUT/'modelsim.ini')
        command('vlib',[MS/'vlib.exe',OUT/'work'],OUT,m['timeouts']['vlib'])
        result['HDL']='COMPILE_STARTED';save(OUT/'result.json',result)
        command('compile',[MS/'vlog.exe','-sv','-work',OUT/'work',
                *['+incdir+'+(project/d).as_posix() for d in m['include_dirs']],
                '+incdir+'+vendor.as_posix(),
                *[vendor/Path(n).relative_to(VENDOR) for n in m['vendor_compile_sources']],
                *[project/n for n in m['compile_sources']]],OUT,m['timeouts']['compile'])
        compile_text=(OUT/'compile.stdout.log').read_text(errors='replace')
        assert 'Errors: 0, Warnings: 0' in compile_text,'Compile diagnostics not clean'
        compiled=re.findall(r'-- Compiling module (\w+)',compile_text)
        assert sorted(compiled)==sorted(m['compiled_module_names']+['GTP_GRS','GTP_DRM36K_E1','GTP_APM_E2']), 'Module closure mismatch'
        for name,top in m['tops'].items():
            gen=project/'sim/camera/key/generated'
            command(name,[MS/'vsim.exe','-batch','-modelsimini',OUT/'modelsim.ini','-lib',OUT/'work',top,
                    '+CONFIG='+(gen/'config.hex').as_posix(),'+DAT='+(gen/'cpu.dat').as_posix(),
                    '+FRAME1='+(gen/'frame1.hex').as_posix(),'+FRAME2='+(gen/'frame2.hex').as_posix(),
                    '+BUS='+(OUT/'bus.log').as_posix(),'+CPU='+(OUT/'cpu.log').as_posix(),
                    *(['+DVP='+(OUT/'dvp.log').as_posix()] if name=='soc' else []),
                    '-logfile',OUT/(name+'.transcript'),'-do','onerror {quit -code 3 -f}; run -all; quit -f'],
                    OUT,m['timeouts'][name])
            command(name+'_check',[sys.executable,project/'sim/camera/key/check_evidence.py','--out',OUT,'--job',name],
                    project,m['timeouts']['check'])
            result['completed'].append(name);save(OUT/'result.json',result)
        require_inputs()
        result.update(status='CAMERA_KEY_EXECUTION_AND_RAW_CHECK_PASS_PENDING_SOL_REVIEW',HDL='EXECUTED',
                      limitations='Native user-port model, no PHY/physical sensor/board pass')
    except BaseException as exc:
        result.update(status='STOPPED_FIRST_FAILURE',failure=repr(exc))
        raise
    finally:
        after=git_snapshot();save(OUT/'git_after.json',after)
        identity={n:sha(ROOT/n) if (ROOT/n).is_file() else 'MISSING' for n in m['project_sha256']}
        save(OUT/'input_identity_after.json',identity)
        if identity!=m['project_sha256'] or before['head']!=after['head'] or before['diff']!=after['diff']:
            result['status']='STOPPED_FIRST_FAILURE';result['input_or_design_changed']=True
        save(OUT/'result.json',result)
        # Bind every emitted evidence file, including failed command records and partial traces.
        evidence={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file() and
                  not p.is_relative_to(OUT/'work') and not p.is_relative_to(OUT/'inputs') and p.name!='evidence_sha256.json'}
        save(OUT/'evidence_sha256.json',evidence)
    print(result['status'])

if __name__=='__main__':main()
