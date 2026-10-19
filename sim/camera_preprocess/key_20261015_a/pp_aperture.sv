`timescale 1ns/1ps
// Access checks go through the real inst/data decode logic with constant-ready slaves.
// The trace is logged; the independent Python checker re-derives every expectation.
module pp_aperture;
    reg clk=0,rst=0,v=0,w=0;
    reg [31:0] a=0;
    reg [1:0] sz=2;
    reg busy=0,done=0,pperr=0,dual=1;
    reg [1:0] owned=0;
    always #5.333 clk=~clk;
    wire ir,iv,ie,idv,dr,dv,de,ddv,cv,pv;
    wire [31:0] prdata;
    inst_bus_interconnect #(.ROM_BASE(0),.ENABLE_DDR(1),.ENABLE_CAMERA(1),.ENABLE_PREPROCESS(1)) inst(
        .clk(clk),.resetn(rst),.m_req_valid(v),.m_req_addr(a),.m_req_ready(ir),
        .m_rsp_valid(iv),.m_rsp_error(ie),
        .rom_req_ready(1'b1),.rom_rsp_valid(1'b1),.rom_rsp_rdata(32'b0),.rom_rsp_error(1'b0),
        .ddr_req_valid(idv),.ddr_req_ready(1'b1),.ddr_rsp_valid(1'b1),.ddr_rsp_rdata(32'b0),.ddr_rsp_error(1'b0));
    data_bus_interconnect #(.RAM_BASE(0),.ENABLE_DDR(1),.ENABLE_CAMERA(1),.ENABLE_UART(1),.ENABLE_PREPROCESS(1)) data(
        .clk(clk),.resetn(rst),.m_req_valid(v),.m_req_write(w),.m_req_size(sz),.m_req_addr(a),
        .m_req_wdata(32'b0),.m_req_wstrb(4'hf),.m_req_ready(dr),
        .m_rsp_valid(dv),.m_rsp_error(de),.m_rsp_rdata(),
        .camera_busy(1'b0),.camera_dual_mode(dual),.camera_cpu_owned(owned),
        .preprocess_busy(busy),.preprocess_done(done),
        .ddr_write_buffer_busy(1'b0),
        .ram_req_ready(1'b1),.ram_rsp_valid(1'b1),.ram_rsp_rdata(32'b0),.ram_rsp_error(1'b0),
        .mmio_req_ready(1'b1),.mmio_rsp_valid(1'b1),.mmio_rsp_rdata(32'b0),.mmio_rsp_error(1'b0),
        .uart_req_ready(1'b1),.uart_rsp_valid(1'b1),.uart_rsp_rdata(32'b0),.uart_rsp_error(1'b0),
        .ddr_req_valid(ddv),.ddr_req_ready(1'b1),.ddr_rsp_valid(1'b1),.ddr_rsp_rdata(32'b0),.ddr_rsp_error(1'b0),
        .pp_req_valid(pv),.pp_req_write(),.pp_req_size(),.pp_req_addr(),.pp_req_wdata(),.pp_req_wstrb(),
        .pp_req_ready(1'b1),.pp_rsp_valid(1'b1),.pp_rsp_rdata(32'b0),.pp_rsp_error(pperr),
        .cam_req_valid(cv),.cam_req_ready(1'b1),.cam_rsp_valid(1'b1),.cam_rsp_rdata(32'b0),.cam_rsp_error(1'b0));
    integer fd,count=0;
    string path;
    task automatic probe(input[31:0]addr,input wr,input[1:0]size);
        begin
            @(negedge clk);a=addr;w=wr;sz=size;v=1;
            #0.001;
            @(posedge clk);
            @(negedge clk);v=0;
            if(!iv || !dv)$fatal(1,"RESULT: FAIL aperture handshake %h",addr);
            $fdisplay(fd,"APERTURE %08h %0d %0d %0d %0d %0d %0d %0d %0d",addr,wr,size,done,busy,pperr,idv,ie,de);
            count=count+1;
            repeat(2)@(negedge clk);
        end
    endtask
    integer i,j,k,s;
    reg [31:0] addr[0:11];reg [1:0] szv[0:2];
    initial begin
        if(!$value$plusargs("PERM=%s",path))$fatal(1,"RESULT: FAIL PERM path");
        fd=$fopen(path,"w");if(!fd)$fatal(1,"RESULT: FAIL PERM open");
        addr[0]=32'h42000000;addr[1]=32'h42006bfc;addr[2]=32'h42006bff;addr[3]=32'h42006c00;
        addr[4]=32'h4200ffff;addr[5]=32'h42010000;addr[6]=32'h41ffffff;addr[7]=32'h41400000;
        addr[8]=32'h10003000;addr[9]=32'h1000303c;addr[10]=32'h10003040;addr[11]=32'h42006bfd;
        szv[0]=2'b00;szv[1]=2'b01;szv[2]=2'b10;
        repeat(8)@(negedge clk);rst=1;repeat(2)@(negedge clk);
        // done/busy/error states: publish valid, before DONE, busy, error latched.
        for(i=0;i<4;i=i+1)begin
            done=(i==0);busy=(i==2)||(i==3);pperr=(i==3);
            for(j=0;j<12;j=j+1)for(k=0;k<2;k=k+1)for(s=0;s<3;s=s+1)probe(addr[j],k,szv[s]);
        end
        $display("APERTURE_PROBES %0d",count);
        $fclose(fd);
    end
endmodule
