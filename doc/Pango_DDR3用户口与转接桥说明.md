# Pango DDR3 用户口与类 SRAM 转接桥说明

## 本步结论

工程中的 DDR3 IP 用户口不是标准 AXI4/AXI4-Lite，而是 Pango 自定义的
AXI-like 接口。不能直接套用书中的标准类 SRAM—AXI 转接桥。

本步新增：

- `myriscv/dual_sram_to_pango_ddr_bridge.v`：两个类 SRAM 端口转一个 Pango
  DDR3 用户口，首版单 outstanding、单拍访问。
- `source/tb_dual_sram_to_pango_ddr_bridge.v`：不依赖加密 DDR 模型的协议级
  testbench，用行为模型检查初始化门控、地址换算、128/32 位数据选槽、字节
  写使能和指令/数据仲裁。

桥现已接入 `soc_top` 的可选 DDR 路径。`ENABLE_DDR` 默认是 0；旧的
ROM/RAM/MMIO 路径仍按原地址和时序工作。启用 DDR 时，两个互连将 DDR 请求
的完整 CPU 地址减去 `DDR_BASE`，再送给共享桥。

默认地址布局如下：

| 目标 | 起始地址 | 容量 | 端口 |
| --- | --- | --- | --- |
| 指令 ROM | `INST_ROM_BASE`，默认 `RESET_PC` | 16 KiB | 只读取指 |
| 数据 RAM | `DATA_RAM_BASE`，默认 `RESET_PC` | 16 KiB | 读写 |
| MMIO | `0x1000_0000` | 4 KiB | 数据端口 |
| DDR3 | `0x4000_0000` | 512 MiB | 指令、数据共享 |

`source/tb_ddr_bus_path.v` 使用行为模型验证了从两个互连到桥的完整路径；
`source/tb_inst_bus_interconnect.v` 和 `source/tb_data_bus_interconnect.v` 也已
重新通过。`myriscv/soc_ddr3_top.v` 已把生成的 x16 DDR3 IP 与 `soc_top`
的 `ddr_axi_*` 用户口连接；它接收已缓冲的单端参考时钟，尚不是最终的
RK3568 板级差分时钟/引脚约束顶层。

## 从 IP 和 example_design 确认的接口规则

### 1. 这不是标准 AXI4

`ipcore/ddr3/ddr3.v` 的用户口有 AW、W、AR、R 信号，但：

- 没有 `axi_wvalid`；
- 没有标准写响应 B 通道；
- 没有 `axi_rready`；
- 当前 x16 配置每个 `axi_wdata/axi_rdata` 是 128 bit，`axi_wstrb` 是 16 bit，
  `axi_awaddr/axi_araddr` 是 28 bit。

因此：

- 写地址必须保持到 `axi_awvalid && axi_awready`；
- 写数据和 strobe 必须提前准备并保持，控制器用 `axi_wready` 表示接受一拍；
- 读地址必须保持到 `axi_arvalid && axi_arready`；
- `axi_rvalid` 出现时必须立即接收，主机不能反压。

### 2. LEN 的含义

example_design 的读写计数器都在地址握手时增加 `len + 1`，所以：

- `axi_awlen = 0`：一个 128-bit 写数据拍；
- `axi_arlen = 0`：一个 128-bit 读数据拍。

桥的首版始终使用 `len=0`，先保证功能正确，再考虑 cache line burst。

### 3. 地址单位和 32 位选槽

当前生成的 IP 配置为 `MEM_DQ_WIDTH=16`、4Gb 时：

- DDR 用户数据拍宽度为 `16 * 8 = 128 bit = 16 byte`；
- example_design 每收到一个数据拍，地址加 8；
- example_design 产生的随机地址低 3 bit 固定为 0；
- 16 拍 burst 后下一个地址加 128，恰好是 `16 * 8` 个 16-bit 字。

因此该用户口地址按一个 16-bit DQ 字计数，而不是按 byte 计数。一拍包含
8 个 16-bit 字，即 4 个 CPU 32-bit 字。

若输入桥的是 DDR 局部 CPU 字节地址 `local_addr`：

```text
DDR command address = (local_addr >> 1) & ~7
32-bit lane         = local_addr[3:2]
byte position       = local_addr[1:0]
```

CPU 当前已经用 `addr[1:0]` 将 store 数据和 4-bit strobe 放到 32-bit 字中的
正确位置；桥只需再按 `addr[3:2]` 把整个字和 strobe 放入 128-bit 数据拍。

### 4. 初始化与时钟

example_design 的 BIST 工作在 DDR3 IP 输出的 `core_clk`，并等待
`ddr_init_done` 后才发请求。因此正式接入时最简单且安全的第一版是：

- CPU、地址译码器、桥都使用 `core_clk`；
- 对外复位先同步到 `core_clk`；
- CPU/桥在 `ddr_init_done` 前不访问 DDR；
- 若 CPU 仍用另一时钟，必须额外设计异步跨时钟桥，不能直接连。

## 首版桥的取舍

- 数据端口固定优先于指令端口；
- 全局最多一笔未完成事务，不使用 ID 做多 outstanding 路由；
- 读写均是一个 128-bit 数据拍；
- 写响应在 `axi_wready` 接受数据拍后返回，不能只看 AW 握手；
- 用户口没有 `BRESP/RRESP`，所以目前无法从 DDR 控制器得到标准总线错误，
  桥的 `rsp_error` 固定为 0；
- `axi_awuser_ap/axi_aruser_ap` 按 example_design 的初始化访问设为 0。

这个版本优先验证协议和正确性。它会让取指与数据访问互相等待，性能不高，
但以后加入 I-cache/D-cache 后，DDR 访问会变成 cache line burst，桥的结构仍可
继续扩展。

## 后续接入顺序

1. 先运行桥的协议级 testbench。
2. 给指令和数据地址译码器各增加 DDR 窗口，并把两个 DDR 从机端口接到桥。（已完成）
3. 新建集成顶层，例化 `soc_top` 和 `ddr3` IP；CPU 改用 `core_clk`，
   令 `soc_top.ENABLE_DDR=1` 并连接 `ddr_axi_*` 用户口。（已完成 RTL 接线）
4. 为 RK3568 板补差分参考时钟缓冲、实板管脚约束，并以实板频率重新生成 IP。
5. 用 DDR example_design 仿真模型做单地址写后读回。
6. 上板只跑 DDR 自检，确认 `ddr_init_done` 和读写回环。
7. 增加 boot ROM 搬运程序：把程序复制到 DDR，再跳转执行。
8. 最后再做 burst、cache、仲裁优化，以及 `fence`/`fence.i` 的可见性处理。
