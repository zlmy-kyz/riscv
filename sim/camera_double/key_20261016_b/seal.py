"""New identity for checker lifecycle repair; original A code/seal/failure evidence stay untouched."""
import ast,importlib.util,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];A=ROOT/'sim/camera_double/key_20261016_a'
spec=importlib.util.spec_from_file_location('abi2_original_seal',A/'seal.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
MS=old.MS;VENDOR=old.VENDOR;sha=old.sha;save=old.save;git=old.git;closure=old.closure
TAG='ds_abi2_soc_resume_20261016_b';SEAL=HERE/'sealed_20261016_b'
def main():
    assert not SEAL.exists() and not (HERE/'inputs.json').exists()
    m=json.loads((A/'inputs.json').read_text(encoding='utf-8'))
    parent='639c6ace530086754a673e65e90d2c9fe59119f10223a87417658c59c40fda7a'
    assert sha(A/'inputs.json')==sha(A/'sealed_20261016_a/inputs.json')==parent
    for n,d in m['project_sha256'].items():assert sha(ROOT/n)==d,n
    run=A/'build/ds_abi2_key_20261016_a';evidence=json.loads((run/'evidence_sha256.json').read_text())
    for n,d in evidence.items():assert sha(run/n)==d,n
    review=HERE/'review_a/review.json';r=json.loads(review.read_text())
    assert r['status']=='ABI2_A_RAW_REVIEW_UNIT_PASS_TEST_POST_RESET_EXPECTATION_BUG_SOC_NOT_RUN' and sha(HERE/'check.py')==r['checker_sha256']
    names=set(m['project_sha256'])
    names.update(p.relative_to(ROOT).as_posix() for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.md'))
    names.add(review.relative_to(ROOT).as_posix())
    names.update(p.relative_to(ROOT).as_posix() for p in review.parent.iterdir() if p.is_file())
    names.add('DeepSeek/双缓冲ABI2_发布后计数检查修复_仅SoC续测_2026-10-16.md')
    # Consume existing raw traces from the new frozen input copy. Do not repeat unit HDL.
    for n in ('unit.log','unit.dvp.log','unit.stdout.log','unit.command.json','unit_check.stdout.log','result.json','inputs.json','evidence_sha256.json'):
        names.add((run/n).relative_to(ROOT).as_posix())
    protected=dict(m['protected_history_sha256'])
    for p in (A/'inputs.json',A/'sealed_20261016_a/inputs.json'):
        protected[p.relative_to(ROOT).as_posix()]=sha(p)
        names.add(p.relative_to(ROOT).as_posix())
    for n,d in evidence.items():protected[(run/n).relative_to(ROOT).as_posix()]=d
    protected[(run/'evidence_sha256.json').relative_to(ROOT).as_posix()]=sha(run/'evidence_sha256.json')
    for n,d in protected.items():assert sha(ROOT/n)==d,n
    m.update(status='ABI2_POST_RESET_CHECKER_FIX_SEALED_SOC_NOT_RUN',date='2026-10-16',tag=TAG,
        parent_manifest_sha256=parent,project_sha256={n:sha(ROOT/n) for n in sorted(names)},protected_history_sha256=protected,
        jobs=dict(soc='tb_double_soc'),reuse_unit_path=run.relative_to(ROOT).as_posix(),
        unit_reuse_review_sha256=sha(review),checker='sim/camera_double/key_20261016_b/check.py',
        changes=['Checker post-publication dropped must be 0 after async reset, independent external EDGE counts 11/1 remain mandatory',
                 'Checker report directory permits unit raw replay without modifying original evidence',
                 'Replay existing unit input trace, then compile identical HDL and execute only never-run SoC'],
        HDL='SOC_NOT_RUN_UNIT_REUSED_REVIEWED',board='NOT_RUN')
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    SEAL.mkdir(exist_ok=False);save(SEAL/'worktree.json',git())
    for n,d in m['project_sha256'].items():
        dst=SEAL/'project'/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dst);assert sha(dst)==d
    shutil.copytree(A/'sealed_20261016_a/vendor',SEAL/'vendor');shutil.copytree(A/'sealed_20261016_a/tools',SEAL/'tools')
    assert closure(SEAL/'project',m['compile_sources'])==m['include_dependencies']
    save(HERE/'inputs.json',m);save(SEAL/'inputs.json',m)
    print(json.dumps(dict(status=m['status'],manifest_sha256=sha(HERE/'inputs.json'),project_files=len(names),protected_files=len(protected))))
if __name__=='__main__':main()
