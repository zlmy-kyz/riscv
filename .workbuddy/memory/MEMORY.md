# 项目长期备忘 — RISCV (D:\riscv\RISCV)

## 项目概况
Pango(紫光同创)FPGA 上的 RV32I 五级流水 CPU。
- 主源文件:`myriscv/mycpu_sync.v`(module `mycpu_sync`)
- 配套模块:`myriscv/regfile.v`、`alu.v`、`l_alu.v`、`br_alu.v`
- IP:`ipcore/` 下的 `inst_rom`、`data_ram`(同步单端口,读延迟 1 拍,
  `OUTPUT_REG=0`/`FAB_REG=0`、`RST_VAL_EN=false`、`NORMAL_WRITE`)
- 设计文档:`doc/` 下三篇(ROM/RAM 时序方案、取指复位丢指令、代码问题清单)

## 设计约定(改代码前必读)
1. **取指方案二**:`inst_rom.addr` 组合直连 `next_pc`;ROM 内部地址寄存器 = IF 边界。
   复位期间 `next_pc` 钉复位向量;CPU 侧 `valid` 比 ROM 侧复位晚一拍释放。
2. **访存方案一**:`data_ram.addr` 由 **EX 级 `alu_result` 组合直连**,中间不夹寄存器。
3. ROM 输出比地址口慢**两拍**:`rd_data(t) = mem[addr(t-2)]`;
   因此 `inst_if(t) = mem[pc(t)-4]`,IF/ID 必须接 `pc_v`(pc 打一拍)。
4. 分支/跳转在 **MEM 级**判定,用打拍过的 `ex_mem_br_taken`;
   命中冲刷 IF/ID + ID/EX + EX/MEM,代价 3 个气泡。
5. 重定向后必须 `fetch_stall = flush 打一拍`,把 ROM 里漏网的旧路径指令挡掉。
6. 三处闸门:`rf_we` 乘 `mem_wb_valid`;`data_sram_we` 乘 `id_ex_valid`;
   冲刷只影响更年轻的槽。
7. 转发「数据随级流动」,不反查指令;load-use 旁路取 `mem_result`,优先级最高。

## 验证环境
- 工作目录:`D:\riscv\RISCV\.workbuddy\pipeline5\`
- `run.ps1 -Test A..H` 一键回归(A~H 八组程序,当前全 PASS)
- `tb_diag*.v` 逐拍诊断台
- iverilog:`D:\iverilog\bin\iverilog.exe`(用 `-g2012 -Wall`)
- **bash 工具在本机不可用**(用户名含单引号 → shim 崩),一律用 PowerShell,
  输出要 `Set-Content -Encoding ASCII` 落盘再 Read。
