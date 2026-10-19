import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[2]
NAME = 'vision_handoff_20261019_a'
OUTPUT = ROOT / 'sim/cnn/vision_handoff_validation_20261019_a'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    global OUTPUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=OUTPUT)
    OUTPUT = parser.parse_args().out.resolve()
    OUTPUT.mkdir(exist_ok=False)
    report = dict(status='RUNNING', serial_opened=False, PDS_started=False, HDL_run=False, retrained=False)

    def run(name, arguments, expected=0):
        command = [sys.executable, '-X', 'utf8', *map(str, arguments)]
        completed = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        (OUTPUT / (name + '.log')).write_bytes(completed.stdout)
        save(OUTPUT / (name + '.command.json'), dict(argv=command, returncode=completed.returncode))
        if (completed.returncode == 0) != (expected == 0):
            raise ValueError(name + ': ' + completed.stdout.decode('utf-8', errors='replace'))
        return completed.stdout

    try:
        archive = ROOT / 'share' / (NAME + '.zip')
        expected_sha = archive.with_suffix('.zip.sha256').read_text().split()[0]
        if sha(archive) != expected_sha:
            raise ValueError('archive checksum')
        extracted = OUTPUT / 'peer_extract'
        with zipfile.ZipFile(archive) as zipped:
            for info in zipped.infolist():
                if info.is_dir() or not (extracted / info.filename).resolve().is_relative_to(extracted.resolve()):
                    raise ValueError('unsafe archive member')
            zipped.extractall(extracted)
        package = extracted / NAME
        peer_report = OUTPUT / 'peer_review.json'
        run('verify_relocated_package', [package / 'verify_package.py', '--plan', '--replay', '--out', peer_report])
        verified = json.loads(peer_report.read_text(encoding='utf-8'))
        if len(verified['replays']) != 7 or not all(value['prediction'] == 0 for value in verified['replays'].values()):
            raise ValueError('capture replay outcomes changed')
        workspace = OUTPUT / 'pds_workspace_01'
        run('create_pds_workspace', [package / 'make_pds_workspace.py', '--out', workspace])
        setup = (workspace / 'RISCV.pds').read_text(encoding='utf-8').split('(_task tsk_compile', 1)[0]
        references = set(re.findall(r'\(_(?:file|ip|ip_source_item)\s+"([^"]+)"', setup))
        if len(references) != 153 or any(not (workspace / name).is_file() for name in references):
            raise ValueError('relocated PDS setup closure')
        for name in ('ipcore/inst_rom/inst_rom.idf', 'ipcore/data_ram/data_ram.idf'):
            text = (workspace / name).read_text(encoding='utf-8')
            match = re.search(r'<name>INIT_FILE</name>\s*<value>([^<]+)</value>', text)
            image = 'loader_rom.dat' if 'inst_rom' in name else 'loader_ram.dat'
            expected = (workspace / 'tests/uart_loader/candidates/verify_run_hello/build' / image).as_posix()
            if match is None or match[1] != expected:
                raise ValueError('initialization path not relocated ' + name)
        refused = run('reject_existing_workspace', [package / 'make_pds_workspace.py', '--out', workspace], expected=1)
        if b'use a new destination' not in refused:
            raise ValueError('wrong existing workspace rejection')
        negative = OUTPUT / 'tamper_probe'
        negative.mkdir()
        shutil.copyfile(package / 'verify_package.py', negative / 'verify_package.py')
        (negative / 'probe.bin').write_bytes(b'original')
        save(negative / 'package_manifest.json', dict(files={'probe.bin': dict(bytes=8, sha256=sha(negative / 'probe.bin'))}))
        (negative / 'probe.bin').write_bytes(b'modified')
        refused = run('reject_tampered_input', [negative / 'verify_package.py'], expected=1)
        if b'changed or missing package file' not in refused:
            raise ValueError('wrong tamper rejection')
        protected = json.loads((ROOT / 'sim/cnn/handwritten_perf46_20261019_a/parent_identity.json').read_text(encoding='utf-8'))
        for name, expected in protected.items():
            if sha(ROOT / name) != expected:
                raise ValueError('protected original changed ' + name)
        report.update(status='VISION_HANDOFF_EXTRACTED_COPY_VALIDATION_PASS_NOT_HDL_OR_ACCURACY_ACCEPTANCE',
                      archive_sha256=sha(archive), archive_bytes=archive.stat().st_size,
                      files_checked=verified['files_checked'], source_images_checked=verified['source_images_checked'],
                      actual_capture_raw_replays=7, recorded_label_mismatches=5,
                      PDS_setup_inputs=153, PDS_relocation_paths_verified=True,
                      rejects_existing_directory=True, rejects_tampered_input=True,
                      preserved_original_inputs=len(protected),
                      peer_review_sha256=sha(peer_report), relocation_review_sha256=sha(workspace / 'relocation_review.json'))
    except BaseException as error:
        report.update(status='STOPPED_FIRST_HANDOFF_VALIDATION_FAILURE', error=repr(error))
        raise
    finally:
        report['validation_script_sha256'] = sha(Path(__file__))
        report['artifact_sha256'] = {path.name: sha(path) for path in OUTPUT.iterdir() if path.is_file()}
        save(OUTPUT / 'review.json', report)
    shutil.copyfile(OUTPUT / 'review.json', ROOT / 'share' / (NAME + '_validation.json'))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
