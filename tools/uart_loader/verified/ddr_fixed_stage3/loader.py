"""PING, fixed RAM RX and fixed64 DDR compare; no program download or execution."""
import argparse
import json
from pathlib import Path
import sys
import time
from protocol import packet, decode_response, crc32, FIXED_DATA, RX_TEST, DDR_TEST, DDR_BASE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--baud', type=int, choices=[115200], default=115200)
    parser.add_argument('--count', type=int, default=1)
    parser.add_argument('--log', type=Path)
    parser.add_argument('command', choices=['ping', 'rx-test', 'ddr-test'])
    args = parser.parse_args()
    if not 1 <= args.count <= 10000: parser.error('--count must be 1..10000')
    try:
        import serial
    except ImportError:
        raise RuntimeError('pyserial is missing; install tools/uart_loader/requirements.txt before board use')
    records = []
    command = {'ping': 1, 'rx-test': RX_TEST, 'ddr-test': DDR_TEST}[args.command]
    with serial.Serial(args.port, args.baud, timeout=0.1, write_timeout=5) as port:
        # Fixed delay allows an earlier malformed frame recovery to finish.
        time.sleep(0.2)
        port.reset_input_buffer()
        for seq in range(1, args.count + 1):
            request = packet(cmd=command, seq=seq, address=DDR_BASE if command == DDR_TEST else 0,
                             payload=FIXED_DATA if command != 1 else b'')
            start = time.monotonic()
            if port.write(request) != len(request): raise RuntimeError('short serial write')
            port.flush()
            response = bytearray()
            while len(response) < 60 and time.monotonic() - start < 5:
                response.extend(port.read(60 - len(response)))
            result = decode_response(bytes(response), seq, command)
            record = {**result, 'tx_hex': request.hex(), 'rx_hex': response.hex(),
                      'seconds': time.monotonic() - start}
            records.append(record)
            if args.log:
                args.log.parent.mkdir(parents=True, exist_ok=True)
                args.log.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
            if result['status']: raise RuntimeError(f'NACK 0x{result["status"]:04x}')
            if command == DDR_TEST:
                print(f'DDR_TEST {seq}: ACK; 64 bytes written/read/matched at 0x{DDR_BASE:08x}; '
                      f'{record["seconds"]:.3f}s')
            elif command == RX_TEST:
                print(f'RX_TEST {seq}: ACK; 64 bytes matched in RAM; '
                      f'payload_crc=0x{crc32(FIXED_DATA):08x}; {record["seconds"]:.3f}s')
            else:
                print(f'PING {seq}: ACK; ROM Loader PING_ONLY; base=0x40000000; '
                      f'max_bin=61440; max_chunk=256; {record["seconds"]:.3f}s')


if __name__ == '__main__':
    try: main()
    except (RuntimeError, ValueError, OSError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)
