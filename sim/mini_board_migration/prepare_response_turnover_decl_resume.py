"""Freeze declaration-order-only correction and immutable compile-failure evidence."""
import ast
import json
import re
from pathlib import Path
from generate_response_turnover_tb import build_tb
from run_response_turnover import ROOT,HERE,sha,read,write

TAG='ds_mini_response_turnover_decl_resume_20261013_a'
MANIFEST=HERE/'response_turnover_decl_resume_inputs.json'
PREP=HERE/'build/response_turnover_decl_resume_preparation_20261013_a'


def main():
    assert not MANIFEST.exists() and not (HERE/'build'/TAG).exists()
    legacy=HERE/'response_turnover_inputs.json';old=json.loads(read(legacy))
    failure=json.loads(read(PREP/'failure_review.json'))
    assert failure['status']=='RESPONSE_TURNOVER_TB_DECLARATION_ORDER_COMPILE_BLOCK_CONFIRMED'
    assert failure['original_manifest_sha256']==sha(legacy)
    old_folder=HERE/'build'/old['fixed_tag']
    for n,h in failure['original_failure_files_sha256'].items():assert sha(ROOT/n)==h,n
    tb=HERE/'tb_response_turnover_x32.sv'
    old_tb=read(old_folder/'inputs/sim/mini_board_migration/tb_response_turnover_x32.sv')
    assert tb.read_bytes()==(old_folder/'inputs/sim/mini_board_migration/tb_response_turnover_x32.sv').read_bytes()
    block=read(HERE/'response_turnover_cpu_mux.svh')
    moved=old_tb.replace(block+'\n','',1)
    anchor='    dual_sram_to_pango_ddr_bridge #'
    moved=moved.replace(anchor,block+'\n'+anchor,1)
    generated=build_tb();assert generated==moved
    for n in ['biv','bdv','bdw','bia','bda','bwd','bws','bds']:
        decl=re.search(r'\bwire\s+(?:\[[^\]]+\]\s+)?'+n+r'\s*=',generated)
        assert decl and decl.start()<generated.index('('+n+')'),n
    tb.write_text(generated,encoding='utf-8')
    allowed=['sim/mini_board_migration/tb_response_turnover_x32.sv',
             'sim/mini_board_migration/generate_response_turnover_tb.py',
             'tools/uart_loader/candidates/perf_2b/run_response_turnover_measurement.py']
    changed={n for n,h in old['sha256'].items() if sha(ROOT/n)!=h}
    assert changed==set(allowed),changed
    extra=['sim/mini_board_migration/'+n for n in ['resume_response_turnover.py',
        'review_response_turnover_decl_resume.py','prepare_response_turnover_decl_resume.py',
        'review_response_turnover_compile_failure.py']]
    extra += ['sim/mini_board_migration/response_turnover_inputs.json',
        'sim/mini_board_migration/build/response_turnover_decl_resume_preparation_20261013_a/failure_review.json',
        'DeepSeek/任务026_结果_ds_mini_response_turnover_20261013_a.md']
    files=set(old['sha256'])|set(extra)|set(failure['original_failure_files_sha256'])
    snapshots=old['snapshot_files']+extra[:4]
    m={**old,'status':'RESPONSE_TURNOVER_DECLARATION_ORDER_RESUME_PREPARED_HDL_NOT_RUN',
       'fixed_tag':TAG,'sha256':{n:sha(ROOT/n) for n in sorted(files)},'snapshot_files':snapshots,
       'original_manifest_sha256':sha(legacy),'allowed_legacy_changes':allowed,
       'original_failure_directory':old_folder.relative_to(ROOT).as_posix(),
       'original_failure_files_sha256':failure['original_failure_files_sha256']}
    for n in snapshots:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    write(MANIFEST,m)
    write(PREP/'static_review.json',dict(status='RESPONSE_TURNOVER_DECLARATION_ORDER_STATIC_REPAIR_PASS_HDL_NOT_RUN',
        manifest_sha256=sha(MANIFEST),bridge_sha256=m['source_sha256']['myriscv/dual_sram_to_pango_ddr_bridge.v'],
        CPU_sha256=m['source_sha256']['myriscv/mycpu_sync.v'],legacy_changes=allowed,
        cases_CPU_image_groups_timeouts_unchanged=True,TB_exact_block_movement=True,
        declaration_before_port_use_verified=8,original_failure_files_unchanged=len(failure['original_failure_files_sha256']),
        inputs=len(files),external_inputs=len(m['external_sha256']),snapshots=len(snapshots),
        HDL_started=False,PDS_started=False,serial_opened=False))
    print('RESUME_FROZEN',len(files),'external',len(m['external_sha256']),'snapshots',len(snapshots),'SHA',sha(MANIFEST))


if __name__=='__main__':main()
