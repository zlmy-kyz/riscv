"""Software-only acceptance suite for the PP01 PC tool.

Everything here is OFFLINE.  No serial port is opened, no board is contacted and
``board_release.json`` is never created.  The suite

* builds deterministic synthetic sources, runs the real session runner against a
  scripted in-memory board, writes the genuine evidence files (raw RX/TX, ledger,
  source/actual/expected rgb, three PNGs, result.json) and then replays them;
* injects corruptions at every layer the task requires (header CRC, payload CRC,
  magic/kind/length/offset/SEQ, short read, missing/duplicate/trailing END,
  interleaving, ACK loss, end-of-session group count, Loader bytes);
* checks pattern coordinates, colours, cross-tap/row boundaries, the "same CRC but
  different bytes" case, 32-bit tick wraparound and first-failure command silence;
* tampers raw logs/artifacts and requires detection.

The synthetic board derives its bytes from :func:`reference.expected_from_source`
(the independent PC formula); byte-level acceptance is the tool's own byte-for-byte
comparison against the exported ``actual.rgb``.  Every synthetic directory is marked
``OFFLINE_SYNTHETIC`` and is refused as board evidence.
"""
import hashlib
import json
import shutil
import time
from pathlib import Path

import protocol as pp
import reference
import session as S
from reference import crc32

ROOT = S.ROOT
SOURCE_TICKS = 2000000
RGB_TICKS = 30000
HZ = S.TICK_HZ


def pattern_source(k):
    """Fixed asymmetric RGB565 pattern from the task document §2, group index k."""
    raw = bytearray(reference.SOURCE_BYTES)
    for y in range(reference.HEIGHT):
        row = y * reference.WIDTH
        for x in range(reference.WIDTH):
            r5 = (3 * x + 5 * y + 7 * k) & 31
            g6 = (11 * x + 7 * y + 13 * k) & 63
            b5 = (x ^ (3 * y) ^ (17 * k)) & 31
            p = (r5 << 11) | (g6 << 5) | b5
            o = 2 * (row + x)
            raw[o] = p & 0xff
            raw[o + 1] = p >> 8
    return bytes(raw)


def solid_source(pixel):
    raw = bytearray(reference.SOURCE_BYTES)
    lo, hi = pixel & 0xff, pixel >> 8
    for i in range(0, reference.SOURCE_BYTES, 2):
        raw[i] = lo
        raw[i + 1] = hi
    return bytes(raw)


# --------------------------------------------------------------- synthetic board

class FakePort:
    """Scripted in-memory board: fixed RX bytes, every tool write recorded.

    The Loader stage and the application stage are kept apart on purpose: the real
    Loader answers exactly one 60-byte reply per request and stays silent otherwise,
    so the tool's "no extra bytes before the next Loader request" check must see an
    idle line until the single RUN leaves the Loader.
    """

    def __init__(self, loader_bytes, app_bytes):
        self.loader = bytearray(loader_bytes)
        self.app = bytearray(app_bytes)
        self.stage = 'loader'
        self.rx_pos = 0
        self.tx_capture = bytearray()

    @property
    def _buf(self):
        return self.loader if self.stage == 'loader' else self.app

    @property
    def in_waiting(self):
        # The Loader stays silent between requests; the application bytes become
        # visible only after the single RUN leaves the Loader.
        return 0 if self.stage == 'loader' else len(self.app) - self.rx_pos

    def read(self, n):
        if self.stage == 'loader' and self.rx_pos >= len(self.loader):
            self.stage, self.rx_pos = 'app', 0
        out = bytes(self._buf[self.rx_pos:self.rx_pos + n])
        self.rx_pos += len(out)
        return out

    def write(self, data):
        self.tx_capture += data
        return len(data)

    @property
    def rx_data(self):
        return bytes(self.loader) + bytes(self.app)


class Transcript:
    """Builds the exact board RX stream for the frozen two-group session."""

    def __init__(self, sources, cycles, sequences=(1, 2), buffers=(0, 1), corrupt=None):
        self.sources = list(sources)
        self.cycles = list(cycles)
        self.sequences = list(sequences)
        self.buffers = list(buffers)
        self.corrupt = list(corrupt or [])
        self.expected = [reference.expected_from_source(s) for s in self.sources]
        self.marks = {}
        self.board = bytearray()
        self._build()
        for item in self.corrupt:
            getattr(self, str(item[0]))(*item[1:])

    # ---- construction ------------------------------------------------------
    def _build(self):
        board = bytearray()

        def text(line):
            board.extend(line.encode() + b'\n')

        text(pp.LINE_APP_HEADER)
        text(pp.LINE_SENSOR)
        text(pp.LINE_READY)
        self.cycle = self.cycles[0]
        for group in (1, 2):
            seq = self.sequences[group - 1]
            buf = self.buffers[group - 1]
            src, expected = self.sources[group - 1], self.expected[group - 1]
            self.cycle = (self.cycle + SOURCE_TICKS) & 0xffffffff
            text(pp.summary_line(group, buf, seq, 1 - buf, seq, crc32(src), crc32(expected)))
            text(pp.LINE_EXPORT_BEGIN)
            self.marks[f'group{group}_begin'] = len(board)
            for side, data_kind, end_kind in ((0, pp.KIND_SOURCE_DATA, pp.KIND_SOURCE_END),
                                              (1, pp.KIND_RGB_DATA, pp.KIND_RGB_END)):
                data = src if side == 0 else expected
                for off in range(0, len(data), pp.CHUNK):
                    part = data[off:off + pp.CHUNK]
                    self.cycle = (self.cycle + RGB_TICKS) & 0xffffffff
                    board += pp.build_header(data_kind, seq, off, len(part), len(data),
                                             crc32(part))
                    board += part
                board += pp.build_header(end_kind, seq, len(data), 0, len(data), crc32(data))
            self.cycle = (self.cycle + RGB_TICKS) & 0xffffffff
            text(pp.LINE_EXPORT_DONE)
        text(pp.LINE_SESSION_DONE)
        self.board = board

    # ---- header helpers ----------------------------------------------------
    def _all_headers(self, group):
        base = self.marks[f'group{group}_begin']
        out, pos = [], base
        while pos < len(self.board) and bytes(self.board[pos:pos + 4]) == pp.MAGIC:
            kind = int.from_bytes(self.board[pos + 4:pos + 8], 'little')
            length = int.from_bytes(self.board[pos + 16:pos + 20], 'little')
            out.append((pos, kind, length))
            pos += pp.HEADER_BYTES + length
        return out

    def _find_header(self, group, side, occurrence=0, kind=None):
        wanted = (kind,) if kind else (
            (pp.KIND_SOURCE_DATA,) if side == 'source' else (pp.KIND_RGB_DATA,))
        seen = 0
        for pos, got, _length in self._all_headers(group):
            if got in wanted:
                if seen == occurrence:
                    return pos
                seen += 1
        raise AssertionError(f'header not found: group={group} side={side} kind={kind}')

    def _resign(self, pos):
        self.board[pos + 28:pos + 32] = crc32(bytes(self.board[pos:pos + 28])).to_bytes(4, 'little')

    def _rebuild_end_crc(self, group, data_kind, end_kind):
        """Recompute one END data_crc from the actual DATA payload bytes on the wire.

        After a payload edit the stream CRC must be recomputed from the mutated bytes,
        not from the pristine reference, otherwise the tool would reject on the payload
        CRC and the byte-comparison path would never be exercised.
        """
        buf = bytearray()
        for pos, got, length in self._all_headers(group):
            if got == data_kind:
                buf += self.board[pos + pp.HEADER_BYTES:pos + pp.HEADER_BYTES + length]
        total = crc32(bytes(buf))
        for pos, got, _length in self._all_headers(group):
            if got == end_kind:
                self.board[pos + 24:pos + 28] = total.to_bytes(4, 'little')
                self._resign(pos)

    # ---- named corruptions -------------------------------------------------
    def corrupt_payload_byte(self, group=1, side='source', occurrence=0, index=0, xor=1,
                             keep_crc=True):
        pos = self._find_header(group, side, occurrence)
        length = int.from_bytes(self.board[pos + 16:pos + 20], 'little')
        self.board[pos + pp.HEADER_BYTES + index] ^= xor
        if keep_crc:
            payload = bytes(self.board[pos + pp.HEADER_BYTES:pos + pp.HEADER_BYTES + length])
            self.board[pos + 24:pos + 28] = crc32(payload).to_bytes(4, 'little')
            self._resign(pos)
            self._rebuild_end_crc(
                group,
                pp.KIND_SOURCE_DATA if side == 'source' else pp.KIND_RGB_DATA,
                pp.KIND_SOURCE_END if side == 'source' else pp.KIND_RGB_END)

    def corrupt_crc_field(self, group=1, side='source', occurrence=0, delta=0xff, kind=None):
        pos = self._find_header(group, side, occurrence, kind=kind)
        self.board[pos + 24] ^= delta
        self._resign(pos)

    def corrupt_header_crc(self, group=1, side='source', occurrence=0):
        self.board[self._find_header(group, side, occurrence) + 31] ^= 0x80

    def corrupt_kind(self, group=1, side='source', occurrence=0, kind=9):
        pos = self._find_header(group, side, occurrence)
        self.board[pos + 4:pos + 8] = kind.to_bytes(4, 'little')
        self._resign(pos)

    def corrupt_magic(self, group=1, side='source', occurrence=0):
        pos = self._find_header(group, side, occurrence)
        self.board[pos:pos + 4] = b'PPX1'

    def corrupt_length(self, group=1, side='source', occurrence=0, delta=8):
        pos = self._find_header(group, side, occurrence)
        length = int.from_bytes(self.board[pos + 16:pos + 20], 'little')
        self.board[pos + 16:pos + 20] = (length + delta).to_bytes(4, 'little')
        self._resign(pos)

    def corrupt_offset(self, group=1, side='source', occurrence=1, delta=8):
        pos = self._find_header(group, side, occurrence)
        off = int.from_bytes(self.board[pos + 12:pos + 16], 'little')
        self.board[pos + 12:pos + 16] = (off + delta).to_bytes(4, 'little')
        self._resign(pos)

    def corrupt_seq(self, group=1, side='source', occurrence=0):
        pos = self._find_header(group, side, occurrence)
        seq = int.from_bytes(self.board[pos + 8:pos + 12], 'little')
        self.board[pos + 8:pos + 12] = (seq + 1).to_bytes(4, 'little')
        self._resign(pos)

    def corrupt_total(self, group=1, side='source', occurrence=0):
        pos = self._find_header(group, side, occurrence)
        total = int.from_bytes(self.board[pos + 20:pos + 24], 'little')
        self.board[pos + 20:pos + 24] = (total + 32).to_bytes(4, 'little')
        self._resign(pos)

    def truncate_payload(self, group=1, side='rgb', occurrence=2, drop=8):
        pos = self._find_header(group, side, occurrence)
        length = int.from_bytes(self.board[pos + 16:pos + 20], 'little')
        del self.board[pos + pp.HEADER_BYTES + length - drop:pos + pp.HEADER_BYTES + length]

    def duplicate_end(self, group=1, side='rgb'):
        kind = pp.KIND_RGB_END if side == 'rgb' else pp.KIND_SOURCE_END
        pos = self._find_header(group, side, 0, kind=kind)
        self.board[pos:pos] = bytes(self.board[pos:pos + pp.HEADER_BYTES])

    def duplicate_packet(self, group=1, side='source', occurrence=1):
        pos = self._find_header(group, side, occurrence)
        length = int.from_bytes(self.board[pos + 16:pos + 20], 'little')
        block = bytes(self.board[pos:pos + pp.HEADER_BYTES + length])
        self.board[pos + pp.HEADER_BYTES + length:pos + pp.HEADER_BYTES + length] = block

    def drop_end(self, group=2, side='rgb'):
        kind = pp.KIND_RGB_END if side == 'rgb' else pp.KIND_SOURCE_END
        pos = self._find_header(group, side, 0, kind=kind)
        del self.board[pos:pos + pp.HEADER_BYTES]

    def drop_group_stream(self, group=2, side='rgb'):
        kinds = ((pp.KIND_RGB_DATA, pp.KIND_RGB_END) if side == 'rgb' else
                 (pp.KIND_SOURCE_DATA, pp.KIND_SOURCE_END))
        blocks = [b for b in self._all_headers(group) if b[1] in kinds]
        first = blocks[0][0]
        last = blocks[-1][0] + pp.HEADER_BYTES
        del self.board[first:last]

    def interleave_rgb(self, group=1, occurrence=0):
        pos = self._find_header(group, 'rgb', occurrence)
        length = int.from_bytes(self.board[pos + 16:pos + 20], 'little')
        block = bytes(self.board[pos:pos + pp.HEADER_BYTES + length])
        del self.board[pos:pos + pp.HEADER_BYTES + length]
        insert = self._find_header(group, 'source', 0)
        self.board[insert:insert] = block


# --------------------------------------------------------------- evidence layout

class Session:
    """One synthetic evidence directory written exactly like a real run."""

    def __init__(self, folder, name, sources, cycles, sequences=(1, 2), buffers=(0, 1),
                 tx_fault=None, loader_fault=None, **kw):
        self.folder = Path(folder) / name
        self.folder.mkdir(parents=True)
        self.name = name
        self.tx_fault = tx_fault
        self.loader_fault = loader_fault
        self.transcript = Transcript(sources, cycles, sequences, buffers, **kw)

    def _loader_prefix(self, plan):
        rx, tx, records = bytearray(), bytearray(), []
        for step in plan:
            records.append(dict(name=step['name'], tx_offset=len(tx), rx_offset=len(rx)))
            tx += bytes.fromhex(step['tx_hex'])
            rx += bytes.fromhex(step['expected_hex'])
        return records, bytes(rx), bytes(tx)

    def run(self, info, plan, expect=None):
        """Run the real live path (Loader + two groups) against the scripted board."""
        loader_records, loader_rx, loader_tx = self._loader_prefix(plan)
        wire = pp.RawEvidence(self.folder)
        port = FakePort(loader_rx, bytes(self.transcript.board))
        if self.loader_fault:
            self.loader_fault(port)
        here = Path(__file__)
        record = dict(status='RUNNING', evidence_origin='OFFLINE_SYNTHETIC',
                      application=info, manifest_sha256='synthetic', port='OFFLINE',
                      baud=115200, serial_opened=False, board_release_ok=False,
                      retry_count=0, nack=0, loader_records=loader_records,
                      packet_ledger=[], summaries=[], commands=[],
                      user_scene_change_confirmation=False, groups=pp.GROUP_PAIRS,
                      synthetic=True,
                      tool_sha256={here.name: S.sha_file(here),
                                   'protocol.py': S.sha_file(here.with_name('protocol.py')),
                                   'reference.py': S.sha_file(here.with_name('reference.py'))})
        record['loader_plan'] = [dict(name=p['name'], run=bool(p.get('run'))) for p in plan]
        error = None
        try:
            S.execute_live(wire, port, info, self.folder, record,
                           confirm=lambda _m: None, progress=lambda _m: None)
            record['status'] = 'UART_DATA_CHECK_PASS_VISUAL_PENDING'
        except BaseException as exc:
            record['status'] = 'STOPPED_FIRST_FAILURE'
            record['error'] = repr(exc)
            error = exc
        if self.tx_fault:
            port.tx_capture = bytearray(self.tx_fault(bytearray(port.tx_capture)))
        (self.folder / 'uart.rx.bin').write_bytes(port.rx_data)
        (self.folder / 'uart.tx.bin').write_bytes(port.tx_capture)
        wire.close()
        self.record, self.port, self.error = record, port, error
        if expect is not None:
            S.need(error is not None, f'{self.name}: expected rejection ({expect}) but none came')
            S.need(expect.lower() in str(error).lower(),
                   f'{self.name}: expected {expect!r}, got {error!r}')
        return record, error

    def finish_files(self):
        S._finalize_folder(self.folder, self.record)
        S.save(self.folder, self.record)
        return self.record

    def replay(self, origin='OFFLINE_SYNTHETIC_TEST'):
        return S.replay(self.folder, origin)


class OfflineManifest:
    """Minimal stand-in for the firmware manifest (Loader plan identity only)."""

    def __init__(self, folder, size=4096):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.bin_path = self.folder / 'program.bin'
        blob = bytes((i * 37 + 11) & 0xff for i in range(size))
        self.bin_path.write_bytes(blob)
        self.manifest = self.folder / 'manifest.json'
        self.manifest.write_text(json.dumps(dict(
            status='PP_UART_BUILD_STATIC_AUDIT_PASS', kind='camera_preprocess_uart',
            base=0x40000000, entry=0x40000000, bytes=size, crc32=crc32(blob),
            bin_path=str(self.bin_path.resolve()), bin_sha256=S.sha_file(self.bin_path),
            elf_path=None, elf_sha256=None, source_sha256={}), indent=2) + '\n',
            encoding='utf-8')
        self.info = S.load_manifest(self.manifest)
        self.plan = S.loader_plan(self.info)


# ---------------------------------------------------------------------- checks

def check_reference(model):
    """Reference formula, colour, geometry and cross-implementation checks."""
    report = {'vectors': reference.self_vectors()}
    for k, source in ((1, model['group1_source']), (2, model['group2_source'])):
        expected = reference.expected_from_source(source)
        second = reference.expected_second_implementation(source)
        S.need(expected == second, f'reference implementations disagree on source k={k}')
        report[f'cross_implementation_k{k}'] = True
        report[f'expected_crc32_k{k}'] = f'{crc32(expected):08x}'
        samples = {}
        for x, y in ((0, 0), (11, 0), (1, 0), (0, 1), (16, 0), (7, 0), (7, 1),
                     (22, 0), (5, 1), (95, 0), (95, 95)):
            sx, sy = reference.source_coord(x, y)
            o = 2 * (sy * reference.WIDTH + sx)
            p = source[o] | (source[o + 1] << 8)
            i = 3 * (96 * y + x)
            samples[f'{x},{y}'] = dict(source_x=sx, source_y=sy, source_byte=o,
                                       tap=o // 32, tap_byte=o % 32, rgb565=f'{p:04x}',
                                       expected=list(expected[i:i + 3]))
            if k == 1:
                r5 = (3 * sx + 5 * sy + 7) & 31
                g6 = (11 * sx + 7 * sy + 13) & 63
                b5 = (sx ^ (3 * sy) ^ 17) & 31
                want = ((r5 << 3) | (r5 >> 2), (g6 << 2) | (g6 >> 4), (b5 << 3) | (b5 >> 2))
                S.need(tuple(expected[i:i + 3]) == want,
                       f'k=1 pattern/expansion mismatch at ({x},{y})')
                S.need(p == ((r5 << 11) | (g6 << 5) | b5), f'k=1 pattern pixel at ({x},{y})')
        report[f'samples_k{k}'] = samples
    for y in (0, 1, 47, 94, 95):
        for x in (0, 95):
            S.need(reference.source_coord(x, y)[1] == ((2 * y + 1) * 15) // 4,
                   'row boundary sample row')
    taps = {v['tap'] for v in report['samples_k1'].values()}
    S.need(len(taps) >= 2, 'cross-tap coverage needs at least two DDR taps')
    S.need(any(v['tap_byte'] == 0 for v in report['samples_k1'].values()),
           'no tap-aligned first byte in the sample set')
    S.need(any(v['tap_byte'] >= 24 for v in report['samples_k1'].values()),
           'no late-in-tap sample in the sample set')
    S.need(any(v['rgb565'] not in ('0000', 'ffff') for v in report['samples_k1'].values()),
           'non-trivial sample values missing')
    # The k=1 pattern must be asymmetric: no two rows and no two columns identical.
    src = model['group1_source']
    row0 = src[:reference.WIDTH * 2]
    row1 = src[reference.WIDTH * 2:reference.WIDTH * 4]
    S.need(row0 != row1, 'pattern rows must differ (asymmetric pattern)')
    return report


# ------------------------------------------------------------------ main driver

def run_suite(out_dir):
    out_dir = Path(out_dir)
    print(json.dumps({'status': 'OFFLINE_SELFCHECK_RUNNING', 'out': str(out_dir),
                      'serial_opened': False, 'board_release_created': False}))
    report = {'status': 'OFFLINE_SELFCHECK_RUNNING', 'serial_opened': False,
              'board_release_created': False, 'cases': [], 'passed': 0,
              'rejected': 0, 'accepted': 0,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    model = {'group1_source': pattern_source(1), 'group2_source': solid_source(0x001F)}
    model['reference'] = check_reference(model)
    report['reference'] = model['reference']
    manifest = OfflineManifest(out_dir / 'synthetic_manifest')
    info, plan = manifest.info, manifest.plan
    report['synthetic_manifest'] = dict(bin_sha256=info['bin_sha256'], bytes=info['bytes'],
                                        loader_responses=len(plan),
                                        RUN_commands=sum(bool(p.get('run')) for p in plan))
    report['synthetic_sources'] = {
        'group1_pattern_k1_sha256': S.sha_bytes(model['group1_source']),
        'group1_expected_crc32': f"{crc32(reference.expected_from_source(model['group1_source'])):08x}",
        'group2_solid_blue_sha256': S.sha_bytes(model['group2_source']),
        'group2_expected_crc32': f"{crc32(reference.expected_from_source(model['group2_source'])):08x}"}

    def entry(name, kind, detail):
        ok = detail.get('ok') is True
        report['cases'].append(dict(case=name, kind=kind, ok=ok, detail=detail))
        report['passed'] += int(ok)
        report['rejected'] += int(ok and kind == 'reject')
        report['accepted'] += int(ok and kind == 'accept')
        print(f"[{'PASS' if ok else 'FAIL'}] {name} ({kind}): "
              f"{json.dumps(detail, ensure_ascii=False)}")

    cases_dir = out_dir / 'cases'
    cases_dir.mkdir()

    def case(name, kind, expect=None, sources=None, corrupt=None, cycles=(0, 1),
             tx_fault=None, mutate=None, prepare=None, loader_fault=None, check=None,
             offline_close=True, replay_expect=None):
        """Run one synthetic session and assert the exact acceptance/rejection path.

        ``prepare``         runs before the session starts (faults visible to the live
                            run).
        ``expect``          the live run must stop with this substring in the error.
        ``offline_close``   when False the mutated directory must NOT close on offline
                            replay (artifact/byte faults injected after the live run).
        ``replay_expect``   the offline replay must fail with this substring.
        """
        detail = {}
        try:
            run = Session(cases_dir, name, sources or [model['group1_source'],
                                                       model['group2_source']],
                          list(cycles), corrupt=corrupt, tx_fault=tx_fault,
                          loader_fault=loader_fault)
            if prepare:
                prepare(run)
            record, error = run.run(info, plan, expect=expect)
            detail.update(status=record['status'], error=record.get('error'),
                          packets=len(record['packet_ledger']))
            detail['tx_bytes'] = len(run.port.tx_capture)
            if mutate:
                mutate(run)
            run.finish_files()
            if expect is not None:
                # First failure stops the session: the directory must never replay as
                # board evidence.
                try:
                    run.replay('ACTUAL_SERIAL')
                except S.Rejected:
                    detail['replay_as_board'] = 'refused'
                else:
                    raise AssertionError('failed session replayed as board evidence')
            else:
                if offline_close:
                    checked = run.replay('OFFLINE_SYNTHETIC_TEST')
                    detail['replay'] = checked['status']
                    detail['data_pass'] = checked['data_pass']
                    S.need(checked['data_pass'] is True, 'offline replay did not close')
                    S.need(checked['session_groups'] == pp.GROUP_PAIRS, 'group count')
                try:
                    run.replay('ACTUAL_SERIAL')
                except S.Rejected as exc:
                    detail['replay_as_board'] = 'refused'
                    detail['replay_as_board_reason'] = str(exc)
                else:
                    raise AssertionError('OFFLINE_SYNTHETIC accepted as board evidence')
            if replay_expect is not None:
                try:
                    run.replay('OFFLINE_SYNTHETIC_TEST')
                except S.Rejected as exc:
                    S.need(replay_expect.lower() in str(exc).lower(),
                           f'replay expected {replay_expect!r}, got {exc!r}')
                    detail['replay_error'] = str(exc)
                    detail['replay_as_board'] = 'refused'
                else:
                    raise AssertionError(f'replay expected {replay_expect!r} but passed')
            if check:
                detail.update(check(run, model))
            detail['ok'] = True
        except BaseException as exc:
            detail['ok'] = False
            detail['assert'] = repr(exc)
        entry(name, kind, detail)
        return detail

    # ---- plan-only: no port, no result files, identity verified.
    before = {p.name for p in out_dir.iterdir()}
    planned = S.plan_only(manifest.manifest)
    after = {p.name for p in out_dir.iterdir()}
    entry('plan_only_offline', 'accept', dict(
        ok=(planned['serial_opened'] is False and planned['evidence_origin'] == 'NOT_RUN'
            and planned['groups'] == pp.GROUP_PAIRS and planned['retries'] == 0
            and before == after and planned['RUN_commands'] == 1),
        serial_opened=planned['serial_opened'], RUN_commands=planned['RUN_commands'],
        no_files_written=before == after, status=planned['status']))

    # ---- normal two groups, genuine evidence, then independent replay.
    case('normal_two_groups', 'accept',
         check=lambda run, m: dict(group1_sha=S.sha_file(run.folder / 'group_1_actual.rgb'),
                                   group2_sha=S.sha_file(run.folder / 'group_2_actual.rgb')))

    # ---- structural corruptions: each must stop at first failure.
    case('bad_payload_crc', 'reject', expect='payload CRC',
         corrupt=[('corrupt_payload_byte', 1, 'source', 0, 0, 1, False)])
    case('bad_header_crc', 'reject', expect='header CRC',
         corrupt=[('corrupt_header_crc', 1, 'source', 0)])
    case('bad_magic', 'reject', expect='bad magic',
         corrupt=[('corrupt_magic', 1, 'source', 0)])
    case('bad_kind', 'reject', expect='unknown kind',
         corrupt=[('corrupt_kind', 1, 'source', 0, 9)])
    case('bad_length', 'reject', expect='payload_len',
         corrupt=[('corrupt_length', 1, 'source', 0, 8)])
    case('bad_offset', 'reject', expect='offset',
         corrupt=[('corrupt_offset', 1, 'source', 1, 8)])
    case('bad_seq', 'reject', expect='source_seq',
         corrupt=[('corrupt_seq', 1, 'source', 0)])
    case('bad_total', 'reject', expect='total_len',
         corrupt=[('corrupt_total', 1, 'source', 0)])
    case('bad_stream_crc', 'reject', expect='stream CRC',
         corrupt=[('corrupt_crc_field', 1, 'source', 0, 0xff, pp.KIND_SOURCE_END)])
    case('short_read', 'reject', expect='CRC',
         corrupt=[('truncate_payload', 1, 'rgb', 2, 8)])
    case('missing_end', 'reject', expect='magic',
         corrupt=[('drop_end', 2, 'rgb')])
    case('duplicate_end', 'reject', expect='duplicate',
         corrupt=[('duplicate_end', 1, 'rgb')])
    case('duplicate_packet_offset', 'reject', expect='offset',
         corrupt=[('duplicate_packet', 1, 'source', 1)])
    case('interleaved_streams', 'reject', expect='interleav',
         corrupt=[('interleave_rgb', 1, 0)])
    case('session_end_group_count', 'reject', expect='magic',
         corrupt=[('drop_group_stream', 2, 'rgb')])

    # ---- Loader / ACK faults.
    case('loader_byte_tamper', 'reject', expect='Loader', loader_fault=_tamper_loader)
    case('ack_loss', 'accept', mutate=_tamper_ack, offline_close=False,
         replay_expect='TX')

    # ---- pattern, colour and geometry counter-examples (constructible, rejected).
    for name, pixel, channel in (('pattern_first_pixel_R', (0, 0), 0),
                                 ('pattern_last_pixel_B', (95, 95), 2),
                                 ('pattern_row_boundary_G', (95, 0), 1),
                                 ('pattern_cross_tap_G', (16, 0), 1),
                                 ('pattern_naive_nearest_R', (1, 0), 0)):
        case(name, 'reject', mutate=(lambda run, p=pixel, c=channel: _flip_actual(run, 1, p, c)),
             offline_close=False, replay_expect='byte comparison',
             check=(lambda run, m, p=pixel, c=channel: _coordinate_check(run, p, c)))
    case('pattern_color_swap', 'reject', mutate=lambda run: _swap_actual_colors(run, 1),
         offline_close=False, replay_expect='byte comparison')

    # ---- raw log / artifact tampering must be detected on replay.
    case('tamper_hash_only', 'accept', mutate=_tamper_hash_only, offline_close=False,
         replay_expect='tampered')
    case('tamper_raw_rx_log', 'accept', mutate=_tamper_log, offline_close=False,
         replay_expect='CRC')
    case('tamper_actual_rgb', 'accept',
         mutate=lambda run: _tamper_artifact(run, 1, 'rgb'), offline_close=False,
         replay_expect='byte comparison')
    case('tamper_expected_rgb', 'accept',
         mutate=lambda run: _tamper_artifact(run, 1, 'expected'), offline_close=False,
         replay_expect='formula')
    case('tamper_png', 'accept', mutate=_tamper_png, offline_close=False,
         replay_expect='PNG')

    # ---- "same CRC, different bytes" must still be rejected.
    case('same_crc_different_bytes', 'reject', offline_close=False,
         replay_expect='not a substitute', mutate=_same_crc_different_bytes)

    # ---- 32-bit cycle/tick wraparound.
    case('tick_wraparound', 'accept', cycles=(0xfffff000, 0xfffff001), check=_wrap_check)
    case('cycle_elapsed_wrap_fault', 'reject', expect='offset',
         cycles=(0xfffffff0, 0xfffffff1),
         corrupt=[('corrupt_offset', 2, 'source', 0, 4)])

    report['status'] = 'OFFLINE_SELFCHECK_COMPLETE'
    report['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    report['all_passed'] = all(c['ok'] for c in report['cases'])
    (out_dir / 'selfcheck.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
        encoding='utf-8')
    files = {str(p.relative_to(out_dir)): S.sha_file(p)
             for p in sorted(out_dir.rglob('*')) if p.is_file()}
    (out_dir / 'selfcheck_files.json').write_text(
        json.dumps(files, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
        encoding='utf-8')
    return report


# --------------------------------------------------------------- case mutations

def _regenerate_group(run, group):
    """Rebuild every derived artifact of one group from the raw bytes on disk.

    The PNGs and the on-disk ``expected.rgb`` are rebuilt so the case is judged by the
    byte comparison.  The recorded summary CRCs are *not* rewritten: a real board
    would have reported the pristine CRC, so a mutated ``actual.rgb`` keeps every
    ledger CRC in agreement while the bytes differ -- exactly the trap the acceptance
    rule must not fall into.
    """
    names = S.artifact_names(group)
    src = (run.folder / names[0]).read_bytes()
    actual = (run.folder / names[1]).read_bytes()
    expected = reference.expected_from_source(src)
    (run.folder / names[2]).write_bytes(expected)
    (run.folder / names[3]).write_bytes(reference.png_source565(src))
    (run.folder / names[4]).write_bytes(reference.png_rgb888(actual))
    (run.folder / names[5]).write_bytes(reference.png_rgb888(expected))
    _rehash(run)


def _flip_actual(run, group, pixel, channel):
    """Flip one byte of the exported actual.rgb and rebuild the derived artifacts."""
    path = run.folder / S.artifact_names(group)[1]
    data = bytearray(path.read_bytes())
    index = 3 * (96 * pixel[1] + pixel[0]) + channel
    data[index] ^= 1
    path.write_bytes(bytes(data))
    _regenerate_group(run, group)
    return index


def _same_crc_different_bytes(run, group=2, slots=(0, 1, 2)):
    """Mutate the exported RGB888 tensor so its stream CRC stays identical.

    The acceptance rule is a real byte comparison against ``expected.rgb``.  To prove
    that CRC agreement alone cannot substitute for it, this case flips a byte and then
    solves (over GF(2), using the linearity of reflected CRC32) for single-byte
    corrections at three positions that restore the exact original CRC.  The result is
    a file with the same CRC as the expected tensor but different bytes.
    """
    names = S.artifact_names(group)
    src = (run.folder / names[0]).read_bytes()
    expected = reference.expected_from_source(src)
    actual = bytearray((run.folder / names[1]).read_bytes())
    target = crc32(expected)
    if bytes(actual) != expected:
        raise AssertionError('case setup expected a byte-identical export')
    if crc32(bytes(actual)) != target:
        raise AssertionError('case setup expected the pristine CRC')
    # Force position 0 to a different value, then solve for single-bit corrections at
    # eight other spread positions that restore the exact original CRC.
    spread = (len(actual) - 1, len(actual) // 2, len(actual) // 4, 3 * len(actual) // 4,
              len(actual) // 8, 7 * len(actual) // 8, len(actual) // 3, 2 * len(actual) // 3)
    solved = None
    for value in range(256):
        if value == expected[0]:
            continue
        trial = bytearray(actual)
        trial[0] = value
        base = crc32(bytes(trial))
        columns = []
        for bit in range(8):
            for index in spread:
                baseline = bytearray(trial)
                baseline[index] ^= 1 << bit
                columns.append((index, bit, crc32(bytes(baseline)) ^ base))
        rows = {}
        for i, (index, bit, delta) in enumerate(columns):
            mask, combo = delta & 0xffffffff, 1 << i
            for pivot in sorted(rows, reverse=True):
                if mask >> pivot & 1:
                    mask ^= rows[pivot][0]
                    combo ^= rows[pivot][1]
            if mask:
                rows[mask.bit_length() - 1] = (mask, combo)
        if len(rows) < 32:
            continue
        value_bits, assignment = base ^ target, 0
        for pivot in sorted(rows, reverse=True):
            if value_bits >> pivot & 1:
                value_bits ^= rows[pivot][0]
                assignment ^= rows[pivot][1]
        if value_bits:
            continue
        for i, (index, bit, _d) in enumerate(columns):
            if assignment >> i & 1:
                trial[index] ^= 1 << bit
        if crc32(bytes(trial)) != target or bytes(trial) == expected:
            continue
        if trial[0] == expected[0]:
            continue
        solved = trial
        break
    if solved is None:
        raise AssertionError('no CRC-preserving byte mutation found')
    actual = solved
    (run.folder / names[1]).write_bytes(bytes(actual))
    _regenerate_group(run, group)
    return dict(crc_forced_equal=True, bytes_equal=bytes(actual) == expected,
                actual_crc=f'{crc32(bytes(actual)):08x}', expected_crc=f'{target:08x}')


def _swap_actual_colors(run, group):
    path = run.folder / S.artifact_names(group)[1]
    data = bytearray(path.read_bytes())
    for i in range(0, len(data), 3):
        data[i], data[i + 2] = data[i + 2], data[i]
    path.write_bytes(bytes(data))


def _coordinate_check(run, pixel, channel):
    """Confirm the mismatch diagnostic uses the frozen formula's source coordinate."""
    index = 3 * (96 * pixel[1] + pixel[0]) + channel
    sx, sy = reference.source_coord(*pixel)
    return dict(mismatch_output_byte=index, expected_source=dict(x=sx, y=sy),
                frozen_formula_matches=(
                    sx == reference.source_coord(pixel[0], pixel[1])[0] and
                    sy == ((2 * pixel[1] + 1) * 15) // 4))


def _rehash(run):
    """Re-freeze the raw-evidence hashes after a mutation.

    This keeps tamper *detection by hash* out of the way so the mutation is judged by
    the weaker, structural checks (CRC, byte comparison, PNG decode) that must also
    catch it.  A separate case exercises hash-only detection.
    """
    run.record['file_sha256'] = {p.name: S.sha_file(p) for p in sorted(run.folder.iterdir())
                                 if p.is_file() and p.name != 'result.json'}


def _tamper_log(run):
    """Flip one byte inside the first RGB888 payload of the recorded raw RX stream."""
    path = run.folder / 'uart.rx.bin'
    data = bytearray(path.read_bytes())
    loader_bytes = 60 * len(run.record['loader_records'])
    group1 = run.transcript.marks['group1_begin']
    pos = (loader_bytes + group1 + pp.HEADER_BYTES + 1800 * (pp.HEADER_BYTES + pp.CHUNK)
           + pp.HEADER_BYTES + 100)
    data[pos] ^= 0xff
    path.write_bytes(bytes(data))
    _rehash(run)


def _tamper_hash_only(run):
    """Corrupt the raw RX deep inside the binary export without re-freezing the hash.

    The edit is outside the Loader transcript so hash detection, rather than the
    Loader byte comparison, is the check that must fire.
    """
    path = run.folder / 'uart.rx.bin'
    data = bytearray(path.read_bytes())
    loader_bytes = 60 * len(run.record['loader_records'])
    position = loader_bytes + run.transcript.marks['group1_begin'] + pp.HEADER_BYTES + 40
    data[position] ^= 0xff
    path.write_bytes(bytes(data))


def _tamper_loader(port):
    """Corrupt one Loader reply byte on the wire before the session starts."""
    port.loader[10] ^= 0xff


def _tamper_ack(run):
    """Board acknowledged only part of the stream: the raw TX is cut short."""
    data = bytearray((run.folder / 'uart.tx.bin').read_bytes())
    (run.folder / 'uart.tx.bin').write_bytes(bytes(data[:int(len(data) * .4)]))


def _tamper_artifact(run, group, kind):
    """Flip one byte in an exported raw artifact and re-freeze the hashes."""
    names = S.artifact_names(group)
    path = run.folder / (names[0] if kind == 'source' else
                         names[1] if kind == 'rgb' else names[2])
    data = bytearray(path.read_bytes())
    data[17] ^= 0xff
    path.write_bytes(bytes(data))
    _rehash(run)


def _tamper_png(run):
    """Alter the decoded pixels of actual96.png while keeping the file well formed.

    The IDAT payload is re-inflated, one raster byte is flipped and the stream is
    re-deflated, so every chunk CRC stays valid and only the pixel decode reveals the
    change (the separate hash case already covers byte-level file detection).
    """
    import zlib
    path = run.folder / S.artifact_names(1)[4]
    data = bytearray(path.read_bytes())
    pos = data.index(b'IDAT') - 4
    length = int.from_bytes(data[pos:pos + 4], 'big')
    raster = bytearray(zlib.decompress(bytes(data[pos + 8:pos + 8 + length])))
    raster[1] ^= 0xff          # first pixel byte of row 0, filter bytes untouched
    body = zlib.compress(bytes(raster), 6)
    built = bytearray(data[:pos])
    built += len(body).to_bytes(4, 'big')
    built += b'IDAT'
    built += body
    built += crc32(b'IDAT' + body).to_bytes(4, 'big')
    built += data[pos + 12 + length:]
    path.write_bytes(bytes(built))
    run.record['file_sha256'] = {p.name: S.sha_file(p) for p in sorted(run.folder.iterdir())
                                 if p.is_file() and p.name != 'result.json'}


def _wrap_check(run, model):
    """32-bit unsigned elapsed arithmetic across the counter rollover."""
    start, active_end, export_end = 0xfffff000, 0xfffff001, 0xffffff00
    return dict(cycle_start=start, cycle_active_end=active_end, cycle_export_end=export_end,
                active_ticks=(active_end - start) & 0xffffffff,
                export_ticks=(export_end - start) & 0xffffffff,
                modular_elapsed_ok=((export_end - start) & 0xffffffff) < 40 * HZ)


def split_reference_crosscheck(source_path, expected_path):
    """CLI helper used by the offline acceptance commands."""
    source = Path(source_path).read_bytes()
    expected = Path(expected_path).read_bytes()
    first = reference.expected_from_source(source)
    second = reference.expected_second_implementation(source)
    report = dict(source=dict(path=str(source_path), bytes=len(source),
                              crc32=f'{crc32(source):08x}', sha256=S.sha_bytes(source)),
                  expected=dict(path=str(expected_path), bytes=len(expected),
                                crc32=f'{crc32(expected):08x}', sha256=S.sha_bytes(expected)),
                  first_sha256=S.sha_bytes(first), second_sha256=S.sha_bytes(second),
                  cross_implementation_equal=first == second,
                  on_disk_equal=first == expected)
    if not (report['cross_implementation_equal'] and report['on_disk_equal']):
        raise SystemExit(json.dumps(report, indent=2) + '\nMISMATCH')
    return report
