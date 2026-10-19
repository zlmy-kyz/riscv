`timescale 1ns/1ps
module tb_mul_ip;
    reg clk=0, rst=1, ce=1;
    reg [32:0] a=0,b=0;
    wire [65:0] p;
    reg [65:0] expected[0:127], held;
    reg [32:0] av[0:127],bv[0:127];
    string vectors;
    integer fd,n,i,j,enabled,checks=0;
    always #5 clk=~clk;
    GTP_GRS GRS_INST(.GRS_N(1'b1));
    mul dut(.clk(clk),.rst(rst),.ce(ce),.a(a),.b(b),.p(p));
    task automatic fail(input string reason);
        $display("RESULT: FAIL mul_ip %s t=%0t p=%h",reason,$time,p); $fatal(1);
    endtask
    initial begin
        if(!$value$plusargs("VECTORS=%s",vectors)) fail("no vectors");
        fd=$fopen(vectors,"r"); if(!fd) fail("open vectors");
        for(n=0;n<128;n=n+1)
            if($fscanf(fd,"%h %h %h\n",av[n],bv[n],expected[n])!=3) fail("vector count");
        $fclose(fd);
        repeat(3) @(negedge clk);
        rst=0; enabled=0;
        // Stream different operands every enabled edge; periodically stop CE mid-pipeline.
        for(i=0;i<131;i=i+1) begin
            if(i<128) begin a=av[i]; b=bv[i]; end else begin a=0;b=0;end
            if(i%7==2) begin
                held=p; ce=0;
                for(j=0;j<2;j=j+1) begin
                    @(posedge clk); #1;
                    if(p!==held) fail("CE hold");
                    checks=checks+1; @(negedge clk);
                end
            end
            ce=1;
            @(posedge clk); #1; enabled=enabled+1;
            if(enabled>=4) begin
                if(p!==expected[enabled-4]) fail($sformatf("latency/product vector=%0d expected=%h",enabled-4,expected[enabled-4]));
                checks=checks+1;
            end
            @(negedge clk);
        end
        // Reset while the pipeline contains nonzero products; then use fresh operands.
        a=33'h1ffffffff; b=33'h100000000;
        repeat(2) @(negedge clk);
        rst=1; repeat(2) @(negedge clk);
        if(p!==66'b0) fail("synchronous reset"); checks=checks+1;
        rst=0; a=33'd3;b=33'd11;
        repeat(4) @(negedge clk);
        if(p!==66'd33) fail("reset recovery"); checks=checks+1;
        $display("CHECK: raw_ip_stream_ce_reset PASS vectors=128 checks=%0d",checks);
        $display("RESULT: PASS mul_ip vectors=128 checks=%0d",checks); $finish;
    end
    initial begin #100000; fail("watchdog"); end
endmodule
