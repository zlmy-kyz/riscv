import argparse
import copy
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import random
import shutil
import struct
import sys
import time
import zlib

import numpy as np
import torch
from torch import nn
from torch.nn import functional as functional

import integer_reference
from prepare import digest, write_json


def rounded(values):
    return torch.sign(values) * torch.floor(torch.abs(values) + 0.5)


class StraightThrough(torch.autograd.Function):
    @staticmethod
    def forward(context, values, quantized):
        return quantized

    @staticmethod
    def backward(context, gradient):
        return gradient, None


def fake_quantize(values, fraction, minimum=None, maximum=None):
    scale = 2 ** fraction
    quantized = rounded(values * scale)
    if minimum is not None:
        quantized = quantized.clamp(minimum, maximum)
    quantized = quantized / scale
    return StraightThrough.apply(values, quantized.detach())


class Digits(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 8, 3, stride=2, padding=1)
        self.conv2 = nn.Conv2d(8, 16, 3, stride=2, padding=1)
        self.conv3 = nn.Conv2d(16, 32, 3, stride=2, padding=1)
        self.fc = nn.Linear(32, 10)
        self.scales = None

    def forward(self, activation, return_layers=False):
        traces = {}
        for layer_index, layer in enumerate((self.conv1, self.conv2, self.conv3, self.fc)):
            if layer_index == 3:
                activation = activation.mean(dim=(2, 3))
                if self.scales is not None:
                    activation = fake_quantize(activation, self.scales[2]['Fout'], 0, 127)
                traces['gap'] = activation
            weight = layer.weight
            bias = layer.bias
            if self.scales is not None:
                scale = self.scales[layer_index]
                weight = fake_quantize(weight, scale['Fw'], -127, 127)
                bias = fake_quantize(bias, scale['Fin'] + scale['Fw'])
            if layer_index < 3:
                activation = functional.conv2d(activation, weight, bias, stride=2, padding=1).relu()
                if self.scales is not None:
                    activation = fake_quantize(activation, self.scales[layer_index]['Fout'], 0, 127)
                traces[f'conv{layer_index + 1}'] = activation
            else:
                activation = functional.linear(activation, weight, bias)
                if self.scales is not None:
                    activation = fake_quantize(activation, self.scales[layer_index]['Fout'])
                traces['scores'] = activation
        return traces if return_layers else activation


def accuracy(model, inputs, labels):
    model.eval()
    with torch.no_grad():
        scores = torch.cat([model(batch) for batch in inputs.split(256)])
    return float((scores.argmax(1) == labels).float().mean().item())


def fit(model, inputs, labels, validation, validation_labels, epochs, rate, out, stage):
    optimizer = torch.optim.AdamW(model.parameters(), lr=rate, weight_decay=0.0001)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs, eta_min=rate * 0.03)
    counts = torch.bincount(labels, minlength=10).float()
    class_weights = counts.sum() / (10 * counts)
    best_accuracy = accuracy(model, validation, validation_labels)
    best_state = copy.deepcopy(model.state_dict())
    torch.save(dict(state=best_state, scales=model.scales, epoch=0,
                    validation_accuracy=best_accuracy), out / (stage + '_best.pt'))
    started = time.monotonic()
    with (out / (stage + '.jsonl')).open('x', encoding='utf-8') as log:
        for epoch in range(epochs):
            model.train()
            order = torch.randperm(len(inputs), device=inputs.device)
            loss_total = 0.0
            for indices in order.split(256):
                optimizer.zero_grad(set_to_none=True)
                scores = model(inputs[indices])
                loss = functional.cross_entropy(scores, labels[indices], weight=class_weights)
                loss.backward()
                optimizer.step()
                loss_total += float(loss.item()) * len(indices)
            scheduler.step()
            validation_accuracy = accuracy(model, validation, validation_labels)
            if validation_accuracy > best_accuracy:
                best_accuracy = validation_accuracy
                best_state = copy.deepcopy(model.state_dict())
                torch.save(dict(state=best_state, scales=model.scales, epoch=epoch + 1,
                                validation_accuracy=best_accuracy), out / (stage + '_best.pt'))
            record = dict(stage=stage, epoch=epoch + 1, loss=loss_total / len(inputs),
                          validation_accuracy=validation_accuracy, best_validation_accuracy=best_accuracy,
                          elapsed_seconds=time.monotonic() - started)
            log.write(json.dumps(record) + '\n')
            log.flush()
            if epoch == 0 or (epoch + 1) % 10 == 0 or epoch + 1 == epochs:
                print(json.dumps(record), flush=True)
    model.load_state_dict(best_state)
    return best_accuracy


def calibrate(model, validation):
    model.eval()
    with torch.no_grad():
        traces = model(validation, return_layers=True)
    previous_fraction = 7
    scales = []
    for layer_index, (name, layer) in enumerate(zip(('conv1', 'conv2', 'conv3', 'scores'),
                                                  (model.conv1, model.conv2, model.conv3, model.fc))):
        weight_maximum = float(layer.weight.abs().max().item())
        weight_fraction = min(15, max(0, math.floor(math.log2(127 / max(weight_maximum, 1e-12)))))
        activation_maximum = float(torch.quantile(traces[name].detach().abs().flatten(), 0.999).item())
        output_fraction = 7 if layer_index == 3 else min(15, max(0, math.floor(math.log2(127 / max(activation_maximum, 1e-12)))))
        output_fraction = min(output_fraction, previous_fraction + weight_fraction)
        scales.append(dict(Fin=previous_fraction, Fw=weight_fraction, Fout=output_fraction))
        previous_fraction = output_fraction
    return scales


def integer_round(values):
    return (np.sign(values) * np.floor(np.abs(values) + 0.5)).astype(np.int64)


def export(model, folder, identity):
    folder.mkdir(exist_ok=False)
    weights = []
    biases = []
    for layer, scale in zip((model.conv1, model.conv2, model.conv3, model.fc), model.scales):
        quantized = integer_round(layer.weight.detach().cpu().numpy() * (2 ** scale['Fw'])).clip(-127, 127)
        if quantized.ndim == 4:
            quantized = quantized.transpose(0, 2, 3, 1)
        weights.extend(quantized.reshape(-1).tolist())
        quantized_bias = integer_round(layer.bias.detach().cpu().numpy() * (2 ** (scale['Fin'] + scale['Fw'])))
        biases.extend(quantized_bias.tolist())
    shifts = [scale['Fin'] + scale['Fw'] - scale['Fout'] for scale in model.scales]
    (folder / 'weights.bin').write_bytes(bytes(value & 255 for value in weights))
    (folder / 'bias.bin').write_bytes(struct.pack('<66i', *biases))
    words = [value & 255 for value in weights] + [value & 0xffffffff for value in biases] + shifts
    packed = struct.pack('<6222I', *words)
    (folder / 'load_words.bin').write_bytes(packed)
    (folder / 'load_words.hex').write_text(''.join(f'{word:08x}\n' for word in words), encoding='ascii')
    model_id = int.from_bytes(hashlib.sha256(b'digits10_int8_v1\0TRAINED_HANDWRITTEN\0' + packed).digest()[:4], 'little') or 1
    metadata = dict(contract='digits10_int8_v1', purpose='TRAINED_HANDWRITTEN_DIGITS_LOCAL_DATASET',
                    trained=True, labels=[str(class_index) for class_index in range(10)],
                    model_id=model_id, model_id_hex=f'{model_id:08x}', load_words=6222, load_bytes=24888,
                    load_crc32=zlib.crc32(packed), scales=model.scales, shifts=shifts,
                    weight_layout='O_KY_KX_I', activation_layout='HWC',
                    weight_offsets=[0, 72, 1224, 5832], bias_byte_offsets=[0, 32, 96, 224],
                    shapes=[[32, 32, 1], [16, 16, 8], [8, 8, 16], [4, 4, 32], [32], [10]],
                    rounding='nearest_ties_away_from_zero', zero_point=0, input_fraction_bits=7,
                    identity=identity, camera_accuracy_verified=False, hardware_verified=False,
                    sha256={name: digest((folder / name).read_bytes()) for name in ('weights.bin', 'bias.bin', 'load_words.bin', 'load_words.hex')})
    write_json(folder / 'model.json', metadata)
    return integer_reference.load_model(folder)


def shift_numpy(values, shift):
    if shift == 0:
        return values
    return np.sign(values) * ((np.abs(values) + (1 << (shift - 1))) >> shift)


def vector_infer(inputs, model):
    activation = inputs.astype(np.int64)[:, :, :, None]
    traces = {'gray32': activation[:, :, :, 0]}
    weight_offset = 0
    bias_offset = 0
    stats = []
    for layer_index, (_, channels, outputs) in enumerate(integer_reference.LAYERS):
        padded = np.pad(activation, ((0, 0), (1, 1), (1, 1), (0, 0)))
        windows = np.lib.stride_tricks.sliding_window_view(padded, (3, 3), axis=(1, 2))[:, ::2, ::2]
        windows = windows.transpose(0, 1, 2, 4, 5, 3)
        count = outputs * 9 * channels
        kernel = np.array(model['weights'][weight_offset:weight_offset + count], dtype=np.int64).reshape(outputs, 3, 3, channels)
        accumulator = np.tensordot(windows, kernel, axes=((3, 4, 5), (1, 2, 3)))
        accumulator += np.array(model['biases'][bias_offset:bias_offset + outputs], dtype=np.int64)
        if accumulator.min() < -2147483648 or accumulator.max() > 2147483647:
            raise ValueError('vector accumulator overflow')
        shifted = shift_numpy(accumulator, model['shifts'][layer_index])
        stats.append(dict(layer=f'conv{layer_index + 1}', min_acc=int(accumulator.min()), max_acc=int(accumulator.max()),
                          saturated=int((shifted > 127).sum()), elements=shifted.size))
        activation = shifted.clip(0, 127)
        traces[f'conv{layer_index + 1}'] = activation
        weight_offset += count
        bias_offset += outputs
    pooled = (activation.sum(axis=(1, 2)) + 8) >> 4
    traces['gap'] = pooled
    kernel = np.array(model['weights'][weight_offset:], dtype=np.int64).reshape(10, 32)
    accumulator = pooled @ kernel.T + np.array(model['biases'][bias_offset:], dtype=np.int64)
    if accumulator.min() < -2147483648 or accumulator.max() > 2147483647:
        raise ValueError('FC accumulator overflow')
    traces['scores'] = shift_numpy(accumulator, model['shifts'][3])
    return traces, stats


def report(predictions, labels):
    matrix = np.zeros((10, 10), dtype=np.int64)
    np.add.at(matrix, (labels, predictions), 1)
    return dict(correct=int((predictions == labels).sum()), total=len(labels),
                accuracy=float((predictions == labels).mean()), confusion_matrix=matrix.tolist(),
                class_recall=(matrix.diagonal() / matrix.sum(axis=1)).tolist())


def verify_cases(dataset, model, trained, device, out):
    cases = []
    for class_index in range(10):
        for sample_index in np.flatnonzero(dataset['test_labels'] == class_index)[:2]:
            cases.append((f'digit{class_index}_{sample_index}', dataset['test_rgb96'][sample_index],
                          dict(label=class_index, sample_id=str(dataset['test_ids'][sample_index]))))
    for value in (0, 128, 255):
        cases.append((f'uniform{value}', np.full((96, 96, 3), value, dtype=np.uint8), dict(label=None)))
    randomizer = np.random.default_rng(20261018)
    cases.append(('asymmetric_rgb', randomizer.integers(0, 256, (96, 96, 3), dtype=np.uint8), dict(label=None)))
    evidence = out / 'reference_cases'
    evidence.mkdir()
    receipts = []
    trained.eval()
    for name, rgb, identity in cases:
        scalar = integer_reference.infer(rgb.tobytes(), model)
        gray = np.array(integer_reference.gray(rgb.tobytes()), dtype=np.int8).reshape(1, 32, 32)
        vector, _ = vector_infer(gray, model)
        with torch.no_grad():
            tensor = torch.tensor(gray[:, None], dtype=torch.float32, device=device) / 128
            qat_traces = trained(tensor, return_layers=True)
        compared = {}
        for layer_name, expected in scalar.items():
            actual = vector[layer_name][0].reshape(-1).tolist()
            if actual != expected:
                raise ValueError(f'scalar/vector mismatch {name}/{layer_name}')
            if layer_name != 'gray32':
                fraction = model['metadata']['scales'][int(layer_name[-1]) - 1]['Fout'] if layer_name.startswith('conv') else model['metadata']['scales'][2 if layer_name == 'gap' else 3]['Fout']
                tensor = qat_traces[layer_name]
                if tensor.ndim == 4:
                    tensor = tensor.permute(0, 2, 3, 1)
                qat_values = rounded(tensor * (2 ** fraction)).to(torch.int64).cpu().numpy().reshape(-1).tolist()
                if qat_values != expected:
                    raise ValueError(f'QAT/scalar mismatch {name}/{layer_name}')
            payload = struct.pack('<10i', *expected) if layer_name == 'scores' else bytes(value & 255 for value in expected)
            case_folder = evidence / name
            case_folder.mkdir(exist_ok=True)
            (case_folder / (layer_name + '.bin')).write_bytes(payload)
            compared[layer_name] = dict(elements=len(expected), sha256=digest(payload))
        (case_folder / 'rgb96.bin').write_bytes(rgb.tobytes())
        receipt = dict(name=name, identity=identity, layers=compared, scores=scalar['scores'],
                       prediction=int(np.argmax(scalar['scores'])), rgb96_sha256=digest(rgb.tobytes()))
        write_json(case_folder / 'reference.json', receipt)
        receipts.append(receipt)
    write_json(out / 'reference_review.json', dict(status='SCALAR_VECTOR_QAT_ALL_LAYERS_EQUAL',
                                                 cases=len(cases), receipts=receipts,
                                                 scope='Software only; no HDL or hardware validation'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--float-epochs', type=int, default=100)
    parser.add_argument('--qat-epochs', type=int, default=40)
    parser.add_argument('--seed', type=int, default=20261017)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required for this training entry')
    device = torch.device('cuda')
    source_folder = args.out / 'source'
    source_folder.mkdir()
    for name in ('prepare.py', 'train.py', 'integer_reference.py', 'review.py'):
        shutil.copyfile(Path(__file__).parent / name, source_folder / name)
    for name in ('digits10_int8_v1.json', '单字符数字识别_INT8首版合同_2026-10-16.md', '数字CNN整网与SoC_ABI1_2026-10-16.md'):
        shutil.copyfile(Path('doc/cnn') / name, source_folder / name)
    data_metadata = json.loads((args.data / 'dataset.json').read_text(encoding='utf-8'))
    for name, expected in data_metadata['sha256'].items():
        if digest((args.data / name).read_bytes()) != expected:
            raise ValueError('changed dataset ' + name)
    identity = dict(seed=args.seed, python=sys.version, torch=torch.__version__, numpy=np.__version__,
                    platform=platform.platform(), cuda=torch.version.cuda, gpu=torch.cuda.get_device_name(),
                    dependencies={name: importlib.metadata.version(name) for name in ('torch', 'numpy', 'Pillow', 'filelock', 'typing_extensions', 'sympy', 'networkx', 'jinja2', 'fsspec')},
                    command=sys.argv, dataset=data_metadata, contract_sha256=digest((source_folder / 'digits10_int8_v1.json').read_bytes()),
                    source_sha256={path.name: digest(path.read_bytes()) for path in sorted(source_folder.iterdir())},
                    nondeterminism='Seed/cudnn deterministic set; cross-version bitwise training reproducibility not claimed')
    write_json(args.out / 'input_identity.json', identity)
    print(json.dumps(dict(stage='environment', gpu=identity['gpu'], torch=identity['torch'], cuda=identity['cuda'])), flush=True)
    dataset = np.load(args.data / 'dataset.npz', allow_pickle=False)
    inputs = torch.tensor(np.concatenate((dataset['train_q'], dataset['augmented_q']))[:, None], dtype=torch.float32, device=device) / 128
    labels = torch.tensor(np.concatenate((dataset['train_labels'], dataset['augmented_labels'])), device=device)
    validation = torch.tensor(dataset['validation_q'][:, None], dtype=torch.float32, device=device) / 128
    validation_labels = torch.tensor(dataset['validation_labels'], device=device)
    model = Digits().to(device)
    float_accuracy = fit(model, inputs, labels, validation, validation_labels, args.float_epochs, 0.003, args.out, 'float')
    float_model = copy.deepcopy(model)
    model.scales = calibrate(model, validation)
    print(json.dumps(dict(stage='calibration', scales=model.scales)), flush=True)
    ptq_accuracy = accuracy(model, validation, validation_labels)
    qat_accuracy = fit(model, inputs, labels, validation, validation_labels, args.qat_epochs, 0.0003, args.out, 'qat')
    integer_model = export(model, args.out / 'model', identity)
    write_json(args.out / 'bounds.json', dict(per_channel=integer_model['bounds'], maximum=max(integer_model['bounds'])))
    verify_cases(dataset, integer_model, model, device, args.out)
    metrics = dict(float_validation_accuracy=float_accuracy, ptq_validation_accuracy=ptq_accuracy,
                   qat_validation_accuracy=qat_accuracy, selection='validation only; best first epoch on ties')
    for split in ('validation', 'test'):
        score_batches = []
        statistics = []
        for start in range(0, len(dataset[split + '_q']), 128):
            traces, stats = vector_infer(dataset[split + '_q'][start:start + 128], integer_model)
            score_batches.append(traces['scores'])
            statistics.append(stats)
        scores = np.concatenate(score_batches)
        evaluation_labels = dataset[split + '_labels']
        metrics[split + '_int8'] = report(scores.argmax(axis=1), evaluation_labels)
        evaluation_inputs = torch.tensor(dataset[split + '_q'][:, None], dtype=torch.float32, device=device) / 128
        with torch.no_grad():
            float_scores = torch.cat([float_model(batch) for batch in evaluation_inputs.split(256)]).cpu().numpy()
            qat_scores = torch.cat([model(batch) for batch in evaluation_inputs.split(256)]).cpu().numpy()
        exact_qat = integer_round(qat_scores * (2 ** model.scales[3]['Fout']))
        if not np.array_equal(exact_qat, scores):
            raise ValueError(f'full {split} QAT/integer score mismatch')
        metrics[split + '_float'] = report(float_scores.argmax(axis=1), evaluation_labels)
        metrics[split + '_accumulators'] = statistics
        np.savez_compressed(args.out / (split + '_predictions.npz'), scores_int8=scores,
                            scores_float=float_scores, labels=evaluation_labels, sample_ids=dataset[split + '_ids'])
    metrics['software_contract_equal'] = True
    metrics['int8_test_drop_percentage_points'] = 100 * (metrics['test_float']['accuracy'] - metrics['test_int8']['accuracy'])
    metrics['dataset_only_goal_met'] = (metrics['test_int8']['accuracy'] >= 0.95 and
                                       min(metrics['test_int8']['class_recall']) >= 0.90 and
                                       metrics['int8_test_drop_percentage_points'] <= 2)
    metrics['camera_accuracy_verified'] = False
    metrics['hardware_verified'] = False
    write_json(args.out / 'metrics.json', metrics)
    manifest = {path.relative_to(args.out).as_posix(): digest(path.read_bytes())
                for path in sorted(args.out.rglob('*')) if path.is_file()}
    write_json(args.out / 'sealed_manifest.json', dict(status='TRAINED_EXPORTED_SOFTWARE_VERIFIED_NOT_BOARD_ACCEPTANCE', files=manifest))
    print(json.dumps(dict(stage='complete', model_id=integer_model['metadata']['model_id_hex'],
                         float_test=metrics['test_float'], int8_test=metrics['test_int8'],
                         dataset_only_goal_met=metrics['dataset_only_goal_met']), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
