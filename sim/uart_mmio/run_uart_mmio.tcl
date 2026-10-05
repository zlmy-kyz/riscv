# Run from sim/uart_mmio. No vendor libraries needed for bus-level validation.
set script_dir [pwd]
set repo_dir [file normalize [file join $script_dir ../..]]
onerror {quit -f -code 1}
quit -sim
set work_dir [file join $script_dir uart_mmio_work]
if {![file exists $work_dir]} {vlib $work_dir}
transcript file [file join $script_dir uart_mmio.log]
vlog -sv -work $work_dir \
    [file join $repo_dir myriscv data_bus_interconnect.v] \
    [file join $repo_dir myriscv simple_mmio.v] \
    [file join $repo_dir myriscv uart_tx.v] \
    [file join $repo_dir myriscv uart_rx.v] \
    [file join $repo_dir myriscv uart_rx_fifo.v] \
    [file join $repo_dir myriscv uart_mmio.v] \
    [file join $repo_dir source tb_uart_mmio.v]
vsim -t 1fs -lib $work_dir tb_uart_mmio
onfinish stop
run 10ms
if {[examine -radix unsigned /tb_uart_mmio/test_pass] != 1} {
    echo "RESULT: FAIL uart_mmio: testbench incomplete"
    quit -f -code 1
}
quit -f -code 0
