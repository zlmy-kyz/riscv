# IP regeneration restores the Micron model's module name to "ddr3", which
# collides with our generated DDR controller wrapper named "ddr3". Compile
# a derived copy as ddr3_mem in EVERY library, rather than relying on stale
# library units. Never modify the vendor source or its timing checks.
proc compile_ddr3_physical_model {work_name repo_dir} {
    set mem_dir [file join $repo_dir ipcore ddr3 example_design bench mem]
    set input_file [open [file join $mem_dir ddr3.v] r]
    set model [read $input_file]
    close $input_file
    if {![regexp {module\s+ddr3_mem\s*\(} $model]} {
        if {[regsub {module\s+ddr3\s*\(} $model {module ddr3_mem (} model] != 1} {
            error "Cannot identify the regenerated DDR3 physical model module"
        }
    }
    set out_dir [file join $repo_dir sim ddr_physical_model]
    file mkdir $out_dir
    set out_path [file join $out_dir ddr3_mem.v]
    set output_file [open $out_path w]
    puts -nonewline $output_file $model
    close $output_file
    vlog -sv -work $work_name +define+den4096Mb +define+x16 +define+sg25E \
        +incdir+$mem_dir $out_path
}
