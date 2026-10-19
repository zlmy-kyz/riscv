"""Sol-only single-use reseal: preserve the A failure and all unchanged DUT tests."""
import ast
import copy
import json
import shutil
from pathlib import Path
from seal import HERE,ROOT,VENDOR,sha,closure,git_snapshot
from run_ini_resume import TAG,SEAL,MANIFEST,rewrite_argv

PRIOR=HERE/'inputs.json'
OLD=HERE/'build/ds_camera_key_20261015_a'
REVIEW=HERE/'review_first_failure_20261015_a'

def main():
    assert not SEAL.exists() and not MANIFEST.exists(),'Never replace a sealed identity'
    old=json.loads(PRIOR.read_text(encoding='utf-8'))
    assert sha(PRIOR)=='859fca5ca0e87c77976b3d3fbe3d80d408c37bb8e62ad9e720ca1d549e3064d3'
    for root in (ROOT,HERE/'sealed_20261015_a/project',OLD/'inputs/project'):
        for name,digest in old['project_sha256'].items():assert sha(root/name)==digest,(root,name)
    receipt=json.loads((REVIEW/'review.json').read_text(encoding='utf-8'))
    assert receipt['tested_functional_cases']==0 and receipt['compiled_modules']==55
    assert receipt['status']=='CAMERA_FIRST_FAILURE_RAW_REVIEW_CONFIRMED_RUNNER_INI_ARGUMENT_ERROR_NO_DUT_EXECUTION'
    probe=json.loads((REVIEW/'startup_probe.command.json').read_text())
    assert probe['returncode']==0 and 'run -all' not in ' '.join(probe['argv'])
    assert 'Errors: 0, Warnings: 0' in (REVIEW/'startup_probe.stdout.log').read_text()
    # Exactly one argv item changes for a simulation job; other commands stay identical.
    argv=receipt['commands']['sccb']['argv'];fixed=rewrite_argv('sccb',argv,OLD)
    assert [(a,b) for a,b in zip(argv,fixed) if a!=b]==[(str(OLD/'modelsim.ini'),'modelsim.ini')]
    assert rewrite_argv('compile',receipt['commands']['compile']['argv'],OLD)==receipt['commands']['compile']['argv']
    names=set(old['project_sha256'])
    names.update(p.relative_to(ROOT).as_posix() for p in OLD.iterdir() if p.is_file())
    names.update(p.relative_to(ROOT).as_posix() for p in REVIEW.rglob('*') if p.is_file())
    names.update(['sim/camera/key/inputs.json','sim/camera/key/run_ini_resume.py','sim/camera/key/seal_ini_resume.py',
                  'DeepSeek/相机首版_INI启动参数修复续测_2026-10-15.md'])
    for p in [HERE/'run_ini_resume.py',HERE/'seal_ini_resume.py']:ast.parse(p.read_text(encoding='utf-8'))
    m=copy.deepcopy(old)
    m.update(status='CAMERA_INI_ARGUMENT_REPAIR_SEALED_HDL_NOT_RUN',tag=TAG,
             prior_manifest_sha256=sha(PRIOR),prior_failed_run=OLD.relative_to(ROOT).as_posix(),
             raw_failure_review_sha256=sha(REVIEW/'review.json'),
             only_execution_change='vsim -modelsimini absolute-path -> modelsim.ini in private run cwd',
             jobs_reused=[],reason_no_functional_reuse='A stopped before design load; all three feature jobs remain unexecuted',
             HDL='NOT_RUN',PDS='NOT_RUN',board='NOT_RUN')
    m['project_sha256']={name:sha(ROOT/name) for name in sorted(names)}
    m['protected_evidence_sha256'].update({p.relative_to(ROOT).as_posix():sha(p) for p in OLD.iterdir() if p.is_file()})
    assert m['compile_sources']==old['compile_sources'] and m['include_dependencies']==old['include_dependencies']
    assert m['timeouts']==old['timeouts'] and m['compiled_module_names']==old['compiled_module_names']
    for name,digest in {**m['vendor_sha256'],**m['tool_sha256']}.items():assert sha(name)==digest
    assert sha(m['modelsim_ini']['path'])==m['modelsim_ini']['sha256']
    SEAL.mkdir(exist_ok=False)
    (SEAL/'worktree_before.json').write_text(json.dumps(git_snapshot(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name,digest in m['project_sha256'].items():
        target=SEAL/'project'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        assert sha(target)==digest
    for name,digest in m['vendor_sha256'].items():
        target=SEAL/'vendor'/Path(name).relative_to(VENDOR);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(name,target);assert sha(target)==digest
    (SEAL/'tools').mkdir()
    shutil.copyfile(m['modelsim_ini']['path'],SEAL/'tools/modelsim.ini')
    assert closure(SEAL/'project',m['compile_sources'])==m['include_dependencies']
    for p in (MANIFEST,SEAL/'inputs.json'):
        with p.open('x',encoding='utf-8') as f:json.dump(m,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(dict(status=m['status'],manifest_sha256=sha(MANIFEST),project=len(names),
                         old_inputs_unchanged=len(old['project_sha256']),compile_sources=49,compiled_modules=55,
                         simulated_functional_cases=0,new_run_directory_exists=(HERE/'build'/TAG).exists())))

if __name__=='__main__':main()
