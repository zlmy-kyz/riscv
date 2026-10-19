`timescale 1ns/1ps
// Electrical open-drain SCCB slave. No DUT state/ROM observations.
module camera_sensor(input wire resetn, input wire scl, inout wire sda,
                     input wire [31:0] injection, output integer writes, reads);
    reg pull_low=0, active=0, sending=0, ack_low=0;
    reg [7:0] shift=0, tx=0, regmap[0:65535];
    reg [15:0] address=0;
    integer bits=0, byte_no=0, transaction=0, i;
    reg [23:0] expected[0:243];
    string path;
    assign sda=pull_low ? 1'b0 : 1'bz;
    initial begin
        writes=0;reads=0;
        if (!$value$plusargs("CONFIG=%s",path)) $fatal(1,"RESULT: FAIL CONFIG path");
        $readmemh(path,expected);
        for(i=0;i<65536;i=i+1) regmap[i]=0;
    end
    always @(negedge resetn) begin
        active=0; sending=0; pull_low=0; bits=0; byte_no=0;
        writes=0; reads=0; transaction=0; address=0;
        for(i=0;i<65536;i=i+1) regmap[i]=0;
    end
    always @(negedge sda) if (resetn && scl===1'b1) begin
        active=1; sending=0; bits=0; byte_no=0; shift=0;
        transaction=transaction+1;
        $display("SCCB_START %0t %0d",$time,transaction);
    end
    always @(posedge sda) if (resetn && scl===1'b1 && active) begin
        active=0; pull_low=0;
    end
    always @(posedge scl) if(resetn && active) begin
        if(sending) begin
            if(bits==8 && sda!==1'b1) $fatal(1,"RESULT: FAIL master must NACK single-byte read");
            bits=bits+1;
        end else if(bits<8) begin
            shift={shift[6:0],sda}; bits=bits+1;
            if(bits==8) begin
                ack_low=!(injection>=1 && injection<=4 && transaction==5 && byte_no==injection-1);
                if(byte_no==0 && shift!=8'h78 && shift!=8'h79)
                    $fatal(1,"RESULT: FAIL SCCB device address %h",shift);
                $display("SCCB_BYTE %0t %0d %0d %02h %0d",$time,transaction,byte_no,shift,ack_low);
                if(byte_no==1) address[15:8]=shift;
                if(byte_no==2) address[7:0]=shift;
                if(byte_no==3 && ack_low) begin
                    if(writes>=244 || {address,shift}!==expected[writes])
                        $fatal(1,"RESULT: FAIL config order/write %0d %04h %02h",writes,address,shift);
                    regmap[address]=shift; writes=writes+1;
                end
            end
        end else bits=bits+1;
    end
    always @(negedge scl) if(resetn && active) begin
        if(sending) begin
            if(bits<8) pull_low=!tx[7-bits];
            else pull_low=0;
        end else if(bits==8) pull_low=ack_low;
        else if(bits==9) begin
            pull_low=0; bits=0;
            if(byte_no==0 && shift==8'h79 && ack_low) begin
                sending=1; reads=reads+1;
                case(address)
                    16'h300a: tx=8'h56;
                    16'h300b: tx=8'h40;
                    default: tx=regmap[address];
                endcase
                if((injection==5 && address==16'h300a) ||
                   (injection==6 && address==16'h4300)) tx=tx^8'h01;
                $display("SCCB_READ %0t %04h %02h",$time,address,tx);
                pull_low=!tx[7];
            end
            byte_no=byte_no+1;
        end
    end
endmodule

// Source drives on falling PCLK. Expected DDR bytes are generated separately in Python.
module camera_dvp(output reg pclk, vsync, href, output reg [7:0] din);
    initial begin pclk=0;vsync=1;href=0;din=0;end
    integer input_log=0;
    string input_path;
    initial if($value$plusargs("DVP=%s",input_path))begin
        input_log=$fopen(input_path,"w");if(!input_log)$fatal(1,"RESULT: FAIL DVP trace open");
    end
    always #7.137 pclk=~pclk; // asynchronous to 93.75 MHz; phase continuously drifts
    function automatic [15:0] sample(input integer pattern,x,y);
        reg [31:0] v;
        begin
            v=x*73+y*151+(x^(y*3))*19;
            sample=v[15:0]^(pattern==1 ? 16'h1357 : 16'heca8);
        end
    endfunction
    task automatic idle(input integer n);
        repeat(n) begin @(negedge pclk); vsync=1; href=0; din=0; end
    endtask
    task automatic frame(input integer pattern,width,height,kind);
        integer x,y,limit;
        reg [15:0] px;
        reg [7:0] first;
        begin
            $display("DVP_FRAME_BEGIN %0t %0d %0d %0d %0d",$time,pattern,width,height,kind);
            if(input_log)$fdisplay(input_log,"FRAME %0d %0d %0d %0d",pattern,width,height,kind);
            idle(12);
            @(negedge pclk);vsync=0;
            repeat(7) @(negedge pclk);
            for(y=0;y<height;y=y+1) begin
                limit=(kind==1 && y==height-1) ? width-1 : width;
                for(x=0;x<limit;x=x+1) begin
                    px=sample(pattern,x,y);
                    @(negedge pclk);href=1;din=px[15:8];first=din;
                    @(negedge pclk);din=px[7:0];
                    if(input_log)$fdisplay(input_log,"%02h%02h",first,din);
                end
                // kind 2: odd byte count; kind 3: simultaneous last HREF/VSYNC edge.
                if(kind==2 && y==height-1) begin @(negedge pclk);din=8'h5a; end
                @(negedge pclk);href=0;
                if(kind==3 && y==height-1) vsync=1;
                repeat(9+y%5) @(negedge pclk);
            end
            @(negedge pclk);vsync=1;href=0;
            idle(12);
            if(input_log)$fflush(input_log);
            $display("DVP_FRAME_END %0t %0d",$time,pattern);
        end
    endtask
endmodule
