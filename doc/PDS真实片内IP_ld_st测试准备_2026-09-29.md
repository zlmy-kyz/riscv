# PDS 真实片内 IP＋DDR3：`ld_st` 测试准备

日期：2026-09-29。前一项 `lb` 已由 PDS 按钮验证通过，见 `doc/PDS真实片内IP_lb测试准备_2026-09-29.md`。本项测试较长的 DDR 代码、独立 `.data` 段，以及 `0x80002000` 的 `tohost` 地址。PDS 按钮完整仿真已 PASS。

## 当前准备

- `MyCpu_test/ddr_stage/ld_st.dat` 末尾清单为 `0x40c` 个代码字（1036）、`.data` 偏移 `0x3000`、`0x14` 个数据字（20），总共应复制 **1056** 个 32 位字。
- 已将 `sim/pds_ddr_ip_run.tcl` 设为 `+TEST=ld_st +TOHOST=80002000 +EXPECTED_WRITES=1056`，独立日志名 `sim/pds_ddr_ip_ld_st.log`。
- `inst_rom` 继续使用 `MyCpu_test/ddr_stage/boot_rom.dat`，PDS 仿真顶层仍为 `tb_soc_ddr3_pds_ip`，编译 Tcl 与 DDR3 IP 无需修改。

## 用户需在 PDS 完成的动作

1. 把 `data_ram` 的初始化文件改成 `D:/riscv/RISCV/MyCpu_test/ddr_stage/ld_st.dat`，重新生成 `data_ram` IP，并确认 `ipcore/data_ram/data_ram.v` 的 `INIT_FILE` 指向 `ld_st.dat`。仅修改 `.dat` 文件名或 Tcl 参数不足以更新生成的片内存储内容。
2. 点击 **Run Behavior Simulation**。自动编译应加载重新生成的真实 `data_ram`，随后运行专用 TB。

## PDS 按钮实测与未覆盖范围

用户已将真实 `data_ram` IP 初始化文件设为 `ld_st.dat` 并重新生成；`ipcore/data_ram/data_ram.v` 和 `rtl/data_ram_init_param.v` 的更新时间均为 2026-09-29 01:06:10。`sim/behav/run_behav_simulate.log` 显示 PDS 按钮调用专用编译和运行 Tcl。独立日志 `sim/pds_ddr_ip_ld_st.log` 显示加载真实 `inst_rom`、`data_ram` 与 DDR3 物理模型，并输出：

```text
CHECK: ld_st CPU copied 1056 words then fetched from DDR
RESULT: PASS ld_st DDR RV32I tohost=1 cycles=67203
Errors: 0, Warnings: 353
```

没有 `RESULT: FAIL`。本次结束时间为 2026-09-29 01:24:53，耗时 16 分 30 秒。此结果与先前仿真专用片内 RAM 路径的 `ld_st` PASS 分开记录，证明 PDS 按钮下真实片内 IP 的长代码、独立 `.data` 和 `0x80002000` 的 `tohost` 路径通过。

本项 `ld_st` 基线运行本身未覆盖其它 RV32I 用例、复位/争用压力、实板启动。后续复位、注入争用及 CPU 原生反压争用的独立结果见 [复位与注入争用记录](./DDR3复位与指令数据争用验证_2026-09-29.md) 和 [CPU 原生争用记录](./CPU原生DDR指令数据争用验证_2026-09-29.md)；实板仍未验证。PDS 真实片内 IP 路径目前共验证 `add`、`lb`、`ld_st` 三项 RV32I 程序，不能写成 42 项物理模型回归通过。
