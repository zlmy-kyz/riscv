"""DeepSeek rechecks preserved unit raw trace then executes only unrun SoC with the fixed checker."""
import argparse,json,re,shutil,subprocess,sys,time
from pathlib import Path
from seal import HERE,ROOT,SEAL,TAG,MS,VENDOR,sha,save,git,closure
OUT=HERE/'build'/TAG
def require():
    p=HERE/'inputs.json';m=json.loads(p.read_text(encoding='utf-8'));assert sha(p)==sha(SEAL/'inputs.json')
    for n,d in m['project_sha256'].items():assert sha(ROOT/n)==sha(SEAL/'project'/n)==d,n
    for n,d in m['protected_history_sha256'].items():assert sha(ROOT/n)==d,n
    for n,d in m['vendor_sha256'].items():assert sha(n)==sha(SEAL/'vendor'/Path(n).relative_to(VENDOR))==d,n
    for n,d in m['tool_sha256'].items():assert sha(n)==d,n
    assert sha(m['modelsim_ini']['path'])==sha(SEAL/'tools/modelsim.ini')==m['modelsim_ini']['sha256']
    assert closure(SEAL/'project',m['compile_sources'])==m['include_dependencies']
    for n in ('tb_unit.sv','tb_soc.sv'):assert 'GTP_GRS GRS_INST' in (SEAL/'project/sim/camera_double/key_20261016_a'/n).read_text()
    return m
def command(name,argv,cwd,timeout):
    meta=dict(argv=list(map(str,argv)),cwd=str(cwd),timeout_seconds=timeout,start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    save(OUT/(name+'.command.json'),meta);start=time.monotonic()
    with (OUT/(name+'.stdout.log')).open('wb') as f:
        p=subprocess.Popen(meta['argv'],cwd=cwd,stdout=f,stderr=subprocess.STDOUT)
        try:code=p.wait(timeout);timed=False
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=f,stderr=subprocess.STDOUT);p.wait();code=p.returncode;timed=True
    meta.update(returncode=code,timed_out=timed,elapsed_seconds=time.monotonic()-start);save(OUT/(name+'.command.json'),meta)
    assert code==0 and not timed,(name,code,timed)
    text=(OUT/(name+'.stdout.log')).read_text(errors='replace')
    assert not any(s in text for s in ('** Error','** Fatal','Error loading design','RESULT: FAIL')),(name,'raw failure')
    return text
def main():
    p=argparse.ArgumentParser();p.add_argument('--check-inputs',action='store_true');p.add_argument('--plan-only',action='store_true');a=p.parse_args();m=require()
    assert not OUT.exists(),'first run directory exists; do not retry/overwrite'
    if a.check_inputs or a.plan_only:print(json.dumps(dict(status='ABI2_IDENTITY_INCLUDE_GRS_PASS_NOT_RUN',manifest_sha256=sha(HERE/'inputs.json'),jobs=['unit_recheck','vlib','compile','soc','soc_check'],timeouts=m['timeouts'])));return
    OUT.mkdir(parents=True,exist_ok=False);result=dict(status='RUNNING',manifest_sha256=sha(HERE/'inputs.json'),completed=[],PDS='NOT_RUN',board='NOT_RUN');save(OUT/'result.json',result);before=git();save(OUT/'git_before.json',before)
    try:
        shutil.copytree(SEAL/'project',OUT/'inputs/project');shutil.copytree(SEAL/'vendor',OUT/'inputs/vendor');shutil.copytree(SEAL/'tools',OUT/'inputs/tools');shutil.copyfile(HERE/'inputs.json',OUT/'inputs.json')
        project=OUT/'inputs/project';vendor=OUT/'inputs/vendor'
        for n,d in m['project_sha256'].items():assert sha(project/n)==d,n
        assert closure(project,m['compile_sources'])==m['include_dependencies']
        shutil.copyfile(SEAL/'tools/modelsim.ini',OUT/'modelsim.ini')
        command('unit_recheck',[sys.executable,project/'sim/camera_double/key_20261016_b/check.py','--out',project/m['reuse_unit_path'],'--job','unit','--report-dir',OUT],project,120)
        result['completed'].append('unit_recheck');save(OUT/'result.json',result)
        command('vlib',[MS/'vlib.exe',OUT/'work'],OUT,60)
        text=command('compile',[MS/'vlog.exe','-sv','-work',OUT/'work',*['+incdir+'+(project/d).as_posix() for d in m['include_dirs']],
            '+incdir+'+vendor.as_posix(),*[vendor/Path(n).relative_to(VENDOR) for n in m['vendor_compile_sources']],*[project/n for n in m['compile_sources']]],OUT,180)
        assert 'Errors: 0, Warnings: 0' in text
        assert sorted(re.findall(r'-- Compiling module (\w+)',text))==sorted(m['modules']+['GTP_GRS','GTP_DRM36K_E1','GTP_APM_E2'])
        for name,top in m['jobs'].items():
            sim_text=command(name,[MS/'vsim.exe','-batch','-modelsimini','modelsim.ini','-lib',OUT/'work',top,
                '+CONFIG='+(project/'sim/camera/key/generated/config.hex').as_posix(),
                '+DAT='+(project/'sim/camera_double/key_20261016_a/generated/cpu.dat').as_posix(),
                '+BUS='+(OUT/'bus.log').as_posix(),'+CPU='+(OUT/'cpu.log').as_posix(),'+UNIT='+(OUT/'unit.log').as_posix(),
                '+DVP='+(OUT/(name+'.dvp.log')).as_posix(),'-logfile',OUT/(name+'.transcript'),'-do','onerror {quit -code 3 -f}; run -all; quit -f'],OUT,m['timeouts'][name])
            counts=re.findall(r'Errors:\s*(\d+)',sim_text)
            assert counts and all(int(n)==0 for n in counts),(name,'ModelSim Errors summary')
            command(name+'_check',[sys.executable,project/'sim/camera_double/key_20261016_b/check.py','--out',OUT,'--job',name],project,120)
            result['completed'].append(name);save(OUT/'result.json',result)
        require();result['status']='ABI2_SOC_RESUME_CHECKED_PENDING_SOL_REVIEW'
    except BaseException as exc:result.update(status='STOPPED_FIRST_FAILURE',failure=repr(exc));raise
    finally:
        after=git();save(OUT/'git_after.json',after)
        identity={n:sha(ROOT/n) if (ROOT/n).is_file() else 'MISSING' for n in m['project_sha256']};save(OUT/'input_identity_after.json',identity)
        protected={n:sha(ROOT/n) if (ROOT/n).is_file() else 'MISSING' for n in m['protected_history_sha256']};save(OUT/'protected_history_identity_after.json',protected)
        if identity!=m['project_sha256'] or protected!=m['protected_history_sha256'] or before['head']!=after['head'] or before['diff']!=after['diff']:result['status']='STOPPED_FIRST_FAILURE';result['identity_changed']=True
        save(OUT/'result.json',result)
        save(OUT/'evidence_sha256.json',{p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file() and not p.is_relative_to(OUT/'inputs') and not p.is_relative_to(OUT/'work') and p.name!='evidence_sha256.json'})
if __name__=='__main__':main()
