import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = HERE / 'parent_identity.json'
    if output.exists() or (HERE / 'hardware.json').exists():
        raise ValueError('preparation already exists')
    hardware_path = ROOT / 'sim/camera/cam2_photo_20261017_a/hardware.json'
    hardware = json.loads(hardware_path.read_text(encoding='utf-8'))
    files = {ROOT / name for name in (*hardware['design_sha256'], *hardware['constraint_sha256'])}
    for name, expected in {**hardware['design_sha256'], **hardware['constraint_sha256']}.items():
        assert sha(ROOT / name) == expected, name
    for folder in ('tests/cnn_digits_photo', 'tools/cnn_digits_photo', 'tools/cnn_cam2_photo'):
        files.update(path for path in (ROOT / folder).iterdir() if path.is_file())
    files.update([ROOT / 'RISCV.pds', hardware_path,
                  ROOT / 'tests/cnn_digits_photo/build/photo_20261016_a/program.bin',
                  ROOT / 'tests/cnn_digits_photo/build/photo_20261016_a/manifest.json',
                  ROOT / 'sim/camera/cam2_photo_20261017_a/board_review_01.json'])
    review = json.loads((ROOT / 'sim/camera/cam2_photo_20261017_a/board_review_01.json').read_text(encoding='utf-8'))
    for name, expected in review['raw_evidence_sha256'].items():
        path = ROOT / review['directory'] / name
        assert sha(path) == expected, name
        files.add(path)
    identities = {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(files)}
    output.write_text(json.dumps(identities, indent=2) + '\n', encoding='utf-8')
    hardware.update(requires_new_bitstream=False, implementation_use='REUSE_ACCEPTED_CAM2_BITSTREAM_NO_NEW_PDS',
                    parent_hardware_manifest_sha256=sha(hardware_path),
                    parent_board_review='sim/camera/cam2_photo_20261017_a/board_review_01.json',
                    parent_board_review_sha256=sha(ROOT / 'sim/camera/cam2_photo_20261017_a/board_review_01.json'))
    (HERE / 'hardware.json').write_text(json.dumps(hardware, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='INPUTS_PREPARED_NO_BOARD_ACTIVITY', preserved_files=len(identities))))


if __name__ == '__main__':
    main()
