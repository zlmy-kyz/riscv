import importlib.util
import json
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'tools/cnn_digits_training/integer_reference.py'
specification = importlib.util.spec_from_file_location('handwritten_integer_reference', SOURCE)
integer = importlib.util.module_from_spec(specification)
specification.loader.exec_module(integer)
MODEL_ID = '4c8b5aca'
MODEL_CRC = 0xb9749177


def load(folder):
    model = integer.load_model(folder)
    metadata = model['metadata']
    if metadata['model_id_hex'] != MODEL_ID or metadata['load_crc32'] != MODEL_CRC:
        raise ValueError('wrong fixed handwritten model')
    model['meta'] = metadata
    model['words'] = list(struct.unpack('<6222I', (Path(folder) / 'load_words.bin').read_bytes()))
    return model


def infer(rgb, model):
    traces = integer.infer(rgb, model)
    scores = traces.pop('scores')
    return dict(layers=traces, scores=scores,
                prediction=max(range(10), key=lambda class_index: scores[class_index]))


def save_trace(folder, result):
    folder = Path(folder)
    folder.mkdir(exist_ok=False)
    for name, values in result['layers'].items():
        (folder / (name + '.bin')).write_bytes(bytes(value & 255 for value in values))
    (folder / 'scores.bin').write_bytes(struct.pack('<10i', *result['scores']))
    (folder / 'reference.json').write_text(json.dumps(dict(scores=result['scores'], prediction=result['prediction']), indent=2) + '\n')
