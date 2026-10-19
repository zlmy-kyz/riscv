"""PP01 camera-preprocess session runner: plan-only, live UART and read-only replay.

Three strictly separated modes (see README.md):

``plan``    -- offline manifest/plan inspection.  Never opens a serial port and never
               writes a board result.
``live``    -- real board run.  Requires a new log directory, the frozen final BIN and
               ``sim/camera_preprocess/key_20261015_a/board_release.json`` (created by
               Sol, never by this tool).  Opens the serial port only after that gate.
``replay``  -- read-only re-derivation of every artifact from the recorded raw RX/TX.
               Trusts no JSON field: expected.rgb, both PNGs, the byte comparison and
               the whole wire structure are recomputed from the raw bytes.

Evidence origin is recorded as ``ACTUAL_SERIAL`` or ``OFFLINE_SYNTHETIC``; synthetic
directories are always refused as board evidence.
"""
import hashlib
import json
import struct
import time
from pathlib import Path

import protocol as pp
import reference
from reference import crc32

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / 'sim/camera_preprocess/key_20261015_a/board_release.json'
DEFAULT_MANIFEST = ROOT / 'tests/camera_preprocess_uart/build/pp_uart_20261015_a/manifest.json'
SOURCE_BYTES = reference.SOURCE_BYTES
OUT_BYTES = reference.OUT_BYTES
SOURCES = ('source', 'rgb')
ARTIFACT_NAMES = ('source.rgb565', 'actual.rgb', 'expected.rgb', 'source.png',
                  'actual96.png', 'expected96.png')
TICK_HZ = 93750000
GROUP_SECONDS = 600.0
LINE_SECONDS = 30.0
PACKET_SECONDS = 5.0


class Rejected(ValueError):
    """Terminal rejection: the run/evidence is not acceptable."""


def need(ok, why):
    if not ok:
        raise Rejected(why)


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def save(folder, record):
    Path(folder, 'result.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
        encoding='utf-8')


def artifact_names(group):
    return [f'group_{group}_' + n for n in ARTIFACT_NAMES]


# ------------------------------------------------------------------- manifest

def load_manifest(path, required=True):
    """Read the frozen firmware manifest and verify BIN/ELF/source hashes."""
    path = Path(path)
    if not path.exists():
        need(not required, f'firmware manifest not found: {path}')
        return None
    info = json.loads(path.read_text(encoding='utf-8'))
    need(str(info.get('status', '')).endswith('STATIC_AUDIT_PASS'),
         f'firmware manifest status: {info.get("status")!r}')
    for key in ('bin_path', 'elf_path', 'bin_sha256', 'bytes'):
        need(key in info, f'manifest missing {key}')
    need(sha_file(ROOT / info['bin_path']) == info['bin_sha256'], 'firmware BIN changed')
    if info.get('elf_path') and info.get('elf_sha256'):
        need(sha_file(ROOT / info['elf_path']) == info['elf_sha256'], 'firmware ELF changed')
    for name, digest in (info.get('source_sha256') or {}).items():
        need(sha_file(ROOT / name) == digest, f'firmware source changed: {name}')
    return info


def loader_plan(info):
    """Reuse the already verified Loader plan/wire implementation read-only."""
    import importlib.util
    path = ROOT / 'tools/uart_loader/candidates/bsp_workflow/plan.py'
    spec = importlib.util.spec_from_file_location('pp_existing_loader_plan', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.make_plan(info)


def plan_only(manifest_path):
    """Offline plan description.  No serial port, no board result written."""
    info = load_manifest(manifest_path)
    plans = loader_plan(info)
    pngs = ['source.png', 'actual96.png', 'expected96.png']
    return dict(status='PP_PLAN_ONLY_SERIAL_NOT_OPENED', evidence_origin='NOT_RUN',
                serial_opened=False, board_release_required=str(RELEASE.relative_to(ROOT)),
                board_release_created_by_this_tool=False,
                manifest=str(manifest_path), bin_sha256=info['bin_sha256'],
                bytes=info['bytes'], crc32=f'{info["crc32"]:08x}',
                loader_responses=len(plans),
                RUN_commands=sum(bool(r.get('run')) for r in plans),
                groups=pp.GROUP_PAIRS, packets_per_group=None,
                source_bytes=SOURCE_BYTES, rgb888_bytes=OUT_BYTES,
                png=pngs, retries=0, nack=0,
                group_wire_min_seconds=round(((SOURCE_BYTES + OUT_BYTES) / pp.CHUNK + 2) *
                                             (32 + 1) * 10 / 115200, 2))


def board_release(info):
    """The Sol release gate binding the exact firmware.  This tool never creates it."""
    need(RELEASE.exists(),
         f'board deployment pending Sol key review: {RELEASE.relative_to(ROOT)} is absent; '
         'no serial port was opened.  This tool must never create that file.')
    gate = json.loads(RELEASE.read_text(encoding='utf-8'))
    need(gate.get('status') == 'SOL_KEY_REVIEW_PASS_BOARD_RELEASED',
         f'board release status: {gate.get("status")!r}')
    need(gate.get('firmware_sha256') == info['bin_sha256'],
         'board release bound to a different firmware BIN')
    return gate


# ---------------------------------------------------------------- writer helper

class AckWriter:
    """Writes ACK bytes through the raw evidence recorder."""

    def __init__(self, wire, port):
        self.wire, self.port = wire, port

    def ack(self, wire, port):
        wire.write(port, pp.ACK)


class PortReader:
    """Binds the raw evidence recorder to a port and exposes ``read(n)``."""

    def __init__(self, wire, port):
        self.wire, self.port = wire, port

    def read(self, n):
        return self.wire.read(self.port, n)


# --------------------------------------------------------------- ASCII scanning

def scan_lines(rx, start, count, what):
    """Return [(text, raw, begin, end)] for the next ``count`` LF-terminated lines."""
    rows, pos = [], start
    for _ in range(count):
        idx = rx.find(b'\n', pos)
        need(idx >= 0, f'{what}: missing newline in raw RX')
        raw = rx[pos:idx + 1]
        need(not raw.endswith(b'\r\n'), f'{what}: CR in raw RX')
        try:
            text = raw[:-1].decode('ascii')
        except UnicodeDecodeError:
            raise Rejected(f'{what}: non-ASCII line in raw RX')
        rows.append((text, raw, pos, idx + 1))
        pos = idx + 1
    return rows


def check_loader_and_app_header(rx, tx, info, recorded):
    """Replay the Loader wire and the application banner from raw RX/TX."""
    plans = loader_plan(info)
    need(len(plans) == len(recorded), 'Loader response count differs from plan')
    a = b = 0
    rebuilt = []
    for plan, row in zip(plans, recorded):
        sent = bytes.fromhex(plan['tx_hex'])
        reply = bytes.fromhex(plan['expected_hex'])
        need(tx[a:a + len(sent)] == sent, f'Loader TX differs: {plan["name"]}')
        need(rx[b:b + 60] == reply, f'Loader RX differs: {plan["name"]}')
        need(row['name'] == plan['name'] and row['tx_offset'] == a and row['rx_offset'] == b,
             f'Loader ledger differs: {plan["name"]}')
        rebuilt.append(dict(name=plan['name'], tx_offset=a, rx_offset=b))
        a += len(sent)
        b += 60
    rows = scan_lines(rx, b, 3, 'application banner')
    need([r[0] for r in rows] == [pp.LINE_APP_HEADER, pp.LINE_SENSOR, pp.LINE_READY],
         'application banner identity/sensor/config differs from raw RX')
    b = rows[-1][3]
    # Return the offset of the session-open byte and the offset just past it.
    need(tx[a:a + 1] == pp.LINE_SESSION_OPEN.encode(), 'session-open command byte')
    return (dict(loader_records=rebuilt, session_line=rows, tx_after_loader=a + 1,
                 rx_after=rows[-1][3]), a, b)


# ------------------------------------------------------------------- live mode

def execute_live(wire, port, info, folder, record, progress=print, confirm=input):
    """Run the two frozen group pairs on the real board, first failure stops all I/O."""
    need(wire.rx_count == 0 and wire.tx_count == 0, 'internal: evidence must start empty')
    plan = loader_plan(info)
    record['loader_records'] = []
    record['loader_plan'] = [dict(name=p['name'], run=bool(p.get('run'))) for p in plan]
    lines = pp.LineReader(wire, port)
    reader = PortReader(wire, port)
    for step in plan:
        record['loader_records'].append(dict(name=step['name'], tx_offset=wire.tx_count,
                                             rx_offset=wire.rx_count))
        wire.write(port, bytes.fromhex(step['tx_hex']))
        reply = pp.exact(reader, 60, PACKET_SECONDS, 'Loader response')
        need(reply == bytes.fromhex(step['expected_hex']),
             f'Loader response/CRC/state mismatch: {step["name"]}')
        if not step.get('run'):
            need(not port.in_waiting, 'unexpected UART bytes before next Loader request')
    for want, what in ((pp.LINE_APP_HEADER, 'application header'),
                       (pp.LINE_SENSOR, 'sensor/config'),
                       (pp.LINE_READY, 'preprocess ready')):
        text, raw = lines.line(LINE_SECONDS, what)
        need(text == want, f'{what}: {text!r} != {want!r}')
        progress(text)
    record['commands'].append(dict(group=0, capture_tx_offset=wire.tx_count - lines.pending))
    wire.write(port, pp.LINE_SESSION_OPEN.encode())
    need(lines.pending == 0, 'internal: line buffer must be drained before binary data')
    record['session_rx_start'] = lines.position()
    receiver = pp.PacketReceiver(lines, AckWriter(wire, port), record['packet_ledger'],
                                 timeout=PACKET_SECONDS)
    for group in (1, 2):
        if group == 2:
            confirm('请按提示改变实物画面并在相机就绪后按 Enter 采第二组：')
            record['user_scene_change_confirmation'] = True
        record['commands'].append(dict(group=group,
                                       capture_tx_offset=wire.tx_count - lines.pending))
        wire.write(port, pp.LINE_CAPTURE.encode())
        line_start = lines.position()
        text, raw = lines.line(LINE_SECONDS, f'group {group} capture summary')
        need(text.startswith(f'PP_GROUP={group} '), f'group {group} summary line: {text!r}')
        record['summaries'].append(pp.read_summary(text, group))
        progress(text)
        record['commands'][-1]['summary_rx'] = [line_start, lines.position()]
        record['commands'][-1]['export_tx_offset'] = wire.tx_count
        wire.write(port, pp.LINE_EXPORT.encode())
        line_start = lines.position()
        text, raw = lines.line(LINE_SECONDS, f'group {group} export begin')
        need(text == pp.LINE_EXPORT_BEGIN, f'group {group} export begin: {text!r}')
        need(lines.pending == 0, 'internal: line buffer must be drained before binary data')
        record['commands'][-1]['export_rx_begin'] = line_start
        start = time.monotonic()
        row = receiver.block(reader, wire, port, record['summaries'][-1]['seq'],
                             start + GROUP_SECONDS)
        record['commands'][-1]['export_seconds'] = round(time.monotonic() - start, 3)
        line_start = lines.position()
        text, raw = lines.line(LINE_SECONDS, f'group {group} export done')
        need(text == pp.LINE_EXPORT_DONE, f'group {group} export done: {text!r}')
        record['commands'][-1]['export_rx_end'] = line_start
        payloads = row.pop('payloads')
        _write_artifacts(record, folder, group, payloads)
        progress(f'PP_GROUP={group} exported source={row["source_bytes"]} '
                 f'rgb888={row["rgb_bytes"]}')
    record['finish_tx_offset'] = wire.tx_count
    wire.write(port, pp.LINE_FINISH.encode())
    text, raw = lines.line(LINE_SECONDS, 'session done')
    receiver.session_done(text)
    record['session_finish'] = text
    record['session_rx_end'] = wire.rx_count
    need(not port.in_waiting, 'extra bytes after session finish')


def _write_artifacts(record, folder, group, payloads):
    """Split the concatenated payloads into source/RGB888 and write every artifact."""
    names = artifact_names(group)
    source_raw = b''.join(payloads)
    summary = record['summaries'][group - 1]
    need(len(source_raw) == SOURCE_BYTES + OUT_BYTES,
         f'group {group}: exported {len(source_raw)} bytes, expected '
         f'{SOURCE_BYTES + OUT_BYTES}')
    src, actual = source_raw[:SOURCE_BYTES], source_raw[SOURCE_BYTES:]
    expected = reference.expected_from_source(src)
    second = reference.expected_second_implementation(src)
    need(expected == second, f'group {group}: cross-implementation reference disagreement')
    need(reference.crc32(expected) == int(summary['pp_crc'], 16),
         f'group {group}: PP hardware CRC differs from the independent expected CRC')
    (folder / names[0]).write_bytes(src)
    (folder / names[1]).write_bytes(actual)
    (folder / names[2]).write_bytes(expected)
    (folder / names[3]).write_bytes(reference.png_source565(src))
    (folder / names[4]).write_bytes(reference.png_rgb888(actual))
    (folder / names[5]).write_bytes(reference.png_rgb888(expected))
    comparison = reference.compare(expected, actual, src)
    record['group_results'] = record.get('group_results', {})
    record['group_results'][str(group)] = dict(
        source_sha256=_sha(src), actual_sha256=_sha(actual), expected_sha256=_sha(expected),
        comparison=comparison, capture_crc=summary['capture_crc'],
        crc_closure={'capture': summary['capture_crc'], 'cpu_expected': summary['cpu_crc'],
                     'cpu_reread': summary['reread_crc'], 'pp_hardware': summary['pp_crc'],
                     'pc_expected': f'{reference.crc32(expected):08x}',
                     'pc_actual': f'{reference.crc32(actual):08x}'})
    record['visual_review'] = 'PENDING'


# ----------------------------------------------------------------- replay mode

class _BytesPort:
    """Read-only port over the recorded RX bytes; no serial side effects."""

    def __init__(self, data):
        self.data, self.pos, self.in_waiting = data, 0, False

    def read(self, n):
        part = self.data[self.pos:self.pos + n]
        self.pos += len(self.data[self.pos:self.pos + n])
        return part

    def write(self, b):
        return len(b)


def parse_group(trace, pos, index, summary_text):
    """Parse one group's PP01 binary stream directly out of the raw RX bytes."""
    seq = pp.read_summary(summary_text, index)['seq']
    offset = {'source': 0, 'rgb': 0}
    running = {'source': 0, 'rgb': 0}
    state = {'source': 'data', 'rgb': 'data'}
    order, packets = [], []
    while True:
        head_raw = trace.rx[pos:pos + pp.HEADER_BYTES]
        need(len(head_raw) == pp.HEADER_BYTES, f'group {index}: truncated header in raw RX')
        head = pp.unpack_header(head_raw, pos)
        side = 'source' if head['kind'] in (pp.KIND_SOURCE_DATA, pp.KIND_SOURCE_END) else 'rgb'
        need(state[side] != 'done', f'group {index}: {side} DATA after END')
        need(head['source_seq'] == seq, f'group {index}: source_seq differs from summary')
        if side == 'rgb':
            need(state['source'] == 'done',
                 f'group {index}: source and RGB888 streams interleaved')
        payload = trace.rx[pos + pp.HEADER_BYTES:pos + pp.HEADER_BYTES + head['payload_len']]
        need(len(payload) == head['payload_len'], f'group {index}: payload truncated')
        if head['kind'] in (pp.KIND_SOURCE_DATA, pp.KIND_RGB_DATA):
            need(head['offset'] == offset[side], f'group {index}: {side} offset gap/overlap')
            need(crc32(payload) == head['data_crc'], f'group {index}: {side} payload CRC')
            running[side] = pp.running_crc(payload, running[side])
            offset[side] += len(payload)
        else:
            need(running[side] == head['data_crc'], f'group {index}: {side} stream CRC')
            need(offset[side] == head['total_len'], f'group {index}: END before full coverage')
            state[side] = 'done'
        packets.append(dict(kind=head['kind'], kind_name=head['kind_name'],
                            source_seq=head['source_seq'], offset=head['offset'],
                            payload_len=head['payload_len'], total_len=head['total_len'],
                            data_crc=f'{head["data_crc"]:08x}', header_hex=head['header_hex'],
                            rx_offset=pos))
        order.append(side)
        pos += pp.HEADER_BYTES + head['payload_len']
        if state['source'] == 'done' and state['rgb'] == 'done':
            break
    need(order == sorted(order, key=lambda s: 0 if s == 'source' else 1),
         f'group {index}: source and RGB888 streams interleaved')
    return dict(group=index, packets=packets, rx_begin=None, rx_end=pos,
                source_bytes=offset['source'], rgb_bytes=offset['rgb'],
                source_crc32=f'{running["source"]:08x}', rgb_crc32=f'{running["rgb"]:08x}')


def replay(folder, origin='ACTUAL_SERIAL'):
    """Independent read-only audit of one evidence directory.

    Every derived value (expected.rgb, PNG pixels, first mismatch, stream CRC) is
    recomputed here from the raw RX bytes; no JSON field is trusted.
    """
    folder = Path(folder)
    need(origin in ('ACTUAL_SERIAL', 'OFFLINE_SYNTHETIC_TEST'), 'unsupported evidence origin')
    record = json.loads((folder / 'result.json').read_text(encoding='utf-8'))
    found = record.get('evidence_origin')
    if origin == 'ACTUAL_SERIAL':
        need(found == 'ACTUAL_SERIAL',
             'OFFLINE_SYNTHETIC evidence cannot be accepted as a board run')
        need(record.get('status') == 'UART_DATA_CHECK_PASS_VISUAL_PENDING',
             f'session status: {record.get("status")!r}')
        need(record.get('serial_opened') is True, 'serial was never opened')
        need(record.get('board_release_ok') is True, 'board release gate not satisfied at run time')
        need(record.get('board_release_sha256') and record.get('firmware_sha256'),
             'board release/firmware identity missing')
    else:
        need(found == 'OFFLINE_SYNTHETIC', f'evidence origin: {found!r}')
    for name, digest in (record.get('file_sha256') or {}).items():
        need(sha_file(folder / name) == digest, f'raw evidence tampered: {name}')
    for name, digest in (record.get('tool_sha256') or {}).items():
        if (Path(__file__).with_name(name)).exists():
            need(sha_file(Path(__file__).with_name(name)) == digest,
                 f'ballot tool changed since the run: {name}')

    trace = pp.Trace(folder)
    info = record['application']
    banner, a, b = check_loader_and_app_header(trace.rx, trace.tx, info,
                                               record['loader_records'])
    need(record['session_rx_start'] == b, 'session-open RX offset')
    need(record['commands'][0] == dict(group=0, capture_tx_offset=a),
         'session-open command ledger')
    a += 1

    # ---- ASCII structure and binary stream spans, all derived from the raw bytes.
    groups, pos, tx_pos = [], b, a
    for index in (1, 2):
        command = record['commands'][index]
        rows = scan_lines(trace.rx, pos, 1, f'group {index} summary')
        text, raw, begin, end = rows[0]
        need(record['summaries'][index - 1] == pp.read_summary(text, index),
             f'group {index} summary ledger differs from raw RX')
        need(command['summary_rx'] == [begin, end],
             f'group {index} summary byte span {command["summary_rx"]} vs {[begin, end]}')
        need(command['capture_tx_offset'] == tx_pos,
             f'group {index} capture command offset {command["capture_tx_offset"]} vs {tx_pos}')
        need(trace.tx[tx_pos:tx_pos + 1] == pp.LINE_CAPTURE.encode(),
             f'group {index} capture command byte')
        tx_pos += 1
        need(command['export_tx_offset'] == tx_pos,
             f'group {index} export command offset')
        need(trace.tx[tx_pos:tx_pos + 1] == pp.LINE_EXPORT.encode(),
             f'group {index} export command byte')
        tx_pos += 1
        pos = end
        begin_line, _raw, begin_start, begin_end = scan_lines(
            trace.rx, pos, 1, f'group {index} export boundary')[0]
        need(begin_line == pp.LINE_EXPORT_BEGIN, f'group {index} export begin {begin_line!r}')
        need(command['export_rx_begin'] == begin_start,
             f'group {index} export begin offset {command["export_rx_begin"]} vs {begin_start}')
        parsed = parse_group(trace, begin_end, index, text)
        done_line, _raw, done_start, done_end = scan_lines(
            trace.rx, parsed['rx_end'], 1, f'group {index} export done')[0]
        need(done_line == pp.LINE_EXPORT_DONE, f'group {index} export done line {done_line!r}')
        need(command['export_rx_end'] == done_start,
             f'group {index} export done offset {command["export_rx_end"]} vs {done_start}')
        for entry in parsed['packets']:
            need(trace.tx[tx_pos:tx_pos + 1] == pp.ACK,
                 f'group {index}: missing K ACK for kind {entry["kind"]} at {entry["offset"]}')
            tx_pos += 1
        parsed['rx_begin'] = begin_start
        groups.append(parsed)
        pos = done_end
    ledger = [e for g in groups for e in g['packets']]
    recorded = record['packet_ledger'][:len(ledger)]
    need(len(recorded) == len(ledger) and len(record['packet_ledger']) == len(ledger),
         'packet ledger count')
    for got, want in zip(recorded, ledger):
        for key in ('kind', 'offset', 'payload_len', 'total_len', 'data_crc', 'header_hex',
                    'rx_offset'):
            need(got[key] == want[key], f'packet ledger field {key} differs from raw RX')
        need(got.get('ack_byte') == 'K', 'packet ledger ACK byte')
    need(len(record['packet_ledger']) == sum(len(g['packets']) for g in groups),
         'packet ledger covers every packet exactly once')

    need(record['finish_tx_offset'] == tx_pos, 'finish command offset')
    need(trace.tx[tx_pos:tx_pos + 1] == pp.LINE_FINISH.encode(), 'finish command byte')
    tx_pos += 1
    need(tx_pos == len(trace.tx), f'extra bytes in raw TX after finish: {len(trace.tx) - tx_pos}')
    rows = scan_lines(trace.rx, pos, 1, 'session done')
    need(rows[0][0] == pp.LINE_SESSION_DONE, f'session done line: {rows[0][0]!r}')
    need(record.get('session_finish') == pp.LINE_SESSION_DONE, 'session finish ledger')
    need(rows[0][3] == len(trace.rx), f'extra bytes in raw RX after session done')
    need(len(groups) == pp.GROUP_PAIRS,
         f'exactly {pp.GROUP_PAIRS} complete groups required, got {len(groups)}')

    # ---- independent regeneration and byte comparison per group.
    report = []
    for index, group in enumerate(groups, 1):
        names = artifact_names(index)
        source_raw = (folder / names[0]).read_bytes()
        actual_raw = (folder / names[1]).read_bytes()
        expected_raw = (folder / names[2]).read_bytes()
        need(len(source_raw) == SOURCE_BYTES, f'{names[0]} size')
        need(len(actual_raw) == OUT_BYTES, f'{names[1]} size')
        # Re-derive the source stream from the raw RX and require byte identity.
        need(crc32(source_raw) & 0xffffffff == int(group['source_crc32'], 16),
             f'group {index} source.rgb565 CRC')
        need(len(expected_raw) == OUT_BYTES, f'{names[2]} size')
        expected = reference.expected_from_source(source_raw)
        second = reference.expected_second_implementation(source_raw)
        need(expected == second, f'group {index}: cross-implementation reference disagreement')
        need(expected == expected_raw,
             f'group {index}: expected.rgb on disk differs from the independent formula')
        need(reference.crc32(expected) == int(group['rgb_crc32'], 16),
             f'group {index}: expected CRC differs from the raw RGB888 stream CRC')
        comparison = reference.compare(expected, actual_raw, source_raw)
        # CRC closure: the RGB888 CRC is independent of the source-frame CRC, so only
        # the four output-tensor CRCs (CPU expected / CPU reread / PP hardware / PC)
        # plus the PC CRC of the actual bytes must agree.
        closed = {'cpu_expected_crc': record['summaries'][index - 1]['cpu_crc'],
                  'cpu_reread_crc': record['summaries'][index - 1]['reread_crc'],
                  'pp_hardware_crc': record['summaries'][index - 1]['pp_crc'],
                  'pc_expected_crc': f'{reference.crc32(expected):08x}',
                  'pc_actual_crc': f'{reference.crc32(actual_raw):08x}'}
        consistent = len(set(closed.values())) == 1
        if comparison['all_equal']:
            # 27648/27648 bytes equal: CPU expected / CPU reread / PP hardware / PC CRC
            # must all close, otherwise the evidence contradicts itself.
            need(consistent, f'group {index}: byte-identical data but CRC closure fails: {closed}')
        elif consistent:
            # The decisive case: every CRC agrees yet the bytes differ.  A CRC check
            # alone would have accepted this, the byte comparison must not.
            need(False, f'group {index}: bytes differ (first mismatch '
                        f'{comparison["first_mismatch"]}) yet every CRC agrees ({closed}); '
                        'CRC is not a substitute for byte comparison')
        else:
            need(False, f'group {index}: byte comparison failed: {comparison["first_mismatch"]}')
        pngs = [pp.png_selfcheck_pixels(folder / names[3], reference.WIDTH, reference.HEIGHT,
                                        source_raw, raw_height=reference.HEIGHT,
                                        row_bytes=3 * reference.WIDTH),
                pp.png_selfcheck_pixels(folder / names[4], reference.OUT, reference.OUT,
                                        actual_raw),
                pp.png_selfcheck_pixels(folder / names[5], reference.OUT, reference.OUT,
                                        expected_raw)]
        need((folder / names[3]).read_bytes() == reference.png_source565(source_raw),
             f'group {index}: source.png is not the deterministic lossless mapping')
        need((folder / names[4]).read_bytes() == reference.png_rgb888(actual_raw),
             f'group {index}: actual96.png must come from the actual DDR export')
        need((folder / names[5]).read_bytes() == reference.png_rgb888(expected_raw),
             f'group {index}: expected96.png is not the deterministic mapping')
        report.append(dict(group=index, source_sha256=_sha(source_raw),
                           source_crc32=f'{reference.crc32(source_raw):08x}',
                           source_capture_crc=record['summaries'][index - 1]['capture_crc'],
                           actual_sha256=_sha(actual_raw),
                           expected_sha256=_sha(expected_raw),
                           comparison=comparison, png=pngs, crc_closure=closed,
                           crc_closure_consistent=consistent,
                           byte_comparison_pass=comparison['all_equal']))
    need(len(report) == pp.GROUP_PAIRS, 'group count')
    return dict(status='ACTUAL_UART_PP01_RAW_BYTES_REPLAY_AND_PNG_VERIFIED_VISUAL_PENDING'
                if origin == 'ACTUAL_SERIAL' else 'OFFLINE_SYNTHETIC_WIRE_REPLAY_PASS',
                evidence_origin=record['evidence_origin'], groups=report,
                packets=len(ledger), session_groups=len(groups),
                session_end_count_required=pp.GROUP_PAIRS,
                visual_review='PENDING',
                data_pass=all(g['byte_comparison_pass'] and g['crc_closure_consistent']
                              for g in report))


def _sha(data):
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------ live driver

def run_live(args):
    """Real board run.  Serial port is opened only after the Sol release gate."""
    info = load_manifest(args.manifest)
    board_release(info)
    need(args.log_dir is not None and not Path(args.log_dir).exists(),
         'a new --log-dir is required; failures are never overwritten')
    folder = Path(args.log_dir).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    port_obj = None
    wire = None
    record = dict(status='RUNNING', evidence_origin='ACTUAL_SERIAL', application=info,
                  manifest_sha256=sha_file(args.manifest), port=args.port, baud=115200,
                  serial_opened=False, board_release_ok=False, retry_count=0, nack=0,
                  loader_records=[], packet_ledger=[], summaries=[], commands=[],
                  user_scene_change_confirmation=False, groups=pp.GROUP_PAIRS,
                  tool_sha256={Path(__file__).name: sha_file(__file__),
                               'protocol.py': sha_file(Path(__file__).with_name('protocol.py')),
                               'reference.py': sha_file(Path(__file__).with_name('reference.py'))})
    try:
        confirm = args.confirm if callable(getattr(args, 'confirm', None)) else input
        confirm('使用已确认时序、且含 PP ID50525001 的位流；关闭串口助手，按KEY0后释放，'
                '等待DDR就绪再按 Enter：')
        record['user_KEY0_confirmation'] = True
        import serial
        port_obj = serial.Serial(args.port, 115200, timeout=.05, write_timeout=2,
                                 xonxoff=False, rtscts=False, dsrdtr=False)
        record['serial_opened'] = True
        record['board_release_ok'] = True
        record['board_release_sha256'] = sha_file(RELEASE)
        record['firmware_sha256'] = info['bin_sha256']
        time.sleep(.25)
        wire = pp.RawEvidence(folder)
        execute_live(wire, port_obj, info, folder, record, confirm=confirm)
        record['status'] = 'UART_DATA_CHECK_PASS_VISUAL_PENDING'
    except BaseException as exc:
        record['status'] = 'STOPPED_FIRST_FAILURE'
        record['error'] = repr(exc)
        if wire and record.get('serial_opened'):
            # Preserve diagnostics already emitted by the halted firmware without ever
            # issuing another command or resynchronising.
            end = time.monotonic() + 2
            while time.monotonic() < end:
                try:
                    if not wire.read(port_obj, 4096):
                        break
                except Exception:
                    break
        raise
    finally:
        if wire:
            _finalize_folder(folder, record)
            wire.close()
        save(folder, record)
    print('日志目录：', folder)
    checked = replay(folder)
    (folder / 'verified.json').write_text(
        json.dumps(checked, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
        encoding='utf-8')
    print(json.dumps(checked, ensure_ascii=False, indent=2))


def _finalize_folder(folder, record):
    """Record the SHA256 of every evidence file so later tampering is detectable."""
    digests = {}
    for path in sorted(Path(folder).iterdir()):
        if path.is_file() and path.name not in ('result.json',):
            digests[path.name] = sha_file(path)
    record['file_sha256'] = digests
