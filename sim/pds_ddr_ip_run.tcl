# PDS Simulation -> Modelsim.simulate.custom_udo
# The isolated ddr_stage ROM/RAM pair contains boot_rom.dat and ld_st.dat.
# Main PDS now runs sim/board_main_selftest/run.tcl with the board images.
set repo_dir D:/riscv/RISCV
set work_name pds_ddr_ip_work
set work_dir [file join $repo_dir sim $work_name]
cd [file join $repo_dir ipcore ddr3 sim modelsim]
quit -sim
vmap $work_name $work_dir
foreach lib_name {usim adc_e2 ddc_e2 dll_e2 hsstlp_lane hsstlp_pll iolhr_dft ipal_e1 ipal_e2 iserdes_e2 oserdes_e2 pciegen2} {
    vmap $lib_name D:/modelsim/pango_sim_libraries/$lib_name
}

vsim -suppress 3486,3680,3781 +nowarn1 -sva \
    -lib $work_name \
    -L usim -L adc_e2 -L ddc_e2 -L dll_e2 \
    -L hsstlp_lane -L hsstlp_pll -L iolhr_dft \
    -L ipal_e1 -L ipal_e2 -L iserdes_e2 -L oserdes_e2 -L pciegen2 \
    tb_soc_ddr3_pds_ip \
    +TEST=ld_st +TOHOST=80002000 +EXPECTED_WRITES=1056 \
    -l [file join $repo_dir sim pds_ddr_ip_ld_st.log]
onfinish stop
run 5ms
quit -sim
