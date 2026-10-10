"""Freeze unified BSP inputs after reviewed builds and focused real-CPU validation."""
from pathlib import Path
import json,shutil,sys
import run
ROOT=run.ROOT;OUT=ROOT/'sim/bsp_workflow/build'
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
from application import require_manifest
from upload import sha,BIT
def main():
    gate=OUT/'deployment_gate.json';assert not gate.exists()
    selected={'hello':'v1/hello_native','crc32':'v1/crc32_fast','irq_probe':'v3/irq_probe_fast',
              'performance_1':'v1/performance_1_fast','validation_1':'v1/validation_1_fast',
              'performance_60':'v1/performance_60_fast','validation_60':'v1/validation_60_fast','timer_wrap':'wrap1/hello_fast'}
    inputs={};evidence={};manifests={};results={}
    for name,folder in selected.items():
        base=OUT/folder;report=json.loads((base/'results.json').read_text())
        assert report['status']=='SAME_LOADER_APPLICATION_SIM_PASS' and report['protected_unchanged'] and report['inputs_unchanged']
        for path,h in report['input_sha256'].items():assert sha(ROOT/path)==h;inputs[path]=h
        for path,h in report['protected_sha256'].items():assert sha(ROOT/path)==h,path
        for path in base.iterdir():
            if path.is_file():evidence[path.relative_to(ROOT).as_posix()]=sha(path)
        assert report['timer_scale']==1
        if name=='hello':assert report['transport']=='115200_REAL_PINS'
        if name.endswith('_1'):assert report['application_result']['status']=='COREMARK_CRC_FUNCTIONAL_PASS'
        if name.endswith('_60'):assert report['partial'] and report['application_result']=='UART_LOAD_VERIFY_RUN_STARTUP_MAIN_PASS_NOT_FULL_BENCHMARK'
        results[name]=dict(path=(base/'results.json').relative_to(ROOT).as_posix(),scope=report['application_result'],evidence=report['evidence'])
    for name in run.NAMES:
        manifest=run.manifest(name);info=require_manifest(manifest)
        if name!='irq_probe':manifests[manifest.relative_to(ROOT).as_posix()]=sha(manifest)
        receipt=json.loads(manifest.with_name('build_receipt.json').read_text())
        assert receipt['status']=='UNIFIED_BSP_BUILD_PASS' and receipt['application_info']==info
        for p,h in receipt['source_sha256'].items():assert sha(ROOT/p)==h;inputs[p]=h
    for file,status,count in [('pc_offline.json','APPLICATIONS_PC_OFFLINE_PASS',30),('pc_controls.json','APPLICATIONS_CLI_OFFLINE_PASS',7),('pc_images.json','UNIFIED_BSP_IMAGE_NEGATIVE_PASS',6),('pc_suite_v3.json','UNIFIED_BSP_SUITE_OFFLINE_PASS',11)]:
        p=OUT/file;r=json.loads(p.read_text());assert r['status']==status and r['count']==count and not r['serial_opened']
        evidence[p.relative_to(ROOT).as_posix()]=sha(p)
    oldpath=ROOT/'sim/uart_loader/build/applications_stage3/deployment_gate.json';old=json.loads(oldpath.read_text())
    for field in ('input_sha256','evidence_sha256'):
        for path,h in old[field].items():assert sha(ROOT/path)==h
    oldreceipt=ROOT/'sim/uart_loader/board/applications_stage3_submission_result.json'
    receipt=json.loads(oldreceipt.read_text());assert receipt['status']=='SECOND_PROGRAM_AND_COREMARK_ACTUAL_BOARD_ARCHIVE_PASS'
    for row in receipt['success_archive_entries']:assert sha(ROOT/row['archive'])==row['sha256']
    assert sha(BIT)==receipt['downloaded_bitstream_identity']['sha256']
    inputs.update(old['input_sha256'])
    for directory in ('tests/bsp_workflow','tools/uart_loader/candidates/bsp_workflow','sim/bsp_workflow'):
        for path in (ROOT/directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.md' and not (directory=='sim/bsp_workflow' and ('build' in path.relative_to(ROOT/directory).parts or 'board' in path.relative_to(ROOT/directory).parts)):
                inputs[path.relative_to(ROOT).as_posix()]=sha(path)
    for path in (BIT,oldpath,oldreceipt):inputs[path.relative_to(ROOT).as_posix()]=sha(path)
    snapshot=OUT/'frozen_inputs';assert not snapshot.exists();copies=[]
    for path,h in sorted(inputs.items()):
        dest=snapshot/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,dest);assert sha(dest)==h
        copies.append(dict(source=path,archive=dest.relative_to(ROOT).as_posix(),sha256=h))
    result=dict(status='UNIFIED_BSP_SIM_PASS',date='2026-10-10',board_result='NOT_TESTED',
                manifests=manifests,input_sha256=inputs,evidence_sha256=evidence,frozen_source_copies=copies,
                simulation_results=results,PC_offline_checks=54,successful_bitstream_sha256=sha(BIT),old_success_snapshot_checked=len(receipt['success_archive_entries']),
                CPU_RTL_modified=False,DDR_bridge_modified=False,Loader_modified=False,FPGA_bitstream_rebuilt=False,
                codex_serial_opened=False,ten_KEY0_rounds='NOT_TESTED',
                coremark_60_scope='New BSP binaries; startup integration simulation only. Full correctness and >=10s duration require the new actual ten-round suite.')
    with gate.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print('RESULT: PASS unified BSP gate',len(inputs),'inputs',len(evidence),'evidence files; real ten-round board NOT_TESTED')
if __name__=='__main__':main()
