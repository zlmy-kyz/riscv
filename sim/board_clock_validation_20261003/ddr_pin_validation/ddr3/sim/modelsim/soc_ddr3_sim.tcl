# In ModelSim, cd to this directory, then: do soc_ddr3_sim.tcl
# This uses a separate library and log; it does not delete the vendor work
# library, alter ctrl_phy_sim.tcl, or change the PDS simulation top.
# ModelSim's `do` does not reliably expose this file through [info script].
set script_dir [pwd]
set repo_dir D:/riscv/RISCV
cd $script_dir

quit -sim
if {![file exists soc_ddr3_work]} {
    vlib soc_ddr3_work
}
vmap soc_ddr3_work soc_ddr3_work

set LIB_DIR C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation
vlog -work soc_ddr3_work $LIB_DIR/modelsim10.2c/adc_e2_source_codes/*.vp
vlog -sv -work soc_ddr3_work -mfcu -incr -suppress 2902 \
    -f sim_file_list.f -y $LIB_DIR +libext+.v \
    +incdir+../../example_design/bench/mem/

source [file join $repo_dir sim compile_ddr3_physical_model.tcl]
compile_ddr3_physical_model soc_ddr3_work $repo_dir

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
    [file join $repo_dir myriscv dual_sram_to_pango_ddr_bridge.v] \
    [file join $repo_dir myriscv soc_top.v] \
    [file join $repo_dir myriscv soc_ddr3_top.v] \
    [file join $repo_dir source tb_soc_ddr3_mem.v] \
    [file join $repo_dir source tb_soc_ddr3_top.v]]
vlog -sv -work soc_ddr3_work -mfcu -incr -suppress 2902 \
    +incdir+[file join $repo_dir myriscv] \
    +incdir+../../example_design/bench/mem/ \
    -y $LIB_DIR +libext+.v {*}$rtl_sources

vsim -suppress 3486,3680,3781 +nowarn1 -c -sva \
    -lib soc_ddr3_work tb_soc_ddr3_top -l soc_ddr3_sim.log
run 300us
