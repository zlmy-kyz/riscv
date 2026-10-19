import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description='Create a separate relocated PDS source copy; never launches PDS')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    destination = args.out.resolve()
    if destination.exists() or destination.is_relative_to(ROOT):
        raise ValueError('use a new destination outside the immutable handoff package')
    manifest = json.loads((ROOT / 'package_manifest.json').read_text(encoding='utf-8'))
    destination.mkdir(parents=True, exist_ok=False)
    changed = {}
    for name in manifest['pds_source_inputs']:
        source = ROOT / 'project' / name
        expected = manifest['files']['project/' + name]['sha256']
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('changed original hardware input ' + name)
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if target.suffix.lower() in ('.v', '.vh', '.sv', '.svh', '.idf', '.pds', '.fdc', '.tcl'):
            raw = target.read_bytes()
            updated = raw.replace(b'D:/riscv/RISCV/', (destination.as_posix() + '/').encode('utf-8'))
            updated = updated.replace(b'D:\\riscv\\RISCV\\', (str(destination) + '\\').encode('utf-8'))
            if updated != raw:
                target.write_bytes(updated)
                changed[name] = dict(before_sha256=expected, after_sha256=hashlib.sha256(updated).hexdigest())
    result = dict(status='RELOCATED_PDS_SOURCE_COPY_CREATED_NOT_COMPILED', original_package_unchanged=True,
                  files=len(manifest['pds_source_inputs']), changed_path_literals=changed,
                  PDS_started=False, bitstream_generated=False,
                  warning='Inspect device/top/active FDC and initialization paths in PDS. This is not new implementation or timing acceptance.')
    (destination / 'relocation_review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
