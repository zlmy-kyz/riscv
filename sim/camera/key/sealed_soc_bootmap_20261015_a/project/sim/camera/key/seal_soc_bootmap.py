"""Sol-only reseal: TB memory-map repair, SoC only, preserve both failed runs."""
import ast
import copy
import json
import re
import shutil
from pathlib import Path
from seal import HERE,ROOT,VENDOR,sha,closure,git_snapshot
from run_soc_bootmap import TAG,SEAL,MANIFEST

PRIOR=HERE/'inputs_ini_resume.json'
OLD=HERE/'build/ds_camera_ini_resume_20261015_a'
REVIEW=HERE/'review_soc_bootmap_20261015_a'
PREP=HERE/'preparation_soc_bootmap_20261015_a'

def main():
    assert not SEAL.exists() and not MANIFEST.exists(),'Preserve all sealed identities'
    old=json.loads(PRIOR.read_text(encoding='utf-8'))
    assert sha(PRIOR)=='0cadecef11c33d41d52b233a9aa629a51791843756f235c829c3fa32c08ce3f7'
    for folder in (ROOT,HERE/'sealed_ini_resume_20261015_a/project',OLD/'inputs/project'):
        for name,d in old['project_sha256'].items():assert sha(folder/name)==d,(folder,name)
    review=json.loads((REVIEW/'review.json').read_text(encoding='utf-8'))
    assert review['status']=='CAMERA_SCCB_FAULTS_RAW_REVIEW_PASS_SOC_BLOCKED_BY_TEST_BOOT_MAP'
    assert review['functional_pass']['sccb']['cases']==7 and review['functional_pass']['faults']['cases']==8
    for name,d in review['evidence_sha256'].items():assert sha(ROOT/name)==d,name
    static=json.loads((PREP/'static_review.json').read_text(encoding='utf-8'))
    assert static['compiled_modules']==55 and static['compile_exit']==0 and not static['HDL_run']
    assert 'Errors: 0, Warnings: 0' in (PREP/'compile.log').read_text(encoding='utf-8')
    sources=old['compile_sources'].copy()
    source_old='sim/camera/key/tb_soc.sv';source_new='sim/camera/key/tb_soc_bootmap.sv'
    assert sources.count(source_old)==1;sources[sources.index(source_old)]=source_new
    assert [(a,b) for a,b in zip(old['compile_sources'],sources) if a!=b]==[(source_old,source_new)]
    tb=(ROOT/source_new).read_text(encoding='utf-8')
    assert "defparam dut.u_soc.INST_ROM_BASE=32'h00000000;" in tb
    assert "defparam dut.u_soc.DATA_RAM_BASE=32'h00000000;" in tb
    assert 'TRAP cycle=' in tb and 'first retired instruction differs' in tb
    assert (HERE/'generated/cpu.dat').read_text(encoding='utf-8').splitlines()[0]=='10002437'
    names=set(old['project_sha256'])
    names.update(p.relative_to(ROOT).as_posix() for p in OLD.iterdir() if p.is_file())
    names.update(p.relative_to(ROOT).as_posix() for p in REVIEW.iterdir() if p.is_file())
    names.update(p.relative_to(ROOT).as_posix() for p in PREP.iterdir() if p.is_file() and p.suffix in ('.json','.log'))
    names.update(['sim/camera/key/inputs_ini_resume.json',source_new,'sim/camera/key/run_soc_bootmap.py',
                  'sim/camera/key/seal_soc_bootmap.py','DeepSeek/相机首版_SoC启动映射修复_仅SoC续测_2026-10-15.md'])
    for n in ['run_soc_bootmap.py','seal_soc_bootmap.py']:ast.parse((HERE/n).read_text(encoding='utf-8'))
    m=copy.deepcopy(old)
    m.pop('only_execution_change',None);m.pop('reason_no_functional_reuse',None)
    m.update(status='CAMERA_SOC_BOOTMAP_TB_REPAIR_SEALED_HDL_NOT_RUN',tag=TAG,
             prior_manifest_sha256=sha(PRIOR),prior_failed_run=OLD.relative_to(ROOT).as_posix(),
             raw_failure_review_sha256=sha(REVIEW/'review.json'),jobs_reused=['sccb','faults'],
             reused_functional_results=review['functional_pass'],
             test_only_change='Explicit ROM/RAM bases=0 in DDR-boot TB; first fetch/retire guards and trap diagnostics',
             reason_for_resume='Old TB aliased ROM and RAM at RESET_PC=40000000; intended DDR program was not fetched',
             HDL='NOT_RUN',PDS='NOT_RUN',board='NOT_RUN')
    m['compile_sources']=sources;m['tops']={'soc':'tb_camera_soc_bootmap'}
    m['test_overrides']=old['test_overrides']+['TB-only soc_top.INST_ROM_BASE=0 and DATA_RAM_BASE=0, RESET_PC remains 40000000']
    m['compiled_module_names']=sorted('tb_camera_soc_bootmap' if n=='tb_camera_soc' else n for n in old['compiled_module_names'])
    m['project_sha256']={name:sha(ROOT/name) for name in sorted(names)}
    m['protected_evidence_sha256'].update({p.relative_to(ROOT).as_posix():sha(p) for p in OLD.iterdir() if p.is_file()})
    m['include_dependencies']=closure(ROOT,sources)
    assert m['include_dependencies']==old['include_dependencies'] and m['timeouts']==old['timeouts']
    assert len(sources)==49 and len(m['compiled_module_names'])+3==55
    for n,d in {**m['vendor_sha256'],**m['tool_sha256']}.items():assert sha(n)==d,n
    SEAL.mkdir(exist_ok=False)
    (SEAL/'worktree_before.json').write_text(json.dumps(git_snapshot(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for n,d in m['project_sha256'].items():
        target=SEAL/'project'/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,target)
        assert sha(target)==d
    for n,d in m['vendor_sha256'].items():
        target=SEAL/'vendor'/Path(n).relative_to(VENDOR);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(n,target);assert sha(target)==d
    (SEAL/'tools').mkdir();shutil.copyfile(m['modelsim_ini']['path'],SEAL/'tools/modelsim.ini')
    assert sha(SEAL/'tools/modelsim.ini')==m['modelsim_ini']['sha256']
    assert closure(SEAL/'project',sources)==m['include_dependencies']
    for p in (MANIFEST,SEAL/'inputs.json'):
        with p.open('x',encoding='utf-8') as f:json.dump(m,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(dict(status=m['status'],manifest_sha256=sha(MANIFEST),project=len(names),old_inputs_unchanged=len(old['project_sha256']),
                         jobs=['vlib','compile','soc'],reused=['sccb','faults'],new_run_directory_exists=(HERE/'build'/TAG).exists())))

if __name__=='__main__':main()
