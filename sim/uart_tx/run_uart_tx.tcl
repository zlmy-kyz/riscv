# Independent ModelSim regression. From the repository root in PowerShell:
# cd sim/uart_tx
# & 'D:/modelsim/win64pe/vsim.exe' -c -do 'do run_uart_tx.tcl'
# No SoC/vendor sources or changes to the PDS simulation entry.
set script_dir [pwd]
set repo_dir [file normalize [file join $script_dir ../..]]
onerror {quit -f -code 1}
quit -sim
# Address the isolated library by path; no modelsim.ini mappings are changed.
set work_dir [file join $script_dir uart_tx_work]
if {![file exists $work_dir]} {vlib $work_dir}
transcript file [file join $script_dir uart_tx.log]
vlog -sv -work $work_dir \
    [file join $repo_dir myriscv uart_tx.v] \
    [file join $repo_dir source tb_uart_tx.v]
vsim -t 1fs -lib $work_dir tb_uart_tx
onfinish stop
run 3ms
if {[examine -radix unsigned /tb_uart_tx/test_pass] != 1} {
    echo "RESULT: FAIL uart_tx: testbench did not complete successfully"
    quit -f -code 1
}
quit -f -code 0
