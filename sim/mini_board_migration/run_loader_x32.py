"""Run the accepted UART Loader ROM/RAM through x32 DDR with real UART pins."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MS = Path('D:/modelsim/win64pe')
VERIFY = ROOT/'sim/uart_loader/verify_run_hello'
TOOLS = ROOT/'tools/uart_loader/candidates/verify_run_hello'
sys.path.insert(0, str(TOOLS))
from cases import cases, materialize, PROGRAM
from protocol import decode

spec = importlib.util.spec_from_file_location('loader_base', VERIFY/'run.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, cwd, log, timeout=1800):
    result = subprocess.run(list(map(str, args)), cwd=cwd, capture_output=True,
                            text=True, errors='replace', timeout=timeout)
    output = result.stdout + result.stderr
    log.write_text(output, encoding='utf-8')
    if result.returncode or re.search(r'\*\* (?:Error|Fatal):|RESULT: FAIL', output):
        raise RuntimeError(f'{log}: exit={result.returncode}\n{output[-2500:]}')
    return output


def derived_tb(out):
    text = (VERIFY/'tb/tb_load.v').read_text()
    substitutions = [
        ('wire [127:0] wdata,rdata;wire [15:0] wstrb;',
         'wire [255:0] wdata,rdata;wire [31:0] wstrb;'),
        ('soc_top #(.ENABLE_DDR(1),.UART_RSP_DELAY_CYCLES(7))',
         "soc_top #(.ENABLE_DDR(1),.DDR_MEM_DQ_WIDTH(32),.DDR_ADDR_MASK(32'hc0000000),.UART_RSP_DELAY_CYCLES(7))"),
        ('loader_ddr_model memory', 'mini_loader_ddr_model_x32 memory'),
        ('memory.beats[inject_offset/16][(inject_offset%16)*8+:8]',
         'memory.beats[inject_offset/32][(inject_offset%32)*8+:8]'),
        ('(req_addr[aw_index]/16)*8', '(req_addr[aw_index]/32)*8'),
        ("{12'b0,req_strobe[aw_index]}", "{28'b0,req_strobe[aw_index]}"),
        ("{96'b0,req_data[aw_index]}", "{224'b0,req_data[aw_index]}"),
        ('(req_addr[aw_index]%16)/4', '(req_addr[aw_index]%32)/4'),
        ('Pango 128-bit byte placement', 'Pango 256-bit byte placement'),
        ('user_aw==user_w && user_aw+user_ar==req_count+if_reqs',
         'user_aw==user_w && user_aw>0 && user_ar>0 && user_aw<=req_count && user_aw+user_ar<=req_count+if_reqs')]
    for old, new in substitutions:
        if old not in text:
            raise RuntimeError('source TB pattern changed: '+old)
        text = text.replace(old, new)
    path = out/'tb_load_x32.v'
    path.write_text(text)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', default='mini200h_loader_20261012_c')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.tag):
        parser.error('invalid tag')
    out = HERE/'build'/args.tag
    out.mkdir(parents=True, exist_ok=False)
    image = base.image_info()
    selected = cases('native')
    requests, responses = materialize(out, selected)
    sy, sec = image['symbols'], image['sections']
    plus = [f'+ROM={(base.IMAGE/"loader_rom.dat").as_posix()}',
            f'+RAM={(base.IMAGE/"loader_ram.dat").as_posix()}']
    for key, value in {
        'BSS_START': sy['__bss_start'], 'BSS_END': sy['__bss_end'],
        'BUFFER_END': sec['.rx_buffer']['address']+sec['.rx_buffer']['size'],
        'MAIN': sy['main'], 'READY': sy['loader_ready'],
        'BOOT_ERROR': sy['loader_boot_error'], 'RX_PC': image['rx_load_pc'],
        'RECOVER_PC': image['recover_rx_load_pc'],
        'ACTIVE': sy['loader_image_active'], 'COMPLETE': sy['loader_image_complete'],
        'TOTAL': sy['loader_image_total'], 'ACCEPTED': sy['loader_image_received'],
        'IMAGE_CRC': sy['loader_image_crc']}.items():
        plus.append(f'+{key}={value:x}')
    plus += [f'+RX_RD={image["rx_load_rd"]}',
             f'+RECOVER_RD={image["recover_rx_load_rd"]}']
    symbols = {}
    for line in (PROGRAM.parent/'symbols.txt').read_text().splitlines():
        parts = line.split()
        if len(parts) == 3:
            symbols[parts[2]] = int(parts[0], 16)
    for key, value in {
        'VERIFIED': sy['loader_image_verified'], 'JUMP': sy['loader_jump_started'],
        'APP_MAIN': symbols['main'], 'APP_BSS_START': symbols['__bss_start'],
        'APP_BSS_END': symbols['__bss_end'], 'APP_GP': symbols['__global_pointer$'],
        'APP_LENGTH': len(PROGRAM.read_bytes()), 'TX_BYTES': len(responses)}.items():
        plus.append(f'+{key}={value:x}')
    for key, name in [('REQUESTS','requests.hex'), ('RESPONSES','responses.hex'),
                      ('META','metadata.hex'), ('CAPTURE','uart_tx.bin'),
                      ('RX_CAPTURE','uart_rx.bin'), ('TRACE','ddr_trace.csv')]:
        plus.append(f'+{key}={(out/name).as_posix()}')
    tb = derived_tb(out)
    sources = [path for path in base.SOURCES if path.parent == ROOT/'myriscv']
    sources += [ROOT/'sim/uart_loader/tb/loader_bram.v',
                HERE/'loader_ddr_model_x32.v', tb]
    protected = {str(path.relative_to(ROOT)): sha(path)
                 for path in sources if path != tb}
    for path in [base.IMAGE/'loader_rom.dat', base.IMAGE/'loader_ram.dat', PROGRAM]:
        protected[str(path.relative_to(ROOT))] = sha(path)
    (out/'inputs.json').write_text(json.dumps(protected, indent=2)+'\n')
    work = out/'work'
    command([MS/'vlib.exe', work], out, out/'vlib.log')
    compiled = command([MS/'vlog.exe', '-sv', '-work', work,
                        f'+incdir+{ROOT/"myriscv"}', *sources],
                       out, out/'compile.log')
    if 'Errors: 0' not in compiled:
        raise RuntimeError('ModelSim compile errors')
    script = ('onerror {quit -f -code 1}\n'
              f'vsim -t 1ps -lib {{{work.as_posix()}}} -gFAST=0 -gTIME_SCALE=1 '
              f'-gCASES={len(selected)} -gRX_BYTES={len(requests)} tb_load '
              + ' '.join(plus) + '\nonfinish stop\nrun 10sec\n'
              'if {[examine -radix unsigned /tb_load/test_pass] != 1} '
              '{echo {RESULT: FAIL incomplete}; quit -f -code 1}\n'
              'quit -f -code 0\n')
    (out/'run.tcl').write_text(script)
    print(f'START x32 Loader real UART pins frames={len(selected)} bytes={len(requests)}', flush=True)
    transcript = command([MS/'vsim.exe', '-c', '-do', 'do run.tcl'],
                         out, out/'simulation.log', timeout=1800)
    lines = re.findall(r'^(?:# )?RESULT: PASS verify_run_hello.*$', transcript, re.M)
    if len(lines) != 1 or 'Errors: 0' not in transcript:
        raise RuntimeError('missing x32 Loader PASS evidence')
    if (out/'uart_tx.bin').read_bytes() != responses or (out/'uart_rx.bin').read_bytes() != requests:
        raise RuntimeError('UART pin transcript mismatch')
    if {name: sha(ROOT/name) for name in protected} != protected:
        raise RuntimeError('protected inputs changed')
    result = {'status': 'MINI_X32_UART_LOADER_HELLO_PASS', 'evidence': lines[0],
              'frames': len(selected), 'rx_bytes': len(requests),
              'scope': 'current Loader ROM/RAM, real UART pins, x32 DDR user-port model; Hello app'}
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('RESULT: PASS', result['status'], flush=True)


if __name__ == '__main__':
    main()
