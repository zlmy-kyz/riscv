"""Audit Task026 compile failure without changing its original evidence directory."""
import json
import re
from run_response_turnover import ROOT,HERE,TAG,MANIFEST,MS,compile_argv,sha,read,write

PREP=HERE/'build/response_turnover_decl_resume_preparation_20261013_a'


def main():
    out=HERE/'build'/TAG;m=json.loads(read(MANIFEST))
    assert sha(MANIFEST)=='05989313a254c6c105ad9837b42f02e367e8949a0f7d616105207bdadec24cca'
    assert (out/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    result=json.loads(read(out/'result.json'));vlib=json.loads(read(out/'vlib.command.json'))
    compile_meta=json.loads(read(out/'compile.command.json'));log=read(out/'compile.log')
    assert result['status']=='STOPPED_FIRST_FAILURE' and result['manifest_sha256']==sha(MANIFEST)
    assert result['expected_checks']==1832 and not result['CPU_changed']
    assert vlib['argv']==[str(MS/'vlib.exe'),str(out/'work')]
    assert vlib['exit_code']==vlib['native_exit_after_wait']==0 and not vlib['timed_out']
    assert compile_meta['argv']==list(map(str,compile_argv(out,m)))
    assert compile_meta['exit_code']==compile_meta['native_exit_after_wait']==2 and not compile_meta['timed_out']
    assert compile_meta['timeout_seconds']==60 and 'Errors: 8, Warnings: 0' in log
    errors=re.findall(r"\(vlog-2388\) '(\w+)' already declared in this scope",log)
    assert errors==['biv','bdv','bdw','bia','bda','bwd','bws','bds']
    assert len(re.findall(r'-- Compiling module (\w+)',log))==20
    absent=['simulation.log','simulation.command.json','transcript','git_after.json']
    assert all(not (out/n).exists() for n in absent)
    for n in m['snapshot_files']:assert sha(out/'inputs'/n)==m['sha256'][n],n
    frozen_tb=read(out/'inputs/sim/mini_board_migration/tb_response_turnover_x32.sv')
    dut=frozen_tb.index('    dual_sram_to_pango_ddr_bridge #')
    for n in errors:
        decl=re.search(r'\bwire\s+(?:\[[^\]]+\]\s+)?'+n+r'\s*=',frozen_tb)
        assert decl and decl.start()>dut and frozen_tb.index('('+n+')')<decl.start(),n
    evidence={p.relative_to(ROOT).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
    PREP.mkdir(exist_ok=False)
    write(PREP/'failure_review.json',dict(status='RESPONSE_TURNOVER_TB_DECLARATION_ORDER_COMPILE_BLOCK_CONFIRMED',
        functional_status='NOT_RUN',checks_completed=0,expected_checks=1832,compile_exit=2,compile_errors=8,
        error_names=errors,attempted_modules=20,bridge_compile_diagnostic=False,
        frozen_copies_verified=len(m['snapshot_files']),missing_evidence=absent,git_before_after_equality='NOT_ESTABLISHED',
        original_manifest_sha256=sha(MANIFEST),original_failure_files_sha256=evidence,
        HDL_started_by_Codex=False,PDS_started=False,serial_opened=False,
        scope='TB declaration-order compile failure; bridge functionality remains unverified'))
    print('COMPILE_BLOCK_CONFIRMED checks=0/1832 frozen_copies=17 old_files=',len(evidence))


if __name__=='__main__':main()
