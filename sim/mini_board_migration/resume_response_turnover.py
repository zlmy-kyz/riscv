"""Task026 compile-block continuation: corrected declaration order, same suite."""
import json
from pathlib import Path
import run_response_turnover as original

ROOT=original.ROOT;HERE=original.HERE
MANIFEST=HERE/'response_turnover_decl_resume_inputs.json'
TAG='ds_mini_response_turnover_decl_resume_20261013_a'
LEGACY_MANIFEST=original.MANIFEST
original.MANIFEST=MANIFEST
original.TAG=TAG
original_require=original.require_inputs


def require_inputs():
    m=original_require()
    old=json.loads(original.read(LEGACY_MANIFEST))
    assert original.sha(LEGACY_MANIFEST)==m['original_manifest_sha256']
    assert m['source_sha256']==old['source_sha256'] and m['software_sha256']==old['software_sha256']
    assert m['groups']==old['groups'] and m['timeouts']==old['timeouts']
    assert m['compile_sources']==old['compile_sources'] and m['cpu_image']==old['cpu_image']
    changed={n for n,h in old['sha256'].items() if original.sha(ROOT/n)!=h}
    assert changed==set(m['allowed_legacy_changes'])
    folder=ROOT/m['original_failure_directory']
    files={p.relative_to(ROOT).as_posix():original.sha(p) for p in folder.rglob('*') if p.is_file()}
    assert files==m['original_failure_files_sha256'],'Original failure evidence changed'
    assert not (folder/'git_after.json').exists() and not (folder/'simulation.log').exists()
    old_tb=original.read(folder/'inputs/sim/mini_board_migration/tb_response_turnover_x32.sv')
    block=original.read(HERE/'response_turnover_cpu_mux.svh')
    assert old_tb.count(block+'\n')==1
    moved=old_tb.replace(block+'\n','',1)
    anchor='    dual_sram_to_pango_ddr_bridge #'
    assert moved.count(anchor)==1
    moved=moved.replace(anchor,block+'\n'+anchor,1)
    assert moved==original.read(HERE/'tb_response_turnover_x32.sv'),'TB changed beyond block movement'
    board_tool='tools/uart_loader/candidates/perf_2b/run_response_turnover_measurement.py'
    old_tool=original.read(folder/'inputs'/board_tool)
    assert original.read(ROOT/board_tool)==old_tool.replace(
        'ds_mini_response_turnover_20261013_a/codex_review.json',TAG+'/codex_review.json',1)
    return m


original.require_inputs=require_inputs
compile_argv=original.compile_argv
simulation_argv=original.simulation_argv
check_evidence=original.check_evidence


if __name__=='__main__':original.main()
