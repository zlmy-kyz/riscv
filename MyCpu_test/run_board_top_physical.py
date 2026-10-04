#!/usr/bin/env python3
"""Exercise board_top + real on-chip IP + DDR physical model at 125 MHz.

Reuse the current self-test testbench/checkers, adapting only its boundary.
Uses board_top's default DDR address and the selected real ROM/RAM IP pair.
Only KEY_DEBOUNCE_CYCLES is accelerated; hardware defaults stay unchanged.
"""
from pathlib import Path
import argparse
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sim" / "board_main_selftest"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boot-smoke", action="store_true",
                        help="Check key bounce, DDR init, loader/fetch and MMIO RUN; stop before full self-test.")
    parser.add_argument("--ip-root", type=Path, default=ROOT / "ipcore")
    parser.add_argument("--prepare-only", action="store_true", help="Write reusable ModelSim Tcl/TB files without running.")
    args = parser.parse_args()
    out = ROOT / "sim/board_key_boot_validation" if args.boot_smoke else OUT
    work_name = "board_key_boot_work" if args.boot_smoke else "board_top_physical_work"
    ip_root = args.ip_root.resolve()
    if ip_root != ROOT / "ipcore":
        out = ROOT / "sim/board_main_selftest_candidate"
        work_name = "board_main_candidate_work"
    out.mkdir(parents=True, exist_ok=True)
    tb = (ROOT / "source/tb_soc_ddr3_pds_ip.v").read_text(encoding="utf-8")
    tb = tb.replace("module tb_soc_ddr3_pds_ip;", "module tb_board_top_selftest;")
    tb = tb.replace("soc_ddr3_top #(", "board_top #(")
    old_instance = "board_top #(.RESET_PC(32'h0000_0000),\n                   .DDR_BASE(32'h8000_0000)) dut"
    assert old_instance in tb
    tb = tb.replace(old_instance, "board_top #() dut", 1)
    # Accelerate only the board debounce interval; DDR/CPU timing stays real.
    # The independent debounce regression checks the hardware 20 ms default.
    tb = tb.replace("board_top #(", "board_top #(.KEY_DEBOUNCE_CYCLES(8), ")
    assert ".KEY_DEBOUNCE_CYCLES(8)" in tb
    tb = tb.replace(".KEY_DEBOUNCE_CYCLES(8), )", ".KEY_DEBOUNCE_CYCLES(8))")
    tb = tb.replace("32'h8000_0000", "32'h4000_0000")
    tb = tb.replace("#50 resetn = 1'b1;",
                    "#50 resetn = 1'b1;\n"
                    "        #20 resetn = 1'b0;\n"
                    "        #5 resetn = 1'b1;\n"
                    "        #25 resetn = 1'b0;\n"
                    "        #3 resetn = 1'b1;", 1)
    tb = tb.replace("dut.", "dut.u_soc.")
    tb = tb.replace(".ddr_ref_clk(ddr_ref_clk),",
                    ".ddr_ref_clk_p(ddr_ref_clk), .ddr_ref_clk_n(~ddr_ref_clk),")
    for name in ("irq_external", "irq_software", "irq_timer", "core_clk",
                 "ddr_init_done", "soc_resetn", "debug_wb_pc", "debug_inst",
                 "debug_wb_rf_we", "debug_wb_rf_wnum", "debug_wb_rf_wdata"):
        tb, count = re.subn(r"^\s*\." + name + r"\([^\n]*\),\n", "", tb, flags=re.M)
        assert count == 1, (name, count)
    aliases = "\n".join(f"    assign {name} = dut.{name};" for name in
                        ("core_clk", "ddr_init_done", "soc_resetn", "debug_wb_pc",
                         "debug_inst", "debug_wb_rf_we", "debug_wb_rf_wnum",
                         "debug_wb_rf_wdata"))
    checks = '''
    integer key_release_count = 0;
    realtime key_last_release = 0;
    always @(posedge resetn) key_last_release = $realtime;
    always @(posedge dut.key_resetn) begin
        key_release_count = key_release_count + 1;
        if ($realtime - key_last_release < 64.0)
            $fatal(1, "board reset escaped release bounce");
    end
    initial begin : board_clock_checks
        realtime t0, t1;
        repeat (4) begin
            @(posedge ddr_ref_clk); #0.01;
            if (dut.ddr_ref_clk !== ddr_ref_clk) $fatal(1, "board P buffer");
            @(negedge ddr_ref_clk); #0.01;
            if (dut.ddr_ref_clk !== ddr_ref_clk) $fatal(1, "board N buffer");
        end
        if ({dut.u_soc.irq_external, dut.u_soc.irq_software,
             dut.u_soc.irq_timer} !== 3'b000) $fatal(1, "board IRQ tie-off");
        wait (soc_resetn);
        @(posedge core_clk); t0 = $realtime;
        @(posedge core_clk); t1 = $realtime;
        if (t1-t0 < 10.65 || t1-t0 > 10.68) $fatal(1, "board core period %f", t1-t0);
        @(posedge mem_ck); t0 = $realtime;
        @(posedge mem_ck); t1 = $realtime;
        if (t1-t0 < 2.65 || t1-t0 > 2.68) $fatal(1, "board DDR CK period %f", t1-t0);
        $display("CHECK: board_top differential buffer, IRQ=0, core=93.75MHz, DDR=750Mbps");
    end
'''
    smoke_checks = ""
    if args.boot_smoke:
        smoke_checks = '''
    initial begin : board_boot_smoke
        wait (saw_ddr_fetch && saw_selftest_run);
        #1;
        if (!ddr_init_done || !soc_resetn || !led_ddr_ready || key_release_count != 1)
            $fatal(1, "board key/DDR boot sequence");
        $display("RESULT: PASS board key bounce, DDR init, 245-word loader/fetch and MMIO RUN");
        $finish;
    end
'''
    tb = tb.replace("    // Same command/address", aliases + "\n" + checks + "\n    // Same command/address", 1)
    if smoke_checks:
        # ModelSim requires these procedural references after the TB's
        # DDR_RV32I variable declarations.
        pos = tb.rfind("endmodule")
        assert pos >= 0
        tb = tb[:pos] + smoke_checks + tb[pos:]
    assert "assign core_clk = dut.core_clk;" in tb
    (out / "tb_board_top_selftest.v").write_text(tb, encoding="utf-8")
    compile_tcl = (ROOT / "sim/pds_ddr_selftest_compile.tcl").read_text(encoding="utf-8")
    compile_tcl = ("# Board 0x40000000 self-test: real ROM/RAM from " + ip_root.as_posix() + "\n" +
                   compile_tcl[compile_tcl.index("set repo_dir"):])
    # This run validates the board images rather than the legacy 0x80000000
    # isolated self-test. Both IP include directories must follow the pair.
    compile_tcl = compile_tcl.replace("[file join $repo_dir MyCpu_test ddr_selftest ipcore data_ram]",
                                      "{" + (ip_root / "data_ram").as_posix() + "}")
    compile_tcl = compile_tcl.replace("[file join $repo_dir MyCpu_test ddr_selftest ipcore inst_rom]",
                                      "{" + (ip_root / "inst_rom").as_posix() + "}")
    compile_tcl = compile_tcl.replace("pds_ddr_selftest_work", work_name)
    compile_tcl = compile_tcl.replace("soc_top.v soc_ddr3_top.v", "soc_top.v soc_ddr3_top.v board_top.v reset_button_debounce.v")
    compile_tcl = compile_tcl.replace("[file join $repo_dir source tb_soc_ddr3_pds_ip.v]",
                                    f"[file join $repo_dir sim {out.name} tb_board_top_selftest.v]")
    run_tcl = (ROOT / "sim/pds_ddr_selftest_run.tcl").read_text(encoding="utf-8")
    run_tcl = ("# Board default address, 0x40001000 tohost, CPU loads DDR itself.\n" +
               run_tcl[run_tcl.index("set repo_dir"):])
    run_tcl = run_tcl.replace("MyCpu_test ddr_selftest manifest.tsv", "MyCpu_test board_selftest manifest.tsv")
    run_tcl = run_tcl.replace("+TOHOST=80001000", "+TOHOST=40001000")
    run_tcl = run_tcl.replace("pds_ddr_selftest_work", work_name)
    run_tcl = run_tcl.replace("tb_soc_ddr3_pds_ip", "tb_board_top_selftest")
    run_tcl = run_tcl.replace("[file join $repo_dir sim pds_ddr_selftest.log]",
                            f"[file join $repo_dir sim {out.name} physical.log]")
    (out / "compile.tcl").write_text(compile_tcl, encoding="utf-8")
    (out / "run.tcl").write_text(run_tcl, encoding="utf-8")
    if args.prepare_only:
        print(f"PREPARED {out / 'compile.tcl'} and {out / 'run.tcl'}")
        return 0
    with (out / "console.log").open("w", encoding="utf-8") as log:
        cmd = ["D:/modelsim/win64pe/vsim.exe", "-c", "-do",
               f"do {out.as_posix()}/compile.tcl; do {out.as_posix()}/run.tcl; quit -f"]
        run = subprocess.run(cmd, cwd=ROOT / "ipcore/ddr3/sim/modelsim",
                             stdout=log, stderr=subprocess.STDOUT)
    output = (out / "physical.log").read_text(encoding="utf-8", errors="replace")
    console = (out / "console.log").read_text(encoding="utf-8", errors="replace")
    ok = (run.returncode == 0 and output.count("RESULT: PASS") == 1 and
          "RESULT: FAIL" not in output and "Errors: 0," in output and
          "** Error" not in console and "** Fatal" not in console and
          "CHECK: board_top differential buffer" in output and
          ("CHECK: MMIO selftest RUN" if args.boot_smoke else "CHECK: MMIO selftest PASS LED=1") in output)
    print("PASS" if ok else "FAIL", "board_top physical boot smoke:" if args.boot_smoke else "board_top physical self-test:", out / "physical.log")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
