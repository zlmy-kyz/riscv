"""Per-application audit and evidence; the successful Loader gate stays immutable."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BSP = ROOT / 'tests/bsp_workflow'
SIM = ROOT / 'sim/c_app'
TOOLS = ROOT / 'tools/uart_loader/candidates/bsp_workflow'
TOOLCHAIN = ROOT / 'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
sys.path.insert(0, str(TOOLS))
import application
import plan
import upload

DONE = b'\nC_APP_DONE return=0\n'
MAX_OUTPUT = 65536


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def inside(path):
    path = Path(path).resolve()
    path.relative_to(ROOT)
    return path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hardware_gate():
    module = load_module('c_app_rebuilt', ROOT / 'tools/uart_loader/candidates/rebuilt_20261010/run_board.py')
    # Validate hardware and all original frozen inputs via an unchanged known manifest.
    digest = module.require_gate(BSP / 'build/hello/manifest.json')
    gate = json.loads(module.GATE.read_text())
    return dict(path=module.GATE.as_posix(), sha256=digest,
                bitstream_path=module.BIT.as_posix(), bitstream_sha256=sha(module.BIT)), gate['input_sha256']


def parse_output(info, data):
    if len(data) > MAX_OUTPUT or not data.endswith(DONE) or data.count(b'C_APP_DONE') != 1:
        raise ValueError('Missing/duplicate completion marker or nonzero main return')
    body = data[:-len(DONE)]
    if any(token in body for token in (b'TRAP_FAIL', b'C_APP_BSP_FAIL')):
        raise ValueError('BSP or trap failure')
    wanted = bytes.fromhex(info['expected_hex'])
    if info['expect_mode'] == 'exact':
        if body != wanted:
            raise ValueError('Application output differs from --expect-file bytes')
    elif body.count(wanted) != 1:
        raise ValueError('Expected UTF-8 text must occur exactly once')
    return dict(status='C_APP_OUTPUT_PASS', mode=info['expect_mode'], output_hex=body.hex(), main_return=0)


def require_manifest(path):
    path = inside(path)
    info = json.loads(path.read_text(encoding='utf-8'))
    if info['status'] != 'C_APP_AUDIT_PASS':
        raise ValueError('Not an audited custom application')
    for rel, expected in info['input_sha256'].items():
        if sha(ROOT / rel) != expected:
            raise ValueError('Application input changed: ' + rel)
    actual = application.audit(ROOT / info['elf_path'], ROOT / info['bin_path'], 'hello')
    saved = {key: info[key] for key in actual}
    saved.update(status='DDR_APPLICATION_AUDIT_PASS', kind='hello')
    if saved != actual:
        raise ValueError('ELF/BIN no longer match audited manifest')
    return info


def command(args, folder, logfile):
    result = subprocess.run(list(map(str, args)), cwd=folder, capture_output=True, text=True)
    (folder / logfile).write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'{logfile}: ' + result.stdout + result.stderr)
    return result.stdout


def build(sources, expected, exact, tag):
    out = HERE / 'build' / tag
    out.mkdir(parents=True, exist_ok=False)
    hardware, _ = hardware_gate()
    flags = ['-march=rv32i', '-mabi=ilp32', '-Os', '-g', '-Wall', '-Wextra',
             '-ffreestanding', '-fno-builtin', '-fno-pic', '-fno-pie', '-msmall-data-limit=0',
             '-ffunction-sections', '-fdata-sections', '-fstack-usage', '-I', str(BSP)]
    user = [inside(p) for p in sources]
    if any(p.suffix.lower() != '.c' or not p.is_file() for p in user):
        raise ValueError('--source must name existing C files within the project')
    support = [BSP / n for n in ('startup.S', 'trap.S', 'trap.c', 'uart.c', 'timer.c', 'crc32.c')] + [HERE / 'wrapper.c']
    tracked = set(user + support + [BSP / 'bsp.h', BSP / 'linker.ld', HERE / 'pipeline.py', HERE / 'run_app.py', SIM / 'run.py'])
    tracked.update(TOOLS.glob('*.py'))
    tracked.add(ROOT / 'tools/uart_loader/candidates/verify_run_hello/protocol.py')
    tracked.add(ROOT / 'tests/uart_loader/candidates/verify_run_hello/image_to_dat.py')
    tracked.add(TOOLCHAIN / 'riscv-none-elf-gcc.exe')
    for name in ('objcopy', 'objdump', 'readelf', 'nm', 'size'):
        tracked.add(TOOLCHAIN / f'riscv-none-elf-{name}.exe')
    before = {p: sha(p) for p in tracked}
    objects = []
    for index, source in enumerate(support + user):
        obj = out / f'{index:02}.o'
        dep = out / f'{index:02}.d'
        args = flags + ['-I', str(source.parent), '-MMD', '-MF', str(dep), '-MT', 'obj']
        if source in user:
            args += ['-Dmain=app_main']
        command([TOOLCHAIN / 'riscv-none-elf-gcc.exe', *args, '-MM', source], out, f'dependencies_{index:02}.log')
        # GCC emits forward slashes; preserve spaces escaped in Make dependencies.
        text = dep.read_text().replace('\\\n', ' ')
        dependencies = re.findall(r'(?:\\ |[^\s])+', text.split(':', 1)[1])
        for token in dependencies:
            path = Path(token.replace('\\ ', ' '))
            if not path.is_absolute():
                path = out / path
            path = inside(path)
            tracked.add(path)
            before.setdefault(path, sha(path))
        command([TOOLCHAIN / 'riscv-none-elf-gcc.exe', *args, '-c', source, '-o', obj], out, f'compile_{index:02}.log')
        objects.append(obj)
    elf, binary = out / 'program.elf', out / 'program.bin'
    link_flags = ['-nostdlib', '-nostartfiles', '-Wl,--no-relax', '-Wl,--build-id=none', '-Wl,--gc-sections',
                  '-T', str(BSP / 'linker.ld'), f'-Wl,-Map={out}/program.map']
    command([TOOLCHAIN / 'riscv-none-elf-gcc.exe', *flags, *link_flags, *objects, '-o', elf, '-lgcc'], out, 'link.log')
    libgcc = Path(command([TOOLCHAIN / 'riscv-none-elf-gcc.exe', '-march=rv32i', '-mabi=ilp32', '-print-libgcc-file-name'], out, 'libgcc_path.txt').strip()).resolve()
    tracked.add(inside(libgcc))
    for tool, args, log in [('objcopy', ['-O', 'binary', elf, binary], 'objcopy.log'),
                            ('readelf', ['-h', '-A', '-l', '-S', elf], 'program.readelf.txt'),
                            ('objdump', ['-d', elf], 'program.dis'), ('nm', ['-n', elf], 'symbols.txt'),
                            ('size', [elf], 'size.txt')]:
        command([TOOLCHAIN / f'riscv-none-elf-{tool}.exe', *args], out, log)
    info = application.audit(elf, binary, 'hello')
    info.update(status='C_APP_AUDIT_PASS', kind='c_app', expect_mode='exact' if exact else 'contains_once', expected_hex=expected.hex())
    if any(sha(path) != digest for path, digest in before.items()):
        raise ValueError('Source/support changed during build')
    tracked.update([elf, binary, out / 'symbols.txt', out / 'program.dis', out / 'program.readelf.txt'])
    info['input_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(tracked)}
    # Preserve a byte-identical source/tool snapshot for each unique build.
    for rel in info['input_sha256']:
        copy = out / 'inputs' / rel
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes((ROOT / rel).read_bytes())
    save(out / 'manifest.json', info)
    save(out / 'build_receipt.json', dict(status='C_APP_BUILD_PASS', source_paths=[p.as_posix() for p in user], hardware=hardware))
    print(f'RESULT: PASS C_APP_BUILD_AUDIT bytes={info["bytes"]} CRC32={info["crc32"]:08X}', flush=True)
    return out


def prepare_gate(out, max_cycles=40000000):
    manifest = out / 'manifest.json'
    info = require_manifest(manifest)
    hardware, hardware_inputs = hardware_gate()
    subprocess.run([sys.executable, str(SIM / 'run.py'), '--build', str(out), '--max-cycles', str(max_cycles)], check=True)
    if require_manifest(manifest) != info:
        raise ValueError('Application changed during simulation')
    folder = SIM / 'build' / out.name
    result_path = folder / 'results.json'
    result = json.loads(result_path.read_text())
    if result['status'] != 'C_APP_FULL_SIM_PASS' or not result['inputs_unchanged']:
        raise ValueError('Full real-CPU simulation did not pass')
    inputs = dict(hardware_inputs, **info['input_sha256'])
    inputs[manifest.relative_to(ROOT).as_posix()] = sha(manifest)
    inputs.update(result['input_sha256'])
    evidence = {p.relative_to(ROOT).as_posix(): sha(p) for p in folder.iterdir() if p.is_file()}
    save(out / 'deployment_gate.json', dict(status='C_APP_SIM_GATE_PASS', hardware=hardware,
         manifest_sha256=sha(manifest), input_sha256=inputs, evidence_sha256=evidence,
         application_output_sha256=sha(folder / 'application_uart.txt'), board_result='NOT_TESTED'))
    print('RESULT: PASS C_APP_PREPARED; board NOT_TESTED; build:', out.as_posix(), flush=True)


def require_gate(out):
    info = require_manifest(out / 'manifest.json')
    gate = json.loads((out / 'deployment_gate.json').read_text())
    hardware, _ = hardware_gate()
    if gate['status'] != 'C_APP_SIM_GATE_PASS' or gate['hardware'] != hardware or gate['manifest_sha256'] != sha(out / 'manifest.json'):
        raise ValueError('Application/hardware gate mismatch')
    for group in ('input_sha256', 'evidence_sha256'):
        for rel, expected in gate[group].items():
            if sha(ROOT / rel) != expected:
                raise ValueError('Gate input/evidence changed: ' + rel)
    folder = SIM / 'build' / out.name
    parse_output(info, (folder / 'application_uart.txt').read_bytes())
    return info, hardware


def execute(port, info, records, app, *, quiet=None, timeout=40):
    import time
    quiet = quiet or time.sleep
    if port.in_waiting:
        raise ValueError('Unexpected startup RX; reset first (no automatic flush)')
    for want in plan.make_plan(info):
        row = dict(want, result='INCOMPLETE', extra_rx_hex='')
        records.append(row)
        tx = bytes.fromhex(want['tx_hex'])
        row['written_bytes'] = port.write(tx)
        if row['written_bytes'] != len(tx):
            raise ValueError('Short serial write')
        raw = upload.read_exact(port, 60)
        row['rx_hex'] = raw.hex()
        row['decoded'] = plan.rvld.decode(raw, bytes.fromhex(want['expected_hex']))
        if not want.get('run'):
            quiet(.002)
            extra = port.read(port.in_waiting) if port.in_waiting else b''
            row['extra_rx_hex'] = extra.hex()
            if extra:
                raise ValueError('Unexpected bytes before next request')
        row['result'] = 'PASS'
    data = bytearray()
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        data += port.read(port.in_waiting or 1)
        app['rx_hex'] = data.hex()
        if len(data) > MAX_OUTPUT:
            raise ValueError('Output exceeds 64 KiB')
        if re.search(rb'\nC_APP_DONE return=-?\d+\n', data):
            break
    else:
        raise ValueError('Application output deadline; main must return')
    parsed = parse_output(info, bytes(data))
    quiet(.1)
    extra = port.read(port.in_waiting) if port.in_waiting else b''
    app.update(rx_hex=data.hex(), extra_rx_hex=extra.hex(), parsed=parsed, seconds=time.monotonic() - start)
    if extra:
        raise ValueError('Extra/duplicate application output')
    app['result'] = 'PASS'
    return parsed


def deploy(out, log):
    import time
    info, hardware = require_gate(out)
    if log.exists():
        raise ValueError('Preserve existing log; choose another --log')
    input('确认已下载成功主工程位流、关闭串口助手；按 KEY0，释放并等待 DDR 初始化完成后按回车：')
    # Recheck after the user waits; no serial opened before gates pass.
    info, hardware = require_gate(out)
    log.parent.mkdir(parents=True, exist_ok=True)
    result = dict(status='RUNNING', evidence_origin='ACTUAL_SERIAL', build_path=out.as_posix(),
                  manifest_sha256=sha(out / 'manifest.json'), gate_sha256=sha(out / 'deployment_gate.json'),
                  hardware=hardware, port='COM11', baud=115200, records=[], application={}, retry_count=0,
                  no_automatic_retry=True, user_KEY0_confirmation=True, JTAG_independently_observed=False)
    with log.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    try:
        import serial
        with serial.Serial('COM11', 115200, bytesize=8, parity='N', stopbits=1, timeout=.05,
                           write_timeout=2, xonxoff=False, rtscts=False, dsrdtr=False) as port:
            time.sleep(.25)
            execute(port, info, result['records'], result['application'])
        result['status'] = 'C_APP_ACTUAL_BOARD_PASS'
        print(bytes.fromhex(result['application']['rx_hex']).decode('utf-8', errors='replace'), end='')
        print('RESULT: PASS C_APP_ACTUAL_BOARD_PASS; log:', log.as_posix())
    except BaseException as error:
        result.update(status='FAIL', error=str(error))
        raise
    finally:
        save(log, result)


def verify_log(path):
    raw = json.loads(path.read_text())
    if raw['status'] != 'C_APP_ACTUAL_BOARD_PASS' or raw['evidence_origin'] != 'ACTUAL_SERIAL':
        raise ValueError('Not a successful actual serial log')
    out = inside(raw['build_path'])
    info, hardware = require_gate(out)
    if raw['hardware'] != hardware or raw['manifest_sha256'] != sha(out / 'manifest.json') or raw['gate_sha256'] != sha(out / 'deployment_gate.json'):
        raise ValueError('Board log identity mismatch')
    if raw['port'] != 'COM11' or raw['baud'] != 115200 or raw['retry_count'] != 0 or not raw['no_automatic_retry'] or not raw['user_KEY0_confirmation']:
        raise ValueError('Board log session mismatch')
    expected = plan.make_plan(info)
    if len(raw['records']) != len(expected):
        raise ValueError('Missing/extra protocol response')
    for row, want in zip(raw['records'], expected):
        if any(row[k] != v for k, v in want.items()) or row['result'] != 'PASS' or row['extra_rx_hex']:
            raise ValueError('Protocol record mismatch')
        if row['written_bytes'] != len(bytes.fromhex(want['tx_hex'])):
            raise ValueError('Short recorded write')
        decoded = plan.rvld.decode(bytes.fromhex(row['rx_hex']), bytes.fromhex(want['expected_hex']))
        if row['decoded'] != decoded:
            raise ValueError('Decoded response differs')
    app = raw['application']
    if app['result'] != 'PASS' or app['extra_rx_hex'] or app['parsed'] != parse_output(info, bytes.fromhex(app['rx_hex'])):
        raise ValueError('Application record mismatch')
    return dict(status='C_APP_ACTUAL_BOARD_VERIFIED', log_sha256=sha(path), responses=len(expected), run_count=1)
