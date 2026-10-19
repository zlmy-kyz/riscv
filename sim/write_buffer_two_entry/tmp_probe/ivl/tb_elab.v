module tb_elab;
  reg clk = 0, resetn = 0, ddr_init_done = 0;
  always #5 clk = ~clk;
  initial begin
    $display("ELAB OK");
    #100 $finish;
  end
  dual_sram_to_pango_ddr_bridge u_dut (
    .clk(clk), .resetn(resetn), .ddr_init_done(ddr_init_done)
  );
endmodule
