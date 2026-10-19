"""Independent raw Task025 review; no HDL/PDS/serial."""
import json
from run_data_write_hit import ROOT,HERE,TAG,MANIFEST,require_inputs,check_evidence,sha,read,write


def main():
    m=require_inputs();out=HERE/'build'/TAG;target=out/'codex_review.json';assert not target.exists()
    result=json.loads(read(out/'result.json'))
    assert result['status']=='DATA_WRITE_HIT_KEY_TEST_PASS' and result['manifest_sha256']==sha(MANIFEST)
    counts=check_evidence(out,m)
    for k,v in counts.items():assert result[k]==v
    assert json.loads(read(out/'git_before.json'))==json.loads(read(out/'git_after.json'))
    assert (out/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    for n in m['snapshot_files']:assert sha(out/'inputs'/n)==m['sha256'][n]
    commands={}
    for step,limit in [('vlib',60),('compile',60),('simulation',180)]:
        meta=json.loads(read(out/(step+'.command.json')))
        assert meta['exit_code']==meta['native_exit_after_wait']==0 and not meta['timed_out']
        assert meta['timeout_seconds']==limit and 0<meta['seconds']<limit
        assert meta['stdout_direct_to_file'] and meta['cleanup'] is None
        commands[step]=meta
    assert 'Errors: 0, Warnings: 0' in read(out/'compile.log')
    from run_data_write_hit import MS,VENDOR
    expected_compile=[str(MS/'vlog.exe'),'-sv','-work',str(out/'work'),str(VENDOR/'GTP_GRS.v'),
                      str(VENDOR/'GTP_DRM36K_E1.v'),*[str(ROOT/n) for n in m['compile_sources']]]
    assert commands['compile']['argv']==expected_compile
    assert commands['simulation']['argv']==[str(MS/'vsim.exe'),'-batch','-lib',str(out/'work'),
           'tb_data_write_hit_x32','-logfile',str(out/'transcript'),'-do','run -all; quit -f']
    evidence={p.relative_to(ROOT).as_posix():sha(p) for p in [out/'result.json',out/'simulation.log',
              out/'transcript',out/'compile.log',out/'simulation.command.json']}
    write(target,dict(status='DATA_WRITE_HIT_RAW_EVIDENCE_REVIEW_PASS',**counts,
                      groups=m['groups'],commands=commands,bridge_sha256=m['sha256']['myriscv/dual_sram_to_pango_ddr_bridge.v'],
                      evidence_sha256=evidence,inputs_unchanged=True,git_unchanged=True,CPU_changed=False,
                      HDL_started=False,PDS_started=False,serial_opened=False,scope='x32 bridge/real I-D DRM only; no SoC execution/PHY/timing/board'))
    print('DATA_WRITE_HIT_RAW_EVIDENCE_REVIEW_PASS')


if __name__=='__main__':main()
