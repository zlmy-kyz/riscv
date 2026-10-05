# Assemble separately with existing difftest/golden/rvtool.py, then run here.
set script_dir [pwd]
set repo_dir [file normalize [file join $script_dir ../..]]
onerror {quit -f -code 1}
quit -sim
set work_dir [file join $script_dir soc_uart_cpu_work]
if {![file exists $work_dir]} {vlib $work_dir}
transcript file [file join $script_dir soc_uart_cpu.log]
set sources [list]
foreach name {alu br_alu l_alu regfile csr_file mycpu_sync inst_bus_interconnect
              data_bus_interconnect inst_bram_adapter data_bram_adapter simple_mmio
              dual_sram_to_pango_ddr_bridge uart_tx uart_rx uart_rx_fifo uart_mmio soc_top} {
    lappend sources [file join $repo_dir myriscv ${name}.v]
}
lappend sources [file join $repo_dir difftest model inst_rom.v]
lappend sources [file join $repo_dir difftest model data_ram.v]
lappend sources [file join $repo_dir source tb_soc_uart_cpu.v]
vlog -sv -work $work_dir +incdir+[file join $repo_dir myriscv] {*}$sources
cd [file join $script_dir cpu_image]
vsim -t 1fs -lib $work_dir tb_soc_uart_cpu
onfinish stop
run 3ms
if {[examine -radix unsigned /tb_soc_uart_cpu/test_pass] != 1} {
    echo "RESULT: FAIL soc_uart_cpu: testbench incomplete"
    quit -f -code 1
}
quit -f -code 0
