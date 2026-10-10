"""Freeze only after application simulations, exact CoreMark reuse, and PC checks pass."""
from pathlib import Path
import json,shutil,sys
import run
ROOT=run.ROOT
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/applications_stage3'))
from application import require_manifest
from upload import BIT,sha

def main():
    out=ROOT/'sim/uart_loader/build/applications_stage3';gatefile=out/'deployment_gate.json'
    assert not gatefile.exists()
    selected={'second':'v3/second_native','performance_1':'v3/performance_1_fast','validation_1':'v3/validation_1_fast',
              'performance_60':'v4/performance_60_fast','validation_60':'v4/validation_60_fast'}
    inputs={};evidence={};summaries={};manifests={}
    for name,folder in selected.items():
        base=out/folder;report=json.loads((base/'results.json').read_text())
        assert report['status']=='SAME_LOADER_APPLICATION_SIM_PASS' and report['protected_unchanged'] and report['inputs_unchanged']
        assert report['application']==name and report['partial']==name.endswith('_60') and report['timer_scale']==1
        assert report['transport']==('115200_REAL_PINS' if name=='second' else 'BYTE_TRANSPORT_REAL_MMIO_FIFO')
        for path,h in report['input_sha256'].items():assert sha(ROOT/path)==h;inputs[path]=h
        for path,h in report['protected_sha256'].items():assert sha(ROOT/path)==h
        for p in base.iterdir():
            if p.is_file():evidence[p.relative_to(ROOT).as_posix()]=sha(p)
        manifest=run.manifest(name);info=require_manifest(manifest)
        assert report['application_info']==info
        manifests[manifest.relative_to(ROOT).as_posix()]=sha(manifest)
        summaries[name]=dict(path=(base/'results.json').relative_to(ROOT).as_posix(),scope=report['application_result'],evidence=report['evidence'])
    offline=out/'pc_offline.json';pc=json.loads(offline.read_text())
    assert pc['status']=='APPLICATIONS_PC_OFFLINE_PASS' and pc['count']==28 and not pc['serial_opened']
    evidence[offline.relative_to(ROOT).as_posix()]=sha(offline)
    control=out/'pc_controls.json';checks=json.loads(control.read_text())
    assert checks['status']=='APPLICATIONS_CLI_OFFLINE_PASS' and checks['count']==7 and not checks['serial_opened']
    evidence[control.relative_to(ROOT).as_posix()]=sha(control)
    originpath=ROOT/'tests/uart_loader/coremark_uart/origin.json';origin=json.loads(originpath.read_text())
    assert origin['status']=='EXACT_COREMARK_BIN_COPY_PASS' and len(origin['records'])==4
    for record in origin['records']:
        old=ROOT/record['source'];new=ROOT/record['destination'];oldproof=ROOT/record['original_evidence']
        assert record['build_reused_without_recompiling'] and sha(oldproof)==record['evidence_sha256']
        assert sha(old/'main.bin')==sha(new/'main.bin')==record['bin_sha256']
        assert sha(old/'main.elf')==sha(new/'main.elf')==record['elf_sha256']
        proof=next(r for r in json.loads(oldproof.read_text())['results'] if r['mode']==record['application'].rsplit('_',1)[0])
        assert proof['result']=='CRC_FUNCTIONAL_PASS' and proof['image']['sha256']['main.bin']==record['bin_sha256']
        assert proof['image']['sha256']['main.elf']==record['elf_sha256'] and proof['evidence'].startswith('RESULT: PASS coremark_full_boot')
        evidence[record['original_evidence']]=sha(oldproof)
    oldgatepath=ROOT/'sim/uart_loader/build/verify_run_hello/deployment_gate.json';oldgate=json.loads(oldgatepath.read_text())
    for field in ('input_sha256','evidence_sha256'):
        for path,h in oldgate[field].items():assert sha(ROOT/path)==h
    receiptpath=ROOT/'sim/uart_loader/board/verify_run_hello_submission_result.json';receipt=json.loads(receiptpath.read_text())
    assert receipt['status']=='COMBINED_ACTUAL_BOARD_ARCHIVE_PASS' and receipt['gate_sha256']==sha(oldgatepath)
    for row in receipt['success_archive_entries']:assert sha(ROOT/row['archive'])==row['sha256']
    for row in receipt['PDS_workspace_snapshot']:assert sha(ROOT/row['source'])==sha(ROOT/row['archive'])==row['sha256']
    assert sha(BIT)==receipt['bitstream_identity']['sha256']
    for field in ('input_sha256',):inputs.update(oldgate[field])
    for directory in ('tests/uart_loader/program_second','tests/uart_loader/coremark_uart',
                      'tools/uart_loader/candidates/applications_stage3','sim/uart_loader/applications_stage3'):
        for path in (ROOT/directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.md':inputs[path.relative_to(ROOT).as_posix()]=sha(path)
    for path in (BIT,oldgatepath,receiptpath,ROOT/'sim/uart_loader/board/verify_run_hello_board_result.json'):
        inputs[path.relative_to(ROOT).as_posix()]=sha(path)
    copies=[];snapshot=out/'frozen_inputs';assert not snapshot.exists()
    for path,h in sorted(inputs.items()):
        target=snapshot/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,target);assert sha(target)==h
        copies.append(dict(source=path,archive=target.relative_to(ROOT).as_posix(),sha256=h))
    result=dict(status='SAME_LOADER_APPLICATIONS_SIM_PASS',date='2026-10-09',board_result='NOT_TESTED',
                scope='Second application and CoreMark UART downloads on the successful Loader bitstream',
                successful_bitstream_sha256=sha(BIT),manifests=manifests,input_sha256=inputs,evidence_sha256=evidence,
                frozen_source_copies=copies,simulation_results=summaries,pc_offline_checks=35,
                original_coremark_builds_reused=origin,old_success_archive_entries_checked=len(receipt['success_archive_entries']),
                original_loader_inputs_checked=len(oldgate['input_sha256']),original_loader_evidence_checked=len(oldgate['evidence_sha256']),
                unchanged_loader=True,FPGA_bitstream_rebuilt=False,serial_opened=False,FPGA_programmed=False,
                formal_60_iteration_scope='New UART LOAD/VERIFY/RUN/startup plus exact-BIN prior full algorithm evidence; new board timing pending',
                additional_ten_reset_test='OUTSIDE_THIS_REQUEST_NOT_TESTED')
    with gatefile.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print('RESULT: PASS same Loader deployment gate',len(inputs),'inputs',len(evidence),'evidence files; board NOT_TESTED')

if __name__=='__main__':main()
