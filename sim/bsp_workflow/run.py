"""UART-load unchanged Loader, check downloaded DDR execution and application output."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
TOOLS=ROOT/'tools/uart_loader/candidates/bsp_workflow'
sys.path.insert(0,str(TOOLS))
from application import require_manifest,parse_output
from plan import materialize
spec=importlib.util.spec_from_file_location('combined',ROOT/'sim/uart_loader/verify_run_hello/run.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NAMES=['hello','crc32','irq_probe','performance_1','validation_1','performance_60','validation_60']
def manifest(name):
    return ROOT/f'tests/bsp_workflow/build/{name}/manifest.json'

def protected():
    saved=json.loads((ROOT/'sim/uart_loader/build/verify_run_hello/deployment_gate.json').read_text())
    paths=set(saved['input_sha256'])|set(saved['evidence_sha256'])
    receipt=json.loads((ROOT/'sim/uart_loader/board/verify_run_hello_submission_result.json').read_text())
    paths|={row['archive'] for row in receipt['success_archive_entries']}
    paths|={row['source'] for row in receipt['PDS_workspace_snapshot']}
    for base in ('tests/coremark_baremetal','coremark-main'):
        paths|={p.relative_to(ROOT).as_posix() for p in (ROOT/base).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    recent=json.loads((ROOT/'sim/uart_loader/board/applications_stage3_submission_result.json').read_text())
    paths|={row['archive'] for row in recent['success_archive_entries']}
    paths|={'RISCV.pds','generate_bitstream/board_top.sbit'}
    return {p:sha(ROOT/p) for p in sorted(paths)}
def main():
    p=argparse.ArgumentParser();p.add_argument('--application',choices=NAMES,required=True);p.add_argument('--native',action='store_true');p.add_argument('--tag',default='v1');a=p.parse_args()
    assert re.fullmatch('[a-z0-9_-]+',a.tag)
    partial=a.application.endswith('_60');assert not(a.native and partial)
    info=require_manifest(manifest(a.application));loader=old.image_info();sy=loader['symbols'];sec=loader['sections']
    folder=ROOT/f'sim/bsp_workflow/build/{a.tag}/{a.application}_{"native" if a.native else "fast"}'
    assert not folder.exists();folder.mkdir(parents=True)
    before=protected();sources=old.SOURCES[:-1]+[HERE/'tb/tb_applications.v']
    inputs=sources+[Path(__file__),manifest(a.application),ROOT/info['elf_path'],ROOT/info['bin_path'],
                   (ROOT/info['elf_path']).with_name('symbols.txt')]+list(TOOLS.glob('*.py'))+list((TOOLS/'references').glob('*.txt'))
    hashes={f.relative_to(ROOT).as_posix():sha(f) for f in inputs}
    rows,requests,responses=materialize(folder,info)
    if a.application=='irq_probe':
        requests+=b'1234';(folder/'requests.hex').write_text(''.join(f'{b:02x}\n' for b in requests))
    (folder/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
    report=dict(status='RUNNING',application=a.application,application_info=info,partial=partial,
                transport='115200_REAL_PINS' if a.native else 'BYTE_TRANSPORT_REAL_MMIO_FIFO',
                timer_scale=1,board_result='NOT_TESTED',frames=len(rows),input_sha256=hashes,protected_sha256=before)
    output=folder/'results.json';output.write_text(json.dumps(report,indent=2)+'\n')
    plus=[f'+ROM={(old.IMAGE/"loader_rom.dat").as_posix()}',f'+RAM={(old.IMAGE/"loader_ram.dat").as_posix()}']
    fields={'BSS_START':sy['__bss_start'],'BSS_END':sy['__bss_end'],'BUFFER_END':sec['.rx_buffer']['address']+sec['.rx_buffer']['size'],
            'MAIN':sy['main'],'READY':sy['loader_ready'],'BOOT_ERROR':sy['loader_boot_error'],
            'RX_PC':loader['rx_load_pc'],'RECOVER_PC':loader['recover_rx_load_pc'],'ACTIVE':sy['loader_image_active'],
            'COMPLETE':sy['loader_image_complete'],'TOTAL':sy['loader_image_total'],'ACCEPTED':sy['loader_image_received'],
            'IMAGE_CRC':sy['loader_image_crc'],'VERIFIED':sy['loader_image_verified'],'JUMP':sy['loader_jump_started'],
            'APP_MAIN':info['symbols']['main'],'APP_BSS_START':info['symbols']['__bss_start'],
            'APP_BSS_END':info['symbols']['__bss_end'],'APP_GP':info['symbols']['__global_pointer$'],
            'APP_DONE':info['symbols']['program_return'],'APP_DATA_START':info['symbols']['__data_start'],
            'APP_DATA_END':info['symbols']['__data_end'],'SP_PC':info['sp_auipc']['pc'],
            'SP_VALUE':info['sp_auipc']['value'],'TIMER_START':info['symbols'].get('start_time',0),'TIMER_STOP':info['symbols'].get('stop_time',0),'APP_LENGTH':info['bytes'],'TX_BYTES':len(responses)}
    plus += [f'+{k}={v:x}' for k,v in fields.items()]
    plus += [f'+RX_RD={loader["rx_load_rd"]}',f'+RECOVER_RD={loader["recover_rx_load_rd"]}']
    plus += [f'+{k}={(folder/v).as_posix()}' for k,v in [('REQUESTS','requests.hex'),('RESPONSES','responses.hex'),
              ('META','metadata.hex'),('CAPTURE','uart_tx.bin'),('RX_CAPTURE','uart_rx.bin'),('TRACE','ddr_trace.csv')]]
    try:
        work=folder/'work';old.base.command([old.base.MS/'vlib.exe',work],folder,folder/'vlib.log')
        compiled,_=old.base.command([old.base.MS/'vlog.exe','-sv','-work',work,f'+incdir+{ROOT/"myriscv"}',*sources],folder,folder/'compile.log')
        assert 'Errors: 0' in compiled
        script='onerror {quit -f -code 1}\n'+f'vsim -t 1ps -lib {{{work.as_posix()}}} -gFAST={int(not a.native)} -gPARTIAL={int(partial)} -gAPP_IRQ={int(a.application=='irq_probe')} -gCASES={len(rows)} -gRX_BYTES={len(requests)} tb_applications '+' '.join(plus)+'\nonfinish stop\nrun 10sec\nif {[examine -radix unsigned /tb_applications/test_pass] != 1} {echo {RESULT: FAIL incomplete}; quit -f -code 1}\nquit -f -code 0\n'
        (folder/'run.tcl').write_text(script)
        print('START',a.application,'partial entry test' if partial else 'full application',report['transport'],len(rows),'responses',flush=True)
        transcript,seconds=old.base.command([old.base.MS/'vsim.exe','-c','-do','do run.tcl'],folder,folder/'modelsim.log',timeout=2400)
        passed=re.findall(r'^(?:# )?RESULT: PASS applications_stage3.*$',transcript,re.M)
        assert len(passed)==1 and 'RESULT: FAIL' not in transcript and 'Errors: 0' in transcript
        assert (folder/'uart_rx.bin').read_bytes()==requests
        actual=(folder/'uart_tx.bin').read_bytes();assert actual[:len(responses)]==responses
        app_data=actual[len(responses):];(folder/'application_uart.txt').write_bytes(app_data)
        if partial:
            assert not app_data
            report['application_result']='UART_LOAD_VERIFY_RUN_STARTUP_MAIN_PASS_NOT_FULL_BENCHMARK'
        else:
            parsed=parse_output(info,app_data)
            report['application_result']=parsed
            if info['kind']=='coremark':
                ticks=int(re.search(r'APP:.*timer_ticks=(\d+)',transcript)[1]);assert ticks==parsed['ticks']
                assert 'timer_bench_reads=2' in transcript
        report.update(status='SAME_LOADER_APPLICATION_SIM_PASS',seconds=seconds,evidence=passed[0],
                      application_uart_sha256=sha(folder/'application_uart.txt'))
        print(passed[0],f'wall_seconds={seconds}',flush=True)
    except Exception as e:report.update(status='FAIL',error=str(e));raise
    finally:
        report.update(protected_unchanged=protected()==before,inputs_unchanged=all(sha(ROOT/p)==h for p,h in hashes.items()))
        output.write_text(json.dumps(report,indent=2)+'\n')
    assert report['protected_unchanged'] and report['inputs_unchanged']
if __name__=='__main__':main()
