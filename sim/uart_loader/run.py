"""Gate ROM residency and fixed-data CPU DDR writes/readback; no program download."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BUILD = HERE / 'build'
IMAGE = ROOT / 'tests/uart_loader/build'
MS = Path('D:/modelsim/win64pe')
NAMES = 'alu br_alu l_alu regfile csr_file mycpu_sync inst_bus_interconnect data_bus_interconnect inst_bram_adapter data_bram_adapter simple_mmio dual_sram_to_pango_ddr_bridge uart_tx uart_rx uart_rx_fifo uart_mmio soc_top'.split()
SOURCES = [ROOT / 'myriscv' / (n + '.v') for n in NAMES] + sorted((HERE / 'tb').glob('*.v'))
sys.path.insert(0, str(ROOT / 'tools/uart_loader'))
from protocol import packet, expected_response, decode_response, crc32, FIXED_DATA, RX_TEST, DDR_TEST, DDR_CRC_TEST, DDR_BASE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected():
    files = list((ROOT / 'myriscv').glob('*.v'))
    files += [ROOT / p for p in (
        'RISCV.pds', 'constraint_check/temp_constraint_file.fdc',
        'ipcore/inst_rom/inst_rom.idf', 'ipcore/inst_rom/inst_rom.v',
        'ipcore/inst_rom/rtl/inst_rom_init_param.v',
        'ipcore/data_ram/data_ram.idf', 'ipcore/data_ram/data_ram.v',
        'ipcore/data_ram/data_ram_tb.v', 'ipcore/data_ram/rtl/data_ram_init_param.v',
        'ipcore/ddr3/ddr3.idf', 'ipcore/ddr3/ddr3.v',
        'MyCpu_test/board_selftest/boot_rom.dat', 'MyCpu_test/board_selftest/ddr_selftest.dat',
        'tests/pc_uart_fpga_uart_pc/main.dat', 'tests/pc_uart_fpga_uart_pc/build/main.dat',
        'tests/fpga_uart_pc_output_30/main.dat',
        'tests/coremark_baremetal/build/validation_60/main.dat',
        'tests/coremark_baremetal/verified/validation_60/main.dat',
        'tests/coremark_baremetal/verified/performance_60/main.dat')]
    files += [ROOT / 'tests/uart_loader/build' / name for name in
              ('loader.elf', 'loader_rom.dat', 'loader_ram.dat', 'manifest.json')]
    files += list((HERE / 'board').glob('*first*'))
    files += [HERE / 'board/ping100_after_reset_verified.json', HERE / 'board/ping_stage1_board_result.json']
    files += [ROOT / 'tests/uart_loader/build/rx_fixed' / name for name in
              ('loader.elf', 'loader_rom.dat', 'loader_ram.dat', 'manifest.json')]
    files += [HERE / 'board' / name for name in ('rx_fixed100_after_reset_verified.json', 'rx_fixed_stage2_board_result.json')]
    files += [ROOT / 'tests/uart_loader/build/ddr_fixed' / name for name in
              ('loader.elf', 'loader_rom.dat', 'loader_ram.dat', 'manifest.json')]
    files += [HERE / 'board' / name for name in ('ddr_fixed100_first_verified.json',
              'ddr_fixed100_after_reset_verified.json', 'ddr_fixed_stage3_board_result.json')]
    return {str(p): sha(p) for p in files}


def command(args, folder, log, timeout=180):
    start = time.monotonic()
    try:
        process = subprocess.run(list(map(str, args)), cwd=folder, capture_output=True,
                                 text=True, errors='replace', timeout=timeout)
        output = process.stdout + process.stderr
    except subprocess.TimeoutExpired as error:
        log.write_text('RESULT: FAIL process timeout\n', encoding='utf-8')
        raise RuntimeError(f'process timeout: {log}') from error
    log.write_text(output, encoding='utf-8')
    if process.returncode: raise RuntimeError(f'exit {process.returncode}: {log}\n{output[-2500:]}')
    return output, round(time.monotonic() - start, 2)


def image_info():
    spec = importlib.util.spec_from_file_location('loader_image', ROOT / 'tests/uart_loader/image_to_dat.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw, sections, symbols, rx_load, recover_load, instructions = module.audit(IMAGE / 'loader.elf')
    saved = json.loads((IMAGE / 'manifest.json').read_text())
    for name, expected_hash in saved['sha256'].items():
        if sha(IMAGE / name) != expected_hash: raise ValueError(f'image changed since build: {name}')
    for name, section in (('loader_rom.dat', '.text'), ('loader_ram.dat', '.rodata')):
        words = [int(w, 16) for w in (IMAGE / name).read_text().split()]
        if len(words) != 4096: raise ValueError('expected 4096-word DAT')
        image = b''.join(w.to_bytes(4, 'little') for w in words)
        s = sections[section]
        if image[s['address']:s['address'] + s['size']] != raw[s['offset']:s['offset'] + s['size']]:
            raise ValueError('DAT does not match ELF section')
        expected = bytearray((0x6f).to_bytes(4, 'little') * 4096 if section == '.text' else bytes(16384))
        expected[s['address']:s['address'] + s['size']] = raw[s['offset']:s['offset'] + s['size']]
        if image != expected: raise ValueError('DAT padding/reservations differ')
    if symbols != saved['symbols'] or instructions != saved['instructions_audited']:
        raise ValueError('manifest audit information differs')
    for key, value in module.ddr_instructions(raw, sections, symbols).items():
        if saved.get(key) != value: raise ValueError('DDR instruction audit differs')
    return saved


def stimulus(folder, count):
    # Independent Python/zlib oracle vs C software, UART pin and CPU retirement.
    if crc32(b'123456789') != 0xcbf43926 or crc32(b'') != 0: raise ValueError('PC CRC vectors')
    half = count // 2
    cases = [{'epoch': 0, 'cmd': 1, 'seq': seq, 'status': 0} for seq in range(1, half + 1)]
    cases += [{'epoch': 0, 'cmd': 1, 'seq': half, 'status': 0, 'duplicate': True}]
    cases += [{'epoch': 0, 'cmd': cmd, 'seq': half + cmd - 1, 'status': 0x8007} for cmd in (2, 3, 4)]
    cases += [{'epoch': 1, 'cmd': 1, 'seq': seq, 'status': 0} for seq in range(1, count - half + 1)]
    requests = b''.join(packet(cmd=c['cmd'], seq=c['seq']) for c in cases)
    responses = b''.join(expected_response(c['seq'], c['cmd'], c['status']) for c in cases)
    for name, data in (('requests', requests), ('responses', responses)):
        (folder / (name + '.bin')).write_bytes(data)
        (folder / (name + '.hex')).write_text(''.join(f'{v:02x}\n' for v in data), encoding='ascii')
    (folder / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n', encoding='utf-8')
    # A damaged response/sequence must not be accepted by the PC tool.
    good = expected_response(1)
    if decode_response(good, 1)['status'] != 0: raise ValueError('PC response decoder')
    for candidate, seq in ((good[:-1] + bytes([good[-1] ^ 1]), 1), (good, 2)):
        try: decode_response(candidate, seq)
        except ValueError: pass
        else: raise ValueError('PC decoder accepted damaged response/sequence')
    return cases, requests, responses


def fixed_stimulus(folder):
    cases = [
        {'cmd': 1, 'seq': 1},
        {'cmd': RX_TEST, 'seq': 2},
        {'cmd': RX_TEST, 'seq': 2, 'duplicate': True},
        {'cmd': 1, 'seq': 2, 'status': 0x8009},
        {'cmd': RX_TEST, 'seq': 3, 'corrupt_crc': True, 'status': 0x8001, 'recover': True},
        {'cmd': RX_TEST, 'seq': 3, 'wrong_data': True, 'status': 0x800a, 'recover': True},
        {'cmd': RX_TEST, 'seq': 3, 'wrong_length': True, 'status': 0x8003, 'recover': True},
        {'cmd': RX_TEST, 'seq': 3},
        {'cmd': 4, 'seq': 4, 'status': 0x8007, 'recover': True},
        {'cmd': 1, 'seq': 4},
        {'cmd': 1, 'seq': 1, 'new_epoch': True},
        {'cmd': RX_TEST, 'seq': 2},
        {'cmd': RX_TEST, 'seq': 3},
        {'cmd': 1, 'seq': 4}]
    requests, responses, lengths, state = bytearray(), bytearray(), [], []
    pings = tests = nacks = last = 0
    for c in cases:
        if c.get('new_epoch'): pings = tests = nacks = last = 0
        c.setdefault('status', 0)
        payload = FIXED_DATA if c['cmd'] == RX_TEST else b''
        if c.get('wrong_data'): payload = payload[:20] + bytes([payload[20] ^ 1]) + payload[21:]
        if c.get('wrong_length'): payload += b'\x99'
        request = packet(c['cmd'], c['seq'], payload=payload)
        if c.get('corrupt_crc'): request = request[:-1] + bytes([request[-1] ^ 1])
        requests += request
        responses += expected_response(c['seq'], c['cmd'], c['status'])
        lengths.append(len(request))
        if c['status']: nacks += 1
        elif not c.get('duplicate'):
            last = c['seq']
            if c['cmd'] == 1: pings += 1
            else: tests += 1
        compare_buffer = c['cmd'] == RX_TEST and not c.get('wrong_length')
        state += [pings, tests, nacks, last, int(c.get('recover', False)), int(compare_buffer)]
    for name, data in (('requests', requests), ('responses', responses)):
        (folder / (name + '.bin')).write_bytes(data)
        (folder / (name + '.hex')).write_text(''.join(f'{v:02x}\n' for v in data), encoding='ascii')
    for name, values in (('frame_lengths', lengths), ('case_state', state)):
        (folder / (name + '.hex')).write_text(''.join(f'{v:08x}\n' for v in values), encoding='ascii')
    (folder / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n', encoding='utf-8')
    return cases, bytes(requests), bytes(responses)


def ddr_stimulus(folder):
    cases = [
        {'cmd': 1, 'seq': 1}, {'cmd': RX_TEST, 'seq': 2},
        {'cmd': DDR_TEST, 'seq': 3, 'attempt': True},
        {'cmd': DDR_TEST, 'seq': 3, 'duplicate': True},
        {'cmd': DDR_TEST, 'seq': 4, 'attempt': True, 'inject': True, 'status': 0x800b},
        {'cmd': DDR_TEST, 'seq': 4, 'attempt': True},
        {'cmd': DDR_TEST, 'seq': 5, 'wrong_address': True, 'status': 0x8002, 'recover': True},
        {'cmd': DDR_TEST, 'seq': 5, 'corrupt_crc': True, 'status': 0x8001, 'recover': True},
        {'cmd': DDR_TEST, 'seq': 5, 'wrong_data': True, 'status': 0x800a, 'recover': True},
        {'cmd': DDR_TEST, 'seq': 5, 'wrong_length': True, 'status': 0x8003, 'recover': True},
        {'cmd': 1, 'seq': 5}, {'cmd': 4, 'seq': 6, 'status': 0x8007, 'recover': True},
        {'cmd': 1, 'seq': 1, 'new_epoch': True},
        {'cmd': DDR_TEST, 'seq': 2, 'attempt': True},
        {'cmd': DDR_TEST, 'seq': 3, 'attempt': True},
        {'cmd': RX_TEST, 'seq': 4}, {'cmd': 1, 'seq': 5}]
    requests, responses, lengths, state, ddr_state = bytearray(), bytearray(), [], [], []
    pings = tests = nacks = last = ddr_count = ddr_status = 0
    for c in cases:
        if c.get('new_epoch'): pings = tests = nacks = last = ddr_count = ddr_status = 0
        c.setdefault('status', 0)
        payload = FIXED_DATA if c['cmd'] in (RX_TEST, DDR_TEST) else b''
        if c.get('wrong_data'): payload = payload[:20] + bytes([payload[20] ^ 1]) + payload[21:]
        if c.get('wrong_length'): payload += b'\x99'
        address = DDR_BASE + int(c.get('wrong_address', False)) if c['cmd'] == DDR_TEST else 0
        request = packet(c['cmd'], c['seq'], address=address, payload=payload)
        if c.get('corrupt_crc'): request = request[:-1] + bytes([request[-1] ^ 1])
        requests += request; lengths.append(len(request))
        responses += expected_response(c['seq'], c['cmd'], c['status'])
        if c.get('attempt'): ddr_status = c['status']
        if c['status']: nacks += 1
        elif not c.get('duplicate'):
            last = c['seq']
            if c['cmd'] == 1: pings += 1
            elif c['cmd'] == RX_TEST: tests += 1
            else: ddr_count += 1
        compare_buffer = c['cmd'] in (RX_TEST, DDR_TEST) and not c.get('wrong_length') and not c.get('wrong_address')
        state += [pings, tests, nacks, last, int(c.get('recover', False)), int(compare_buffer)]
        ddr_state += [ddr_count, int(c.get('attempt', False)), int(c.get('inject', False)), ddr_status]
    for name, data in (('requests', requests), ('responses', responses)):
        (folder / (name + '.bin')).write_bytes(data)
        (folder / (name + '.hex')).write_text(''.join(f'{v:02x}\n' for v in data), encoding='ascii')
    for name, values in (('frame_lengths', lengths), ('case_state', state), ('ddr_state', ddr_state)):
        (folder / (name + '.hex')).write_text(''.join(f'{v:08x}\n' for v in values), encoding='ascii')
    (folder / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n', encoding='utf-8')
    return cases, bytes(requests), bytes(responses)


def crc_stimulus(folder):
    cases = [
        {'cmd': 1, 'seq': 1},
        {'cmd': DDR_CRC_TEST, 'seq': 2, 'crc_read': True, 'status': 0x8001},
        {'cmd': DDR_TEST, 'seq': 2, 'attempt': True},
        {'cmd': DDR_CRC_TEST, 'seq': 3, 'crc_read': True},
        {'cmd': DDR_CRC_TEST, 'seq': 3, 'crc_read': True, 'duplicate': True},
        {'cmd': DDR_CRC_TEST, 'seq': 4, 'crc_read': True, 'inject': True, 'status': 0x8001},
        {'cmd': DDR_CRC_TEST, 'seq': 4, 'crc_read': True, 'status': 0x8001},
        {'cmd': DDR_TEST, 'seq': 4, 'attempt': True},
        {'cmd': DDR_CRC_TEST, 'seq': 5, 'crc_read': True, 'wrong_expected': True, 'status': 0x8001},
        {'cmd': DDR_CRC_TEST, 'seq': 5, 'crc_read': True},
        {'cmd': DDR_CRC_TEST, 'seq': 5, 'wrong_expected': True, 'status': 0x8009},
        {'cmd': DDR_CRC_TEST, 'seq': 6, 'corrupt_crc': True, 'status': 0x8001, 'recover': True},
        {'cmd': DDR_CRC_TEST, 'seq': 6, 'wrong_address': True, 'status': 0x8002, 'recover': True},
        {'cmd': DDR_CRC_TEST, 'seq': 6, 'wrong_length': True, 'status': 0x8003, 'recover': True},
        {'cmd': 4, 'seq': 6, 'status': 0x8007, 'recover': True},
        {'cmd': 1, 'seq': 6},
        {'cmd': DDR_CRC_TEST, 'seq': 1, 'crc_read': True, 'new_epoch': True},
        {'cmd': DDR_TEST, 'seq': 2, 'attempt': True},
        {'cmd': DDR_CRC_TEST, 'seq': 3, 'crc_read': True},
        {'cmd': RX_TEST, 'seq': 4}, {'cmd': 1, 'seq': 5}]
    requests, responses, lengths, state, ddr_state, crc_state = bytearray(), bytearray(), [], [], [], []
    pings = tests = nacks = last = ddr_count = ddr_status = 0
    crc_count = crc_reads = crc_actual = crc_expected = crc_status = 0
    memory = bytes([0xa5]*64)
    for c in cases:
        if c.get('new_epoch'):
            pings = tests = nacks = last = ddr_count = ddr_status = 0
            crc_count = crc_reads = crc_actual = crc_expected = crc_status = 0
        c.setdefault('status', 0)
        payload = FIXED_DATA if c['cmd'] in (RX_TEST, DDR_TEST) else b''
        is_crc = c['cmd'] == DDR_CRC_TEST
        expected = crc32(FIXED_DATA) ^ int(c.get('wrong_expected', False)) if is_crc else 0
        address = DDR_BASE + int(c.get('wrong_address', False)) if c['cmd'] in (DDR_TEST, DDR_CRC_TEST) else 0
        request = packet(c['cmd'], c['seq'], address=address, payload=payload, image_crc=expected,
                         length=65 if c.get('wrong_length') else 64 if is_crc else None)
        if c.get('corrupt_crc'): request = request[:-1] + bytes([request[-1]^1])
        if c.get('attempt'): memory = FIXED_DATA; ddr_status = 0
        if c.get('inject'): memory = memory[:26] + bytes([memory[26]^1]) + memory[27:]
        if c.get('crc_read'):
            crc_reads += 1; crc_actual = crc32(memory); crc_expected = expected; crc_status = c['status']
            if (crc_actual == expected) != (c['status'] == 0): raise ValueError('CRC oracle status')
        c['actual_crc'] = crc_actual if c.get('crc_read') else 0
        c['expected_crc'] = expected
        requests += request; lengths.append(len(request))
        responses += expected_response(c['seq'], c['cmd'], c['status'], c['actual_crc'])
        if c['status']: nacks += 1
        elif not c.get('duplicate'):
            last = c['seq']
            if c['cmd'] == 1: pings += 1
            elif c['cmd'] == RX_TEST: tests += 1
            elif c['cmd'] == DDR_TEST: ddr_count += 1
            else: crc_count += 1
        state += [pings, tests, nacks, last, int(c.get('recover', False)), int(bool(payload))]
        ddr_state += [ddr_count, int(c.get('attempt', False)), int(c.get('inject', False)), ddr_status]
        crc_state += [crc_count, crc_reads, crc_actual, crc_expected, crc_status,
                      int(c.get('crc_read', False)), crc32(memory)]
    for name, data in (('requests', requests), ('responses', responses)):
        (folder / (name + '.bin')).write_bytes(data)
        (folder / (name + '.hex')).write_text(''.join(f'{v:02x}\n' for v in data), encoding='ascii')
    for name, values in (('frame_lengths', lengths), ('case_state', state), ('ddr_state', ddr_state), ('crc_state', crc_state)):
        (folder / (name + '.hex')).write_text(''.join(f'{v:08x}\n' for v in values), encoding='ascii')
    (folder / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n', encoding='utf-8')
    # A response packet can have a valid packet CRC but claim an incorrect DDR CRC.
    try: decode_response(expected_response(1, DDR_CRC_TEST, actual_crc=crc32(FIXED_DATA)^1), 1, DDR_CRC_TEST)
    except ValueError: pass
    else: raise ValueError('PC accepted forged ACK DDR CRC')
    return cases, bytes(requests), bytes(responses)


def run(options):
    global IMAGE, BUILD
    crc = options.stage == 'ddr-crc'
    ddr = crc or options.stage == 'ddr-fixed'
    fixed = ddr or options.stage == 'rx-fixed'
    IMAGE = ROOT / 'tests/uart_loader/build' / ('ddr_crc' if crc else 'ddr_fixed' if ddr else 'rx_fixed' if fixed else '')
    BUILD = HERE / 'build' / ('ddr_crc' if crc else 'ddr_fixed' if ddr else 'rx_fixed' if fixed else 'ping_recheck')
    if fixed:
        gate = json.loads((HERE / 'board' / ('ddr_fixed_stage3_board_result.json' if crc else 'rx_fixed_stage2_board_result.json' if ddr else 'ping_stage1_board_result.json')).read_text())
        if gate['board_result'] != 'PASS': raise RuntimeError('previous board stage not PASS')
        for key in ('first_round', 'after_reset_round'):
            if sha(HERE / 'board' / gate[key]['evidence']) != gate[key]['sha256']:
                raise RuntimeError('stage-1 board evidence hash differs')
    BUILD.mkdir(parents=True, exist_ok=True)
    before = protected()
    info = image_info()
    own = [ROOT / 'tests/uart_loader' / p for p in
           ('main.c', 'startup.S', 'linker.ld', 'uart_loader.c', 'uart_loader.h', 'uart_io.c', 'uart_io.h', 'crc32.c', 'crc32.h')]
    own += SOURCES + [Path(__file__), ROOT / 'tools/uart_loader/protocol.py',
                      ROOT / 'tools/uart_loader/loader.py', ROOT / 'tests/uart_loader/build.ps1',
                      ROOT / 'tests/uart_loader/image_to_dat.py']
    if ddr: own += [ROOT / 'tests/uart_loader/ddr_test.c', ROOT / 'tests/uart_loader/ddr_test.h']
    inputs = {str(p): sha(p) for p in own}
    symbols = info['symbols']
    plus = [f'+ROM={IMAGE.joinpath("loader_rom.dat").as_posix()}', f'+RAM={IMAGE.joinpath("loader_ram.dat").as_posix()}']
    mapping = {'BSS_START': '__bss_start', 'BSS_END': '__bss_end', 'MAIN': 'main',
               'READY': 'loader_ready', 'PING_ADDR': 'loader_ping_count', 'NACK_ADDR': 'loader_nack_count',
               'LAST_SEQ': 'loader_last_seq', 'BOOT_ERROR': 'loader_boot_error',
               'RECOVER': 'loader_recovering', 'PROBE': 'loader_bss_probe'}
    plus += [f'+{key}={symbols[value]:x}' for key, value in mapping.items()]
    if fixed:
        plus += [f'+{key}={symbols[value]:x}' for key, value in
                 {'TEST_COUNT': 'loader_test_count', 'TEST_BYTES': 'loader_test_bytes',
                  'TEST_CRC': 'loader_test_crc'}.items()]
    if ddr:
        plus += [f'+{key}={symbols[value]:x}' for key, value in
                 {'DDR_COUNT': 'loader_ddr_count', 'DDR_BYTES': 'loader_ddr_bytes',
                  'DDR_STATUS': 'loader_ddr_status'}.items()]
        plus += [f'+DDR_WRITE_PC={info["ddr_write_pc"]:x}', f'+DDR_READ_PC={info["ddr_read_pc"]:x}',
                 f'+DDR_READ_RD={info["ddr_read_rd"]}']
    if crc:
        plus += [f'+{key}={symbols[value]:x}' for key, value in
                 {'CRC_COUNT': 'loader_crc_count', 'CRC_READS': 'loader_crc_reads',
                  'CRC_ACTUAL': 'loader_crc_actual', 'CRC_EXPECTED': 'loader_crc_expected',
                  'CRC_STATUS': 'loader_crc_status'}.items()]
        plus += [f'+CRC_READ_PC={info["ddr_crc_read_pc"]:x}', f'+CRC_READ_RD={info["ddr_crc_read_rd"]}']
    plus += [f'+STACK_SET={symbols["loader_stack_ready"] - 4:x}']
    rodata = info['sections']['.rodata']
    plus += [f'+RODATA_END={rodata["address"] + rodata["size"]:x}', f'+RX_PC={info["rx_load_pc"]:x}',
             f'+RX_RD={info["rx_load_rd"]}', f'+RECOVER_RX_PC={info["recover_rx_load_pc"]:x}',
             f'+RECOVER_RX_RD={info["recover_rx_load_rd"]}']
    report = {'image': info, 'protected_sha256': before, 'input_sha256': inputs,
              'board_result': 'NOT_TESTED', 'results': []}
    try:
        stages = ((0, 'residency'), (4, 'ddr_crc')) if crc else ((0, 'residency'), (3, 'ddr_fixed')) if ddr else ((0, 'residency'), (2, 'rx_fixed')) if fixed else ((0, 'residency'), (1, 'ping'))
        for stage, name in stages:
            folder = BUILD / name
            folder.mkdir(parents=True, exist_ok=True)
            if stage == 1:
                cases, requests, responses = stimulus(folder, options.ping_count)
            elif stage == 2:
                cases, requests, responses = fixed_stimulus(folder)
            elif stage == 3:
                cases, requests, responses = ddr_stimulus(folder)
            elif stage == 4:
                cases, requests, responses = crc_stimulus(folder)
            work = folder / 'work'
            if not work.exists(): command([MS / 'vlib.exe', work], folder, folder / 'vlib.log')
            output, _ = command([MS / 'vlog.exe', '-sv', '-work', work,
                                 f'+incdir+{ROOT / "myriscv"}', *SOURCES], folder, folder / 'compile.log')
            if 'Errors: 0' not in output: raise RuntimeError('compile missing Errors: 0')
            arguments = plus + [f'+CAPTURE={folder.joinpath("uart_tx.bin").as_posix()}',
                                f'+RX_CAPTURE={folder.joinpath("uart_rx.bin").as_posix()}']
            if stage != 0:
                arguments += [f'+STIMULUS={folder.joinpath("requests.hex").as_posix()}',
                              f'+EXPECTED={folder.joinpath("responses.hex").as_posix()}']
            if stage >= 2:
                arguments += [f'+LENGTHS={folder.joinpath("frame_lengths.hex").as_posix()}',
                              f'+CASE_STATE={folder.joinpath("case_state.hex").as_posix()}',
                              f'+DATA_CRC={crc32(FIXED_DATA):x}']
            if stage >= 3:
                arguments += [f'+DDR_STATE={folder.joinpath("ddr_state.hex").as_posix()}',
                              f'+TRACE={folder.joinpath("ddr_trace.csv").as_posix()}']
            if stage == 4:
                arguments += [f'+CRC_STATE={folder.joinpath("crc_state.hex").as_posix()}']
            script = folder / 'run.tcl'
            script.write_text('onerror {quit -f -code 1}\n' +
                              f'vsim -t 1ps -lib {{{work.as_posix()}}} -gSTAGE={stage} -gPING_COUNT={options.ping_count} tb_uart_loader ' +
                              ' '.join(arguments) + '\nonfinish stop\nrun 2500ms\n' +
                              'if {[examine -radix unsigned /tb_uart_loader/test_pass] != 1} {\n' +
                              'echo {RESULT: FAIL incomplete loader simulation}\nquit -f -code 1\n}\nquit -f -code 0\n', encoding='ascii')
            print(f'START {name}: exact ROM/RAM DAT; ModelSim; frames={len(cases) if stage else 0}', flush=True)
            output, seconds = command([MS / 'vsim.exe', '-c', '-do', 'do run.tcl'], folder,
                                      folder / 'modelsim.log', timeout=2400)
            matches = re.findall(r'^(?:# )?RESULT: PASS uart_loader .*$', output, re.M)
            if len(matches) != 1 or 'RESULT: FAIL' in output or 'Errors: 0' not in output:
                raise RuntimeError(f'{name} acceptance failed: {folder}\n{output[-2500:]}')
            decoded_tx = (folder / 'uart_tx.bin').read_bytes()
            decoded_rx = (folder / 'uart_rx.bin').read_bytes()
            if stage != 0:
                if decoded_tx != responses or decoded_rx != requests: raise ValueError('raw UART captures differ from oracle')
                for i, case in enumerate(cases):
                    frame = decoded_tx[i * 60:(i + 1) * 60]
                    result = decode_response(frame, case['seq'], case['cmd'], expected_crc=case.get('expected_crc'))
                    if result['status'] != case['status']: raise ValueError('unexpected diagnostic response')
                    if result['actual_ddr_crc'] != case.get('actual_crc', 0): raise ValueError('DDR CRC response differs')
                (folder / 'decoded_responses.json').write_text(json.dumps(cases, indent=2) + '\n', encoding='utf-8')
            elif decoded_tx or decoded_rx: raise ValueError('residency emitted UART')
            if protected() != before: raise RuntimeError('protected source/IP/image changed')
            print(f'{name}: {matches[0]} ({seconds}s)', flush=True)
            report['results'].append({'stage': name, 'result': 'PASS', 'seconds': seconds, 'evidence': matches[0]})
            (BUILD / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            if options.residency_only: break
        report['status'] = 'RESIDENCY_PASS' if options.residency_only else 'DDR_CRC_STAGE_PASS' if crc else 'FIXED_DDR_STAGE_PASS' if ddr else 'FIXED_RX_STAGE_PASS' if fixed else 'PING_STAGE_PASS'
        if protected() != before or any(sha(IMAGE / name) != value for name, value in info['sha256'].items()):
            raise RuntimeError('protected files/image changed before validation receipt')
        (BUILD / 'validated_image.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf-8')
        print(f'RESULT: PASS uart_loader {report["status"]}; board NOT_TESTED; LOAD/VERIFY/RUN not implemented', flush=True)
    except Exception as error:
        report['status'] = 'FAIL'
        report['error'] = str(error)
        raise
    finally:
        report['protected_unchanged'] = protected() == before
        report['image_unchanged'] = all(sha(IMAGE / name) == value for name, value in info['sha256'].items())
        (BUILD / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        if not report['protected_unchanged'] or not report['image_unchanged']:
            raise RuntimeError('protected files or exact candidate DAT changed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['ddr-crc', 'ddr-fixed', 'rx-fixed', 'ping'], default='ddr-crc')
    parser.add_argument('--ping-count', type=int, default=100)
    parser.add_argument('--residency-only', action='store_true')
    args = parser.parse_args()
    if not 2 <= args.ping_count <= 200: parser.error('--ping-count must be 2..200')
    try: run(args)
    except Exception as error:
        print(f'RESULT: FAIL uart_loader: {error}', file=sys.stderr, flush=True)
        sys.exit(1)
