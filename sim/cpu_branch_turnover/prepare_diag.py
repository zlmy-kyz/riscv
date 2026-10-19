"""Freeze only a fail-path observation clone; preserve Task030 and first failure."""
import json,ast
import run_diag as d
def main():
    assert not d.MANIFEST.exists() and not (d.HERE/'build'/d.TAG).exists()
    old=d.original.require_inputs();prep=d.HERE/'build/coverage_diag_preparation_20261014_a'
    receipt=prep/'old_failure_review.json';r=json.loads(d.read(receipt))
    for n,h in r['old_evidence_sha256'].items():assert d.sha(d.ROOT/n)==h,n
    tb=d.HERE/'tb_branch_turnover_diag.sv';assert not tb.exists();tb.write_text(d.diagnostic_tb(),encoding='utf-8')
    new=['sim/cpu_branch_turnover/'+n for n in ('run_diag.py','review_diag.py','prepare_diag.py','review_failure.py','tb_branch_turnover_diag.sv')]
    for n in new:
        if n.endswith('.py'):ast.parse(d.read(d.ROOT/n))
    files={**old['sha256'],**r['old_evidence_sha256']}
    files[d.original.MANIFEST.relative_to(d.ROOT).as_posix()]=d.sha(d.original.MANIFEST)
    files[receipt.relative_to(d.ROOT).as_posix()]=d.sha(receipt)
    for n in new:files[n]=d.sha(d.ROOT/n)
    sources=[n.replace('tb_branch_turnover.sv','tb_branch_turnover_diag.sv') for n in old['compile_sources']]
    modules=[n.replace('tb_branch_turnover','tb_branch_turnover_diag') for n in old['expected_modules']]
    m=dict(status='COVERAGE_DIAGNOSTIC_PREPARED_HDL_NOT_RUN',fixed_tag=d.TAG,
        original_manifest_sha256=d.sha(d.original.MANIFEST),sha256=files,external_sha256=old['external_sha256'],
        compile_sources=sources,vendor_compile_sources=old['vendor_compile_sources'],expected_modules=modules,
        snapshot_files=new,key_specs=old['key_specs'],RTL_changed=False,model_changed=False,thresholds_changed=False,
        scope='One key diagnostic only; reused control94/key455 architectural evidence; original coverage gates and ISA/board still incomplete')
    d.write(d.MANIFEST,m);d.require_inputs()
    d.write(prep/'static_review.json',dict(status='COVERAGE_DIAGNOSTIC_STATIC_READY_NOT_RUN',manifest_sha256=d.sha(d.MANIFEST),
        engineering_inputs=len(files),external_inputs=len(m['external_sha256']),snapshots=len(new),modules=16,
        old_files_preserved=len(r['old_evidence_sha256']),RTL_changed=False,model_changed=False,thresholds_changed=False,
        changes='module name and fail-path display only',HDL_started=False,PDS_started=False,serial_opened=False))
    print('COVERAGE_DIAGNOSTIC_STATIC_READY SHA',d.sha(d.MANIFEST),'inputs',len(files),'+5 snapshots5 modules16')
if __name__=='__main__':main()
