import argparse
import builtins
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace
import zlib


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/cnn_handwritten_photo'))
import run as pc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=HERE / 'checks_01')
    args = parser.parse_args()
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status='RUNNING', origin='OFFLINE_SYNTHETIC_TEST', HDL=False,
                  real_CPU=False, serial_opened=False, tests=[])

    def command(name, argv):
        argv = list(map(str, argv))
        completed = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        (output / (name + '.log')).write_bytes(completed.stdout)
        pc.save(output / (name + '.command.json'), dict(argv=argv, returncode=completed.returncode))
        assert completed.returncode == 0, (name, completed.stdout.decode(errors='replace'))
        return completed.stdout

    def rejects(name, function, reason=None):
        try:
            function()
        except (ValueError, AssertionError) as error:
            if reason:
                assert reason in str(error), (name, str(error))
            report['tests'].append(dict(name=name, rejected=True, error=str(error)))
            return
        raise AssertionError('wrongly accepted ' + name)

    class Fragmented(pc.Replay):
        def read(self, count):
            return super().read(min(count, 73))

    try:
        manifest, model = pc.image()
        hardware = pc.hardware()
        source_path = ROOT / 'sim/cnn/board_photo_20261016_a/checks_01/input.rgb565'
        source = source_path.read_bytes()
        assert len(source) == 1843200
        rgb = pc.ppref.expected_from_source(source)
        assert rgb == pc.ppref.expected_second_implementation(source)
        (output / 'input.rgb565').write_bytes(source)
        (output / 'input.rgb').write_bytes(rgb)
        expected = pc.reference.infer(rgb, model)
        (output / 'scores.bin').write_bytes(struct.pack('<10i', *expected['scores']))
        changed = bytearray(rgb)
        changed[123] ^= 8
        changed = bytes(changed)
        (output / 'wrong.rgb').write_bytes(changed)
        (output / 'wrong_scores.bin').write_bytes(struct.pack('<10i', *pc.reference.infer(changed, model)['scores']))
        build = pc.DEFAULT.parent
        command('compile_native', ['D:/mingw64/bin/gcc.exe', '-O2', '-std=c11', '-Wall', '-Wextra', '-Werror',
                                  '-Wno-int-to-pointer-cast', '-I', build, ROOT / 'tests/cnn_handwritten_photo/native_flow.c',
                                  ROOT / 'tests/cnn_handwritten_photo/pp01_wire.c', '-o', output / 'flow.exe'])
        plans = pc.loader_plan(manifest)
        loader_receive = b''.join(bytes.fromhex(plan['expected_hex']) for plan in plans)
        loader_transmit = b''.join(bytes.fromhex(plan['tx_hex']) for plan in plans)
        flows = {}
        good = {}
        scenarios = [('fast', 'normal', False), ('full', 'normal', True), ('no_tail', 'no_tail', False),
                     ('wrong_label', 'normal', False), ('score', 'score', False), ('count', 'count', False),
                     ('release', 'release', False), ('timeout', 'timeout', False),
                     ('source_crc', 'source_crc', True), ('source_ack', 'source_ack', True),
                     ('pp_mismatch', 'normal', True)]
        for name, scenario, full_source in scenarios:
            folder = output / name
            folder.mkdir()
            prefix = folder / 'run'
            wrong_pp = name == 'pp_mismatch'
            response = command(name, [output / 'flow.exe', output / 'input.rgb565', output / ('wrong.rgb' if wrong_pp else 'input.rgb'),
                                      output / ('wrong_scores.bin' if wrong_pp else 'scores.bin'), pc.MODEL / 'load_words.bin',
                                      scenario, prefix, int(full_source)])
            ledger = json.loads(response)
            flows[name] = ledger
            assert ledger['camera_starts'] == ledger['pp_starts'] == ledger['cnn_starts'] == 1 or name == 'count'
            receive = loader_receive + Path(str(prefix) + '.fw.tx.bin').read_bytes()
            transmit = loader_transmit + Path(str(prefix) + '.fw.rx.bin').read_bytes()
            sample_folder = folder / 'pc'
            sample_folder.mkdir()
            label = (expected['prediction'] + 1) % 10 if name == 'wrong_label' else expected['prediction']
            replay = Fragmented(receive, transmit)
            if name in ('fast', 'full', 'no_tail', 'wrong_label'):
                session = pc.exchange(replay, manifest, sample_folder, model, full_source, label)
                assert replay.rx_count == len(receive) and replay.tx_count == len(transmit)
                assert len(session['packets']) == (1829 if full_source else 28)
                assert ledger['status'] == 2 and ledger['model_words'] == 6222 and ledger['model_crc'] == pc.reference.MODEL_CRC
                assert ledger['releases'] == (1 if name == 'no_tail' else 2)
                assert session['comparison']['label_match'] == (name != 'wrong_label')
                assert (sample_folder / 'source.rgb565').exists() == full_source
                shutil.copyfile(pc.DEFAULT, sample_folder / 'manifest.json')
                shutil.copyfile(ROOT / manifest['bin_path'], sample_folder / 'application.bin')
                shutil.copyfile(HERE / 'hardware.json', sample_folder / 'hardware.json')
                shutil.copytree(pc.MODEL, sample_folder / 'model')
                (sample_folder / 'uart.rx.bin').write_bytes(receive)
                (sample_folder / 'uart.tx.bin').write_bytes(transmit)
                sample = dict(label=label, session='synthetic', sample_number=1, purpose='EXPLORATORY_HANDWRITTEN_TRIAL')
                pc.save(sample_folder / 'sample.json', sample)
                result = dict(status='HANDWRITTEN_CAPTURE_DATA_VERIFIED', evidence_origin='OFFLINE_SYNTHETIC_TEST',
                              application=manifest, manifest_sha256=pc.sha(sample_folder / 'manifest.json'), sample=sample,
                              full_source_export=full_source, session=session)
                result['file_sha256'] = {path.relative_to(sample_folder).as_posix(): pc.sha(path) for path in sample_folder.rglob('*') if path.is_file()}
                pc.save(sample_folder / 'result.json', result)
                pc.save(sample_folder / 'verified.json', pc.verify(sample_folder, 'OFFLINE_SYNTHETIC_TEST'))
                rejects('synthetic_not_actual_' + name, lambda: pc.verify(sample_folder), 'synthetic')
                good[name] = (receive, transmit)
            else:
                reason = 'SCORE MISMATCH' if name == 'score' else 'PP BYTE MISMATCH' if wrong_pp else None
                rejects(name, lambda: pc.exchange(replay, manifest, sample_folder, model, full_source, label), reason)
        receive, transmit = good['fast']
        packet_offset = receive.index(b'CN03')
        wrong_magic = bytearray(receive)
        wrong_magic[packet_offset:packet_offset + 4] = b'CN02'
        struct.pack_into('<I', wrong_magic, packet_offset + 28, zlib.crc32(wrong_magic[packet_offset:packet_offset + 28]) & 0xffffffff)
        variants = dict(old_magic=bytes(wrong_magic), old_model=receive.replace(b'MODEL ID=4c8b5aca', b'MODEL ID=05a032af', 1),
                        corrupt_payload=receive[:packet_offset + 33] + bytes([receive[packet_offset + 33] ^ 1]) + receive[packet_offset + 34:],
                        truncated=receive[:packet_offset + 80])
        for name, altered in variants.items():
            folder = output / name
            folder.mkdir()
            rejects(name, lambda: pc.exchange(Fragmented(altered, transmit), manifest, folder, model, False, expected['prediction']))
        provisional = output / 'provisional_stage'
        provisional.mkdir()
        pc.save(provisional / 'ready.json', dict(status='HANDWRITTEN_SOFTWARE_READY_FOR_USER_TRIAL_NOT_BOARD_PASS',
                                               firmware_sha256=manifest['bin_sha256'], input_sha256={}))
        shutil.copyfile(HERE / 'hardware.json', provisional / 'hardware.json')
        original_stage, original_input = pc.STAGE, builtins.input
        def cancel(prompt):
            assert 'CAM2/J5' in prompt and '无需重新PDS' in prompt
            raise KeyboardInterrupt('offline cancellation before serial')
        try:
            pc.STAGE = provisional
            builtins.input = cancel
            cancel_folder = output / 'cancel_before_serial'
            options = SimpleNamespace(log_dir=cancel_folder, label=0, session='trial01', sample=1, port='DO_NOT_OPEN', full_source=False)
            try:
                pc.live(options, manifest, model, hardware)
            except KeyboardInterrupt:
                pass
            else:
                raise AssertionError('cancel did not propagate')
            assert pc.read(cancel_folder / 'result.json')['serial_opened'] is False
        finally:
            pc.STAGE, builtins.input = original_stage, original_input
        report.update(status='HANDWRITTEN_SOFTWARE_OFFLINE_CHECKS_PASS_NOT_HDL_NOT_BOARD', flows=flows,
                      cancel_before_serial=True, fast_packets=28, full_packets=1829, model_id=pc.reference.MODEL_ID,
                      CNN_scores_injected_from_independent_reference_not_hardware_computed=True,
                      wrong_prediction_preserved_as_labeled_sample=True)
    except BaseException as error:
        report.update(status='STOPPED_FIRST_OFFLINE_FAILURE', error=repr(error))
        raise
    finally:
        inputs = [Path(__file__), *list((ROOT / 'tests/cnn_handwritten_photo').glob('*.*')),
                  *list((ROOT / 'tools/cnn_handwritten_photo').glob('*.py')), ROOT / 'tools/cnn_digits_training/integer_reference.py']
        report['input_sha256'] = {path.relative_to(ROOT).as_posix(): pc.sha(path) for path in inputs if path.is_file()}
        report['artifact_sha256'] = {path.relative_to(output).as_posix(): pc.sha(path) for path in output.rglob('*') if path.is_file()}
        pc.save(output / 'review.json', report)
    print(json.dumps(dict(status=report['status'], flows=len(flows), rejections=len(report['tests'])), indent=2))


if __name__ == '__main__':
    main()
