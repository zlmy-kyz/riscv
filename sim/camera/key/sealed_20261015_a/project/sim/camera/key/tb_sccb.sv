`timescale 1ns/1ps
module tb_camera_sccb;
    GTP_GRS GRS_INST(.GRS_N(1'b1));
    reg clk=0, resetn=0;
    always #5.333 clk=~clk;
    tri1 scl,sda;
    wire sl,dl,sensor_resetn,done,error;
    wire [7:0] code,index;
    wire [15:0] id;
    integer injection=0,writes,reads,k;
    assign scl=sl ? 1'b0 : 1'bz;
    assign sda=dl ? 1'b0 : 1'bz;
    ov5640_config #(.CLK_HZ(1600000)) dut(.clk(clk),.resetn(resetn),.scl_in(scl),.sda_in(sda),
        .scl_low(sl),.sda_low(dl),.sensor_resetn(sensor_resetn),.config_done(done),
        .config_error(error),.config_error_code(code),.sensor_id(id),.config_index(index));
    camera_sensor sensor(.resetn(resetn),.scl(scl),.sda(sda),.injection(injection),.writes(writes),.reads(reads));
    initial begin
        for(k=0;k<7;k=k+1) begin
            @(negedge clk);resetn=0;injection=k;
            repeat(8) @(negedge clk);
            resetn=1;
            repeat(16000) begin @(posedge clk); if(sensor_resetn) $fatal(1,"RESULT: FAIL early RESETB release"); end
            wait(done || error); @(negedge clk);
            if(k==0) begin
                if(!done || error || id!=16'h5640 || writes!=244 || reads!=8 || index!=243)
                    $fatal(1,"RESULT: FAIL normal config done=%b error=%b writes=%0d reads=%0d",done,error,writes,reads);
            end else if(done || !error || code!=(k<=4 ? 1 : k==5 ? 6 : 7))
                $fatal(1,"RESULT: FAIL config injected fault %0d code=%0d",k,code);
            repeat(1000) @(negedge clk);
            if(k==0 && (writes!=244 || reads!=8)) $fatal(1,"RESULT: FAIL extra config transactions");
            $display("CASE SCCB %0d %0d %0d %0d",k,writes,reads,code);
        end
        $display("RESULT: PASS camera_sccb");$finish;
    end
    initial begin #200000000; $fatal(1,"RESULT: FAIL SCCB timeout"); end
endmodule
