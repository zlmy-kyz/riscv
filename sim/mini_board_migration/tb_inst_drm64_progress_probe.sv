`timescale 1ns/1ps
// Diagnostic-only second top: observes the original TB without driving any signal.
// Original RTL/TB/checks/watchdog are unchanged. Flushes a separate file so a
// killed native simulator cannot hide all progress behind a stdout pipe.
module tb_inst_drm64_progress_probe;
    integer progress_file;
    initial begin
        progress_file=$fopen("hdl_progress.log","w");
        if (progress_file==0) $fatal(1,"DIAGNOSTIC FILE OPEN ERROR");
        $fdisplay(progress_file,"PROBE_START time_ns=%0d checks=%0d",$time,tb_inst_drm64_x32.tests);
        $fflush(progress_file);
        forever begin
            #10000;
            $fdisplay(progress_file,"PROGRESS time_ns=%0d checks=%0d state=%0d AR=%0d AW=%0d",
                $time,tb_inst_drm64_x32.tests,tb_inst_drm64_x32.dut.state,
                tb_inst_drm64_x32.ar_count,tb_inst_drm64_x32.aw_count);
            $fflush(progress_file);
        end
    end
endmodule
