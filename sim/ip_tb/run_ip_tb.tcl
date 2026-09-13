# ----------------------------------------
# inst_rom 独立仿真脚本(IP 单元级自检)
#
# 用法:
#   cd D:/riscv/RISCV/sim/ip_tb
#   vsim -c -do run_ip_tb.tcl            # 命令行模式
#   或在 ModelSim GUI 中: do run_ip_tb.tcl
#
# 说明:
#   * 与 Pango 自动生成的 sim/behav/*.tcl 互不影响(那份跑的是 topcpu_tb)。
#   * 只编译 inst_rom 相关文件 + 本测试台,不涉及 CPU。
#   * 跑完看转录里的 "inst_rom 独立仿真报告"。
# ----------------------------------------

vlib  work
vmap  work ./work
vmap  usim "D:/modelsim/modelsimm/pango_sim_libraries/usim"

vlog -work work +incdir+"D:/riscv/RISCV/ipcore/inst_rom/rtl" \
  "D:/riscv/RISCV/ipcore/inst_rom/rtl/ipm2l_rom_v1_8_inst_rom.v" \
  "D:/riscv/RISCV/ipcore/inst_rom/rtl/ipm2l_spram_v1_8_inst_rom.v" \
  "D:/riscv/RISCV/ipcore/inst_rom/inst_rom.v" \
  "D:/riscv/RISCV/source/tb_instrom.v"

vsim -novopt -L work -L usim tb_instrom usim.GTP_GRS
run -all
