# Run CPU-driven DDR self-test with PDS-generated real on-chip ROM and
# isolated self-test data_ram IP, plus DDR3 IP and x16 physical model.
set repo_dir D:/riscv/RISCV
set work_name board_key_boot_work
set work_dir [file join $repo_dir sim $work_name]
cd [file join $repo_dir ipcore ddr3 sim modelsim]
quit -sim
vmap $work_name $work_dir
foreach lib_name {usim adc_e2 ddc_e2 dll_e2 hsstlp_lane hsstlp_pll iolhr_dft ipal_e1 ipal_e2 iserdes_e2 oserdes_e2 pciegen2} {
    vmap $lib_name D:/modelsim/pango_sim_libraries/$lib_name
}
set manifest_file [open [file join $repo_dir MyCpu_test ddr_selftest manifest.tsv] r]
set manifest_text [read $manifest_file]
close $manifest_file
if {![regexp -line {^ddr_selftest\s+([0-9]+)\s} $manifest_text unused expected_writes]} {
    error "self-test word count missing from manifest.tsv; rebuild images first"
}

vsim -suppress 3486,3680,3781 +nowarn1 -sva \
    -lib $work_name \
    -L usim -L adc_e2 -L ddc_e2 -L dll_e2 \
    -L hsstlp_lane -L hsstlp_pll -L iolhr_dft \
    -L ipal_e1 -L ipal_e2 -L iserdes_e2 -L oserdes_e2 -L pciegen2 \
    tb_board_top_selftest \
    +TEST=ddr_selftest +TOHOST=80001000 +EXPECTED_WRITES=$expected_writes +CHECK_SELFTEST_LED \
    -l [file join $repo_dir sim board_key_boot_validation physical.log]
onfinish stop
run 5ms
quit -sim
