import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

import numpy as np

import integer_reference
from prepare import gray32, write_json


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--run', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('review output must be new')
    metadata = json.loads((args.data / 'dataset.json').read_text(encoding='utf-8'))
    for name, expected in metadata['sha256'].items():
        if sha256(args.data / name) != expected:
            raise ValueError('dataset identity ' + name)
    records = json.loads((args.data / 'samples.json').read_text(encoding='utf-8'))
    data = np.load(args.data / 'dataset.npz', allow_pickle=False)
    split_ids = {}
    rgb_compared = 0
    for split in ('train', 'validation', 'test'):
        identities = data[split + '_ids'].tolist()
        split_labels = data[split + '_labels']
        split_rgb = data[split + '_rgb96']
        split_gray = data[split + '_q']
        split_ids[split] = set(identities)
        if len(identities) != len(split_ids[split]):
            raise ValueError('duplicate split identity')
        expected_records = {record['pixels_sha256']: record['label'] for record in records if record['split'] == split}
        if set(expected_records) != split_ids[split]:
            raise ValueError('source manifest split identity')
        for sample_index, identity in enumerate(identities):
            if expected_records[identity] != split_labels[sample_index]:
                raise ValueError('source label mismatch')
            if not np.array_equal(gray32(split_rgb[sample_index]), split_gray[sample_index]):
                raise ValueError('RGB96 -> gray32 mismatch')
            rgb_compared += 1
        if len(identities) != metadata['splits'][split]['count']:
            raise ValueError('split count')
    for left, right in (('train', 'validation'), ('train', 'test'), ('validation', 'test')):
        if split_ids[left] & split_ids[right]:
            raise ValueError('source leakage')
    source_root = Path(metadata['dataset_root'])
    for record in records:
        if sha256(source_root / record['path']) != record['sha256']:
            raise ValueError('source raw file changed ' + record['path'])
    if args.run is None:
        receipt = dict(status='LOCAL_DATA_PREPARATION_REVIEW_PASS', source_files_checked=len(records),
                       split_disjoint=True, rgb96_gray32_pairs_checked=rgb_compared,
                       dataset_metadata_sha256=sha256(args.data / 'dataset.json'),
                       camera_accuracy_verified=False)
        write_json(args.out, receipt)
        print(json.dumps(receipt), flush=True)
        return
    manifest = json.loads((args.run / 'sealed_manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files'].items():
        if sha256(args.run / name) != expected:
            raise ValueError('run identity ' + name)
    model = integer_reference.load_model(args.run / 'model')
    compared = Counter()
    for case_folder in sorted((args.run / 'reference_cases').iterdir()):
        traces = integer_reference.infer((case_folder / 'rgb96.bin').read_bytes(), model)
        for name, expected in traces.items():
            payload = (case_folder / (name + '.bin')).read_bytes()
            if name == 'scores':
                actual = list(struct.unpack('<10i', payload))
            elif name == 'gray32':
                actual = [value if value < 128 else value - 256 for value in payload]
            else:
                actual = list(payload)
            if actual != expected:
                raise ValueError(f'scalar trace mismatch {case_folder.name}/{name}')
            compared[name] += len(expected)
    metrics = json.loads((args.run / 'metrics.json').read_text(encoding='utf-8'))
    for split in ('validation', 'test'):
        predictions = np.load(args.run / (split + '_predictions.npz'), allow_pickle=False)
        if not np.array_equal(predictions['sample_ids'], data[split + '_ids']) or not np.array_equal(predictions['labels'], data[split + '_labels']):
            raise ValueError('prediction sample identity')
        matrix = np.zeros((10, 10), dtype=np.int64)
        np.add.at(matrix, (predictions['labels'], predictions['scores_int8'].argmax(axis=1)), 1)
        if matrix.tolist() != metrics[split + '_int8']['confusion_matrix']:
            raise ValueError('metric confusion matrix')
        if int(matrix.trace()) != metrics[split + '_int8']['correct'] or int(matrix.sum()) != metrics[split + '_int8']['total']:
            raise ValueError('metric count')
    successful_bin = Path('tests/cnn_digits_photo/build/photo_20261016_a/program.bin')
    expected_bin = '2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4'
    if sha256(successful_bin) != expected_bin:
        raise ValueError('historical successful firmware changed')
    if sha256(Path('doc/cnn/digits10_int8_v1.json')) != model['metadata']['identity']['contract_sha256']:
        raise ValueError('numeric contract changed')
    receipt = dict(status='LOCAL_TRAINED_MODEL_DATA_AND_INTEGER_REFERENCE_REVIEW_PASS',
                   source_files_checked=len(records), split_disjoint=True, rgb96_gray32_pairs_checked=rgb_compared,
                   run_artifacts_checked=len(manifest['files']), scalar_trace_elements=dict(compared),
                   model_id=model['metadata']['model_id_hex'], load_crc32=f"{model['metadata']['load_crc32']:08x}",
                   maximum_proven_accumulator_bound=max(model['bounds']),
                   float_test=metrics['test_float'], int8_test=metrics['test_int8'],
                   dataset_only_goal_met=metrics['dataset_only_goal_met'],
                   firmware_sha256=expected_bin, contract_unchanged=True,
                   sealed_manifest_sha256=sha256(args.run / 'sealed_manifest.json'),
                   camera_accuracy_verified=False, hardware_verified=False,
                   exclusions=['writer-independent accuracy', 'near-duplicate isolation', 'CAM2 handwritten photo accuracy', 'HDL/PDS/new model board acceptance'])
    write_json(args.out, receipt)
    print(json.dumps(receipt, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
