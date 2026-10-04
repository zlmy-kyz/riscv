# Board 0x40000000 self-test: real ROM/RAM from D:/riscv/RISCV/ipcore
set repo_dir D:/riscv/RISCV
set ddr_sim_dir [file join $repo_dir ipcore ddr3 sim modelsim]
set vendor_lib_dir C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation
set selftest_ram {D:/riscv/RISCV/ipcore/data_ram}
set selftest_rom {D:/riscv/RISCV/ipcore/inst_rom}
set work_name board_top_physical_work
set work_dir [file join $repo_dir sim $work_name]

cd $ddr_sim_dir
quit -sim
if {![file exists $work_dir]} {vlib $work_dir}
vmap $work_name $work_dir
foreach lib_name {usim adc_e2 ddc_e2 dll_e2 hsstlp_lane hsstlp_pll iolhr_dft ipal_e1 ipal_e2 iserdes_e2 oserdes_e2 pciegen2} {
    vmap $lib_name D:/modelsim/pango_sim_libraries/$lib_name
}

vlog -work $work_name $vendor_lib_dir/modelsim10.2c/adc_e2_source_codes/*.vp
vlog -sv -work $work_name -mfcu -incr -suppress 2902 \
    -f sim_file_list.f -y $vendor_lib_dir +libext+.v \
    +incdir+../../example_design/bench/mem/

source [file join $repo_dir sim compile_ddr3_physical_model.tcl]
compile_ddr3_physical_model $work_name $repo_dir

set cpu_sources [list]
foreach name {
    alu.v br_alu.v l_alu.v regfile.v csr_file.v mycpu_sync.v
    inst_bus_interconnect.v data_bus_interconnect.v
    inst_bram_adapter.v data_bram_adapter.v simple_mmio.v
    dual_sram_to_pango_ddr_bridge.v soc_top.v soc_ddr3_top.v board_top.v reset_button_debounce.v
} {
    lappend cpu_sources [file join $repo_dir myriscv $name]
}
set onchip_ip_sources [list \
    [file join $selftest_rom rtl ipm2l_rom_v1_8_inst_rom.v] \
    [file join $selftest_rom rtl ipm2l_spram_v1_8_inst_rom.v] \
    [file join $selftest_rom inst_rom.v] \
    [file join $selftest_ram rtl ipm2l_spram_v1_8_data_ram.v] \
    [file join $selftest_ram data_ram.v]]

vlog -sv -work $work_name -mfcu -incr -suppress 2902 \
    +define+DDR_RV32I \
    +incdir+[file join $repo_dir myriscv] \
    +incdir+[file join $selftest_rom rtl] \
    +incdir+[file join $selftest_ram rtl] \
    +incdir+../../example_design/bench/mem/ \
    -y $vendor_lib_dir +libext+.v \
    {*}$cpu_sources {*}$onchip_ip_sources \
    [file join $repo_dir sim board_main_selftest tb_board_top_selftest.v]
