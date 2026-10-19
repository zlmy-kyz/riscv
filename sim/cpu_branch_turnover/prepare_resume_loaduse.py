"""Freeze one stimulus profile fix and formal key/ISA continuation only."""
import ast,json
import resume_loaduse as resume
from run import require_inputs as old_inputs,MANIFEST as OLD,check_job,TAG as OLD_TAG
ROOT=resume.ROOT;HERE=resume.HERE;sha=resume.sha;read=resume.read;write=resume.write
def main():
    assert not resume.MANIFEST.exists() and not (HERE/'build'/resume.TAG).exists()
    old=old_inputs();prep=HERE/'build/loaduse_resume_preparation_20261014_a'
    diagnosis=prep/'diagnosis_review.json';d=json.loads(read(diagnosis))
    for n,h in d['evidence_sha256'].items():assert sha(ROOT/n)==h,n
    rows=[row.split() for row in read(ROOT/old['key_specs']).splitlines()]
    assert rows[4][0]=='load_branch_jalr' and rows[4][1]=='1';rows[4][1]='0'
    spec=prep/'key_specs_profile0.txt';assert not spec.exists();spec.write_text(''.join(' '.join(r)+'\n' for r in rows),encoding='utf-8')
    plan=json.loads(json.dumps(old['plan']));plan['cases'][4]['profile']=0
    new=['sim/cpu_branch_turnover/'+n for n in ('resume_loaduse.py','review_resume_loaduse.py','prepare_resume_loaduse.py','review_load_diagnosis.py')]
    new += [spec.relative_to(ROOT).as_posix(),'tools/uart_loader/candidates/perf_2b/run_branch_loaduse_resume_measurement.py',
            'tools/uart_loader/candidates/perf_2b/run_branch_loaduse_resume_measurements.ps1']
    files={**old['sha256'],**d['evidence_sha256'],OLD.relative_to(ROOT).as_posix():sha(OLD),diagnosis.relative_to(ROOT).as_posix():sha(diagnosis)}
    for n in new:
        files[n]=sha(ROOT/n)
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    m=dict(status='LOAD_USE_FORMAL_RESUME_PREPARED_HDL_NOT_RUN',fixed_tag=resume.TAG,original_manifest_sha256=sha(OLD),
        sha256=files,external_sha256=old['external_sha256'],source_sha256=old['source_sha256'],software_sha256=old['software_sha256'],
        compile_sources=old['compile_sources'],vendor_compile_sources=old['vendor_compile_sources'],expected_modules=old['expected_modules'],
        snapshot_files=old['snapshot_files']+new,plan=plan,key_specs=spec.relative_to(ROOT).as_posix(),
        reused_control=check_job(HERE/'build'/OLD_TAG,old,'control'),historical_evidence_sha256=d['evidence_sha256'],
        scope='Original CPU branch target turnover RTL/TB/oracles; only load-use stimulus profile fixed; key455 + two ISA samples; no SoC/PHY/PDS/board')
    write(resume.MANIFEST,m);resume.require_inputs()
    write(prep/'static_review.json',dict(status='LOAD_USE_RESUME_STATIC_PREPARATION_PASS_HDL_NOT_RUN',manifest_sha256=sha(resume.MANIFEST),
        engineering_inputs=len(files),external_inputs=5,snapshots=len(m['snapshot_files']),modules=16,
        only_stimulus_change='load_branch_jalr profile1 to profile0',RTL_changed=False,TB_changed=False,oracle_changed=False,thresholds_changed=False,
        key_events=455,reused_control_events=94,ISA_seed=2026101430,ISA_samples=['auipc','sb'],HDL_started=False,PDS_started=False,serial_opened=False))
    print('LOAD_USE_FORMAL_RESUME_STATIC_PASS SHA',sha(resume.MANIFEST),'inputs',len(files),'+5 snapshots',len(m['snapshot_files']),'modules16')
if __name__=='__main__':main()
