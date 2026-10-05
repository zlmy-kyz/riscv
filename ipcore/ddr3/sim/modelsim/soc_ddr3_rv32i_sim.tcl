# CPU-driven RV32I image loading through the real DDR3 IP and physical model.
# Run build_ddr_stage.py first, then cd here and do this file. For a subset:
#   set rv32i_cases {add lb}; do soc_ddr3_rv32i_sim.tcl
set script_dir [pwd]
set repo_dir [file normalize [file join $script_dir ../../../..]]
set stage_dir [file join $repo_dir MyCpu_test ddr_stage]
cd $script_dir

if {![info exists rv32i_cases]} {
    set fd [open [file join $stage_dir cases.txt] r]
    set rv32i_cases [split [string trim [read $fd]] "\n"]
    close $fd
}
if {[llength $rv32i_cases] == 0} {error "no RV32I cases selected"}
set fd [open [file join $stage_dir tohost.tsv] r]
array set tohost_map [read $fd]
close $fd

quit -sim
if {![file exists soc_ddr3_rv32i_work]} {vlib soc_ddr3_rv32i_work}
vmap soc_ddr3_rv32i_work soc_ddr3_rv32i_work

set LIB_DIR C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation
vlog -work soc_ddr3_rv32i_work $LIB_DIR/modelsim10.2c/adc_e2_source_codes/*.vp
vlog -sv -work soc_ddr3_rv32i_work -mfcu -incr -suppress 2902 \
    -f sim_file_list.f -y $LIB_DIR +libext+.v \
    +incdir+../../example_design/bench/mem/

source [file join $repo_dir sim compile_ddr3_physical_model.tcl]
compile_ddr3_physical_model soc_ddr3_rv32i_work $repo_dir

set rtl_sources [list \
    [file join $repo_dir myriscv alu.v] \
    [file join $repo_dir myriscv br_alu.v] \
    [file join $repo_dir myriscv l_alu.v] \
    [file join $repo_dir myriscv regfile.v] \
    [file join $repo_dir myriscv csr_file.v] \
    [file join $repo_dir myriscv mycpu_sync.v] \
    [file join $repo_dir myriscv inst_bus_interconnect.v] \
    [file join $repo_dir myriscv data_bus_interconnect.v] \
    [file join $repo_dir myriscv inst_bram_adapter.v] \
    [file join $repo_dir myriscv data_bram_adapter.v] \
    [file join $repo_dir myriscv simple_mmio.v] \
    [file join $repo_dir myriscv uart_tx.v] \
    [file join $repo_dir myriscv uart_rx.v] \
    [file join $repo_dir myriscv uart_rx_fifo.v] \
    [file join $repo_dir myriscv uart_mmio.v] \
    [file join $repo_dir myriscv dual_sram_to_pango_ddr_bridge.v] \
    [file join $repo_dir myriscv soc_top.v] \
    [file join $repo_dir myriscv soc_ddr3_top.v] \
    [file join $repo_dir source tb_soc_ddr3_rv32i_mem.v] \
    [file join $repo_dir source tb_soc_ddr3_top.v]]
vlog -sv -work soc_ddr3_rv32i_work -mfcu -incr -suppress 2902 \
    +define+DDR_RV32I \
    +incdir+[file join $repo_dir myriscv] \
    +incdir+../../example_design/bench/mem/ \
    -y $LIB_DIR +libext+.v {*}$rtl_sources

set summary_path [file join $script_dir soc_ddr3_rv32i_summary.txt]
set summary [open $summary_path w]
set pass_count 0
set fail_count 0
foreach test $rv32i_cases {
    set image_path [file join $stage_dir "${test}.dat"]
    if {![file exists $image_path]} {error "missing image: $image_path"}
    if {![info exists tohost_map($test)]} {error "missing tohost for $test"}
    set log_path [file join $script_dir "soc_ddr3_rv32i_${test}.log"]
    quit -sim
    vsim -suppress 3486,3680,3781 +nowarn1 -c -sva \
        -lib soc_ddr3_rv32i_work tb_soc_ddr3_top -l $log_path \
        +BOOT=[file join $stage_dir boot_rom.dat] \
        +IMAGE=$image_path +TEST=$test +TOHOST=$tohost_map($test)
    onfinish stop
    run 5ms
    quit -sim
    set log [open $log_path r]
    set output [read $log]
    close $log
    if {[string first "RESULT: PASS $test DDR RV32I" $output] >= 0 &&
        [string first "RESULT: FAIL" $output] < 0 &&
        [string first "** Error:" $output] < 0 &&
        [string first "** Fatal:" $output] < 0} {
        incr pass_count
        puts $summary "PASS $test $log_path"
    } else {
        incr fail_count
        puts $summary "FAIL $test $log_path"
    }
    flush $summary
}
puts $summary "TOTAL pass=$pass_count fail=$fail_count"
close $summary
puts "RV32I DDR summary: pass=$pass_count fail=$fail_count ($summary_path)"
