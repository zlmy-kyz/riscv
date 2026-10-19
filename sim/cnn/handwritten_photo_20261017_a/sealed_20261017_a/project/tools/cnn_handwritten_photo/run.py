import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import time
import zlib

import reference


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/camera_uart'))
from capture import loader_plan
from protocol import Wire, exact, need

specification = importlib.util.spec_from_file_location('handwritten_source_reference', ROOT / 'tools/camera_preprocess_photo/reference.py')
ppref = importlib.util.module_from_spec(specification)
specification.loader.exec_module(ppref)
STAGE = ROOT / 'sim/cnn/handwritten_photo_20261017_a'
DEFAULT = ROOT / 'tests/cnn_handwritten_photo/build/handwritten_20261017_b/manifest.json'
MODEL = ROOT / 'sim/cnn/training/handwritten_run_20261017_a/model'
HEADER = 'CNN_HANDWRITTEN_APP=1 CONTRACT=digits10_int8_v1 HZ=93750000 TRAINED=1 SOURCE_EXPORT=OPTIONAL'
JOB = re.compile(r'CNN_JOB BUF=0 SEQ=1 MODEL=([0-9a-f]{8}) MODEL_CRC=([0-9a-f]{8}) PP_CRC=([0-9a-f]{8}) BYTES=27648 READS=864 GRAY=1024 STATUS=0000000a ERROR=00000000 CLASS=(\d+) CYCLES=(\d+) PP_CYCLES=(\d+)')
SOURCE = re.compile(r'SOURCE BUF=0 SEQ=1 WIDTH=1280 HEIGHT=720 BYTES=1843200 CRC=([0-9a-f]{8})')
RELEASED = re.compile(r'CNN_RELEASED CLAIMS=(\d+) DISCARDS=(\d+) GLOBAL_SEQ=(\d+) CAM_STATE=([0-9a-f]{8}) PP_STATUS=00000002 CNN_STATUS=0000000a')
PROMPT = '沿用已成功拍照的CAM2/J5位流，载板J10，两测试模式均0；仅加载新软件，无需重新PDS。关闭串口助手，白纸黑笔单个数字居中正向。按下并释放KEY0，等DDR就绪及画面稳定后Enter：'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def crc(payload):
    return zlib.crc32(payload) & 0xffffffff


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def preserve(folder, name, payload, write):
    path = folder / name
    if write:
        path.write_bytes(payload)
    else:
        need(path.read_bytes() == payload, 'artifact differs: ' + name)


def image(path=DEFAULT):
    manifest = read(path)
    need(manifest['status'] == 'CNN_HANDWRITTEN_BUILD_STATIC_AUDIT_PASS' and manifest['kind'] == 'cnn_handwritten_photo', 'wrong handwritten firmware')
    for kind in ('bin', 'elf'):
        need(sha(ROOT / manifest[kind + '_path']) == manifest[kind + '_sha256'], 'changed ' + kind)
    for name, expected in manifest['source_sha256'].items():
        need(sha(ROOT / name) == expected, 'changed firmware input ' + name)
    model = reference.load(MODEL)
    need(model['meta'] == manifest['trained_model'] and manifest['embedded_model_words_equal'], 'firmware model identity')
    return manifest, model


def hardware():
    expected = read(STAGE / 'hardware.json')
    need(expected['camera_connector'] == 'CAM2/J5' and expected['connector'] == 'J10', 'CAM2/J10 required')
    need(expected['camera_count'] == 1 and expected['DDR_frame_buffers'] == 2, 'single camera, two DDR buffers required')
    need(expected['parameters'] == dict(CAMERA_COLORBAR_ENABLE=0, CAMERA_DVP_TEST_ENABLE=0), 'real photo required')
    for name, expected_hash in {**expected['design_sha256'], **expected['constraint_sha256']}.items():
        need(sha(ROOT / name) == expected_hash, 'changed CAM2 design ' + name)
    return expected


def line(wire):
    payload = bytearray()
    deadline = time.monotonic() + 30
    while not payload.endswith(b'\n'):
        payload += exact(wire, 1, max(.001, deadline - time.monotonic()))
        need(len(payload) <= 2048, 'excess ASCII line')
    need(b'\r' not in payload, 'unexpected CR')
    return payload[:-1].decode('ascii')


def receive_stream(wire, folder, kind, total, expected_crc, packets, write, deadline):
    payload = bytearray()
    stream = (folder / ('rgb96.partial' if kind == 1 else 'source.partial')).open('xb') if write else None
    try:
        while True:
            remaining = deadline - time.monotonic()
            need(remaining > 0, 'export deadline')
            receive_offset = wire.rx_count
            header = exact(wire, 32, min(5, remaining))
            magic, actual_kind, sequence, offset, length, actual_total, checksum, header_crc = struct.unpack('<4s7I', header)
            need(magic == b'CN03' and crc(header[:28]) == header_crc, 'CN03 magic/header CRC')
            need(sequence == 1 and offset == len(payload) and actual_total == total, 'packet identity/order')
            if actual_kind == kind:
                need(length == min(1024, total - offset) and length > 0, 'packet DATA length')
                remaining = deadline - time.monotonic()
                need(remaining > 0, 'export deadline')
                part = exact(wire, length, min(5, remaining))
                need(crc(part) == checksum, 'packet payload CRC')
                payload += part
                if stream:
                    stream.write(part)
                    stream.flush()
            else:
                need(actual_kind == kind + 1 and len(payload) == total and length == 0 and checksum == crc(payload) == expected_crc, 'END/whole stream CRC')
            transmit_offset = wire.tx_count
            wire.write(b'K')
            packets.append(dict(rx_offset=receive_offset, tx_ack_offset=transmit_offset, header_hex=header.hex()))
            if actual_kind == kind + 1:
                return bytes(payload)
    finally:
        if stream:
            stream.close()


def artifacts(folder, rgb, job, scores, model, write, label):
    result = reference.infer(rgb, model)
    preserve(folder, 'rgb96.bin', rgb, write)
    preserve(folder, 'rgb96.png', ppref.png_rgb888(rgb), write)
    gray = bytes(value + 128 for value in result['layers']['gray32'])
    rows = [b''.join(bytes((value, value, value)) for value in gray[row * 32:(row + 1) * 32]) for row in range(32)]
    preserve(folder, 'gray32.png', ppref.png_rgb(32, 32, rows), write)
    if write:
        reference.save_trace(folder / 'integer_reference', result)
    else:
        for name, values in result['layers'].items():
            preserve(folder / 'integer_reference', name + '.bin', bytes(value & 255 for value in values), False)
        preserve(folder / 'integer_reference', 'scores.bin', struct.pack('<10i', *result['scores']), False)
    comparison = dict(all_10_scores_equal=scores == result['scores'], board_scores=scores,
                      expected_scores=result['scores'], board_class=job['prediction'], expected_class=result['prediction'],
                      argmax_equal=job['prediction'] == result['prediction'], label=label,
                      label_match=job['prediction'] == label, model_id=reference.MODEL_ID,
                      cnn_cycles=job['cycles'], cnn_ms=job['cycles'] / 93750,
                      scope='One labeled trial; score equality and recognition correctness are separate')
    if write:
        save(folder / 'comparison.json', comparison)
    else:
        need(read(folder / 'comparison.json') == comparison, 'comparison ledger differs')
    need(comparison['all_10_scores_equal'], 'SCORE MISMATCH')
    need(comparison['argmax_equal'], 'argmax mismatch')
    return comparison


def source_artifacts(folder, source, rgb, write):
    expected = ppref.expected_from_source(source)
    need(expected == ppref.expected_second_implementation(source), 'independent PP references differ')
    comparison = ppref.compare(expected, rgb, source)
    for name, payload in [('source.rgb565', source), ('source.png', ppref.png_source565(source)),
                          ('expected96.rgb', expected), ('expected96.png', ppref.png_rgb888(expected))]:
        preserve(folder, name, payload, write)
    if write:
        save(folder / 'preprocess_comparison.json', comparison)
    else:
        need(read(folder / 'preprocess_comparison.json') == comparison, 'PP comparison ledger differs')
    need(comparison['all_equal'], 'PP BYTE MISMATCH')
    return comparison


def exchange(wire, manifest, folder, model, full_source, label, write=True, progress=lambda value: None):
    session = dict(loader_records=[], packets=[], full_source_export=full_source)
    for plan in loader_plan(manifest):
        session['loader_records'].append(dict(name=plan['name'], tx_offset=wire.tx_count, rx_offset=wire.rx_count))
        wire.write(bytes.fromhex(plan['tx_hex']))
        need(exact(wire, 60) == bytes.fromhex(plan['expected_hex']), 'Loader ' + plan['name'])
    metadata = model['meta']
    model_banner = f"MODEL ID={metadata['model_id']:08x} WORDS=6222 CRC={metadata['load_crc32']:08x} STATUS=00000008"
    for expected in (HEADER, model_banner, 'SENSOR_ID=00005640 CONFIG=OK', 'CNN_READY'):
        actual = line(wire)
        need(actual == expected, 'firmware/model/config banner: ' + actual)
        progress(actual)
    wire.write(b'G')
    wire.write(b'C')
    raw = line(wire)
    match = JOB.fullmatch(raw)
    need(match is not None, 'job metadata/error: ' + raw)
    model_id, model_crc, pp_crc, prediction, cycles, pp_cycles = match.groups()
    need(model_id == reference.MODEL_ID and int(model_crc, 16) == reference.MODEL_CRC, 'job model identity')
    job = dict(model_id=model_id, model_crc=model_crc, pp_crc=pp_crc, prediction=int(prediction), cycles=int(cycles), pp_cycles=int(pp_cycles))
    need(0 <= job['prediction'] < 10 and 0 < job['cycles'] < 3 * 93750000 and 0 < job['pp_cycles'] < 3 * 93750000, 'class/cycles')
    scores_line = line(wire)
    need(re.fullmatch(r'SCORES(?: -?\d+){10}', scores_line) is not None, 'ten scores required')
    scores = list(map(int, scores_line.split()[1:]))
    need(all(-2**31 <= score < 2**31 for score in scores), 'signed score range')
    need(max(range(10), key=lambda class_index: scores[class_index]) == job['prediction'], 'board class/score mismatch')
    source_line = line(wire)
    source_match = SOURCE.fullmatch(source_line)
    need(source_match is not None, 'source identity metadata/error: ' + source_line)
    session.update(job=job, job_line=raw, scores=scores, source_line=source_line)
    progress(raw)
    progress(scores_line)
    wire.write(b'D' if full_source else b'd')
    need(line(wire) == 'CNN_EXPORT_BEGIN', 'export begin')
    deadline = time.monotonic() + (600 if full_source else 60)
    rgb = receive_stream(wire, folder, 1, 27648, int(pp_crc, 16), session['packets'], write, deadline)
    if full_source:
        source = receive_stream(wire, folder, 3, 1843200, int(source_match[1], 16), session['packets'], write, deadline)
        session['preprocess_comparison'] = source_artifacts(folder, source, rgb, write)
    else:
        session['preprocess_comparison'] = dict(status='NOT_RUN_RGB96_ONLY', source_cpu_pc_crc_verified=False, source_to_PP_all_bytes_verified=False)
    need(line(wire) == 'CNN_EXPORT_DONE', 'export done/error')
    release = line(wire)
    match = RELEASED.fullmatch(release)
    need(match is not None, 'release/error: ' + release)
    claims, discards, sequence, state = match.groups()
    need(int(claims) == int(sequence) == 1 + int(discards) and int(discards) in (0, 1) and int(state, 16) & 0x2cf == 0, 'ownership ledger not closed')
    session['release'] = release
    session['comparison'] = artifacts(folder, rgb, job, scores, model, write, label)
    wire.write(b'Q')
    finish = line(wire)
    need(finish == f'CNN_HANDWRITTEN_DONE JOBS=1 CPU_CONTROL=PASS MODEL={model_id}', 'finish/error: ' + finish)
    session['finish'] = finish
    progress(f"DIGIT={job['prediction']} LABEL={label} LABEL_MATCH={int(job['prediction'] == label)} ALL_10_SCORES=MATCH")
    return session


class Replay:
    def __init__(self, receive, transmit):
        self.rx = receive
        self.tx = transmit
        self.rx_count = self.tx_count = 0

    def read(self, count):
        need(self.rx_count < len(self.rx), 'short raw RX')
        result = self.rx[self.rx_count:self.rx_count + count]
        self.rx_count += len(result)
        return result

    def write(self, payload):
        need(self.tx[self.tx_count:self.tx_count + len(payload)] == payload, 'raw TX mismatch/retry')
        self.tx_count += len(payload)
        return len(payload)


def verify(folder, origin='ACTUAL_SERIAL'):
    folder = Path(folder)
    result = read(folder / 'result.json')
    need(origin in ('ACTUAL_SERIAL', 'OFFLINE_SYNTHETIC_TEST') and result['evidence_origin'] == origin, 'synthetic evidence is not actual serial')
    need(result['status'] == 'HANDWRITTEN_CAPTURE_DATA_VERIFIED', 'capture did not finish')
    if origin == 'ACTUAL_SERIAL':
        need(result['serial_opened'] and result['operator_CAM2_KEY0_confirmation'], 'actual prerequisites')
    for name, expected in result['file_sha256'].items():
        need(sha(folder / name) == expected, 'changed evidence ' + name)
    manifest = read(folder / 'manifest.json')
    need(manifest['status'] == 'CNN_HANDWRITTEN_BUILD_STATIC_AUDIT_PASS' and manifest['kind'] == 'cnn_handwritten_photo', 'wrong archived firmware')
    need(manifest == result['application'] and sha(folder / 'manifest.json') == result['manifest_sha256'], 'firmware manifest identity')
    need(sha(folder / 'application.bin') == manifest['bin_sha256'], 'firmware bytes')
    model = reference.load(folder / 'model')
    need(model['meta'] == manifest['trained_model'], 'trained model identity')
    model_offset = manifest['symbols']['model_words'] - manifest['base']
    need((folder / 'application.bin').read_bytes()[model_offset:model_offset + 24888] == (folder / 'model/load_words.bin').read_bytes(), 'embedded model words differ')
    sample = read(folder / 'sample.json')
    need(sample == result['sample'] and sample['purpose'] == 'EXPLORATORY_HANDWRITTEN_TRIAL', 'sample identity')
    need(type(sample['label']) is int and 0 <= sample['label'] < 10, 'sample label')
    expected_hardware = read(folder / 'hardware.json')
    need(expected_hardware['camera_connector'] == 'CAM2/J5' and expected_hardware['connector'] == 'J10' and expected_hardware['camera_count'] == 1 and expected_hardware['DDR_frame_buffers'] == 2, 'CAM2/J10 identity')
    need(expected_hardware['parameters'] == dict(CAMERA_COLORBAR_ENABLE=0, CAMERA_DVP_TEST_ENABLE=0), 'real photo identity')
    replay = Replay((folder / 'uart.rx.bin').read_bytes(), (folder / 'uart.tx.bin').read_bytes())
    session = exchange(replay, manifest, folder, model, result['full_source_export'], sample['label'], False)
    need(session == result['session'] and replay.rx_count == len(replay.rx) and replay.tx_count == len(replay.tx), 'raw/session mismatch or extra bytes')
    return dict(status='HANDWRITTEN_ONE_SAMPLE_RAW_SCORES_VERIFIED', evidence_origin=origin,
                model_id=reference.MODEL_ID, label=sample['label'], prediction=session['job']['prediction'],
                label_match=session['comparison']['label_match'], cnn_ms=session['comparison']['cnn_ms'],
                full_source_export=result['full_source_export'], formal_camera_accuracy_verified=False,
                hardware_layer_dump_verified=False, retry_count=0)


def live(args, manifest, model, expected_hardware):
    need(args.log_dir is not None and not args.log_dir.exists(), 'new --log-dir required')
    need(args.label is not None and args.session is not None and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', args.session), '--label and valid --session required')
    need(args.sample >= 1, 'sample number must be positive')
    ready = read(STAGE / 'ready.json')
    need(ready['status'] == 'HANDWRITTEN_SOFTWARE_READY_FOR_USER_TRIAL_NOT_BOARD_PASS' and ready['firmware_sha256'] == manifest['bin_sha256'], 'software preparation not sealed')
    for name, expected in ready['input_sha256'].items():
        need(sha(ROOT / name) == expected, 'changed sealed input ' + name)
    folder = args.log_dir.resolve()
    folder.mkdir(parents=True, exist_ok=False)
    for source, name in [(DEFAULT, 'manifest.json'), (ROOT / manifest['bin_path'], 'application.bin'), (STAGE / 'hardware.json', 'hardware.json'), (STAGE / 'ready.json', 'ready.json')]:
        shutil.copyfile(source, folder / name)
    shutil.copytree(MODEL, folder / 'model')
    sample = dict(label=args.label, session=args.session, sample_number=args.sample,
                  purpose='EXPLORATORY_HANDWRITTEN_TRIAL', medium='white paper, black pen, centered upright single digit')
    save(folder / 'sample.json', sample)
    result = dict(status='RUNNING', evidence_origin='ACTUAL_SERIAL', serial_opened=False,
                  operator_CAM2_KEY0_confirmation=False, hardware_bitstream_independently_identified=False,
                  application=manifest, manifest_sha256=sha(DEFAULT), sample=sample, port=args.port,
                  full_source_export=args.full_source, retry_count=0, PDS_started=False, key_HDL='NOT_COMPLETED',
                  tool_sha256=sha(Path(__file__)))
    save(folder / 'result.json', result)
    wire = None
    try:
        print(f'MODEL={reference.MODEL_ID} LABEL={args.label} SESSION={args.session} FULL_SOURCE={int(args.full_source)}')
        input(PROMPT)
        result['operator_CAM2_KEY0_confirmation'] = True
        import serial
        with serial.Serial(args.port, 115200, timeout=.05, write_timeout=2, xonxoff=False, rtscts=False, dsrdtr=False) as port:
            result['serial_opened'] = True
            wire = Wire(port, folder)
            need(port.in_waiting == 0, 'unexpected initial bytes; no flush/retry')
            result['session'] = exchange(wire, manifest, folder, model, args.full_source, args.label, True, print)
            time.sleep(.05)
            need(port.in_waiting == 0, 'extra final serial bytes')
        wire.close()
        wire = None
        result['status'] = 'HANDWRITTEN_CAPTURE_DATA_VERIFIED'
    except BaseException as error:
        result.update(status='STOPPED_FIRST_FAILURE', error=repr(error))
        raise
    finally:
        if wire:
            wire.close()
        result['file_sha256'] = {path.relative_to(folder).as_posix(): sha(path) for path in folder.rglob('*') if path.is_file() and path.name not in ('result.json', 'verified.json')}
        save(folder / 'result.json', result)
    checked = verify(folder)
    save(folder / 'verified.json', checked)
    print(json.dumps(checked, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default='COM9')
    parser.add_argument('--log-dir', type=Path)
    parser.add_argument('--label', type=int, choices=range(10))
    parser.add_argument('--session')
    parser.add_argument('--sample', type=int, default=1)
    parser.add_argument('--full-source', action='store_true')
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(args.verify), ensure_ascii=False, indent=2))
        return
    manifest, model = image()
    expected_hardware = hardware()
    if args.plan_only:
        print(json.dumps(dict(status='HANDWRITTEN_PLAN_NO_SERIAL', model_id=reference.MODEL_ID,
                              firmware_sha256=manifest['bin_sha256'], full_source_export=args.full_source,
                              camera=expected_hardware['camera_connector'], serial_opened=False,
                              new_PDS_required=False, prompt=PROMPT), ensure_ascii=False, indent=2))
        return
    live(args, manifest, model, expected_hardware)


if __name__ == '__main__':
    main()
