`timescale 1ns/1ps
module tool_health;
  initial begin
    #1;
    $display("TOOL_KERNEL_OK time=%0t", $time);
    $finish;
  end
endmodule
