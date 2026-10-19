"""Run existing short CoreMark BINs on the current CPU and 256-bit DDR bridge."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MS = Path('D:/modelsim/win64pe')
RTL = 'alu br_alu l_alu regfile csr_file mycpu_sync inst_bus_interconnect data_bus_interconnect inst_bram_adapter data_bram_adapter simple_mmio dual_sram_to_pango_ddr_bridge uart_tx uart_rx uart_rx_fifo uart_mmio soc_top'.split()
SOURCES = [ROOT/'myriscv'/f'{name}.v' for name in RTL]
SOURCES += [ROOT/'sim/coremark/bram.v', HERE/'ddr_model_x32.v', HERE/'tb_coremark_x32.v']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, cwd, log, timeout=180):
    try:
        result = subprocess.run(list(map(str, args)), cwd=cwd, capture_output=True,
                                text=True, errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f'timeout: {log}') from exc
    output = result.stdout + result.stderr
    log.write_text(output, encoding='utf-8')
    if result.returncode or re.search(r'\*\* (?:Error|Fatal):|RESULT: FAIL', output):
        raise RuntimeError(f'{log}: exit={result.returncode}\n{output[-2500:]}')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['performance', 'validation', 'all'], default='all')
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.tag):
        parser.error('tag must contain only letters, digits, underscore, hyphen')
    spec = importlib.util.spec_from_file_location(
        'bsp_application', ROOT/'tools/uart_loader/candidates/bsp_workflow/application.py')
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    out = HERE/'build'/args.tag
    out.mkdir(parents=True, exist_ok=False)
    protected = {str(p.relative_to(ROOT)): sha(p) for p in SOURCES}
    for name in ('performance_1', 'validation_1'):
        src = ROOT/'tests/bsp_workflow/build'/name
        for path in (src/'program.bin', src/'program.elf', src/'manifest.json'):
            protected[str(path.relative_to(ROOT))] = sha(path)
    (out/'inputs.json').write_text(json.dumps(protected, indent=2)+'\n')
    work = out/'work'
    command([MS/'vlib.exe', work], out, out/'vlib.log')
    compile_log = command([MS/'vlog.exe', '-sv', '-work', work,
                           f'+incdir+{ROOT/"myriscv"}', *SOURCES], out,
                          out/'compile.log')
    if 'Errors: 0' not in compile_log:
        raise RuntimeError('ModelSim compile did not confirm Errors: 0')
    results = {}
    for mode in ('performance', 'validation') if args.mode == 'all' else (args.mode,):
        src = ROOT/'tests/bsp_workflow/build'/f'{mode}_1'
        info = app.require_manifest(src/'manifest.json')
        raw = (src/'program.bin').read_bytes()
        padded = raw + bytes((-len(raw)) % 4)
        words = list(struct.unpack('<'+'I'*(len(padded)//4), padded))
        if not 0 < len(words) <= 4092:
            raise ValueError('CoreMark payload does not fit 16 KiB image')
        image = words + [0]*(4096-len(words))
        image[4092] = len(words)
        folder = out/mode
        folder.mkdir()
        dat = folder/'program.dat'
        dat.write_text(''.join(f'{word:08x}\n' for word in image), encoding='ascii')
        plus = [f'+ROM={(ROOT/"tests/uart_loader/candidates/verify_run_hello/build/loader_rom.dat").as_posix()}',
                f'+DAT={dat.as_posix()}',
                f'+DONE={info["symbols"]["program_return"]:x}',
                f'+OUT={folder.as_posix()}', '+MAX_CYCLES=60000000']
        print(f'START {mode} x32 direct CoreMark', flush=True)
        log = command([MS/'vsim.exe', '-c', '-lib', work, 'tb_coremark_x32',
                       *plus, '-do', 'run -all; quit -f'], folder,
                      folder/'simulation.log', timeout=1800)
        if 'Errors: 0' not in log or log.count('RESULT: PASS coremark_x32_direct') != 1:
            raise RuntimeError(f'x32 CoreMark acceptance missing: {folder}')
        parsed = app.parse_output(info, (folder/'uart.txt').read_bytes())
        results[mode] = {'status': 'CRC_FUNCTIONAL_PASS', 'parsed': parsed,
                         'evidence': re.search(r'RESULT: PASS coremark_x32_direct[^\r\n]*', log).group(),
                         'program_bin_sha256': sha(src/'program.bin'),
                         'program_dat_sha256': sha(dat),
                         'scope': 'CPU and 256-bit DDR user-port model; direct preloaded execution'}
        print(f'PASS {mode}: {results[mode]["evidence"]}; CRC={parsed["crcfinal"]}', flush=True)
    after = {name: sha(ROOT/name) for name in protected}
    if after != protected:
        raise RuntimeError('protected RTL or CoreMark input changed during simulation')
    (out/'results.json').write_text(json.dumps(results, indent=2)+'\n')
    print(f'RESULT: PASS {out}', flush=True)


if __name__ == '__main__':
    main()
