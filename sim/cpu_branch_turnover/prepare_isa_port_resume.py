"""Freeze the exact ISA port tie-off and reuse the reviewed formal key."""
import ast,json,re
from pathlib import Path
import resume_isa_port as s
ROOT=s.ROOT;HERE=s.HERE;sha=s.sha;read=s.read;write=s.write
def main():
    assert not s.MANIFEST.exists() and not (HERE/'build'/s.TAG).exists()
    prep=HERE/'build/isa_port_preparation_20261014_a';review=prep/'key_review.json';r=json.loads(read(review))
    previous=HERE/'loaduse_resume_inputs.json';old=json.loads(read(previous))
    assert {n for n,h in old['sha256'].items() if sha(ROOT/n)!=h}=={s.TB}
    before=prep/'tb_cpu_rv32i_sample_before.sv'
    assert sha(before)==old['sha256'][s.TB]
    assert read(ROOT/s.TB)==read(before).replace(s.ANCHOR,s.ANCHOR+"        .memory_order_busy(1'b0),\n",1)
    for n,h in r['evidence_sha256'].items():assert sha(ROOT/n)==h,n
    sources=[n for n in old['compile_sources'] if n not in ('myriscv/inst_bus_interconnect.v','sim/cpu_branch_turnover/tb_branch_turnover.sv')]
    modules=[n for p in [*[Path(n) for n in old['vendor_compile_sources']],*[ROOT/n for n in sources]]
        for n in re.findall(r'^\s*module\s+(\w+)',read(p),re.M)]
    assert len(modules)==len(set(modules))==14
    new=['sim/cpu_branch_turnover/'+n for n in ('resume_isa_port.py','review_isa_port_resume.py','prepare_isa_port_resume.py','review_isa_warning_stop.py')]
    new += ['tools/uart_loader/candidates/perf_2b/run_branch_isa_port_measurement.py',
            'tools/uart_loader/candidates/perf_2b/run_branch_isa_port_measurements.ps1',before.relative_to(ROOT).as_posix()]
    files={**old['sha256'],**r['evidence_sha256']};files[s.TB]=sha(ROOT/s.TB)
    files[previous.relative_to(ROOT).as_posix()]=sha(previous);files[review.relative_to(ROOT).as_posix()]=sha(review)
    for n in new:
        files[n]=sha(ROOT/n)
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    fixtures=[n for sample in old['plan']['ISA_samples'] for n in (sample['rom'],sample['ram'],sample['traps']) if n]
    snapshots=sorted(set(sources+new+fixtures+['myriscv/csr_defs.vh']))
    m=dict(status='ISA_PORT_RESUME_PREPARED_HDL_NOT_RUN',fixed_tag=s.TAG,sha256=files,external_sha256=old['external_sha256'],
        previous_manifest=previous.relative_to(ROOT).as_posix(),previous_manifest_sha256=sha(previous),old_TB_copy=before.relative_to(ROOT).as_posix(),
        source_sha256=r['source_sha256'],software_sha256=r['software_sha256'],compile_sources=sources,vendor_compile_sources=old['vendor_compile_sources'],
        expected_modules=modules,snapshot_files=snapshots,plan=old['plan'],reused_key=r['key'],reused_control=r['reused_control'],
        reused_key_directory='sim/cpu_branch_turnover/build/ds_cpu_branch_loaduse_resume_20261014_a',
        warning_auipc_trace='sim/cpu_branch_turnover/build/ds_cpu_branch_loaduse_resume_20261014_a/isa_auipc.events.log',
        historical_evidence_sha256=r['evidence_sha256'],scope='Reviewed formal CPU branch key455/control94 reused; exact idle-input ISA TB fix; two zero-warning ISA samples; no SoC/PHY/PDS/board')
    write(s.MANIFEST,m);s.require_inputs()
    write(prep/'static_review.json',dict(status='ISA_PORT_TIEOFF_STATIC_PREPARATION_PASS_HDL_NOT_RUN',manifest_sha256=sha(s.MANIFEST),
        engineering_inputs=len(files),external_inputs=5,snapshots=len(snapshots),modules=14,
        old_TB_sha256=sha(before),new_TB_sha256=sha(ROOT/s.TB),only_change=".memory_order_busy(1'b0)",
        RTL_changed=False,model_or_criteria_changed=False,reused_key_events=455,reused_control_events=94,ISA_seed=2026101430,ISA_samples=['auipc','sb'],
        HDL_started=False,PDS_started=False,serial_opened=False))
    print('ISA_PORT_STATIC_PASS SHA',sha(s.MANIFEST),'inputs',len(files),'+5 snapshots',len(snapshots),'modules14 TB',sha(ROOT/s.TB))
if __name__=='__main__':main()
