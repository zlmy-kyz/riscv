import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/cnn_handwritten_photo'))
import run as pc


def main():
    frozen = HERE / 'sealed_20261017_a'
    ready_path = HERE / 'ready.json'
    if frozen.exists() or ready_path.exists():
        raise ValueError('new seal directory required')
    manifest, model = pc.image()
    hardware = pc.hardware()
    parents = pc.read(HERE / 'parent_identity.json')
    for name, expected in parents.items():
        assert pc.sha(ROOT / name) == expected, ('historical input changed', name)
    review_path = HERE / 'checks_01/review.json'
    review = pc.read(review_path)
    assert review['status'] == 'HANDWRITTEN_SOFTWARE_OFFLINE_CHECKS_PASS_NOT_HDL_NOT_BOARD'
    for name, expected in review['input_sha256'].items():
        assert pc.sha(ROOT / name) == expected, ('changed tested input', name)
    for name, expected in review['artifact_sha256'].items():
        assert pc.sha(review_path.parent / name) == expected, ('changed check artifact', name)
    inputs = {ROOT / name for name in manifest['source_sha256']}
    inputs.update(path for path in pc.DEFAULT.parent.iterdir() if path.is_file())
    inputs.update(path for path in HERE.iterdir() if path.is_file() and path.suffix in ('.py', '.json'))
    inputs.update([review_path, ROOT / 'tools/cnn_handwritten_photo/README.md', ROOT / 'tests/cnn_handwritten_photo/README.md'])
    project = frozen / 'project'
    project.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for path in sorted(inputs):
        name = path.relative_to(ROOT).as_posix()
        destination = project / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        hashes[name] = pc.sha(destination)
        assert hashes[name] == pc.sha(path)
    pc.save(frozen / 'manifest.json', dict(status='SEALED_SOFTWARE_INPUTS_NOT_HDL_PACKAGE', sha256=hashes,
                                         existing_design_sha256=hardware['design_sha256'],
                                         scope='New application and PC software only; prior CAM2 RTL baseline reused'))
    ready = dict(status='HANDWRITTEN_SOFTWARE_READY_FOR_USER_TRIAL_NOT_BOARD_PASS',
                 firmware_manifest=pc.DEFAULT.relative_to(ROOT).as_posix(), firmware_path=manifest['bin_path'],
                 firmware_sha256=manifest['bin_sha256'], firmware_bytes=manifest['bytes'], firmware_crc32=f"{manifest['crc32']:08x}",
                 model_id=model['meta']['model_id_hex'], model_crc32=f"{model['meta']['load_crc32']:08x}",
                 load_words_sha256=pc.sha(pc.MODEL / 'load_words.bin'), input_sha256=hashes,
                 frozen_manifest_sha256=pc.sha(frozen / 'manifest.json'),
                 offline_review=review_path.relative_to(ROOT).as_posix(), offline_review_sha256=pc.sha(review_path),
                 historical_inputs_preserved=len(parents), design_unchanged=True, PDS_started=False,
                 new_bitstream_required=False, serial_opened=False, key_HDL='NOT_COMPLETED', real_CPU='NOT_RUN',
                 board='NOT_RUN', formal_camera_accuracy_verified=False, fast_source_to_PP_check=False,
                 full_source_source_to_PP_check='REQUIRED_ALL_27648_BYTES', retry_count=0)
    pc.save(ready_path, ready)
    print(json.dumps(dict(status=ready['status'], inputs=len(hashes), firmware_sha256=manifest['bin_sha256']), indent=2))


if __name__ == '__main__':
    main()
