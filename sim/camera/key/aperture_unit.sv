`timescale 1ns/1ps
// Boundary/access checks use the real decode logic, with constant ready slaves.
module camera_aperture_unit(output reg done=0);
    reg clk=0,resetn=0,v=0,writing=0,cam_busy=0;
    reg[31:0]addr=0;
    always #5.333 clk=~clk;
    wire ir,iv,ie,idv,dr,dv,de,ddv,cv;
    inst_bus_interconnect #(.ROM_BASE(0),.ENABLE_DDR(1),.ENABLE_CAMERA(1)) inst(
        .clk(clk),.resetn(resetn),.m_req_valid(v),.m_req_addr(addr),.m_req_ready(ir),
        .m_rsp_valid(iv),.m_rsp_error(ie),.rom_req_ready(1'b1),.rom_rsp_valid(1'b1),
        .rom_rsp_rdata(32'b0),.rom_rsp_error(1'b0),.ddr_req_valid(idv),.ddr_req_ready(1'b1),
        .ddr_rsp_valid(1'b1),.ddr_rsp_rdata(32'b0),.ddr_rsp_error(1'b0));
    data_bus_interconnect #(.RAM_BASE(0),.ENABLE_DDR(1),.ENABLE_CAMERA(1),.ENABLE_UART(1)) data(
        .clk(clk),.resetn(resetn),.m_req_valid(v),.m_req_write(writing),.m_req_size(2'd2),
        .m_req_addr(addr),.m_req_wdata(32'b0),.m_req_wstrb(4'hf),.m_req_ready(dr),
        .m_rsp_valid(dv),.m_rsp_error(de),.camera_busy(cam_busy),.ddr_write_buffer_busy(1'b0),
        .ram_req_ready(1'b1),.ram_rsp_valid(1'b1),.ram_rsp_rdata(32'b0),.ram_rsp_error(1'b0),
        .mmio_req_ready(1'b1),.mmio_rsp_valid(1'b1),.mmio_rsp_rdata(32'b0),.mmio_rsp_error(1'b0),
        .uart_req_ready(1'b1),.uart_rsp_valid(1'b1),.uart_rsp_rdata(32'b0),.uart_rsp_error(1'b0),
        .cam_req_valid(cv),.cam_req_ready(1'b1),.cam_rsp_valid(1'b1),.cam_rsp_rdata(32'b0),.cam_rsp_error(1'b0),
        .ddr_req_valid(ddv),.ddr_req_ready(1'b1),.ddr_rsp_valid(1'b1),.ddr_rsp_rdata(32'b0),.ddr_rsp_error(1'b0));
    task automatic probe(input[31:0]a,input integer busy,wr,inst_error,data_error,cam);
        begin
            @(negedge clk);v=1;addr=a;cam_busy=busy;writing=wr;
            #0.001;
            if(!ir || !dr || idv===inst_error[0] || cv!==cam[0] || (data_error && ddv))
                $fatal(1,"RESULT: FAIL aperture route %h",a);
            @(posedge clk);@(negedge clk);v=0;
            if(!iv || !dv || ie!==inst_error[0] || de!==data_error[0])
                $fatal(1,"RESULT: FAIL aperture response %h",a);
            $display("APERTURE %08h %0d %0d %0d %0d",a,busy,wr,inst_error,data_error);
            @(negedge clk);
        end
    endtask
    initial begin
        repeat(8)@(negedge clk);resetn=1;
        probe(32'h41000000,0,0,1,0,0);
        probe(32'h411ffffc,0,0,1,0,0);
        probe(32'h41000000,1,0,1,1,0);
        probe(32'h411ffffc,1,1,1,1,0);
        probe(32'h40fffffc,1,0,0,0,0);
        probe(32'h41200000,1,1,0,0,0);
        probe(32'h10002000,0,0,1,0,1);
        probe(32'h1000203c,0,0,1,0,1);
        probe(32'h10002040,0,0,1,1,0);
        done=1;
    end
endmodule
