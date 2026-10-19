import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib


CONTRACT = 'digits10_int8_v1'
LAYERS = ((32, 1, 8), (16, 8, 16), (8, 16, 32))


def round_shift(value, shift):
    if not 0 <= shift <= 31:
        raise ValueError('invalid shift')
    if shift == 0:
        return value
    magnitude = (abs(value) + (1 << (shift - 1))) >> shift
    return -magnitude if value < 0 else magnitude


def gray(rgb):
    if len(rgb) != 27648:
        raise ValueError('RGB96 must contain exactly 27648 bytes')
    output = []
    for row in range(32):
        for column in range(32):
            offset = 3 * (96 * (3 * row + 1) + 3 * column + 1)
            red, green, blue = rgb[offset:offset + 3]
            output.append(((77 * red + 150 * green + 29 * blue + 128) >> 8) - 128)
    return output


def load_model(folder):
    folder = Path(folder)
    metadata = json.loads((folder / 'model.json').read_text(encoding='utf-8'))
    if metadata['contract'] != CONTRACT or metadata['trained'] is not True:
        raise ValueError('trained contract required')
    if metadata['purpose'] != 'TRAINED_HANDWRITTEN_DIGITS_LOCAL_DATASET':
        raise ValueError('wrong model purpose')
    if metadata['labels'] != [str(class_index) for class_index in range(10)]:
        raise ValueError('class order')
    if metadata['load_words'] != 6222 or metadata['load_bytes'] != 24888:
        raise ValueError('load dimensions')
    expected_layout = dict(weight_layout='O_KY_KX_I', activation_layout='HWC',
                           weight_offsets=[0, 72, 1224, 5832], bias_byte_offsets=[0, 32, 96, 224],
                           shapes=[[32, 32, 1], [16, 16, 8], [8, 8, 16], [4, 4, 32], [32], [10]],
                           rounding='nearest_ties_away_from_zero', zero_point=0, input_fraction_bits=7)
    if any(metadata[key] != value for key, value in expected_layout.items()):
        raise ValueError('numeric contract layout/rounding')
    for name, expected in metadata['sha256'].items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
            raise ValueError('model SHA256: ' + name)
    raw_weights = (folder / 'weights.bin').read_bytes()
    raw_bias = (folder / 'bias.bin').read_bytes()
    if len(raw_weights) != 6152 or len(raw_bias) != 264 or 128 in raw_weights:
        raise ValueError('parameter encoding')
    weights = [value if value < 128 else value - 256 for value in raw_weights]
    biases = list(struct.unpack('<66i', raw_bias))
    shifts = metadata['shifts']
    if len(shifts) != 4 or len(metadata['scales']) != 4:
        raise ValueError('four scales required')
    previous_fraction = 7
    for scale, shift in zip(metadata['scales'], shifts):
        if any(not isinstance(scale[key], int) or not 0 <= scale[key] <= 15 for key in ('Fin', 'Fw', 'Fout')):
            raise ValueError('fraction bits')
        if scale['Fin'] != previous_fraction or scale['Fin'] + scale['Fw'] - scale['Fout'] != shift or not 0 <= shift <= 31:
            raise ValueError('scale continuity/shift')
        previous_fraction = scale['Fout']
    words = [value & 255 for value in weights] + [value & 0xffffffff for value in biases] + shifts
    packed = struct.pack('<6222I', *words)
    if packed != (folder / 'load_words.bin').read_bytes() or zlib.crc32(packed) != metadata['load_crc32']:
        raise ValueError('ABI1 word encoding/CRC')
    identity = int.from_bytes(hashlib.sha256(b'digits10_int8_v1\0TRAINED_HANDWRITTEN\0' + packed).digest()[:4], 'little') or 1
    if identity != metadata['model_id'] or metadata['model_id_hex'] != f'{identity:08x}':
        raise ValueError('model identity')
    weight_offset = 0
    bias_offset = 0
    bounds = []
    for layer_index, (_, inputs, outputs) in enumerate((*LAYERS, (1, 32, 10))):
        terms = inputs * 9 if layer_index < 3 else inputs
        for channel in range(outputs):
            bias = biases[bias_offset + channel]
            start = weight_offset + channel * terms
            bound = abs(bias) + 128 * sum(abs(value) for value in weights[start:start + terms])
            if bound > 2147483647 or abs(bias) > 2145142783:
                raise ValueError('INT32 accumulation or ABI1 bias bound')
            bounds.append(bound)
        weight_offset += terms * outputs
        bias_offset += outputs
    return dict(metadata=metadata, weights=weights, biases=biases, shifts=shifts, bounds=bounds)


def infer(rgb, model):
    activation = gray(rgb)
    traces = {'gray32': activation[:]}
    weight_offset = 0
    bias_offset = 0
    for layer_index, (side, inputs, outputs) in enumerate(LAYERS):
        next_activation = []
        for row in range(side // 2):
            for column in range(side // 2):
                for output_channel in range(outputs):
                    accumulator = model['biases'][bias_offset + output_channel]
                    for kernel_row in range(3):
                        input_row = row * 2 + kernel_row - 1
                        for kernel_column in range(3):
                            input_column = column * 2 + kernel_column - 1
                            for input_channel in range(inputs):
                                value = 0
                                if 0 <= input_row < side and 0 <= input_column < side:
                                    value = activation[(input_row * side + input_column) * inputs + input_channel]
                                weight_index = weight_offset + ((output_channel * 3 + kernel_row) * 3 + kernel_column) * inputs + input_channel
                                accumulator += value * model['weights'][weight_index]
                    if not -2147483648 <= accumulator <= 2147483647:
                        raise ValueError('convolution accumulator overflow')
                    next_activation.append(min(127, max(0, round_shift(accumulator, model['shifts'][layer_index]))))
        activation = next_activation
        traces[f'conv{layer_index + 1}'] = activation[:]
        weight_offset += outputs * 9 * inputs
        bias_offset += outputs
    pooled = [(sum(activation[position * 32 + channel] for position in range(16)) + 8) >> 4 for channel in range(32)]
    traces['gap'] = pooled
    scores = []
    for class_index in range(10):
        accumulator = model['biases'][bias_offset + class_index]
        accumulator += sum(pooled[channel] * model['weights'][weight_offset + class_index * 32 + channel] for channel in range(32))
        if not -2147483648 <= accumulator <= 2147483647:
            raise ValueError('FC accumulator overflow')
        scores.append(round_shift(accumulator, model['shifts'][3]))
    traces['scores'] = scores
    return traces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--rgb96', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = infer(args.rgb96.read_bytes(), load_model(args.model))
    args.out.mkdir(parents=True, exist_ok=False)
    for name, values in result.items():
        payload = struct.pack('<10i', *values) if name == 'scores' else bytes(value & 255 for value in values)
        (args.out / (name + '.bin')).write_bytes(payload)
    print(json.dumps(dict(scores=result['scores'], prediction=max(range(10), key=lambda class_index: result['scores'][class_index]))))


if __name__ == '__main__':
    main()
