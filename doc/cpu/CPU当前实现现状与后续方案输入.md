# RISC-V CPU 当前实现现状与后续方案输入

> 用途：把当前 RTL 的真实状态、已经验证的能力、已知限制和后续目标提供给 GPT-6，作为制定下一阶段开发方案的基础。

## 1. 项目目标

本项目面向全国大学生嵌入式芯片与系统设计竞赛紫光同创方向，使用 Verilog 实现一颗可在紫光同创 FPGA 上运行的 32 位 RISC-V CPU，并逐步扩展为带总线、外设、Cache、分支预测和 AI 加速能力的 SoC。

当前代码主要位于：

- `myriscv/mycpu_sync.v`：五级流水线 CPU 内核。
- `myriscv/csr_file.v`：M 模式 CSR、异常入口和中断状态。
- `myriscv/soc_top.v`：当前最小 SoC 顶层。
- `ipcore/inst_rom`：指令 ROM IP。
- `ipcore/data_ram`：数据 RAM IP。
- `difftest`：行为模型、差分测试和异常/中断定向测试。
- `MyCpu_test`：riscv-tests 测试镜像及反汇编文件。

## 2. CPU 总体结构

### 2.1 基本参数

- 32 位单发射、顺序执行处理器。
- 指令集基础为 RV32I，固定 32 位指令，不支持压缩指令扩展。
- 当前仅实现机器模式 M-mode，没有 U/S 模式。
- 五级流水线：IF、ID、EX、MEM、WB。
- 复位 PC 可以通过 `RESET_PC` 参数配置；riscv-tests 使用 `0x8000_0000`。
- 指令和数据通路分离，属于简单 Harvard 结构。

### 2.2 各流水级的主要功能

| 流水级 | 当前功能 |
|---|---|
| IF | 产生取指地址，适配固定一拍同步 ROM；处理保持和重定向。 |
| ID | 指令译码、立即数生成、寄存器堆读取、数据前递选择、分支条件判断和跳转目标计算。 |
| EX | ALU 运算、load/store 地址计算、store 数据和字节写使能生成、数据地址非对齐检测。 |
| MEM | 接收固定一拍 RAM 的读数据，完成字节/半字加载提取和符号扩展。 |
| WB | GPR 写回、CSR 指令提交、同步异常提交、MRET 提交和调试信息输出。 |

### 2.3 流水线相关机制

- 使用 `valid` 位表示各级流水项是否有效，气泡不会产生架构副作用。
- 已实现 EX、MEM、WB 到 ID 的数据前递，优先级为较新的流水级优先。
- 已实现精确的 load-use 冒险检测，只在当前 ID 指令真正读取相关源寄存器时暂停。
- 分支、JAL 和 JALR 当前在 ID 阶段判断并产生重定向。
- 分支跳转后会冲刷错误路径指令。
- 当前没有动态或静态分支预测器，所有采用的控制转移都通过实际译码结果重定向。
- CSR、ECALL、EBREAK、MRET、FENCE 和 WFI 使用串行排空状态机，避免与更老指令的副作用冲突。

## 3. 当前指令支持情况

### 3.1 已实现的 RV32I 普通指令

- 整数寄存器运算：`ADD`、`SUB`、`SLL`、`SLT`、`SLTU`、`XOR`、`SRL`、`SRA`、`OR`、`AND`。
- 整数立即数运算：`ADDI`、`SLTI`、`SLTIU`、`XORI`、`ORI`、`ANDI`、`SLLI`、`SRLI`、`SRAI`。
- 高位立即数：`LUI`、`AUIPC`。
- 条件分支：`BEQ`、`BNE`、`BLT`、`BGE`、`BLTU`、`BGEU`。
- 无条件跳转：`JAL`、`JALR`。
- 读取存储器：`LB`、`LBU`、`LH`、`LHU`、`LW`。
- 写存储器：`SB`、`SH`、`SW`。

### 3.2 CSR 和系统指令

- 已实现六条 Zicsr CSR 指令：`CSRRW`、`CSRRS`、`CSRRC`、`CSRRWI`、`CSRRSI`、`CSRRCI`。
- 已实现 `ECALL`、`EBREAK` 和 `MRET`。
- `WFI` 当前按串行 NOP 处理，不具备真正的低功耗等待和唤醒行为。
- `FENCE` 当前能够被识别并排空流水线。由于系统还没有总线、写缓冲、乱序访存或 Cache，它只是一个最小串行屏障，尚未形成完整的系统级存储序保证。
- `FENCE.I` 未实现，当前会作为非法指令处理。

因此，对外描述时可以说“RV32I 的运算、跳转和基本访存指令已经实现；FENCE 只有最小串行行为，FENCE.I 尚未实现”。

### 3.3 当前不支持的指令扩展

- 不支持 RVC 压缩指令。
- 不支持 M 扩展乘除法。
- 不支持 A、F、D、V 等扩展。
- 不支持自定义 AI 指令。

## 4. 异常与中断现状

### 4.1 已实现的同步异常

- 指令地址非对齐，cause 0。
- 非法指令及非法 CSR 访问，cause 2。
- `EBREAK`，cause 3。
- load 地址非对齐，cause 4。
- store 地址非对齐，cause 6。
- M 模式 `ECALL`，cause 11。

异常信息随指令在流水线中传递，在 WB 阶段提交。发生异常时会抑制故障指令的 GPR、CSR 和存储器副作用，并清除年轻指令，保证精确异常。

当前存储接口没有错误响应，所以尚未实现：

- 指令访问故障，cause 1。
- load 访问故障，cause 5。
- store 访问故障，cause 7。

这些异常需要等总线接口能够返回访问错误后再接入。

### 4.2 已实现的机器中断

- 机器软件中断 MSI，cause 3。
- 机器定时器中断 MTI，cause 7。
- 机器外部中断 MEI，cause 11。
- 当前仲裁优先级：MEI > MSI > MTI。
- 使用 `mstatus.MIE` 作为全局使能，使用 `mie` 作为各中断源局部使能。
- `mip` 的 MEIP、MTIP、MSIP 直接反映三个外部输入电平。
- 接受中断前先排空已发射流水项，使用单独维护的架构续执行地址写入 `mepc`。
- 同步异常优先于中断。
- 支持进入 trap 后保存 MIE 到 MPIE、清除 MIE，并在 `MRET` 时恢复。

目前 CPU 只有三个同步电平中断输入：

```text
irq_external
irq_software
irq_timer
```

还没有实现 CLINT、`mtime`、`mtimecmp`、内存映射 `msip`、PLIC，也没有板级异步中断同步器和中断源保持/清除逻辑。

### 4.3 已实现的 CSR

| CSR | 地址 | 当前行为 |
|---|---:|---|
| `mstatus` | `0x300` | MIE、MPIE 可写，MPP 固定为 M。 |
| `misa` | `0x301` | 固定返回 RV32I 标识，写入无效果。 |
| `mie` | `0x304` | 支持 MEIE、MTIE、MSIE。 |
| `mtvec` | `0x305` | 仅支持 Direct 模式，低两位固定 0。 |
| `mstatush` | `0x310` | 固定为 0。 |
| `mscratch` | `0x340` | 32 位读写。 |
| `mepc` | `0x341` | 低两位固定 0。 |
| `mcause` | `0x342` | 保存异常/中断标志和原因。 |
| `mtval` | `0x343` | 保存非法指令或故障地址等信息。 |
| `mip` | `0x344` | 三个机器中断 pending 位来自外部输入。 |
| `mvendorid` 等 | `0xF11`～`0xF15` | 当前返回 0，按只读或固定值处理。 |

没有实现 `mcycle/minstret` 等性能计数器，也没有 PMP、地址转换和特权级委托功能。

## 5. 访存与当前最小 SoC

### 5.1 CPU 存储接口

CPU 已经与具体 ROM/RAM 实例解耦，当前端口包括：

- 指令侧：`inst_addr`、`inst_rdata`。
- 数据侧：`data_addr`、`data_wdata`、`data_wstrb`、`data_read`、`data_write`、`data_rdata`。

这些端口仍然假设存储器是固定一拍同步读：

- 没有 `valid/ready` 握手。
- 没有读响应有效信号。
- 没有总线错误响应。
- 没有 burst、ID 或 outstanding 事务。
- 流水线不能处理任意延迟存储器。

因此它们只是为后续总线化预留的边界，还不能直接连接存在等待周期的 AXI、AHB、Wishbone 或 DDR3 控制器。

### 5.2 当前 `soc_top`

当前最小 SoC 只包含：

```text
mycpu_sync
 ├─ 16 KiB 指令 ROM（4096 × 32 bit）
 └─ 16 KiB 数据 RAM（4096 × 32 bit）
```

- ROM 和 RAM 使用紫光同创 IP，均为固定一拍同步读。
- CPU 使用完整的 32 位字节地址，当前 SoC 存储器侧使用地址低 14 位寻址。
- 这种做法能让链接在 `0x8000_0000` 的测试镜像映射到片内 ROM，但不同高地址可能发生别名。
- 当前没有正式的地址译码和统一内存映射。
- 当前没有 GPIO、UART、定时器、中断控制器等外设。
- 当前没有启动 ROM、片外 DDR3 控制器和软件运行环境。

### 5.3 对齐访问现状

- 对齐的字节、半字和字访问已经实现。
- 非对齐半字/字访问当前触发 load/store address-misaligned 异常。
- 没有把一次跨 32 位字边界的访问拆成两次总线访问并重新拼接。
- 因此 riscv-tests 中涉及跨字访问的测试尚未通过。

## 6. 当前验证状态

### 6.1 riscv-tests

- 当前共运行 42 项测试。
- 已通过 40 项。
- 未通过的两项为：
  - `rv32ui-p-fence_i`：FENCE.I 未实现。
  - `rv32ui-p-ma_data`：未实现跨字/非对齐访问拆分。

当前通过率为 `40 / 42`，约为 `95.24%`。

### 6.2 自建验证

现有测试还覆盖：

- 普通 ALU、访存、跳转、前递和 load-use 冒险。
- 六条 CSR 指令及连续 CSR 指令。
- 非法指令和非法 CSR 访问。
- ECALL、EBREAK、trap handler 和 MRET 闭环。
- load/store 地址非对齐异常。
- 被采用的 branch、JAL、JALR 目标地址非对齐异常。
- 三类机器中断、优先级、重复 pending、中断撤销和流水线精确排空。
- 异常/中断过程中年轻 store 的副作用抑制。
- 正常退休轨迹、GPR、CSR 和 RAM 终值差分。

现有异常/中断专项回归已经核对过正常退休、同步 trap、中断和 MRET 的架构状态。

当前还没有形成以下验收结果：

- CoreMark/MHz。
- FPGA 综合后的最高频率、LUT/FF/BRAM 用量。
- 总线压力测试。
- Cache 一致性、替换和回写测试。
- GPIO/UART 板级测试。
- DDR3 联调测试。
- AI 加速性能和资源数据。

## 7. 尚未实现的主要模块

1. 完整 `FENCE.I` 及取指侧同步机制。
2. 跨字/非对齐 load/store 的硬件拆分；或者明确只采用异常方式并调整对应测试目标。
3. 支持等待和错误响应的内部总线。
4. 正式的 SoC 地址映射和 MMIO 地址译码。
5. GPIO、UART 等基础外设。
6. CLINT 或等价的软件中断、机器定时器模块。
7. PLIC 或简化外部中断控制器。
8. DDR3 控制器接入及片内外存储桥接。
9. 指令 Cache 和数据 Cache；竞赛高阶目标要求二路组相联。
10. 总线 burst 访问和 Cache line refill/writeback。
11. 分支预测器和 BTB。
12. 性能计数器和 CoreMark 性能分析接口。
13. AI 加速器、DMA、传感器或显示设备接口。

## 8. 后续设计必须注意的现有约束

1. **固定一拍存储器假设**：当前 IF 和 MEM 时序直接依赖 ROM/RAM 的固定一拍延迟。接总线或 Cache 时必须增加请求、等待、响应和 outstanding 状态，并统一控制流水线暂停。
2. **store 当前在 EX 阶段提交**：现有片内 RAM 的地址、数据和写使能在 EX 同拍送出。接可等待总线后，store 必须变成可保持的事务，直到握手完成，同时保证异常和中断精确性。
3. **load 数据在 MEM 阶段返回**：当前前递和 load-use 逻辑基于固定返回时间。Cache miss 或总线等待会要求 MEM 级停顿并冻结前后级。
4. **中断排空条件**：当前只检查 ID/EX、EX/MEM、MEM/WB 是否为空。总线化以后必须把尚未完成的取指、load、store、Cache refill/writeback 和其他 outstanding 事务纳入排空条件。
5. **访问故障尚无来源**：总线 `SLVERR/DECERR` 或等价错误必须映射到 cause 1、5、7，并保存准确的 `mepc/mtval`。
6. **FENCE/FENCE.I 与 Cache 相关**：实现 Cache 后，需要重新定义 FENCE 的完成条件，并为 FENCE.I 增加指令 Cache 失效、流水线清空和重新取指流程。
7. **当前分支在 ID 判断**：增加预测器时，需要定义预测发生阶段、预测 PC、预测元数据沿流水线传递、实际结果比较、错误预测冲刷和 BTB 更新时机。
8. **地址高位当前被片内 RAM 忽略**：加入外设和 DDR3 前必须先建立清晰且不重叠的地址映射，不能继续依赖低位别名。
9. **异步外设输入**：GPIO/UART/外部中断进入 CPU 时必须在 SoC 边界完成时钟域同步；窄脉冲需要保持或转换成可清除 pending 位。
10. **保持现有精确异常语义**：任何总线、Cache、预测器和加速器改动都不能让被冲刷或发生异常的指令产生 GPR、CSR、RAM 或 MMIO 副作用。

## 9. 希望 GPT-6 输出的方案

请基于上述现状制定一套可以逐步实现、每一步都能独立仿真验收的开发方案。方案至少需要回答：

1. 下一阶段功能的推荐开发顺序，以及各阶段的依赖关系。
2. CPU 存储端口如何改造成支持等待、返回和错误响应的接口。
3. 内部总线选择：自定义 ready/valid、Wishbone、AHB-Lite、AXI4-Lite 或 AXI4，各方案的优缺点及推荐选择。
4. 如何在不破坏现有五级流水线和精确异常的前提下实现全流水线暂停。
5. SoC 地址映射建议，以及 ROM、SRAM、DDR3、UART、GPIO、CLINT、PLIC 和 AI 加速器的地址范围。
6. GPIO、UART、机器定时器和软件中断的模块接口与寄存器设计。
7. 二路组相联 I-Cache/D-Cache 的容量、line 大小、替换策略、写策略和状态机设计。
8. Cache miss、总线错误、FENCE 和 FENCE.I 如何与流水线及异常机制配合。
9. BTB/动态分支预测器的结构、预测与更新时机、错误预测恢复流程。
10. DDR3 接入时的时钟域、位宽转换、burst、仲裁和启动流程。
11. AI 加速器建议，包括 CPU 控制方式、寄存器接口、DMA、数据格式和适合 FPGA 的模型。
12. 每个阶段需要新增或修改的 Verilog 模块、关键信号和状态机。
13. 每个阶段的定向测试、随机测试、riscv-tests、CoreMark 和上板验收标准。
14. 对频率、LUT、FF、BRAM 和 DDR 带宽的主要风险，以及可执行的优化顺序。

请把方案拆成小步骤。每一步都应说明：目标、需要修改的模块、接口定义、控制流程、异常情况、测试方法、通过标准，以及完成后再进入下一步的检查点。

