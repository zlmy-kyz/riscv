# 盘古 MINI-(200H) 三个新 IP 适配（2026-10-11）

后续上板前仿真、物理模型复验和 CoreMark 交接见 [2026-10-12 记录](盘古MINI上板前仿真与CoreMark交接_2026-10-12.md)。

**最新复核（2026-10-11）：**用户已在 DDR IP Step 3 导入板级 FDC 并重新 Generate。`USER_PINS_CON_EN=true`，71 个 DDR 球位对照全部 PASS；生成日志为 0 error、0 warning，接口仍是 32 DQ/4 DQS/4 DM。工程 FDC 中由编辑器追加的重复 DDR 属性已清除，包括 `mem_dq[26]` 前后冲突的 SLEW；`mem_a[2]` 只保留 L2、1.5 V、SSTL15_I。用户调整的 LED 球位保留为 `led_clk_alive=A20`、`led_ddr_ready=C19`、`led_selftest=C18`。顶层静态编译和 x32 桥定向仿真复验通过。仍待用户 PDS 实现、时序和实板验证。

## 输入与改动

- 板卡 PG2L200H-6IFBG676，两片 x16 DDR3 构成 x32，总容量按 1 GiB；CPU 窗口 `0x4000_0000–0x7fff_ffff`。
- 新 `inst_rom`、`data_ram` 均 4096×32，与原适配器端口一致；RAM 保留 4 字节使能。ROM/RAM 初始化为 `tests/uart_loader/candidates/verify_run_hello/build/loader_rom.dat` / `loader_ram.dat`，SHA-256 分别为 `53a2d9912e85b6b5c90768fb0422be6cde8d5bdab37ef07b7eabfb065b76cea1` / `986cda2d60cc4d4d97bf71b6bcc90c938126b241ef1656c3275c41b0999f2975`。
- 新 `ddr3` 为 Controller + PHY、Simplified AXI、32 DQ、4 DQS/DM、256-bit 用户数据、32-bit strobe、28-bit 控制地址、125 MHz 参考、750 Mbps。`board_top.v` / `soc_ddr3_top.v` 已扩宽物理及用户口，移除新 IP 没有的 `init_samp_position_odd`，调试输入按 4 DQS 位宽接零。
- `soc_ddr3_top` 向 `soc_top` 传入 x32、`DDR_ADDR_MASK=0xc000_0000` 和实际核心时钟。DDR 桥按 DQ 宽度计算 32-byte 拍、8 个 CPU word 槽、控制地址和 I/D 缓存行；通用 `soc_top`/桥默认 x16 留给原独立 TB。
- `RISCV.pds` 已注册三个 IDF 和 98 个实际存在的 IP 源文件。`constraint_check/temp_constraint_file.fdc` 为候选：DDR 电气属性取新 IP 生成 FDC，DDR 球位取 MINI-(200H) 资料包 `HDMI_IN_DDR3_YCbCr_top.fdc`，其他板级引脚按手册及 KEY/LED/UART 例程。

## DDR IP Pin/Bank 修正前记录（已解决）

修正前的 DDR IP `ipcore/ddr3/pnr/ddr_test.fdc` 与板卡例程有 **33 个 DQ/DM 球位不一致**。DQS、地址、控制共 35 个信号球位一致。尤其 `mem_dm[0]` 原为 G5，板卡为 K6，G5 是板卡 DQ0。DDR3 向导的 Data Pin Options 只显示 Bank/Group；逐位 `PAD_DQ*`、`PAD_DM*` 控件在 PDS 2022.2 的 `ips2l_hmic_s-1.16a/ui.tcl` 中被隐藏。该向导在 Step 3 勾选 `Enable fdc file select` 并选择 FDC 后，会扫描其中的 `PAP_IO_LOC`，自动填入这些隐藏参数。用户已按此流程导入 `D:/riscv/RISCV/constraint_check/temp_constraint_file.fdc` 并重新 Generate，板级 FDC 同时继续作为 PDS 工程约束。以下差异表保留为修正前记录。

复核命令：`python sim/mini_board_migration/check_ddr_pinmap.py`。原结果为 `RESULT: FAIL 33 DDR pin location mismatches`；重新生成后实测 `RESULT: PASS all 71 DDR pin locations match the MINI-(200H) board FDC`。

再次保存工程 FDC 后复核：有效约束共 79 个端口球位，无重复属性或球位冲突；DDR Bank R4/R5 对应约束均为 1.5 V。IP 生成的 `ddr_test.fdc` 也无重复属性或球位冲突。PDS 仍引用 `constraint_check/temp_constraint_file.fdc`，三个 IP 的 98 个注册源文件均存在。检查器仅解析有效约束行，已注释的旧 `led_selftest=C19` 不参与冲突判断。若再次使用 PDS User Constraint Editor 保存，请重跑上述检查命令，并检查重复属性。

| 信号 | 修正前生成球位 | 板卡球位 |
|---|---|---|
| `mem_dm[0]` | G5 | **K6** |
| `mem_dm[1]` | H9 | **F7** |
| `mem_dm[2]` | F3 | **D5** |
| `mem_dm[3]` | G2 | **E2** |
| `mem_dq[0]` | J6 | **G5** |
| `mem_dq[1]` | J5 | **J6** |
| `mem_dq[2]` | L8 | **F5** |
| `mem_dq[3]` | K8 | **L8** |
| `mem_dq[4]` | K7 | **G4** |
| `mem_dq[5]` | K6 | **K7** |
| `mem_dq[6]` | G4 | **F4** |
| `mem_dq[7]` | F4 | **J5** |
| `mem_dq[8]` | E6 | **H6** |
| `mem_dq[9]` | D6 | **F8** |
| `mem_dq[11]` | G8 | **D6** |
| `mem_dq[12]` | F8 | **G8** |
| `mem_dq[13]` | F7 | **E6** |
| `mem_dq[14]` | H6 | **H9** |
| `mem_dq[16]` | E5 | **C4** |
| `mem_dq[17]` | D5 | **D4** |
| `mem_dq[18]` | D4 | **A4** |
| `mem_dq[19]` | C4 | **E3** |
| `mem_dq[20]` | B4 | **C3** |
| `mem_dq[21]` | A4 | **F3** |
| `mem_dq[22]` | D3 | **B4** |
| `mem_dq[23]` | C3 | **D3** |
| `mem_dq[24]` | C2 | **F2** |
| `mem_dq[25]` | B2 | **D1** |
| `mem_dq[26]` | A3 | **G1** |
| `mem_dq[28]` | F2 | **E1** |
| `mem_dq[29]` | E2 | **A3** |
| `mem_dq[30]` | E1 | **G2** |
| `mem_dq[31]` | D1 | **C2** |

## 验证与边界

- 顶层静态编译：`iverilog -g2012 -i -tnull -s board_top -I myriscv -I ipcore/ddr3`，输入全部 `myriscv/*.v` 与三个 IP 顶层，退出码 0；Icarus 提示 `ddr_init_done` 输出被转成 inout，这仅为语法/连线检查。
- x32 桥定向仿真：`iverilog -g2012 -s tb_ddr_bridge_x32 -o sim/mini_board_migration/tb_ddr_bridge_x32.vvp sim/mini_board_migration/tb_ddr_bridge_x32.v myriscv/dual_sram_to_pango_ddr_bridge.v`，再运行 `vvp`，得到 `RESULT: PASS`。覆盖末槽/字节写使能、I/D 缓存命中与写失效、512 MiB 边界及 1 GiB 末地址映射。
- 原 x16 `sim/inst_line_buffer/tb_data_cache4.sv` 用 Icarus 编译在 TB 动态 memory part-select 处报 `name is not a valid net`，未记为新 RTL 回归 PASS。
- 尚未运行 PDS 综合/实现/位流、DDR PHY 物理联仿或 MINI 实板。新 FDC 的派生时钟层次、固定 PHY 位置、电气标准须由 PDS 实现报告复核。下一步核对 PDS 的三个 IDF、`AXI_REDUCED_EN`、x32 端口及上述同一对 DAT，再由用户执行 PDS 实现、时序和上板。
- 用户提供的 MINI 硬件手册电源表写明 DDR3 与 R4/R5 Bank 为 1.5 V；表中 FPGA 型号文字仍是 PG2L100H，因此对 200H 实板供电的最终确认仍以对应修订版原理图或板厂资料为准。当前 DDR FDC 与 IP 生成 FDC 均设置 1.5 V、SSTL15_I；HSST_1.2V 是高速收发器锁相环电源，不应用于 DDR 地址/数据 IO。
