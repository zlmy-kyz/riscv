"""Build the fixed real-CPU simulation image for the preprocess key group."""
import hashlib, json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TOOLS = ROOT / 'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
PREV = ROOT / 'tests/camera_uart'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(label, name, args, out, timeout=120):
    argv = [str(TOOLS / ('riscv-none-elf-' + name + '.exe')), *map(str, args)]
    r = subprocess.run(argv, cwd=out, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    (out / (label + '.log')).write_text(r.stdout, encoding='utf-8')
    (out / (label + '.command.json')).write_text(
        json.dumps(dict(argv=argv, cwd=str(out), returncode=r.returncode), indent=2) + '\n')
    if r.returncode:
        raise RuntimeError(label + '\n' + r.stdout)

def main():
    out = HERE / 'generated'
    out.mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(HERE / 'prepare.py')], check=True, stdout=subprocess.DEVNULL)
    flags = ['-march=rv32i', '-mabi=ilp32', '-O2', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror',
             '-ffreestanding', '-fno-builtin', '-fno-pic', '-fno-pie', '-msmall-data-limit=0',
             '-ffunction-sections', '-fdata-sections', '-fstack-usage', '-nostdlib', '-nostartfiles',
             '-Wl,--no-relax', '-Wl,--build-id=none', '-Wl,--gc-sections']
    elf, binary = out / 'pp_sim.elf', out / 'pp_sim.bin'
    run('compile', 'gcc', flags + [PREV / 'startup.S', HERE / 'cpu_sim/main_sim.c',
                                   '-I', HERE / 'cpu_sim', '-T', PREV / 'linker.ld',
                                   f'-Wl,-Map={out}/pp_sim.map', '-o', elf, '-lgcc'], out)
    run('objcopy', 'objcopy', ['-O', 'binary', elf, binary], out)
    run('readelf', 'readelf', ['-h', '-A', '-l', '-S', elf], out)
    run('disassembly', 'objdump', ['-d', elf], out)
    run('symbols', 'nm', ['-n', elf], out)
    run('size', 'size', [elf], out)
    raw = binary.read_bytes()
    assert len(raw) < 16384, len(raw)
    padded = raw + b'\0' * ((-len(raw)) % 4)
    (out / 'cpu.dat').write_text(''.join(f'{int.from_bytes(padded[i:i+4],"little"):08x}\n'
                                         for i in range(0, len(padded), 4)), encoding='ascii')
    info = dict(status='PREPROCESS_SIM_CPU_BUILD_PASS', bin_bytes=len(raw), bin_sha256=sha(binary),
                dat_bytes=(out / 'cpu.dat').stat().st_size,
                source_sha256={n: sha(HERE / ('cpu_sim/' + n)) for n in ('main_sim.c', 'expect.h')},
                shared_sha256={n: sha(PREV / n) for n in ('startup.S', 'linker.ld')},
                flags=flags, serial='NOT_USED', board='NOT_RUN')
    (out / 'cpu_build.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=info['status'], bytes=len(raw), sha256=info['bin_sha256']), indent=2))

if __name__ == '__main__':
    main()
