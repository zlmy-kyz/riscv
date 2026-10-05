# Step-2 full DDR3 regression. In ModelSim, cd here and:
#   do soc_ddr3_regress_sim.tcl
# Uses a separate library/log. The step-1 soc_ddr3_sim.tcl remains unchanged.
set script_dir [pwd]
set repo_dir [file normalize [file join $script_dir ../../../..]]
cd $script_dir

quit -sim
if {![file exists soc_ddr3_regress_work]} {
    vlib soc_ddr3_regress_work
}
vmap soc_ddr3_regress_work soc_ddr3_regress_work

set LIB_DIR C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation
vlog -work soc_ddr3_regress_work $LIB_DIR/modelsim10.2c/adc_e2_source_codes/*.vp
vlog -sv -work soc_ddr3_regress_work -mfcu -incr -suppress 2902 \
    -f sim_file_list.f -y $LIB_DIR +libext+.v \
    +incdir+../../example_design/bench/mem/

source [file join $repo_dir sim compile_ddr3_physical_model.tcl]
compile_ddr3_physical_model soc_ddr3_regress_work $repo_dir

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
    [file join $repo_dir source tb_soc_ddr3_mem.v] \
    [file join $repo_dir source tb_soc_ddr3_top.v]]
vlog -sv -work soc_ddr3_regress_work -mfcu -incr -suppress 2902 \
    +define+DDR_REGRESSION \
    +incdir+[file join $repo_dir myriscv] \
    +incdir+../../example_design/bench/mem/ \
    -y $LIB_DIR +libext+.v {*}$rtl_sources

vsim -suppress 3486,3680,3781 +nowarn1 -c -sva \
    -lib soc_ddr3_regress_work tb_soc_ddr3_top -l soc_ddr3_regress_sim.log
run 300us
