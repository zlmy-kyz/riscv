"""Finalize undispatched Task030 preparation after raw trace/cycle audit tightening."""
import ast,json
from run import ROOT,HERE,TAG,MANIFEST,sha,read,write,require_inputs
def main():
    assert not (HERE/'build'/TAG).exists(), 'Never change dispatched inputs'
    prep=HERE/'build/preparation_20261014_a';draft=prep/'draft_inputs.json'
    assert not draft.exists()
    m=json.loads(read(MANIFEST));changed={n for n,h in m['sha256'].items() if sha(ROOT/n)!=h}
    assert changed=={'sim/cpu_branch_turnover/tb_branch_turnover.sv','sim/cpu_branch_turnover/run.py','sim/cpu_branch_turnover/review.py'}
    draft.write_bytes(MANIFEST.read_bytes())
    name='sim/cpu_branch_turnover/finalize.py';m['sha256'][name]=sha(ROOT/name);m['snapshot_files'].append(name)
    for n in changed:m['sha256'][n]=sha(ROOT/n)
    for n in m['snapshot_files']:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    m['controlled_model_performance_check']='key flow_fast cycles < disabled control flow_fast cycles; not board score'
    write(MANIFEST,m);require_inputs()
    r=json.loads(read(prep/'static_review.json'))
    (prep/'draft_static_review.json').write_bytes((prep/'static_review.json').read_bytes())
    r.update(manifest_sha256=sha(MANIFEST),engineering_inputs=len(m['sha256']),snapshots=len(m['snapshot_files']),
        trace_outputs='actual DUT fields, masked IRQ PC/inst; independent oracle comparison',
        controlled_model_cycle_check=m['controlled_model_performance_check'],pre_dispatch_draft_preserved=True)
    write(prep/'static_review.json',r)
    print('TASK030_FINAL_STATIC_PASS SHA',sha(MANIFEST),'inputs',len(m['sha256']),'+5 snapshots',len(m['snapshot_files']),'modules',len(m['expected_modules']))
if __name__=='__main__':main()
