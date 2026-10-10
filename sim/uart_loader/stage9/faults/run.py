"""Stage 8 isolated CPU/UART/DDR error-path gate; does not build or deploy."""
from pathlib import Path
import argparse, importlib.util, json, re, sys, time
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
TOOLS=ROOT/'tools/uart_loader/candidates/uart_fault_stage8_diag'
sys.path.insert(0,str(TOOLS))
from cases import host_cases, wire_cases, materialize, CRC
from protocol import decode_response
spec=importlib.util.spec_from_file_location('stage7_runner',ROOT/'sim/uart_loader/run.py')
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
base.IMAGE=ROOT/'tests/uart_loader/candidates/random_stage9/build'
IMAGE=base.IMAGE
sha=base.sha
SOURCES=[ROOT/'myriscv'/(n+'.v') for n in base.NAMES]+[ROOT/'sim/uart_loader/tb/loader_bram.v',ROOT/'sim/uart_loader/tb/loader_ddr_model.v',HERE/'tb/tb_uart_loader.v']

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

base.image_info=image_info

def protected():
    p=base.protected()
    for f in (ROOT/'tests/uart_loader/candidates/uart_fault_stage8_diag').rglob('*'):
        if f.is_file() and '__pycache__' not in f.parts:p[str(f)]=base.sha(f)
    for folder in ['tests/uart_loader/build/ddr_crc','tests/uart_loader/verified',
                   'tools/uart_loader/verified','sim/uart_loader/build/ddr_crc_stage7_sources','sim/uart_loader/board']:
        for f in (ROOT/folder).rglob('*'):
            if f.is_file() and '__pycache__' not in f.parts: p[str(f)]=base.sha(f)
    return p

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',choices=['host','native'],default='native')
    parser.add_argument('--tag',default='v1')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9_-]+',args.tag): parser.error('invalid tag')
    native=args.suite=='native'
    folder=ROOT/'sim/uart_loader/build/random_stage9'/args.tag/'faults'
    if (folder/'results.json').exists(): raise RuntimeError('existing run evidence: choose a new directory in source before rerunning')
    folder.mkdir(parents=True,exist_ok=True)
    gate=json.loads((ROOT/'sim/uart_loader/board/ddr_crc_stage7_board_result.json').read_text())
    if gate['board_result']!='PASS': raise RuntimeError('stage7 board gate not PASS')
    for key in ['first_round','after_reset_round']:
        if base.sha(ROOT/'sim/uart_loader/board'/gate[key]['evidence'])!=gate[key]['sha256']: raise RuntimeError('stage7 evidence differs')
    receipt=json.loads((ROOT/'sim/uart_loader/build/ddr_crc_stage7_sources/archive_receipt.json').read_text())
    for e in receipt['archive_entries']:
        if base.sha(ROOT/e['archive'])!=e['sha256']: raise RuntimeError('stage7 archive differs')
    before=protected(); info=base.image_info()
    selected=wire_cases() if native else host_cases(uart_faults=False)
    requests,responses=materialize(folder,selected)
    report=dict(status='RUNNING',suite=args.suite,board_result='NOT_TESTED',time_scale=1 if native else 64,
        image=info,protected_sha256=before,input_sha256={str(p):base.sha(p) for p in SOURCES+[Path(__file__),TOOLS/'cases.py',TOOLS/'protocol.py',TOOLS/'original_cases.py',HERE/'preparation.json',ROOT/'sim/uart_loader/run.py']},results=[])
    (folder/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    sy=info['symbols']
    mapping={'BSS_START':'__bss_start','BSS_END':'__bss_end','MAIN':'main','READY':'loader_ready','PING_ADDR':'loader_ping_count',
        'NACK_ADDR':'loader_nack_count','LAST_SEQ':'loader_last_seq','BOOT_ERROR':'loader_boot_error','RECOVER':'loader_recovering',
        'PROBE':'loader_bss_probe','TEST_COUNT':'loader_test_count','TEST_BYTES':'loader_test_bytes','TEST_CRC':'loader_test_crc',
        'DDR_COUNT':'loader_ddr_count','DDR_BYTES':'loader_ddr_bytes','DDR_STATUS':'loader_ddr_status','CRC_COUNT':'loader_crc_count',
        'CRC_READS':'loader_crc_reads','CRC_ACTUAL':'loader_crc_actual','CRC_EXPECTED':'loader_crc_expected','CRC_STATUS':'loader_crc_status','UART_FLAGS':'loader_uart_error_status'}
    plus=[f'+{k}={sy[v]:x}' for k,v in mapping.items()]
    for k,v in [('DDR_WRITE_PC','ddr_write_pc'),('DDR_READ_PC','ddr_read_pc'),('DDR_READ_RD','ddr_read_rd'),
                ('CRC_READ_PC','ddr_crc_read_pc'),('CRC_READ_RD','ddr_crc_read_rd'),('RX_PC','rx_load_pc'),('RX_RD','rx_load_rd'),
                ('RECOVER_RX_PC','recover_rx_load_pc'),('RECOVER_RX_RD','recover_rx_load_rd')]:
        plus.append(f'+{k}={info[v] if k.endswith("_RD") else format(info[v],"x")}')
    plus += [f'+STACK_SET={sy["loader_stack_ready"]-4:x}',f'+RODATA_END={info["sections"][".rodata"]["address"]+info["sections"][".rodata"]["size"]:x}',f'+DATA_CRC={CRC:x}']
    plus += [f'+ROM={(base.IMAGE/"loader_rom.dat").as_posix()}',f'+RAM={(base.IMAGE/"loader_ram.dat").as_posix()}']
    try:
        for stage,name in [(0,'residency'),(4,args.suite)]:
            out=folder/name;out.mkdir(exist_ok=True);work=out/'work'
            base.command([base.MS/'vlib.exe',work],out,out/'vlib.log')
            output,_=base.command([base.MS/'vlog.exe','-sv','-work',work,f'+incdir+{ROOT/"myriscv"}',*SOURCES],out,out/'compile.log')
            if 'Errors: 0' not in output: raise RuntimeError('compile Errors not 0')
            arguments=plus+[f'+CAPTURE={(out/"uart_tx.bin").as_posix()}',f'+RX_CAPTURE={(out/"uart_rx.bin").as_posix()}']
            if stage:
                arguments += [f'+{k}={(folder/v).as_posix()}' for k,v in [('STIMULUS','requests.hex'),('EXPECTED','responses.hex'),
                    ('LENGTHS','frame_lengths.hex'),('CASE_STATE','case_state.hex'),('DDR_STATE','ddr_state.hex'),('CRC_STATE','crc_state.hex'),('FAULTS','faults.hex')]]
                arguments += [f'+TRACE={(out/"ddr_trace.csv").as_posix()}',f'+TIMING={(out/"timing.csv").as_posix()}']
            scale=1 if native or stage==0 else 64
            (out/'run.tcl').write_text('onerror {quit -f -code 1}\n'+f'vsim -t 1ps -lib {{{work.as_posix()}}} -gSTAGE={stage} -gCASES={len(selected)} -gTIME_SCALE={scale} tb_uart_loader '+' '.join(arguments)+'\nonfinish stop\nrun 20sec\nif {[examine -radix unsigned /tb_uart_loader/test_pass] != 1} {echo {RESULT: FAIL incomplete}; quit -f -code 1}\nquit -f -code 0\n',encoding='ascii')
            print(f'START {args.suite}/{name} frames={len(selected) if stage else 0} TIME_SCALE={scale}',flush=True)
            output,seconds=base.command([base.MS/'vsim.exe','-c','-do','do run.tcl'],out,out/'modelsim.log',timeout=7200)
            matches=re.findall(r'^(?:# )?RESULT: PASS uart_loader .*$',output,re.M)
            if len(matches)!=1 or 'RESULT: FAIL' in output or 'Errors: 0' not in output: raise RuntimeError(output[-3000:])
            tx=(out/'uart_tx.bin').read_bytes();rx=(out/'uart_rx.bin').read_bytes()
            if stage:
                if tx!=responses or rx!=requests: raise RuntimeError('raw RX/TX differs from oracle')
                timings={int(a):float(b) for a,b in (line.split(',') for line in (out/'timing.csv').read_text().splitlines())}
                records=[]
                for i,c in enumerate(selected):
                    raw=tx[i*60:(i+1)*60]; decoded=decode_response(raw,c['seq'],c['cmd'],expected_crc=c.get('expected_crc',CRC),uart_error_flags=c.get('uart_error_flags',0))
                    if decoded['status']!=c['status'] or decoded['actual_ddr_crc']!=c['actual_crc']: raise RuntimeError(f'bad response {c["name"]}')
                    records.append(dict(**c,rx_hex=raw.hex(),seconds=timings.get(i,timings.get(i-1)),decoded=decoded,result='PASS'))
                (folder/'decoded_responses.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf8')
                if native:
                    events=re.search(r'CHECK: WIRE_ERRORS frame=(\d+) overflow=(\d+) dropped=(\d+) clears=(\d+) accepted=(\d+)',output)
                    if not events or int(events[1])!=1 or int(events[2])<=0 or int(events[2])!=int(events[3]) or int(events[4])<2:
                        raise RuntimeError('native physical faults were not observed/cleared')
                    times={x['name']:x['seconds'] for x in records}
                    if not .100<=times['wire_break']<=.125 or not .100<=times['wire_fifo_overflow']<=.13:
                        raise RuntimeError('native fault recovery timing differs')
                    report['wire_events']=dict(frame=int(events[1]),overflow=int(events[2]),dropped=int(events[3]),clears=int(events[4]),accepted=int(events[5]),no_cpu_or_uart_force=True)
            elif tx or rx: raise RuntimeError('residency UART activity')
            report['results'].append(dict(stage=name,result='PASS',seconds=seconds,evidence=matches[0]))
            print(matches[0],f'wall_seconds={seconds}',flush=True)
            if protected()!=before: raise RuntimeError('protected file changed')
        report['status']='STAGE9_UART_COMPAT_'+args.suite.upper()+'_SIM_PASS'
        report['negative_cases']=sum(bool(c.get('negative')) for c in selected)
        report['frame_count']=len(selected)
        (folder/'validated_image.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf8')
    except Exception as e:
        report['status']='FAIL';report['error']=str(e);raise
    finally:
        report['protected_unchanged']=protected()==before
        report['image_unchanged']=all(base.sha(base.IMAGE/k)==v for k,v in info['sha256'].items())
        report['inputs_unchanged']=all(base.sha(Path(k))==v for k,v in report['input_sha256'].items())
        (folder/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
        if not all(report[k] for k in ['protected_unchanged','image_unchanged','inputs_unchanged']): raise RuntimeError('hash protection failed')
    print('RESULT: PASS',report['status'],'board NOT_TESTED; successful DAT preserved',flush=True)

if __name__=='__main__':
    try: main()
    except Exception as e: print('RESULT: FAIL stage8:',e,file=sys.stderr,flush=True);sys.exit(1)
