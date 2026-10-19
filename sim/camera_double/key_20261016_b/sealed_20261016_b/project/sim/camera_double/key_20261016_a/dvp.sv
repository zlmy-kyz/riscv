`timescale 1ns/1ps
// Source drives on falling PCLK. Expected DDR bytes are generated separately in Python.
module double_dvp(output reg pclk, vsync, href, output reg [7:0] din);
    initial begin pclk=0;vsync=1;href=0;din=0;end
    integer input_log=0;
    string input_path;
    initial if($value$plusargs("DVP=%s",input_path))begin
        input_log=$fopen(input_path,"w");if(!input_log)$fatal(1,"RESULT: FAIL DVP trace open");
    end
    reg clock_enable=1;
    always #7.137 if(clock_enable)pclk=~pclk; // asynchronous; phase continuously drifts
    function automatic [15:0] sample(input integer pattern,x,y);
        reg [31:0] v;
        begin
            v=x*73+y*151+(x^(y*3))*19;
            sample=v[15:0]^((pattern*16'h3d79+16'h1357)&16'hffff);
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
                if(pattern==2 && height==8)repeat(6000)@(negedge pclk);
                if(pattern==9 && height==8)repeat(1500)@(negedge pclk);
            end
            @(negedge pclk);vsync=1;href=0;
            idle(12);
            if(input_log)$fflush(input_log);
            $display("DVP_FRAME_END %0t %0d",$time,pattern);
        end
    endtask
endmodule
