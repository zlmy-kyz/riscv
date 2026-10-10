"""PING-only PC client; does not load or execute a program."""
import argparse
import json
from pathlib import Path
import sys
import time
from protocol import packet, decode_response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--baud', type=int, choices=[115200], default=115200)
    parser.add_argument('--count', type=int, default=1)
    parser.add_argument('--log', type=Path)
    parser.add_argument('command', choices=['ping'])
    args = parser.parse_args()
    if not 1 <= args.count <= 10000: parser.error('--count must be 1..10000')
    try:
        import serial
    except ImportError:
        raise RuntimeError('pyserial is missing; install tools/uart_loader/requirements.txt before board use')
    records = []
    with serial.Serial(args.port, args.baud, timeout=0.1, write_timeout=5) as port:
        # Fixed delay allows an earlier malformed frame recovery to finish.
        time.sleep(0.2)
        port.reset_input_buffer()
        for seq in range(1, args.count + 1):
            request = packet(seq=seq)
            start = time.monotonic()
            if port.write(request) != len(request): raise RuntimeError('short serial write')
            port.flush()
            response = bytearray()
            while len(response) < 60 and time.monotonic() - start < 5:
                response.extend(port.read(60 - len(response)))
            result = decode_response(bytes(response), seq)
            record = {**result, 'tx_hex': request.hex(), 'rx_hex': response.hex(),
                      'seconds': time.monotonic() - start}
            records.append(record)
            if args.log:
                args.log.parent.mkdir(parents=True, exist_ok=True)
                args.log.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
            if result['status']: raise RuntimeError(f'NACK 0x{result["status"]:04x}')
            print(f'PING {seq}: ACK; ROM Loader PING_ONLY; base=0x40000000; '
                  f'max_bin=61440; max_chunk=256; {record["seconds"]:.3f}s')


if __name__ == '__main__':
    try: main()
    except (RuntimeError, ValueError, OSError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)
