from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib
from pathlib import Path
import time
import urllib.request


URL = 'https://download.pytorch.org/whl/cu128/torch-2.7.1%2Bcu128-cp313-cp313-win_amd64.whl'
EXPECTED_SHA256 = '500ad5b670483f62d4052e41948a3fb19e8c8de65b99f8d418d879cbb15a82d6'
TOTAL_BYTES = 3273029450
CHUNK_BYTES = 32 * 1024 * 1024
FOLDER = Path('sim/cnn/training/wheels_20261017_a')
NAME = 'torch-2.7.1+cu128-cp313-cp313-win_amd64.whl'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--workers', type=int, default=24)
    args = parser.parse_args()
    FOLDER.mkdir(parents=True, exist_ok=args.resume)
    temporary = FOLDER / (NAME + '.part')
    if not args.resume:
        with temporary.open('xb') as stream:
            stream.truncate(TOTAL_BYTES)
    elif temporary.stat().st_size != TOTAL_BYTES:
        raise ValueError('partial file length')
    started = time.monotonic()
    pending = []
    reused = 0
    with temporary.open('rb') as stream:
        for start in range(0, TOTAL_BYTES, CHUNK_BYTES):
            end = min(TOTAL_BYTES, start + CHUNK_BYTES)
            stream.seek(start)
            first = stream.read(64)
            stream.seek(end - 64)
            last = stream.read(64)
            if args.resume and any(first) and any(last):
                reused += end - start
            else:
                pending.append(start)
    print(f'provisionally_reused={reused} pending_chunks={len(pending)}; final official SHA256 mandatory', flush=True)

    def download(start):
        end = min(TOTAL_BYTES, start + CHUNK_BYTES) - 1
        request = urllib.request.Request(URL, headers={'Range': f'bytes={start}-{end}'})
        with urllib.request.urlopen(request, timeout=30) as response:
            expected_range = f'bytes {start}-{end}/{TOTAL_BYTES}'
            if response.status != 206 or response.headers.get('Content-Range') != expected_range:
                raise ValueError('unexpected range response: ' + str(response.headers))
            payload = response.read()
        if len(payload) != end - start + 1:
            raise ValueError('incomplete range')
        with temporary.open('r+b') as stream:
            stream.seek(start)
            stream.write(payload)
        return len(payload)

    completed = reused
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(download, start) for start in pending]
        for count, future in enumerate(as_completed(futures), 1):
            completed += future.result()
            if count % 10 == 0 or completed == TOTAL_BYTES:
                print(f'downloaded={completed}/{TOTAL_BYTES} elapsed={time.monotonic() - started:.1f}s', flush=True)
    with temporary.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    if checksum != EXPECTED_SHA256:
        raise ValueError('wheel SHA256 does not match official index')
    temporary.rename(FOLDER / NAME)
    print('OFFICIAL_WHEEL_SHA256_MATCH ' + checksum, flush=True)


if __name__ == '__main__':
    main()
