"""Read-only V1 continuation audit; no simulation, PDS or serial."""
import json
from resume_coremark_v1 import ROOT, OUT, MANIFEST, sha, read, write, require_inputs, evidence


def main():
    destination = OUT/'codex_review.json'; assert not destination.exists()
    m,p1 = require_inputs()
    result = json.loads(read(OUT/'result.json'))
    assert result['status']=='PASS' and result['phase']=='DONE'
    assert result['input_manifest_sha256']==sha(MANIFEST)
    assert (OUT/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    for n in m['snapshot_new_files']: assert sha(OUT/'new_inputs'/n)==m['sha256'][n]
    v1 = evidence(OUT/'validation_1','validation')
    assert result['reused_P1']==p1 and result['V1']==v1
    assert json.loads(read(OUT/'validation_1/crc_review.json'))==v1
    before,after = [json.loads(read(OUT/name)) for name in ['git_before.json','git_after.json']]
    assert before==after
    meta = json.loads(read(OUT/'validation_1/simulation.command.json'))
    planned = json.loads(read(OUT/'planned_simulation.json'))
    assert meta['exit_code']==meta['native_exit_after_wait']==0 and not meta['timed_out']
    assert 0 < meta['seconds'] < meta['timeout_seconds']==3600
    assert meta['argv']==planned['argv'] and meta['cwd']==planned['cwd']
    assert meta['stdout_direct_to_file'] and meta['cleanup'] is None
    gate_path = OUT/'software_gate.json'; gate = json.loads(read(gate_path))
    assert sha(gate_path)==result['software_gate_sha256']
    assert gate['status']=='ZMMUL_P_V_SHORT_CRC_GATE_PASS_300_READY_FOR_USER_BOARD'
    assert gate['P1']==p1 and gate['V1']==v1 and gate['V1_command']==meta
    assert gate['continuation_input_sha256']==m['sha256']
    for n,h in {**gate['registered_input_sha256'],**gate['software_sha256']}.items(): assert sha(ROOT/n)==h
    assert sha(ROOT/'generate_bitstream/board_top.sbit')==gate['bitstream_sha256']
    review = dict(status='ZMMUL_P_V_SHORT_CRC_AND_300_HANDOFF_RAW_EVIDENCE_REVIEW_PASS',
             P1_reused=p1,V1=v1,V1_native_command=meta,software_gate_sha256=sha(gate_path),
             original_P1_native_exit='UNKNOWN_NOT_RECONSTRUCTED',old_orchestration_not_rewritten=True,
             old_artifacts_checked=len(m['original_artifact_sha256']),new_inputs_checked=len(m['sha256']),
             git_unchanged=True,original_logs_unchanged=True,HDL_started=False,PDS_started=False,
             serial_opened=False,board_300='NOT_RUN',formal_benchmark=False)
    write(destination,review); print(review['status'])


if __name__=='__main__': main()
