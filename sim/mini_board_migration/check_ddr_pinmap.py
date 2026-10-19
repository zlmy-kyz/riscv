"""Compare generated DDR IP pin locations with the MINI-(200H) board FDC."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
BOARD_FDC = ROOT / "constraint_check/temp_constraint_file.fdc"
IP_FDC = ROOT / "ipcore/ddr3/pnr/ddr_test.fdc"


def locations(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    pairs = re.findall(
        r"^\s*define_attribute \{p:(mem_[^}]+)\} \{PAP_IO_LOC\} \{([^}]+)\}",
        text,
        flags=re.MULTILINE,
    )
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError(f"Duplicate DDR LOC declarations in {path}")
    if len(set(result.values())) != len(result):
        raise ValueError(f"Multiple DDR signals share a physical pin in {path}")
    return result


def main() -> int:
    try:
        board = locations(BOARD_FDC)
        ip = locations(IP_FDC)
    except ValueError as exc:
        print(f"RESULT: FAIL {exc}")
        return 1
    if len(board) != 71 or len(ip) != 71 or board.keys() != ip.keys():
        print(f"RESULT: FAIL DDR signal set, board={len(board)} IP={len(ip)}")
        return 1
    mismatches = [(name, ip[name], board[name]) for name in board if ip[name] != board[name]]
    for name, actual, wanted in sorted(mismatches):
        print(f"{name}: IP={actual}, board={wanted}")
    if mismatches:
        print(f"RESULT: FAIL {len(mismatches)} DDR pin location mismatches")
        return 1
    print("RESULT: PASS all 71 DDR pin locations match the MINI-(200H) board FDC")
    return 0


if __name__ == "__main__":
    sys.exit(main())
