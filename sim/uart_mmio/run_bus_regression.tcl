# Existing address/MMIO and instruction/data DDR-path TBs, unchanged test logic.
set script_dir [pwd]
set repo_dir [file normalize [file join $script_dir ../..]]
onerror {quit -f -code 1}
quit -sim
set work_dir [file join $script_dir bus_regression_work]
if {![file exists $work_dir]} {vlib $work_dir}
transcript file [file join $script_dir bus_regression_compile.log]
vlog -sv -work $work_dir \
    [file join $repo_dir myriscv data_bus_interconnect.v] \
    [file join $repo_dir myriscv inst_bus_interconnect.v] \
    [file join $repo_dir myriscv simple_mmio.v] \
    [file join $repo_dir myriscv dual_sram_to_pango_ddr_bridge.v] \
    [file join $repo_dir source tb_data_bus_interconnect.v] \
    [file join $repo_dir source tb_ddr_bus_path.v]
foreach top {tb_data_bus_interconnect tb_ddr_bus_path} {
    vsim -lib $work_dir $top -l [file join $script_dir ${top}.log]
    onfinish stop
    run 1ms
    if {[examine -radix unsigned /${top}/failures] != 0} {
        echo "RESULT: FAIL $top"
        quit -f -code 1
    }
    quit -sim
}
quit -f -code 0
