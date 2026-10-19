import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def gray32(rgb96):
    sampled = rgb96[1:96:3, 1:96:3].astype(np.int32)
    luminance = (sampled[:, :, 0] * 77 + sampled[:, :, 1] * 150 + sampled[:, :, 2] * 29 + 128) >> 8
    return (luminance - 128).astype(np.int8)


def render(image, randomizer=None):
    side = 80 if randomizer is None else int(randomizer.integers(72, 85))
    resized = image.resize((side, side), Image.Resampling.BICUBIC)
    canvas = Image.new('L', (96, 96), 255)
    offset_x = (96 - side) // 2
    offset_y = offset_x
    if randomizer is not None:
        offset_x += int(randomizer.integers(-4, 5))
        offset_y += int(randomizer.integers(-4, 5))
    canvas.paste(resized, (offset_x, offset_y))
    if randomizer is not None:
        canvas = canvas.rotate(float(randomizer.uniform(-8, 8)), Image.Resampling.BICUBIC, fillcolor=255)
        canvas = ImageEnhance.Contrast(canvas).enhance(float(randomizer.uniform(0.75, 1.15)))
        canvas = ImageEnhance.Brightness(canvas).enhance(float(randomizer.uniform(0.8, 1.0)))
    return np.asarray(canvas.convert('RGB'), dtype=np.uint8)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=20261017)
    parser.add_argument('--variants', type=int, default=4)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    randomizer = np.random.default_rng(args.seed)
    groups = defaultdict(list)
    records = []
    pixels = {}
    for class_index in range(10):
        for path in sorted((args.dataset / str(class_index)).iterdir()):
            if not path.is_file():
                continue
            raw = path.read_bytes()
            with Image.open(path) as opened:
                opened.load()
                if opened.mode != 'L' or opened.size != (28, 28):
                    raise ValueError(f'unexpected input {path}: {opened.mode} {opened.size}')
                image = opened.copy()
            pixel_hash = digest(image.tobytes())
            record = dict(path=path.relative_to(args.dataset).as_posix(), label=class_index,
                          bytes=len(raw), sha256=digest(raw), pixels_sha256=pixel_hash)
            records.append(record)
            groups[pixel_hash].append(record)
            pixels[pixel_hash] = image
    if any(len({record['label'] for record in group}) != 1 for group in groups.values()):
        raise ValueError('identical pixels have conflicting labels')
    splits = {}
    for class_index in range(10):
        keys = sorted(key for key, group in groups.items() if group[0]['label'] == class_index)
        randomizer.shuffle(keys)
        count = len(keys)
        if count < 20:
            raise ValueError(f'insufficient class {class_index}')
        train_end = int(count * 0.6)
        validation_end = train_end + int(count * 0.2)
        for position, key in enumerate(keys):
            splits[key] = 'train' if position < train_end else 'validation' if position < validation_end else 'test'
    arrays = {}
    summaries = {}
    preview = Image.new('RGB', (10 * 100, 4 * 118), 'white')
    draw = ImageDraw.Draw(preview)
    for split in ('train', 'validation', 'test'):
        rgb_images = []
        gray_images = []
        labels = []
        sample_ids = []
        for pixel_hash in sorted(groups):
            if splits[pixel_hash] != split:
                continue
            record = groups[pixel_hash][0]
            rgb = render(pixels[pixel_hash])
            rgb_images.append(rgb)
            gray_images.append(gray32(rgb))
            labels.append(record['label'])
            sample_ids.append(pixel_hash)
        arrays[split + '_rgb96'] = np.stack(rgb_images)
        arrays[split + '_q'] = np.stack(gray_images)
        arrays[split + '_labels'] = np.asarray(labels, dtype=np.int64)
        arrays[split + '_ids'] = np.asarray(sample_ids)
        summaries[split] = dict(count=len(labels), classes=dict(sorted(Counter(labels).items())))
    augmented = []
    augmented_labels = []
    for pixel_hash in sorted(groups):
        if splits[pixel_hash] == 'train':
            for variant in range(args.variants):
                augmented.append(gray32(render(pixels[pixel_hash], randomizer)))
                augmented_labels.append(groups[pixel_hash][0]['label'])
    arrays['augmented_q'] = np.stack(augmented)
    arrays['augmented_labels'] = np.asarray(augmented_labels, dtype=np.int64)
    for class_index in range(10):
        selected = np.flatnonzero(arrays['train_labels'] == class_index)[:4]
        for row_index, image_index in enumerate(selected):
            preview.paste(Image.fromarray(arrays['train_rgb96'][image_index]), (class_index * 100, row_index * 118))
            draw.text((class_index * 100 + 3, row_index * 118 + 98), str(class_index), fill='black')
    preview.save(args.out / 'preview.png')
    np.savez_compressed(args.out / 'dataset.npz', **arrays)
    for record in records:
        record['split'] = splits[record['pixels_sha256']]
    write_json(args.out / 'samples.json', records)
    summary = dict(status='LOCAL_HANDWRITTEN_DATA_PREPARED_NOT_CAMERA_ACCURACY', seed=args.seed,
                   dataset_root=str(args.dataset.resolve()), images=len(records), unique_pixels=len(groups),
                   source_bytes=sum(record['bytes'] for record in records), splits=summaries,
                   augmented_train_count=len(augmented), augmentation_variants=args.variants,
                   preprocessing='28x28 L -> bicubic 80x80 -> centered white 96RGB -> contract gray32',
                   augmentation='train only: side72..84, offset+-4, rotation+-8deg, contrast0.75..1.15, brightness0.8..1',
                   split_unit='exact decoded image hash; writer/session identities unavailable; near duplicates not audited',
                   source_repository='https://gitcode.com/open-source-toolkit/80bfd.git',
                   provenance='Repository README claims Stanford origin; original sample identities not independently established',
                   sha256={name: digest((args.out / name).read_bytes()) for name in ('dataset.npz', 'samples.json', 'preview.png')})
    write_json(args.out / 'dataset.json', summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
