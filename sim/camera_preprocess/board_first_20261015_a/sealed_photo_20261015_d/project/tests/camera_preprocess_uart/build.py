"""Build, statically audit and host-cross-check the fixed two-group preprocess program.

Writes everything into build/<tag>/ (refuses to overwrite an existing tag):
  program.elf / program.bin / program.dat, compile/objcopy/readelf/objdump/nm/size
  logs with the exact argv, cwd and exit code, *.su stack-usage logs, the RV32I
  section/stack/instruction audit, a stack-usage vs disassembly cross-check, a
  static wire-contract check against tools/camera_preprocess_uart/protocol.py, the
  native host check of the reference formula and of the PP01 header/CRC encoder,
  and manifest.json with all source/tool SHA256 values.

Never opens a serial port, never starts PDS, never creates board_release.json.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOLS = ROOT / 'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
PPTOOL = ROOT / 'tools/camera_preprocess_uart'
TAG_DEFAULT = 'pp_uart_20261015_a'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

SOURCES = ['startup.S', 'main.c', 'preprocess_ref.c', 'pp01_wire.c']
HEADERS = ['preprocess_ref.h', 'pp01_wire.h']
HOST_ONLY = ['native_check.c']
FLAGS = ['-march=rv32i', '-mabi=ilp32', '-O2', '-std=c11', '-g', '-Wall', '-Wextra',
         '-Werror', '-ffreestanding', '-fno-builtin', '-fno-pic', '-fno-pie',
         '-msmall-data-limit=0', '-ffunction-sections', '-fdata-sections',
         '-fstack-usage', '-nostdlib', '-nostartfiles', '-Wl,--no-relax',
         '-Wl,--build-id=none', '-Wl,--gc-sections']
HOST_FLAGS = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror']


def run(argv, label, out, timeout=120, expect=0):
    argv = [str(a) for a in argv]
    proc = subprocess.run(argv, cwd=str(out), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, timeout=timeout)
    (out / (label + '.log')).write_text(proc.stdout, encoding='utf-8')
    (out / (label + '.command.json')).write_text(
        json.dumps(dict(argv=argv, cwd=str(out), returncode=proc.returncode), indent=2) + '\n',
        encoding='utf-8')
    if proc.returncode != expect:
        raise RuntimeError(f'{label} exit {proc.returncode}\n{proc.stdout}')
    return proc.stdout


# ------------------------------------------------------------------ static audit

def parse_symbols(path):
    funcs = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        m = re.match(r'^([0-9a-f]{8})\s+([Tt])\s+(\S+)$', line)
        if m:
            funcs.append((int(m.group(1), 16), m.group(3)))
    funcs.sort()
    return funcs


def frame_from_disassembly(disassembly, funcs):
    """Largest `addi sp,sp,-N` prologue per function, plus resolved call edges."""
    frames, edges, calls = {}, {}, []
    bounds = []
    for i, (addr, name) in enumerate(funcs):
        end = funcs[i + 1][0] if i + 1 < len(funcs) else 0xffffffff
        bounds.append((addr, end, name))
        frames[name] = 0
        edges[name] = set()
    owner = None
    for line in disassembly.splitlines():
        m = re.match(r'^([0-9a-f]+):\t[0-9a-f ]+\t(.*)$', line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        body = m.group(2)
        if owner is None or not (owner[0] <= addr < owner[1]):
            owner = None
            for start, end, name in bounds:
                if start <= addr < end:
                    owner = (start, end, name)
                    break
            if owner is None:
                continue
        name = owner[2]
        adj = re.search(r'addi\s+sp,sp,-(\d+)', body)
        if adj:
            frames[name] = max(frames[name], int(adj.group(1)))
        if re.match(r'^(jal|jalr)\b', body):
            mnemonic = body.split()[0]
            if mnemonic in ('jal', 'jalr'):
                target = re.search(r'<([^>]+)>', body)
                if target:
                    calls.append((name, addr, mnemonic, target.group(1)))
    known = {n for _, n in funcs}
    for caller, addr, mnemonic, target in calls:
        if caller != target and target in known:
            edges[caller].add(target)
    return frames, edges, calls


def stack_usage(path):
    frames = {}
    for su in sorted(Path(path).glob('*.su')):
        for line in su.read_text(encoding='utf-8').splitlines():
            m = re.match(r'^(.+?):(\d+):(\d+):(\S+)\t(\d+)\t(\S+)$', line)
            if m:
                frames[m.group(4)] = int(m.group(5))
    return frames


def stack_depth(frames, edges):
    """Conservative static bound: frame(f) + max over callees (tail calls counted)."""
    best, chain, cycles = {}, {}, []

    def visit(name, stack):
        if name in best:
            return best[name], chain[name]
        if name in stack:
            cycles.append(list(stack) + [name])
            return 0, [name]
        deepest, deepchain = 0, []
        for callee in sorted(edges.get(name, ())):
            value, child = visit(callee, stack + [name])
            if value > deepest:
                deepest, deepchain = value, child
        total = frames.get(name, 0) + deepest
        best[name] = total
        chain[name] = [name] + deepchain
        return total, chain[name]

    for name in frames:
        visit(name, [])
    if not best:
        return 0, [], cycles
    top = max(best, key=lambda n: best[n])
    return best[top], chain[top], cycles


# --------------------------------------------------------------- wire contract

def load_peer_protocol():
    path = PPTOOL / 'protocol.py'
    if not path.exists():
        return None, None
    sys.path.insert(0, str(PPTOOL))
    spec = importlib.util.spec_from_file_location('pp_peer_protocol', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def c_literals(source):
    return ''.join(re.findall(r'"((?:[^"\\]|\\.)*)"', source))


def wire_contract_check(protocol, module_path):
    """Static proof that the firmware emits the frozen lines and header layout."""
    main_c = (HERE / 'main.c').read_text(encoding='utf-8')
    blob = c_literals(main_c).replace('\\n', '')
    checks, failures = {}, []

    def require(name, ok, detail=''):
        checks[name] = dict(ok=bool(ok), detail=detail)
        if not ok:
            failures.append(name)

    if protocol is None:
        require('peer_protocol_imported', False, f'missing {module_path}')
        return dict(checks=checks, failures=failures, protocol_sha256=None)

    lines = [protocol.LINE_APP_HEADER, protocol.LINE_SENSOR, protocol.LINE_READY,
             protocol.LINE_EXPORT_BEGIN, protocol.LINE_EXPORT_DONE, protocol.LINE_SESSION_DONE]
    for i, line in enumerate(lines):
        require(f'line_{i}', line in blob, line)
    for name, value in (('cmd_open', protocol.LINE_SESSION_OPEN),
                        ('cmd_capture', protocol.LINE_CAPTURE),
                        ('cmd_export', protocol.LINE_EXPORT),
                        ('cmd_finish', protocol.LINE_FINISH)):
        require(name, f"(uint8_t)'{value}'" in main_c, value)
    summary = re.sub(r'\{[^}]*\}', '', protocol.SUMMARY_FMT)
    require('summary_layout', summary in blob, summary)
    require('kind_totals', (protocol.SOURCE_TOTAL, protocol.RGB_TOTAL, protocol.CHUNK) ==
            (1843200, 27648, 1024), 'peer totals/chunk')
    require('header_bytes', protocol.HEADER_BYTES == 32 and protocol.MAGIC == b'PP01',
            'peer header/magic')
    wire_c = (HERE / 'pp01_wire.c').read_text(encoding='utf-8')
    require('magic_bytes', all(f"out[{i}] = '{c}';" in wire_c
                               for i, c in enumerate("PP01")), 'PP01 literal')
    require('header_crc_span', 'pp01_crc_bytes(out, 28u)' in wire_c, 'header CRC over 28 bytes')
    for i, field in enumerate(('kind', 'seq', 'offset', 'length', 'total', 'data_crc')):
        require(f'header_field_{field}', f'put_le32(out + {4 * (i + 1)}, {field});' in wire_c, field)
    require('data_payload_rule', 'send_packet(1u, cur_seq, off, CHUNK, SRC_BYTES,' in main_c and
            'send_packet(3u, cur_seq, off, CHUNK, OUT_BYTES,' in main_c, 'DATA payload_len')
    require('end_payload_rule', 'send_packet(2u, cur_seq, SRC_BYTES, 0u, SRC_BYTES, cur_src_crc)' in main_c and
            'send_packet(4u, cur_seq, OUT_BYTES, 0u, OUT_BYTES, cur_pp_crc)' in main_c,
            'END offset=total, len=0, whole-stream CRC')
    require('single_ack_per_packet', main_c.count('EXPORT_ACK_TIMEOUT') == 1 and
            main_c.count('EXPORT_ACK_BYTE') == 1, 'one K wait per packet')
    require('source_before_rgb', main_c.index('send_packet(1u') < main_c.index('send_packet(3u'),
            'source stream precedes RGB888 stream')
    return dict(checks=checks, failures=failures, protocol_sha256=sha(module_path),
                protocol_path=str(module_path.relative_to(ROOT)))


# ------------------------------------------------------------- native host check

def expected_python(source):
    """Frozen doc formula, implemented independently of the C code under test."""
    out = bytearray(96 * 96 * 3)
    k = 0
    for y in range(96):
        base = ((2 * y + 1) * 15) // 4 * 1280
        for x in range(96):
            sx = 280 + ((2 * x + 1) * 15) // 4
            o = 2 * (base + sx)
            p = source[o] | (source[o + 1] << 8)
            r5, g6, b5 = (p >> 11) & 31, (p >> 5) & 63, p & 31
            out[k] = (r5 << 3) | (r5 >> 2)
            out[k + 1] = (g6 << 2) | (g6 >> 4)
            out[k + 2] = (b5 << 3) | (b5 >> 2)
            k += 3
    return bytes(out)


def expand565(p):
    return (((p >> 11) & 31) << 3 | ((p >> 11) & 31) >> 2,
            ((p >> 5) & 63) << 2 | ((p >> 5) & 63) >> 4,
            (p & 31) << 3 | (p & 31) >> 2)


def pattern_source(k):
    out = bytearray()
    for y in range(720):
        for x in range(1280):
            r5 = (3 * x + 5 * y + 7 * k) & 31
            g6 = (11 * x + 7 * y + 13 * k) & 63
            b5 = (x ^ (3 * y) ^ (17 * k)) & 31
            p = (r5 << 11) | (g6 << 5) | b5
            out.append(p & 0xff)
            out.append(p >> 8)
    return bytes(out)


def solid_source(pixel):
    return bytes((pixel & 0xff, pixel >> 8)) * (1280 * 720)


def native_check(out, host_gcc):
    folder = out / 'native'
    folder.mkdir()
    exe = folder / 'native_check.exe'
    run([host_gcc, *HOST_FLAGS, '-o', exe, HERE / 'native_check.c',
         HERE / 'preprocess_ref.c', HERE / 'pp01_wire.c'], 'native_compile', folder)
    report = dict(patterns={}, wire={}, vectors={})

    text = run([exe, '--vectors'], 'native_vectors', folder)
    vectors = {}
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] == 'VECTOR':
            vectors[parts[1]] = parts[2]
        elif parts and parts[0] == 'FIRST':
            report['first'] = [int(v) for v in parts[1:]]
        elif parts and parts[0] == 'LAST':
            report['last'] = [int(v) for v in parts[1:]]
        elif parts and parts[0] == 'STRIDE':
            report['stride'] = line
    for p, name in ((0x0000, '0000'), (0xffff, 'ffff'), (0x2104, '2104'), (0x0841, '0841'),
                    (0xf800, 'f800'), (0x07e0, '07e0'), (0x001f, '001f'), (0x0001, '0001'),
                    (0x0010, '0010')):
        r, g, b = expand565(p)
        want = f'{r:02x}{g:02x}{b:02x}'
        if vectors.get(name) != want:
            raise RuntimeError(f'native vector {name}: {vectors.get(name)} != {want}')
        report['vectors'][name] = want
    if report.get('first') != [283, 3, 2 * (3 * 1280 + 283)]:
        raise RuntimeError(f"native first coordinate {report.get('first')}")
    if report.get('last') != [996, 716, 2 * (716 * 1280 + 996)]:
        raise RuntimeError(f"native last coordinate {report.get('last')}")
    if report.get('stride') != 'STRIDE 7=47 8=48 other=0':
        raise RuntimeError(f"native stride {report.get('stride')}")

    patterns = [('k1_asymmetric', pattern_source(1)), ('k2_asymmetric', pattern_source(2)),
                ('solid_red_f800', solid_source(0xf800)),
                ('solid_green_07e0', solid_source(0x07e0)),
                ('solid_blue_001f', solid_source(0x001f))]
    for name, source in patterns:
        src = folder / f'source_{name}.rgb565'
        src.write_bytes(source)
        exp = folder / f'expected_{name}.rgb'
        coords = folder / f'coords_{name}.bin'
        run([exe, '--ref', src, exp, coords], f'native_ref_{name}', folder)
        want = expected_python(source)
        got = exp.read_bytes()
        if got != want:
            bad = next(i for i in range(len(want)) if got[i] != want[i])
            raise RuntimeError(f'{name}: native expected differs at byte {bad}')
        raw = coords.read_bytes()
        if len(raw) != 96 * 96 * 24:
            raise RuntimeError(f'{name}: coords size {len(raw)}')
        crc = 0xffffffff
        for i in range(0, len(raw), 24):
            x, y, sx, sy, offset, pixel = (int.from_bytes(raw[i + 4 * j:i + 4 * j + 4], 'little')
                                           for j in range(6))
            wy, wx = divmod(i // 24, 96)
            if (x, y) != (wx, wy):
                raise RuntimeError(f'{name}: coord order at {i // 24}')
            wsx = 280 + ((2 * x + 1) * 15) // 4
            wsy = ((2 * y + 1) * 15) // 4
            if (sx, sy) != (wsx, wsy):
                raise RuntimeError(f'{name}: sample coordinate ({x},{y}) {sx},{sy} != {wsx},{wsy}')
            if offset != 2 * (wsy * 1280 + wsx):
                raise RuntimeError(f'{name}: byte offset ({x},{y})')
            if pixel != (source[offset] | (source[offset + 1] << 8)):
                raise RuntimeError(f'{name}: sampled pixel ({x},{y})')
            if got[3 * (y * 96 + x) + 0] != ((pixel >> 11) & 31) << 3 | ((pixel >> 11) & 31) >> 2:
                raise RuntimeError(f'{name}: R bit replication ({x},{y})')
        report['patterns'][name] = dict(source_sha256=sha(src), expected_sha256=sha(exp),
                                        coords_sha256=sha(coords), expected_crc32=f'{zlib.crc32(want) & 0xffffffff:08x}',
                                        source_crc32=f'{zlib.crc32(source) & 0xffffffff:08x}',
                                        bytes=len(want))

    records = folder / 'wire_records.bin'
    run([exe, '--wire', records], 'native_wire', folder)
    protocol, protocol_path = load_peer_protocol()
    tuples = [(1, 1, 0, 1843200), (1, 1, 1024, 1843200), (1, 3, 512, 1843200),
              (1, 4294967295, 1842176, 1843200), (2, 1, 1843200, 1843200),
              (2, 4294967295, 1843200, 1843200), (3, 2, 0, 27648), (3, 2, 26624, 27648),
              (4, 2, 27648, 27648), (4, 7, 27648, 27648)]
    data = records.read_bytes()
    pos = 0
    for index, (kind, seq, offset, total) in enumerate(tuples):
        length = min(1024, total - offset) if kind in (1, 3) else 0
        header = data[pos:pos + 32]
        payload = data[pos + 32:pos + 32 + length]
        if len(payload) != length:
            raise RuntimeError(f'wire record {index}: truncated')
        expect_payload = bytes((offset + j) * 37 + 11 & 0xff for j in range(length))
        if payload != expect_payload:
            raise RuntimeError(f'wire record {index}: payload formula')
        want_crc = zlib.crc32(payload) & 0xffffffff
        if int.from_bytes(header[24:28], 'little') != want_crc:
            raise RuntimeError(f'wire record {index}: firmware CRC != zlib.crc32')
        if protocol is not None:
            if header != protocol.build_header(kind, seq, offset, length, total, want_crc):
                raise RuntimeError(f'wire record {index}: header != protocol.build_header')
        if int.from_bytes(header[28:32], 'little') != zlib.crc32(header[:28]) & 0xffffffff:
            raise RuntimeError(f'wire record {index}: header CRC != zlib.crc32(header[0:28])')
        if header[:4] != b'PP01':
            raise RuntimeError(f'wire record {index}: magic')
        for field, value in ((4, kind), (8, seq), (12, offset), (16, length), (20, total)):
            if int.from_bytes(header[field:field + 4], 'little') != value:
                raise RuntimeError(f'wire record {index}: field {field}')
        pos += 32 + length
    if pos != len(data):
        raise RuntimeError('wire records: trailing bytes')
    report['wire'] = dict(records=len(tuples), bytes=len(data),
                          peer_header_encoder=protocol is not None,
                          records_sha256=sha(records))
    report['expected_formula_source'] = 'doc/camera/OV5640预处理96RGB888与DDR接口_2026-10-15.md §2'
    report['host_gcc'] = run([host_gcc, '--version'], 'native_gcc_version', folder).splitlines()[0]
    return exe, report


# ------------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tag', default=TAG_DEFAULT)
    ap.add_argument('--host-gcc', default=None)
    args = ap.parse_args()
    if not re.fullmatch('[a-z0-9_]+', args.tag):
        raise SystemExit('tag must be [a-z0-9_]+')
    out = HERE / 'build' / args.tag
    out.mkdir(parents=True, exist_ok=False)

    host_gcc = args.host_gcc or shutil.which('gcc')
    if host_gcc is None:
        raise SystemExit('a host C compiler is required for the native cross-check')

    elf = out / 'program.elf'
    binary = out / 'program.bin'
    sources = [HERE / s for s in SOURCES]
    run([TOOLS / 'riscv-none-elf-gcc.exe', *FLAGS, *sources, '-T', HERE / 'linker.ld',
         f'-Wl,-Map={out / "program.map"}', '-o', elf, '-lgcc'], 'compile', out, timeout=180)
    for label, tool, tool_args in (('objcopy', 'objcopy', ['-O', 'binary', elf, binary]),
                                   ('readelf', 'readelf', ['-h', '-A', '-l', '-S', elf]),
                                   ('disassembly', 'objdump', ['-d', elf]),
                                   ('symbols', 'nm', ['-n', elf]),
                                   ('size', 'size', [elf])):
        run([TOOLS / f'riscv-none-elf-{tool}.exe', *tool_args], label, out)
    (out / 'symbols.txt').write_text((out / 'symbols.log').read_text(encoding='utf-8'),
                                     encoding='utf-8')
    su = stack_usage(out)
    (out / 'stack_usage.log').write_text(
        ''.join(f'{name} {size}\n' for name, size in sorted(su.items())), encoding='utf-8')

    # ---- section/stack/instruction audit (RV32I legality, no float/compressed).
    sys.path.insert(0, str(ROOT / 'tools/uart_loader/candidates/bsp_workflow'))
    from application import audit                                        # noqa: E402
    info = audit(elf, binary, 'crc32')

    funcs = parse_symbols(out / 'symbols.txt')
    frames, edges, calls = frame_from_disassembly((out / 'disassembly.log').read_text(encoding='utf-8'), funcs)
    mismatch = {n: (su[n], frames[n]) for n in su if n in frames and su[n] != frames[n]}
    if mismatch:
        raise RuntimeError(f'stack usage vs disassembly mismatch: {mismatch}')
    depth, chain, cycles = stack_depth(frames, edges)
    (out / 'stack_depth.json').write_text(json.dumps(dict(
        frames_su=su, frames_disassembly=frames, calls=[list(c) for c in calls],
        edges={k: sorted(v) for k, v in edges.items()}, max_depth_bytes=depth,
        max_depth_chain=chain, cycles=cycles), indent=2) + '\n', encoding='utf-8')
    if depth >= 4096:
        raise RuntimeError(f'static stack depth {depth} does not fit the 4 KiB stack')
    info['stack_usage'] = dict(frames=su, max_function_frame=max(frames.values()),
                               max_depth_bytes=depth, max_depth_chain=chain,
                               su_vs_disassembly_mismatch=mismatch, call_edges=sum(len(v) for v in edges.values()))

    # ---- frozen wire contract against the peer PC tool.
    protocol, protocol_path = load_peer_protocol()
    contract = wire_contract_check(protocol, protocol_path)
    if contract['failures']:
        raise RuntimeError(f'wire contract check failed: {contract["failures"]}')

    # ---- host cross-check of the board reference and wire encoder.
    exe, native = native_check(out, host_gcc)
    (out / 'native_check.json').write_text(
        json.dumps(native, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    # ---- DAT (DDR image representation; ROM/RAM initialisation is untouched).
    raw = binary.read_bytes()
    padded = raw + b'\0' * ((-len(raw)) % 4)
    dat = out / 'program.dat'
    dat.write_text(''.join(f'{int.from_bytes(padded[i:i + 4], "little"):08x}\n'
                           for i in range(0, len(padded), 4)), encoding='ascii')
    decoded = b''.join(int(w, 16).to_bytes(4, 'little') for w in dat.read_text().split())
    if decoded != padded:
        raise RuntimeError('program.dat round trip failed')

    inputs = [*sources, *[HERE / h for h in HEADERS], *[HERE / h for h in HOST_ONLY],
              HERE / 'linker.ld', Path(__file__),
              ROOT / 'tools/uart_loader/candidates/bsp_workflow/application.py',
              ROOT / 'tools/uart_loader/candidates/bsp_workflow/plan.py',
              ROOT / 'tests/uart_loader/candidates/verify_run_hello/image_to_dat.py']
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    protected = [*(ROOT / 'myriscv').glob('*.v'), ROOT / 'RISCV.pds',
                 *(ROOT / 'tests/camera_uart').glob('*'),
                 *(ROOT / 'tests/camera_double100').glob('*'),
                 *(ROOT / 'tools/camera_uart').glob('*.py')]
    protect = {p.relative_to(ROOT).as_posix(): sha(p) for p in protected if p.is_file()}
    peer = {p.name: sha(p) for p in sorted(PPTOOL.glob('*.py'))}

    info.update(status='PP_UART_BUILD_STATIC_AUDIT_PASS', kind='camera_preprocess_uart',
                audit_kind='crc32', tag=args.tag, command='python tests/camera_preprocess_uart/build.py',
                source_sha256=hashes, protected_sha256=protect, wire_contract_tools_sha256=peer,
                flags=FLAGS, host_flags=HOST_FLAGS, host_gcc=host_gcc,
                groups=2, abi='camera ABI2 43414d02 / PP 50525001',
                sources=['A=0x41000000', 'B=0x41200000'], output='0x42000000',
                frame=dict(source_bytes=1843200, source_pixels=921600, source_beats=57600,
                           rgb888_bytes=27648, rgb888_side=96, rgb888_planes=3,
                           chunk_bytes=1024, groups=2),
                timeouts_seconds=dict(config=5, camera_ready=5, pp_normal=5, cpu_verify=20,
                                      packet_ack=5, uart_tx=5, command_auto=30,
                                      command_group2_user_confirm=600),
                protocol=dict(magic='PP01', header_bytes=32, endian='little',
                              kinds={1: 'source_data', 2: 'source_end', 3: 'rgb888_data',
                                     4: 'rgb888_end'},
                              data_payload_len='min(1024,total-offset)', end_offset='total',
                              ack='one K per accepted packet', order='source then rgb888',
                              ascii_blocks=['PPX_BEGIN', 'PPX_DONE'],
                              summary=protocol.SUMMARY_FMT if protocol else None),
                reference='integer only; sx=280+((2x+1)*15)/4, sy=((2y+1)*15)/4, bit replication',
                wire_contract=contract, native_check=native, native_check_exe=str(exe.relative_to(ROOT)),
                dat_path=str(dat.relative_to(ROOT)), dat_bytes=len(padded),
                dat_round_trip=True, board='NOT_RUN', serial_opened=False, PDS_started=False,
                board_release_created=False, board_release_required='sim/camera_preprocess/key_20261015_a/board_release.json',
                full_CPU_HDL_simulation='NOT_RUN', CNN='NOT_CONNECTED',
                scope='offline build and static audit only; never opened a serial port')

    for name, digest in {**hashes, **protect}.items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('input changed during the build: ' + name)
    (out / 'manifest.json').write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n',
                                       encoding='utf-8')
    print(json.dumps(dict(status=info['status'], tag=args.tag, bytes=info['bytes'],
                          bin_sha256=info['bin_sha256'], crc32=f"{info['crc32']:08x}",
                          dat=info['dat_path'], max_stack_bytes=depth, max_depth_chain=chain,
                          instructions_audited=info['instructions_audited'],
                          native_patterns=len(native['patterns']),
                          serial_opened=False, PDS_started=False), indent=2))


if __name__ == '__main__':
    main()
