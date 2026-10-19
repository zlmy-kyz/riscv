"""Sol raw review of immutable A first failure; no HDL execution or writes into old run."""
import json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE));import check
import hashlib
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    a=ROOT/'sim/camera_double/key_20261016_a';run=a/'build/ds_abi2_key_20261016_a';dest=HERE/'review_a';dest.mkdir(exist_ok=False)
    m=json.loads((a/'inputs.json').read_text(encoding='utf-8'));identity='639c6ace530086754a673e65e90d2c9fe59119f10223a87417658c59c40fda7a'
    assert sha(a/'inputs.json')==sha(a/'sealed_20261016_a/inputs.json')==sha(run/'inputs.json')==identity
    for base in (ROOT,a/'sealed_20261016_a/project',run/'inputs/project'):
        for n,d in m['project_sha256'].items():assert sha(base/n)==d,(base,n)
    for n,d in m['protected_history_sha256'].items():assert sha(ROOT/n)==d,n
    for n,d in m['vendor_sha256'].items():
        assert sha(n)==d
        rel=Path(n).relative_to(Path(n).parent)
        for base in (a/'sealed_20261016_a/vendor',run/'inputs/vendor'):assert sha(base/rel)==d
    for n,d in m['tool_sha256'].items():assert sha(n)==d,n
    for f in (Path(m['modelsim_ini']['path']),a/'sealed_20261016_a/tools/modelsim.ini',run/'modelsim.ini'):
        assert sha(f)==m['modelsim_ini']['sha256']
    evidence=json.loads((run/'evidence_sha256.json').read_text())
    for n,d in evidence.items():assert sha(run/n)==d,n
    assert (run/'git_before.json').read_bytes()==(run/'git_after.json').read_bytes()
    assert json.loads((run/'input_identity_after.json').read_text(encoding='utf-8'))==m['project_sha256']
    assert json.loads((run/'protected_history_identity_after.json').read_text(encoding='utf-8'))==m['protected_history_sha256']
    commands={n:json.loads((run/(n+'.command.json')).read_text()) for n in ('vlib','compile','unit','unit_check')}
    assert all(commands[n]['returncode']==0 and not commands[n]['timed_out'] for n in ('vlib','compile','unit'))
    assert commands['unit_check']['returncode']==1 and not commands['unit_check']['timed_out']
    compile_text=(run/'compile.stdout.log').read_text();assert 'Errors: 0, Warnings: 0' in compile_text
    assert len(re.findall(r'-- Compiling module ',compile_text))==54
    stdout=(run/'unit.stdout.log').read_text();assert 'RESULT: PASS ABI2_OWNERSHIP_FAULTS_PERMISSIONS' in stdout
    assert re.findall(r'Errors:\s*(\d+)',stdout)==['0']
    assert not any(s in stdout for s in ('** Error','** Fatal','RESULT: FAIL'))
    result=check.check_unit(run);result['DVP_frames']=check.data_input(run/'unit.dvp.log','unit')
    # Demonstrate that the actual edge/data/CRC/timing criteria still reject corruption.
    original=(run/'unit.log').read_text()
    class File:
        def __init__(self,s):self.s=s
        def read_text(self,*a,**k):return self.s
    class Fixture:
        def __init__(self,s):self.s=s
        def __truediv__(self,n):return File(self.s if n=='unit.log' else stdout)
    lines=original.splitlines();negative={}
    variants={}
    i=next(i for i,l in enumerate(lines) if l.startswith('EDGE '));variants['missing_warmup_edge']='\n'.join(lines[:i]+lines[i+1:])
    i=next(i for i,l in enumerate(lines) if l.startswith('PUB '));r=lines[i].split()
    changed=r.copy();changed[-1]='10';v=lines.copy();v[i]=' '.join(changed);variants['wrong_post_reset_dropped']='\n'.join(v)
    changed=r.copy();changed[5]=f'{int(r[5],16)^1:08x}';v=lines.copy();v[i]=' '.join(changed);variants['wrong_capture_CRC']='\n'.join(v)
    changed=r.copy();changed[6]=r[2];v=lines.copy();v[i]=' '.join(changed);variants['publication_not_after_actual_W']='\n'.join(v)
    i=next(i for i,l in enumerate(lines) if l.startswith('W '));r=lines[i].split();r[-1]=f'{int(r[-1],16)^1:064x}';v=lines.copy();v[i]=' '.join(r);variants['corrupt_DMA_byte']='\n'.join(v)
    for name,text in variants.items():
        try:check.check_unit(Fixture(text))
        except AssertionError:negative[name]='REJECTED'
        else:raise AssertionError('negative accepted: '+name)
    assert sha(run/'result.json')==evidence['result.json'] and not (run/'soc.command.json').exists()
    receipt=dict(status='ABI2_A_RAW_REVIEW_UNIT_PASS_TEST_POST_RESET_EXPECTATION_BUG_SOC_NOT_RUN',date='2026-10-16',
       original_manifest_sha256=identity,project_files=308,input_copies_checked=3,evidence_files_checked=len(evidence),
       protected_history_files=len(m['protected_history_sha256']),input_vendor_tools_INI_Git_match=True,
       original_result='STOPPED_FIRST_FAILURE_UNCHANGED',compile_modules=54,compile_errors=0,compile_warnings=0,
       unit_native=0,unit_seconds=commands['unit']['elapsed_seconds'],unit_errors=0,unit_warnings=int(re.findall(r'Warnings:\s*(\d+)',stdout)[-1]),
       failure='Old checker expected dropped=10 at first post-publication sample; async capture reset makes it 0',
       lifecycle='camera_mmio sets busy=0 at publication; capture_resetn=resetn&&busy asserts wr_reset_pipe reset; ov5640_capture dropped resets before TB #0.001 sample',
       first_pub=dict(input_pattern=1,buffer=0,seq=1,CRC='e9ee1be4',cycle=724182,last_actual_W=724173,dropped_after_reset=0,actual_frame_start_edges=11),
       corrected_independent_replay=result,negative_checks=negative,checker_sha256=sha(HERE/'check.py'),reviewer_sha256=sha(Path(__file__)),
       original_evidence_sha256=evidence,soc='NOT_RUN',board='NOT_RUN',Full_Boot='NOT_RUN',PHY='NOT_RUN',RTL_modified=False,HDL_rerun=False,
       decision='Reuse unchanged original unit trace with new checker; new frozen identity and fresh directory for only unexecuted SoC plus unit recheck; no board release')
    (dest/'review.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],review_sha256=sha(dest/'review.json'),unit_replay=result,negative_checks=negative),indent=2))
if __name__=='__main__':main()
