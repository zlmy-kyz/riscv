"""Sol prepares/seals the single boundary test; DeepSeek executes three jobs once."""
import argparse
import ast
import json
import re
import shutil
from pathlib import Path
import run as base
from check_inst_lookup_triple import PLAN, review

ROOT, HERE, MS = base.ROOT, base.HERE, base.MS
TAG='ds_data_bus_inst_lookup_triple_20261014_a'
MANIFEST=HERE/'inputs_inst_lookup_triple.json'
PREVIOUS=HERE/'inputs_inst_lookup_protocol_completion.json'
PREVIOUS_SHA='d9d215eaa72e84aeeda76fee4c777f2d6f2a0d0a58ed279b666a962434ca1cb7'
RECEIPT=HERE/'build/protocol_completion_review_20261014_a/evidence_review.json'
OLD_TB='sim/data_bus_turnover/tb_inst_lookup_protocol_completion.sv'
TB='sim/data_bus_turnover/tb_inst_lookup_triple.sv'
FILES=[TB,'sim/data_bus_turnover/check_inst_lookup_triple.py',
       'sim/data_bus_turnover/run_inst_lookup_triple.py']
BRIDGE='myriscv/dual_sram_to_pango_ddr_bridge.v'
BRIDGE_SHA='f14b16cb97fa24fd17050995a1b254933aea5bca3b4a071a33712c7a17c52ba0'
JOBS=['vlib','compile','triple']


def build_manifest():
    assert base.sha(PREVIOUS)==PREVIOUS_SHA
    previous=json.loads(base.common.read(PREVIOUS))
    receipt=json.loads(base.common.read(RECEIPT))
    assert receipt['status']=='TASK032_COMPLETION_RAW_PASS_ACCEPTANCE_BLOCKED_OLD_HIT_DUAL_REQUEST'
    project=dict(previous['project_sha256'])
    for name in FILES:
        assert name not in project
        project[name]=base.sha(ROOT/name)
    protected=dict(previous['protected_evidence_sha256'])
    extra=dict(receipt['prior_files_sha256'])
    for p in RECEIPT.parent.iterdir():
        if p.is_file(): extra[p.relative_to(ROOT).as_posix()]=base.sha(p)
    for name in ('check_reference_synthetic.py','synthetic_reference_qa.json'):
        p=HERE/'build/triple_preparation_20261014_a'/name
        extra[p.relative_to(ROOT).as_posix()]=base.sha(p)
    for name,digest in extra.items():
        assert name not in protected or protected[name]==digest
        protected[name]=digest
    sources=[TB if n==OLD_TB else n for n in previous['compile_sources']]
    modules=['tb_inst_lookup_triple' if n=='tb_inst_lookup_protocol_completion' else n
             for n in previous['expected_modules']]
    return dict(tag=TAG,roles=dict(RTL='other GPT-6 Astra conversation',
                    test_code='GPT-6.1 Sol',execution='DeepSeek'),
        previous_manifest=PREVIOUS.relative_to(ROOT).as_posix(),previous_manifest_sha256=PREVIOUS_SHA,
        review_receipt=RECEIPT.relative_to(ROOT).as_posix(),review_receipt_sha256=base.sha(RECEIPT),
        project_sha256=project,vendor_sha256=previous['vendor_sha256'],
        tool_sha256=previous['tool_sha256'],protected_evidence_sha256=protected,
        compile_sources=sources,expected_modules=modules,
        include_dependencies=base.check_includes(ROOT,sources),jobs=JOBS,
        timeouts=dict(vlib=60,compile=60,triple=180),stimulus_plan=PLAN,
        coverage_contract=dict(triple_hit_dual_d_wins=1,accepts=4,responses=4,ar=2,r=2,aw=1,w=1,
                               held_I_must_miss_after_store=True,old_and_new_data_must_differ=True),
        reused_key=receipt['checked_key'],reused_A=receipt['checked_A'],reused_B=receipt['checked_B'],
        changed_design_files=[],bridge_sha256=BRIDGE_SHA,
        user_reported_pds_timing='PASS_REPORTED_BY_USER_NOT_INDEPENDENTLY_REVIEWED')


def require_inputs():
    data=json.loads(base.common.read(MANIFEST))
    assert data==build_manifest(), 'Manifest differs from the pre-execution contract'
    assert len(data['project_sha256'])==199 and len(data['expected_modules'])==39
    assert data['jobs']==JOBS and base.sha(ROOT/BRIDGE)==BRIDGE_SHA
    assert 'doc/CODEX_HANDOFF.md' not in data['protected_evidence_sha256']
    for name,digest in data['project_sha256'].items():
        assert base.sha(ROOT/name)==digest, 'Changed input: '+name
        if name.endswith('.py'): ast.parse(base.common.read(ROOT/name),filename=name)
    for name,digest in {**data['vendor_sha256'],**data['tool_sha256']}.items():
        assert base.sha(name)==digest,name
    for name,digest in data['protected_evidence_sha256'].items():
        assert base.sha(ROOT/name)==digest,'Changed old evidence: '+name
    assert len(data['include_dependencies'])==5
    assert 'GTP_GRS GRS_INST' in base.common.read(ROOT/TB)
    for name in ('ipcore/inst_rom/rtl/inst_rom_init_param.v',
                 'ipcore/data_ram/rtl/data_ram_init_param.v'):
        assert name in data['project_sha256']
    return data


def snapshot(out,data):
    project=out/'inputs/project'
    for name,digest in data['project_sha256'].items():
        dst=project/name; dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dst)
        assert base.sha(dst)==digest
    for name,digest in data['vendor_sha256'].items():
        dst=out/'inputs/vendor'/Path(name).name; dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(name,dst)
        assert base.sha(dst)==digest
    shutil.copyfile(MANIFEST,out/'inputs.json')
    assert base.sha(out/'inputs.json')==base.sha(MANIFEST)
    assert base.check_includes(project,data['compile_sources'])==data['include_dependencies']
    return project


def sim_command(out):
    return [MS/'vsim.exe','-batch','-lib',out/'work','tb_inst_lookup_triple',
            '+EDGE_LOG='+str(out/'edge.log'),'+PLAN_LOG='+str(out/'plan.log'),
            '-logfile',out/'triple.transcript','-do','run -all; quit -f']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seal',action='store_true')
    p.add_argument('--check-inputs',action='store_true')
    p.add_argument('--tag',default=TAG)
    a=p.parse_args()
    assert a.tag==TAG
    if a.seal:
        value=build_manifest()
        if MANIFEST.exists(): assert json.loads(base.common.read(MANIFEST))==value,'Preserve frozen manifest'
        else: base.common.save(MANIFEST,value)
    data=require_inputs()
    if a.seal or a.check_inputs:
        print('Static inputs verified; HDL NOT_RUN; '+str(len(data['project_sha256']))+' project / '+
              str(len(data['protected_evidence_sha256']))+' protected; one 4-token case; manifest '+base.sha(MANIFEST))
        return
    out=HERE/'build'/TAG
    assert not out.exists(),'Preserve run directory; no retry or reuse'
    before=base.common.git_snapshot()
    out.mkdir(exist_ok=False)
    result=dict(status='RUNNING',manifest_sha256=base.sha(MANIFEST),completed={},
                HDL_started=False,PDS_started=False,serial_opened=False,board='NOT_RUN',
                changed_design_files=[],key_A_B_reused=True)
    base.common.save(out/'git_before.json',before)
    base.common.save(out/'result.json',result)
    try:
        project=snapshot(out,data)
        result['HDL_started']=True
        base.common.save(out/'result.json',result)
        base.common.command([MS/'vlib.exe',out/'work'],out,out/'vlib',60)
        log=base.common.command(base.compile_command(out,project,data),out,out/'compile',60)
        modules=re.findall(r'-- Compiling module (\w+)',log)
        assert len(modules)==39 and set(modules)==set(data['expected_modules'])
        assert 'Errors: 0, Warnings: 0' in log
        base.common.command(sim_command(out),out,out/'triple',180)
        console=base.common.read(out/'triple.log')
        assert console.strip()==base.common.read(out/'triple.transcript').strip()
        assert '$finish' in console and 'Errors: 0, Warnings: 0' in console
        assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT',console)
        assert re.findall(r'IPSpecCheck: (\d+)',console)==['04030130']*2
        assert console.count('RESULT: PASS inst_lookup_triple accepts=4 responses=4 aw=1 w=1')==1
        result['completed']['triple']=review(out/'edge.log',out/'plan.log')
        assert require_inputs()==data
        assert base.common.git_snapshot()==before,'Worktree changed during run'
        result['status']='TASK032_TRIPLE_SUPPLEMENT_PASS_REUSED_KEY_A_B'
    except Exception as exc:
        result.update(status='STOPPED_FIRST_FAILURE',error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        try:
            after=base.common.git_snapshot()
            base.common.save(out/'git_after.json',after)
            result['git_unchanged']=before==after
        except Exception as exc:
            result['git_after_error']=str(exc)
        try:
            result['inputs_after']=require_inputs()==data
        except Exception as exc:
            result['inputs_after']=False; result['inputs_after_error']=str(exc)
        if result['status']=='TASK032_TRIPLE_SUPPLEMENT_PASS_REUSED_KEY_A_B' and not (
                result.get('git_unchanged') and result.get('inputs_after')):
            result['status']='STOPPED_FIRST_FAILURE'
        base.common.save(out/'result.json',result)
    assert result['status']=='TASK032_TRIPLE_SUPPLEMENT_PASS_REUSED_KEY_A_B'
    print('RESULT: PASS single triple-boundary supplement; waiting for Codex raw review')


if __name__=='__main__': main()
