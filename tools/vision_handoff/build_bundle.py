import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NAME = 'vision_handoff_20261019_a'
OUTPUT = ROOT / 'share' / NAME
specification = importlib.util.spec_from_file_location('handoff_pc', ROOT / 'tools/cnn_handwritten_perf46/run.py')
pc = importlib.util.module_from_spec(specification)
specification.loader.exec_module(pc)


def main():
    archive = OUTPUT.with_suffix('.zip')
    if OUTPUT.exists() or archive.exists():
        raise ValueError('new bundle name required')
    pc.image()
    hardware = pc.hardware()
    ready_path = pc.STAGE / 'ready.json'
    ready = pc.read(ready_path)
    for name, expected in ready['input_sha256'].items():
        pc.need(pc.sha(ROOT / name) == expected, 'sealed input changed ' + name)
    inputs = set(ready['input_sha256']) | set(hardware['design_sha256']) | set(hardware['constraint_sha256'])
    inputs.add(ready_path.relative_to(ROOT).as_posix())
    pds_text = (ROOT / 'RISCV.pds').read_text(encoding='utf-8')
    setup = pds_text.split('(_task tsk_compile', 1)[0]
    pds_inputs = set(re.findall(r'\(_(?:file|ip|ip_source_item)\s+"([^"]+)"', setup))
    pc.need(len(pds_inputs) == 153, 'unexpected PDS setup inputs')
    pds_inputs.add('RISCV.pds')
    source_suffixes = {'.v', '.vh', '.sv', '.svh', '.vp', '.idf', '.fdc', '.dat', '.hex', '.mif', '.mem'}
    for ip in ('inst_rom', 'data_ram', 'ddr3', 'icache', 'dcache', 'mul'):
        for path in (ROOT / 'ipcore' / ip).rglob('*'):
            if path.is_file() and path.suffix.lower() in source_suffixes and not set(path.parts) & {'work', 'pnr', 'example_design', 'sim_lib'}:
                pds_inputs.add(path.relative_to(ROOT).as_posix())
    for name in ('loader_rom.dat', 'loader_ram.dat', 'manifest.json', 'loader.elf', 'symbols.txt', 'loader.readelf.txt'):
        pds_inputs.add('tests/uart_loader/candidates/verify_run_hello/build/' + name)
    for path in (ROOT / 'myriscv').iterdir():
        if path.is_file() and path.suffix.lower() in {'.vh', '.svh'}:
            pds_inputs.add(path.relative_to(ROOT).as_posix())
    for name in sorted(pds_inputs):
        path = ROOT / name
        pc.need(path.is_file(), 'missing PDS input ' + name)
        if path.suffix in {'.v', '.vh', '.sv', '.svh', '.vp'}:
            for include in re.findall(r'`include\s+"([^"]+)"', path.read_text(encoding='utf-8', errors='ignore')):
                candidates = [path.parent / include, ROOT / include, ROOT / 'myriscv' / include]
                resolved = next((candidate for candidate in candidates if candidate.is_file()), None)
                pc.need(resolved is not None, 'unresolved include ' + name + ':' + include)
                pds_inputs.add(resolved.relative_to(ROOT).as_posix())
    inputs.update(pds_inputs)
    inputs.update({'AGENTS.md', 'doc/CODEX_HANDOFF.md', 'generate_bitstream/board_top.sbit',
                   'tools/cnn_digits_training/prepare.py', 'tools/cnn_digits_training/train.py',
                   'tools/cnn_digits_training/review.py', 'tools/cnn_digits_training/README.md',
                   'tools/cnn_handwritten_perf46/README.md',
                   'doc/cnn/视觉识别同学交接与复现_2026-10-19.md'})
    for directory in ('doc/cnn', 'doc/camera'):
        inputs.update(path.relative_to(ROOT).as_posix() for path in (ROOT / directory).iterdir() if path.is_file() and path.suffix in {'.md', '.json'})
    run = ROOT / 'sim/cnn/training/handwritten_run_20261017_a'
    for name, expected in pc.read(run / 'sealed_manifest.json')['files'].items():
        pc.need(pc.sha(run / name) == expected, 'training archive changed ' + name)
    for directory in (run, ROOT / 'sim/cnn/training/handwritten_data_20261017_a', pc.STAGE):
        inputs.update(path.relative_to(ROOT).as_posix() for path in directory.rglob('*')
                      if path.is_file() and '__pycache__' not in path.parts and 'sealed_20261019_a' not in path.parts)
    inputs.update(path.relative_to(ROOT).as_posix() for path in (ROOT / 'sim/cnn/training').glob('*.json'))
    inputs.update(path.relative_to(ROOT).as_posix() for path in (ROOT / 'sim/cnn/training').glob('*.log'))
    captures = sorted(path for path in (ROOT / 'sim/cnn/board').glob('handwritten_perf46_trial01_*') if path.is_dir())
    pc.need(len(captures) == 7, 'unexpected capture count')
    for folder in captures:
        pc.verify(folder)
        inputs.update(path.relative_to(ROOT).as_posix() for path in folder.rglob('*') if path.is_file())
    inputs.add('tests/cnn_digits_photo/build/photo_20261016_a/program.bin')
    data_meta = pc.read(ROOT / 'sim/cnn/training/handwritten_data_20261017_a/dataset.json')
    data_npz = ROOT / 'sim/cnn/training/handwritten_data_20261017_a/dataset.npz'
    pc.need(pc.sha(data_npz) == data_meta['sha256']['dataset.npz'], 'prepared data changed')
    samples = pc.read(data_npz.parent / 'samples.json')
    original_data = ROOT / '80bfd/经典手写数字数据集'
    for record in samples:
        pc.need(pc.sha(original_data / record['path']) == record['sha256'], 'relocated raw data differs ' + record['path'])
    OUTPUT.mkdir(parents=True, exist_ok=False)
    project = OUTPUT / 'project'
    for name in sorted(inputs):
        source = ROOT / name
        pc.need(source.is_file(), 'missing handoff input ' + name)
        destination = project / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    for record in samples:
        destination = OUTPUT / 'dataset_source' / record['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original_data / record['path'], destination)
    for name in ('README.md', 'LICENSE'):
        shutil.copyfile(ROOT / '80bfd' / name, OUTPUT / 'dataset_source' / name)
    for name in ('verify_package.py', 'make_pds_workspace.py'):
        shutil.copyfile(HERE / name, OUTPUT / name)
    shutil.copyfile(HERE / 'README_交接.md', OUTPUT / 'README.md')
    shutil.copyfile(Path(__file__), OUTPUT / 'build_bundle_source.py')
    hashes = {path.relative_to(OUTPUT).as_posix(): dict(sha256=pc.sha(path), bytes=path.stat().st_size)
              for path in sorted(OUTPUT.rglob('*')) if path.is_file()}
    manifest = dict(status='VISION_HANDOFF_SNAPSHOT_NOT_NEW_HDL_OR_ACCURACY_ACCEPTANCE',
                    public_data_publication_authorized=True, files=hashes, pds_source_inputs=sorted(pds_inputs),
                    capture_directories=[path.relative_to(ROOT).as_posix() for path in captures],
                    fixed_application_sha256=ready['firmware_sha256'], model_id='4c8b5aca',
                    raw_source_images=len(samples), source_dataset_current_location=str(original_data),
                    source_dataset_historical_location=data_meta['dataset_root'],
                    bitstream=dict(path='project/generate_bitstream/board_top.sbit',
                                   sha256=pc.sha(ROOT / 'generate_bitstream/board_top.sbit'),
                                   status='CURRENT_GENERATED_FILE_SNAPSHOT_NOT_FPGA_READBACK_IDENTITY'),
                    exclusions=['PDS installation and compiler distributions', 'Python/CUDA environments',
                                'PDS implementation has not been rerun for the bundle',
                                'Adaptive preprocessing is a proposal, not implemented or accepted'])
    pc.save(OUTPUT / 'package_manifest.json', manifest)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for path in sorted(OUTPUT.rglob('*')):
            if path.is_file():
                zipped.write(path, Path(NAME) / path.relative_to(OUTPUT))
    archive_hash = pc.sha(archive)
    archive.with_suffix('.zip.sha256').write_text(archive_hash + '  ' + archive.name + '\n', encoding='ascii')
    report = dict(status='BUNDLE_CREATED_PENDING_EXTRACTED_COPY_VALIDATION', files=len(hashes),
                  archive=archive.relative_to(ROOT).as_posix(), archive_bytes=archive.stat().st_size,
                  archive_sha256=archive_hash, package_manifest_sha256=pc.sha(OUTPUT / 'package_manifest.json'),
                  pds_source_inputs=len(pds_inputs), captures=len(captures), source_images=len(samples),
                  source_originals_changed=False, serial_opened=False, PDS_started=False)
    pc.save(OUTPUT.with_name(NAME + '_build_review.json'), report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
