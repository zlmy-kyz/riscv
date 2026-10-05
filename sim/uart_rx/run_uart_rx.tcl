# Independent RX/FIFO/loopback regression. Run from sim/uart_rx:
# & 'D:/modelsim/win64pe/vsim.exe' -c -do 'do run_uart_rx.tcl'
set script_dir [pwd]
set repo_dir [file normalize [file join $script_dir ../..]]
onerror {quit -f -code 1}
quit -sim
set work_dir [file join $script_dir uart_rx_work]
if {![file exists $work_dir]} {vlib $work_dir}
transcript file [file join $script_dir uart_rx.log]
vlog -sv -work $work_dir \
    [file join $repo_dir myriscv uart_tx.v] \
    [file join $repo_dir myriscv uart_rx.v] \
    [file join $repo_dir myriscv uart_rx_fifo.v] \
    [file join $repo_dir source tb_uart_rx.v]
vsim -t 1fs -lib $work_dir tb_uart_rx
onfinish stop
run 20ms
if {[examine -radix unsigned /tb_uart_rx/test_pass] != 1} {
    echo "RESULT: FAIL uart_rx: testbench did not complete successfully"
    quit -f -code 1
}
quit -f -code 0
