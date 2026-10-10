"""Stage9 real CPU/DDR byte-range checks plus independent 115200 pin confirmation."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,sys,time
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
TOOLS=ROOT/'tools/uart_loader/candidates/random_stage9';IMAGE=ROOT/'tests/uart_loader/candidates/random_stage9/build'
sys.path.insert(0,str(TOOLS))
from cases import positive_cases,negative_cases,materialize
from protocol import decode
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('stage7_runner',ROOT/'sim/uart_loader/run.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
SOURCES=[ROOT/'myriscv'/(n+'.v') for n in base.NAMES]+[ROOT/'sim/uart_loader/tb/loader_bram.v',ROOT/'sim/uart_loader/tb/loader_ddr_model.v',HERE/'tb/tb_random.v']

def image_info():
    spec=importlib.util.spec_from_file_location('stage9_audit',ROOT/'tests/uart_loader/candidates/random_stage9/image_to_dat.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    raw,sections,symbols,rx,rec,instructions=module.audit(IMAGE/'loader.elf')
    saved=json.loads((IMAGE/'manifest.json').read_text())
    assert sections==saved['sections'] and symbols==saved['symbols'] and instructions==saved['instructions_audited']
    for n,h in saved['sha256'].items():assert sha(IMAGE/n)==h
    for name,section in [('loader_rom.dat','.text'),('loader_ram.dat','.rodata')]:
        image=b''.join(int(w,16).to_bytes(4,'little') for w in (IMAGE/name).read_text().split());assert len(image)==16384
        expected=bytearray((0x6f).to_bytes(4,'little')*4096 if section=='.text' else bytes(16384));s=sections[section]
        expected[s['address']:s['address']+s['size']]=raw[s['offset']:s['offset']+s['size']];assert image==expected
    return saved

def protected():
    files=list((ROOT/'myriscv').glob('*.v'))
    for folder in ('tests/uart_loader/build/ddr_crc','tests/uart_loader/verified','tests/uart_loader/candidates/uart_fault_stage8_diag',
                   'tools/uart_loader/candidates/uart_fault_stage8_diag','tools/uart_loader/verified','sim/uart_loader/board'):
        files += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [ROOT/p for p in ('RISCV.pds','ipcore/inst_rom/inst_rom.idf','ipcore/inst_rom/inst_rom.v','ipcore/inst_rom/rtl/inst_rom_init_param.v',
                              'ipcore/data_ram/data_ram.idf','ipcore/data_ram/data_ram.v','ipcore/data_ram/rtl/data_ram_init_param.v')]
    files += list((ROOT/'generate_bitstream').glob('*.sbit'))
    return {p.relative_to(ROOT).as_posix():sha(p) for p in files}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--suite',choices=['native','bulk','negative','legacy'],required=True);parser.add_argument('--tag',default='v1');args=parser.parse_args()
    assert re.fullmatch('[a-z0-9_-]+',args.tag)
    folder=ROOT/f'sim/uart_loader/build/random_stage9/{args.tag}/{args.suite}';assert not folder.exists();folder.mkdir(parents=True)
    gate=json.loads((ROOT/'sim/uart_loader/board/uart_fault_stage8_diag_board_result.json').read_text());assert gate['stage8_full_board_diagnostic_candidate']=='PASS'
    info=image_info();before=protected();native=args.suite=='native'
    if args.suite=='negative':selected=negative_cases()
    elif args.suite=='legacy':
        path=ROOT/'tools/uart_loader/candidates/uart_fault_stage8_diag/original_cases.py'
        legacy_spec=importlib.util.spec_from_file_location('legacy_cases',path);legacy=importlib.util.module_from_spec(legacy_spec);legacy_spec.loader.exec_module(legacy)
        selected=legacy.cases(uart_faults=False)
        for c in selected:
            raw=bytes.fromhex(c['tx_hex']);c.update(write_bytes=64 if c.get('attempt') else 0,read_bytes=64 if c.get('attempt') or c.get('crc_read') else 0,
                                                  address=0x40000000,length=64,actual_crc=legacy.CRC if c.get('crc_read') else 0)
        selected[0]['new_epoch']=True
    else:selected=positive_cases(ROOT/'sim/uart_loader/build/random_stage9/corpus/sim',native).cases
    requests,responses=materialize(folder,selected);sy=info['symbols'];sec=info['sections']
    inputs=SOURCES+[Path(__file__)]+list(TOOLS.glob('*.py'))+list((ROOT/'tests/uart_loader/candidates/random_stage9').glob('*.c'))+list((ROOT/'tests/uart_loader/candidates/random_stage9').glob('*.h'))
    inputs += [ROOT/'tests/uart_loader/candidates/random_stage9'/p for p in ('startup.S','linker.ld','image_to_dat.py','build.ps1')]
    input_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    report=dict(status='RUNNING',suite=args.suite,board_result='NOT_TESTED',image_sha256=info['sha256'],input_sha256=input_hashes,
                protected_sha256=before,transport='115200_REAL_PINS' if native else 'BYTE_TRANSPORT_MODEL_REAL_MMIO_FIFO',
                time_scale=1 if native else 512,frames=len(selected),random_execute=False)
    output=folder/'results.json';output.write_text(json.dumps(report,indent=2)+'\n')
    plus=[f'+ROM={(IMAGE/"loader_rom.dat").as_posix()}',f'+RAM={(IMAGE/"loader_ram.dat").as_posix()}']
    for k,v in {'BSS_START':sy['__bss_start'],'BSS_END':sy['__bss_end'],'BUFFER_END':sec['.rx_buffer']['address']+sec['.rx_buffer']['size'],
                'MAIN':sy['main'],'READY':sy['loader_ready'],'BOOT_ERROR':sy['loader_boot_error'],'RX_PC':info['rx_load_pc'],'RECOVER_PC':info['recover_rx_load_pc']}.items():plus.append(f'+{k}={v:x}')
    plus += [f'+RX_RD={info["rx_load_rd"]}',f'+RECOVER_RD={info["recover_rx_load_rd"]}']
    for k,v in [('REQUESTS','requests.hex'),('RESPONSES','responses.hex'),('META','metadata.hex'),('CAPTURE','uart_tx.bin'),('RX_CAPTURE','uart_rx.bin'),('TRACE','ddr_trace.csv')]:plus.append(f'+{k}={(folder/v).as_posix()}')
    try:
        work=folder/'work';base.command([base.MS/'vlib.exe',work],folder,folder/'vlib.log')
        compiled,_=base.command([base.MS/'vlog.exe','-sv','-work',work,f'+incdir+{ROOT/"myriscv"}',*SOURCES],folder,folder/'compile.log')
        assert 'Errors: 0' in compiled
        (folder/'run.tcl').write_text('onerror {quit -f -code 1}\n'+f'vsim -t 1ps -lib {{{work.as_posix()}}} -gFAST={0 if native else 1} -gTIME_SCALE={1 if native else 512} -gCASES={len(selected)} -gRX_BYTES={len(requests)} tb_random '+' '.join(plus)+'\nonfinish stop\nrun 10sec\nif {[examine -radix unsigned /tb_random/test_pass] != 1} {echo {RESULT: FAIL incomplete}; quit -f -code 1}\nquit -f -code 0\n')
        print(f'START stage9 {args.suite} frames={len(selected)} raw_RX={len(requests)} transport={report["transport"]}',flush=True)
        transcript,seconds=base.command([base.MS/'vsim.exe','-c','-do','do run.tcl'],folder,folder/'modelsim.log',timeout=7200)
        line=re.findall(r'^(?:# )?RESULT: PASS random_stage9.*$',transcript,re.M);assert len(line)==1 and 'RESULT: FAIL' not in transcript and 'Errors: 0' in transcript
        assert (folder/'uart_tx.bin').read_bytes()==responses and (folder/'uart_rx.bin').read_bytes()==requests
        records=[dict(**c,rx_hex=responses[i*60:(i+1)*60].hex(),decoded=decode(responses[i*60:(i+1)*60],c)) for i,c in enumerate(selected)]
        (folder/'decoded_responses.json').write_text(json.dumps(records,indent=2)+'\n')
        report.update(status='STAGE9_'+args.suite.upper()+'_SIM_PASS',seconds=seconds,evidence=line[0],
                      image_checks=sum(bool(c.get('image_end')) for c in selected),negative_cases=sum(bool(c['status']) for c in selected))
        print(line[0],f'wall_seconds={seconds}',flush=True)
    except Exception as error:report.update(status='FAIL',error=str(error));raise
    finally:
        report.update(protected_unchanged=protected()==before,image_unchanged=all(sha(IMAGE/n)==h for n,h in info['sha256'].items()),
                      inputs_unchanged=all(sha(ROOT/n)==h for n,h in input_hashes.items()))
        output.write_text(json.dumps(report,indent=2)+'\n')
    assert report['protected_unchanged'] and report['image_unchanged'] and report['inputs_unchanged']
    print('RESULT: PASS',report['status'],'board NOT_TESTED',flush=True)

if __name__=='__main__':
    try:main()
    except Exception as error:print('RESULT: FAIL stage9',error,file=sys.stderr,flush=True);sys.exit(1)
