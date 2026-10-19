`timescale 1ns/1ps
module double_aperture(output reg done=0);
    reg clk=0,rst=0,v=0,w=0;reg[31:0]a=0;reg[1:0]owned=0;reg busy=0,dual=1;
    always #5.333 clk=~clk;
    wire ir,iv,ie,idv,dr,dv,de,ddv,cv;
    inst_bus_interconnect #(.ROM_BASE(0),.ENABLE_DDR(1),.ENABLE_CAMERA(1)) inst(
        .clk(clk),.resetn(rst),.m_req_valid(v),.m_req_addr(a),.m_req_ready(ir),.m_rsp_valid(iv),.m_rsp_error(ie),
        .rom_req_ready(1'b1),.rom_rsp_valid(1'b1),.rom_rsp_rdata(32'b0),.rom_rsp_error(1'b0),
        .ddr_req_valid(idv),.ddr_req_ready(1'b1),.ddr_rsp_valid(1'b1),.ddr_rsp_rdata(32'b0),.ddr_rsp_error(1'b0));
    data_bus_interconnect #(.RAM_BASE(0),.ENABLE_DDR(1),.ENABLE_CAMERA(1),.ENABLE_UART(1)) data(
        .clk(clk),.resetn(rst),.m_req_valid(v),.m_req_write(w),.m_req_size(2'b00),.m_req_addr(a),.m_req_wdata(32'b0),.m_req_wstrb(4'b1),
        .m_req_ready(dr),.m_rsp_valid(dv),.m_rsp_error(de),.camera_busy(busy),.camera_dual_mode(dual),.camera_cpu_owned(owned),.ddr_write_buffer_busy(1'b0),
        .ram_req_ready(1'b1),.ram_rsp_valid(1'b1),.ram_rsp_rdata(32'b0),.ram_rsp_error(1'b0),
        .mmio_req_ready(1'b1),.mmio_rsp_valid(1'b1),.mmio_rsp_rdata(32'b0),.mmio_rsp_error(1'b0),
        .uart_req_ready(1'b1),.uart_rsp_valid(1'b1),.uart_rsp_rdata(32'b0),.uart_rsp_error(1'b0),
        .ddr_req_valid(ddv),.ddr_req_ready(1'b1),.ddr_rsp_valid(1'b1),.ddr_rsp_rdata(32'b0),.ddr_rsp_error(1'b0),
        .cam_req_valid(cv),.cam_req_ready(1'b1),.cam_rsp_valid(1'b1),.cam_rsp_rdata(32'b0),.cam_rsp_error(1'b0));
    task access(input[31:0]addr,input wr,input iexp,dexp,ddrexp);
        begin
            @(negedge clk);a=addr;w=wr;v=1;
            #0.001;if(!ir || !dr || idv!==!iexp || ddv!==ddrexp)$fatal(1,"RESULT: FAIL aperture route %h",a);
            @(posedge clk);
            @(negedge clk);v=0;
            if(!iv || !dv || ie!==iexp || de!==dexp)$fatal(1,"RESULT: FAIL aperture response %h",a);
            $display("APERTURE %08h %0d %0d %0d %0d %0d %0d",addr,wr,dual,busy,owned,iexp,dexp);
            repeat(3)@(negedge clk);
        end
    endtask
    reg[31:0]addr[0:7];integer i,o,k;
    initial begin
        addr[0]=32'h41000000;addr[1]=32'h411c1fff;addr[2]=32'h411fffff;addr[3]=32'h41200000;
        addr[4]=32'h413c1fff;addr[5]=32'h413fffff;addr[6]=32'h40ffffff;addr[7]=32'h41400000;
        repeat(5)@(negedge clk);rst=1;
        for(o=0;o<4;o=o+1)for(k=0;k<2;k=k+1)begin
            owned=o;busy=k;
            for(i=0;i<8;i=i+1)begin
                access(addr[i],0,i<6,i<6?!owned[addr[i][21]]:0,i<6?owned[addr[i][21]]:1);
                access(addr[i],1,i<6,i<6,!(i<6));
            end
        end
        dual=0;owned=0;
        for(k=0;k<2;k=k+1)begin busy=k;access(32'h41000000,0,1,k,!k);access(32'h413fffff,1,1,k,!k);end
        done=1;
    end
endmodule
