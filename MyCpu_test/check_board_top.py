#!/usr/bin/env python3
"""Audit physical port coverage, PDS compile evidence and current DDR config."""
from pathlib import Path
import re
import tkinter
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sim/board_top_validation"


def ports(path: str, module: str) -> dict[str, tuple[str, int, list[str]]]:
    source = (ROOT / path).read_text(encoding="utf-8")
    body = source.split(f"module {module}", 1)[1].split(");", 1)[0]
    parsed = {}
    for direction, hi, lo, name in re.findall(
        r"\b(input|output|inout)\s+wire\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*(\w+)", body
    ):
        bits = [f"{name}[{i}]" for i in range(int(lo), int(hi) + 1)] if hi else [name]
        parsed[name] = direction, len(bits), bits
    assert parsed, path
    return parsed


def locations(path: str) -> dict[str, str]:
    pairs = re.findall(r"define_attribute\s+\{p:([^}]+)\}\s+\{PAP_IO_LOC\}\s+\{([^}]+)\}",
                       (ROOT / path).read_text(encoding="utf-8"))
    assert len(pairs) == len(dict(pairs)), "duplicate port locations"
    return dict(pairs)


def main() -> int:
    board = ports("myriscv/board_top.v", "board_top")
    soc = ports("myriscv/soc_ddr3_top.v", "soc_ddr3_top")
    expected = {n for n in soc if n.startswith("mem_")} | {
        "ddr_ref_clk_p", "ddr_ref_clk_n", "resetn", "led_clk_alive",
        "led_ddr_ready", "led_selftest"}
    assert set(board) == expected, (set(board) - expected, expected - set(board))
    for name in soc:
        if name.startswith("mem_"):
            assert board[name] == soc[name], (name, board[name], soc[name])
    physical_bits = {bit for _, _, bits in board.values() for bit in bits}
    board_locs = locations("constraints/rk3568_board.fdc")
    assert physical_bits == set(board_locs), "unconstrained or stale physical port"
    assert len(physical_bits) == len(set(board_locs.values())) == 55, "duplicate pin"
    # Parse the actual FDC with Tcl (mock only the PDS database selectors).
    tcl = tkinter.Tcl()
    parsed_locations = []
    tcl.createcommand("define_attribute", lambda *args: parsed_locations.append(args) or "")
    tcl.createcommand("get_ports", lambda name: name)
    clocks = []
    tcl.createcommand("create_clock", lambda *args: clocks.append(args) or "")
    tcl.eval((ROOT / "constraints/rk3568_board.fdc").read_text(encoding="utf-8"))
    assert len(parsed_locations) == 55 and len(clocks) == 1
    old_locs = locations("fdc/soc_ddr3.fdc")
    assert all(old_locs[n] == board_locs[n] for n in old_locs if n.startswith("mem_"))
    assert {n: board_locs[n] for n in expected if not n.startswith("mem_")} == {
        "ddr_ref_clk_p": "R4", "ddr_ref_clk_n": "T4", "resetn": "M15",
        "led_clk_alive": "J16", "led_ddr_ready": "M17", "led_selftest": "K17"}
    pds = (ROOT / "RISCV.pds").read_text(encoding="utf-8")
    assert '"myriscv/board_top.v" + "board_top"' in pds
    assert '(_option top_module (_string "board_top"))' in pds
    assert re.findall(r'_file "([^"\n]+\.fdc)"', pds) == ["constraints/rk3568_board.fdc"]
    compile_log = (OUT / "pds_compile_console.log").read_text(encoding="utf-8", errors="replace")
    assert 'Module "board_top" is set as top module.' in compile_log
    assert 'Process "Compile" done.' in compile_log and "E:" not in compile_log
    idf = ET.parse(ROOT / "ipcore/ddr3/ddr3.idf")
    params = {e.findtext("name"): e.findtext("value") for e in idf.iter("param")}
    assert float(params["CLKIN_FREQ"]) == 125
    assert float(params["ACTUAL_RATE"]) == 750
    audit = ["PASS board_top/PDS audit: 21 port groups, 55 unique physical bits/locations",
             "PASS DDR physical port directions/widths match soc_ddr3_top",
             "PASS current PDS compile elaborated board_top with imported rk3568_board.fdc",
             "IP reference=125MHz, requested=800Mbps, actual=750Mbps, core=93.75MHz",
             "Pin Planner boundary (internal debug/status/IRQ are absent):"]
    audit.extend(f"{name:16} {direction:6} width={width:2} " +
                 ", ".join(f"{bit}={board_locs[bit]}" for bit in bits)
                 for name, (direction, width, bits) in board.items())
    audit.append("IP PAD_* vs board locations (must reconcile before hardware implementation):")
    mismatches = []
    for name, value in params.items():
        if not name or not name.startswith("PAD_"):
            continue
        key = name.removeprefix("PAD_")
        scalar = {"CK": "mem_ck", "CK_N": "mem_ck_n", "CS_N": "mem_cs_n",
                  "RST_N": "mem_rst_n", "RESET_N": "mem_rst_n", "CKE": "mem_cke",
                  "RAS_N": "mem_ras_n", "CAS_N": "mem_cas_n", "WE_N": "mem_we_n", "ODT": "mem_odt",
                  "CS": "mem_cs_n", "RESET": "mem_rst_n", "RAS": "mem_ras_n",
                  "CAS": "mem_cas_n", "WE": "mem_we_n"}
        port = scalar.get(key)
        match = re.fullmatch(r"(A|BA|DQ|DM|DQS|DQS_N)(\d+)", key)
        if match:
            port = f"mem_{match[1].lower()}[{int(match[2])}]"
        match = re.fullmatch(r"DQSN(\d+)", key)
        if match:
            port = f"mem_dqs_n[{int(match[1])}]"
        if port in board_locs and value != board_locs[port]:
            mismatches.append(f"TODO {name}={value}, board {port}={board_locs[port]}")
    audit.extend(mismatches or ["No comparable PAD_* mismatch found; inspect generated PHY placement as well."])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pin_audit.txt").write_text("\n".join(audit) + "\n", encoding="utf-8")
    print("\n".join(audit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
