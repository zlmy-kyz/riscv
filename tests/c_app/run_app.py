"""Build, audit, simulate and optionally UART-download a new C application."""
from pathlib import Path
import argparse
import datetime
import sys
import uuid
import pipeline as app


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path, action='append', help='Repeat for multiple C files; paths must be within the project')
    mode.add_argument('--deploy', type=Path, help='Reuse an already prepared build directory')
    mode.add_argument('--verify-log', type=Path, help='Offline audit of an actual serial log; no serial opened')
    expect = p.add_mutually_exclusive_group()
    expect.add_argument('--expect', help='UTF-8 text required exactly once in application output')
    expect.add_argument('--expect-file', type=Path, help='Exact expected output bytes, including line endings')
    p.add_argument('--prepare', action='store_true', help='Build/audit/full simulation only; never open serial')
    p.add_argument('--log', type=Path, help='New actual board JSON log; default under sim/c_app/board')
    p.add_argument('--sim-max-cycles', type=int, default=40000000, help='Simulation bound including download; default 40 million cycles')
    a = p.parse_args()
    if not 100000 <= a.sim_max_cycles <= 2000000000:
        p.error('--sim-max-cycles must be between 100000 and 2000000000')
    if a.prepare and a.log:
        p.error('--prepare does not create a board log')
    if a.verify_log:
        if a.prepare or a.log or a.expect is not None or a.expect_file:
            p.error('--verify-log cannot be combined with build/download options')
        print(app.verify_log(a.verify_log.resolve()))
        return
    if a.source:
        if a.expect is None and a.expect_file is None:
            p.error('--source requires --expect or --expect-file')
        wanted = a.expect.encode('utf-8') if a.expect is not None else a.expect_file.read_bytes()
        if not wanted or len(wanted) > app.MAX_OUTPUT or b'C_APP_DONE' in wanted:
            p.error('Expected output must be nonempty, <=64 KiB and must not contain reserved C_APP_DONE')
        tag = datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8]
        out = app.build(a.source, wanted, a.expect_file is not None, tag)
        app.prepare_gate(out, a.sim_max_cycles)
    else:
        if a.prepare or a.expect is not None or a.expect_file:
            p.error('--deploy uses the expectation in its prepared manifest')
        out = app.inside(a.deploy)
    if a.prepare:
        return
    log = a.log.resolve() if a.log else app.SIM / 'board' / (out.name + '.json')
    app.deploy(out, log)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('RESULT: FAIL C_APP', error, file=sys.stderr, flush=True)
        sys.exit(1)
