"""PC-side capture and audit tool for the fixed OV5640 -> 96x96 RGB888 preprocessing job.

Usage (see README.md for the full contract):

    python run.py --plan-only
    python run.py --port COM9 --log-dir <new empty path>
    python run.py --verify <evidence directory>
    python run.py --png-check <evidence directory>
    python run.py --selfcheck --out <new empty path>

``--plan-only``, ``--verify``, ``--png-check`` and ``--selfcheck`` never open a serial
port.  The board mode requires ``sim/camera_preprocess/key_20261015_a/board_release.json``
(created by the solution author, never by this tool) and a brand new log directory.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import protocol as pp          # noqa: E402
import reference               # noqa: E402
import session as S            # noqa: E402


def _dump(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def png_check(folder):
    """Read-only: decode every PNG in an evidence directory and compare with the raw."""
    folder = Path(folder)
    report = {'status': 'PNG_PIXEL_DECODE_AND_EXPECTED_RECOMPUTE_CHECK',
              'folder': str(folder), 'png_source': 'standard library zlib/struct only',
              'groups': []}
    for group in (1, 2):
        names = S.artifact_names(group)
        paths = [folder / n for n in names]
        if not paths[0].exists():
            continue
        source, actual, expected = (p.read_bytes() for p in paths[:3])
        S.need(reference.expected_from_source(source) == expected,
               f'group {group}: expected.rgb differs from the independent formula')
        report['groups'].append(dict(group=group, png=[
            pp.png_selfcheck_pixels(paths[3], reference.WIDTH, reference.HEIGHT, source,
                                    raw_height=reference.HEIGHT,
                                    row_bytes=3 * reference.WIDTH),
            pp.png_selfcheck_pixels(paths[4], reference.OUT, reference.OUT, actual),
            pp.png_selfcheck_pixels(paths[5], reference.OUT, reference.OUT, expected)],
            expected_recomputed=True))
    S.need(report['groups'], 'no evidence artifacts found')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--manifest', type=Path, default=S.DEFAULT_MANIFEST,
                        help='frozen firmware manifest (used by --plan-only and board mode)')
    parser.add_argument('--port', default='COM9')
    parser.add_argument('--log-dir', type=Path, help='new directory for a board run')
    parser.add_argument('--plan-only', action='store_true',
                        help='offline plan/identity check; never opens the serial port')
    parser.add_argument('--verify', type=Path,
                        help='read-only replay of an evidence directory')
    parser.add_argument('--png-check', type=Path,
                        help='read-only PNG pixel decode + expected recomputation')
    parser.add_argument('--selfcheck', action='store_true',
                        help='run the offline software acceptance suite')
    parser.add_argument('--out', type=Path, help='new directory for --selfcheck evidence')
    parser.add_argument('--tool-versions', action='store_true')
    args = parser.parse_args(argv)

    if args.tool_versions:
        import zlib
        _dump(dict(python=sys.version, zlib=zlib.ZLIB_VERSION,
                   pyserial=_pyserial_version(),
                   pillow=_pillow_version(), png='standard library zlib/struct only',
                   reference='reference.py bit-replication, no Pillow dependency'))
        return 0

    if args.selfcheck:
        import selfcheck
        S.need(args.out is not None, '--selfcheck requires --out <new empty path>')
        report = selfcheck.run_suite(args.out)
        print(f"selfcheck cases={len(report['cases'])} passed={report['passed']} "
              f"rejected={report['rejected']} accepted={report['accepted']} "
              f"all_passed={report['all_passed']}")
        return 0 if report['all_passed'] else 1

    if args.plan_only:
        _dump(S.plan_only(args.manifest))
        return 0

    if args.verify:
        _dump(S.replay(args.verify, origin='ACTUAL_SERIAL'))
        return 0

    if args.png_check:
        _dump(png_check(args.png_check))
        return 0

    S.need(args.log_dir is not None, 'board mode requires --log-dir <new empty path>')
    S.run_live(args)
    return 0


def _pyserial_version():
    try:
        import serial
        return serial.__version__
    except Exception as exc:                                   # pragma: no cover
        return f'unavailable: {exc!r}'


def _pillow_version():
    try:
        import PIL
        return PIL.__version__
    except Exception:                                          # pragma: no cover
        return 'not installed (not required)'


if __name__ == '__main__':
    raise SystemExit(main())
