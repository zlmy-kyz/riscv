# RISCV 工程 IP 核说明:inst_rom 与 data_ram

> 分析对象:`D:\riscv\RISCV\ipcore`、`D:\riscv\RISCV\ip_backup`
> 分析日期:2026-09-11
> 说明:本文档为只读分析结论,未修改任何 RTL 或 IP 配置文件。

---

## 1. 结论概述

`ipcore` 目录下共有 **2 个 IP 核**,由 Pango(紫光同创)IP Compiler 生成:

| 序号 | 实例名 | IP 类型 | 用途 | 目录 |
| :--: | :-- | :-- | :-- | :-- |
| 1 | `inst_rom` | 28nm DRM Based ROM v1.8(id 04100204) | 存放指令,只读 | `ipcore/inst_rom/` |
| 2 | `data_ram` | 28nm DRM Based Single Port RAM v1.8(id 04100203) | 存放数据,可读写 | `ipcore/data_ram/` |

两者容量相同,均为 **1024 × 32 bit = 4 KB**,并且底层复用**同一个 36 Kb 存储原语** `GTP_DRM36K_E1`。ROM 与 RAM 的差别仅在于:ROM 把 `c_RAM_MODE` 设为 `"ROM"` 并把全部写端口接到常 0。

- 厂商 / 器件:Logos2 / `PG2L100H` / `FBG484` / 速度等级 `-6`
- 生成工具:IP Compiler `2022.2-SP6.4` build 146967
- 综合脚本:`set_option -vlog_std v2001`、`set_option -disable_io_insertion 1`

> `ip_backup` 目录中**没有 RAM**,只有一份旧版 `inst_rom` 的配置快照,详见第 6 节。

---

## 2. IP 核一:inst_rom(只读指令 ROM)

### 2.1 配置文件与源码

| 文件 | 说明 |
| :-- | :-- |
| `inst_rom/inst_rom.idf` | IP 配置文件(XML),记录全部参数与端口定义 |
| `inst_rom/inst_rom.v` | 用户层封装,含参数声明与例化(116 行) |
| `inst_rom/rtl/ipm2l_rom_v1_8_inst_rom.v` | ROM 包装层,内部例化 SPRAM 并强制 `c_RAM_MODE="ROM"` |
| `inst_rom/rtl/ipm2l_spram_v1_8_inst_rom.v` | 实际存储原语封装(53.7 KB) |
| `inst_rom/rtl/inst_rom_init_param.v` | 固化在 RTL 中的初始化数据(`INIT_xx`) |
| `inst_rom/rtl/inst_rom_Reset_Value.v` | 复位值定义 |
| `inst_rom/inst_rom_tmpl.v` / `.vhdl` | 例化模板 |
| `inst_rom/inst_rom_tb.v` | 自动生成的仿真测试文件 |

### 2.2 参数配置(`inst_rom.idf`)

| 参数 | 值 | 含义 |
| :-- | :-- | :-- |
| `CAS_MODE` | `36K` | 使用 36 Kb 存储块 |
| `ADDR_WIDTH` | `10` | 地址位宽 10 → 1024 深度 |
| `DATA_WIDTH` | `32` | 数据位宽 32 |
| `INIT_EN` | `true` | 使能初始化 |
| `INIT_FILE` | `D:/riscv/tbtb/rom_test.dat` | 初始化文件 |
| `INIT_FORMAT` | `HEX` | 十六进制格式 |
| `RESET_TYPE` | `SYNC` | 同步复位 |
| `RST_VAL_EN` / `RST_VAL` | `false` / `0` | 不使用自定义复位值 |
| `OUTPUT_REG` | `false` | 不加输出寄存器 |
| `FAB_REG` | `false` | 不加 fabric 侧寄存器 |
| `CLK_EN` | `false` | 无时钟使能 |
| `ADDR_STROBE_EN` | `false` | 无地址选通 |
| `RD_OCE_EN` | `false` | 无读输出使能 |
| `CLK_OR_POL_INV` | `false` | 时钟不反相 |
| `POWER_OPT` | `false` | 不做低功耗优化 |

### 2.3 端口定义

| 端口 | 方向 | 位宽 | 说明 |
| :-- | :-- | :-- | :-- |
| `addr` | input | `[9:0]` | 读地址 |
| `clk` | input | 1 | 时钟 |
| `rst` | input | 1 | 复位(同步,高有效) |
| `rd_data` | output | `[31:0]` | 读出数据 |

共 4 个端口,**无写通道**。例化模板:

```verilog
inst_rom the_instance_name (
  .addr(addr),          // input  [9:0]
  .clk(clk),            // input
  .rst(rst),            // input
  .rd_data(rd_data)     // output [31:0]
);
```

---

## 3. IP 核二:data_ram(单口读写 RAM)

### 3.1 配置文件与源码

| 文件 | 说明 |
| :-- | :-- |
| `data_ram/data_ram.idf` | IP 配置文件(XML) |
| `data_ram/data_ram.v` | 用户层封装(165 行) |
| `data_ram/rtl/ipm2l_spram_v1_8_data_ram.v` | 存储原语封装 |
| `data_ram/rtl/data_ram_init_param.v` | 初始化数据(本 IP 未使能) |
| `data_ram/rtl/data_ram_Reset_Value.v` | 复位值定义 |
| `data_ram/data_ram_tmpl.v` / `.vhdl` | 例化模板 |
| `data_ram/data_ram_tb.v` | 自动生成的仿真测试文件 |

### 3.2 参数配置(`data_ram.idf`)

除与 ROM 相同的公共项外(均为上表同一取值),RAM 特有的参数:

| 参数 | 值 | 含义 |
| :-- | :-- | :-- |
| `WRITE_MODE` | `NORMAL_WRITE` | 普通写:写期间读输出保持不变 |
| `WR_BYTE_EN` | `true` | 使能字节写 |
| `BYTE_SIZE` | `8` | 每字节 8 bit |
| `BE_WIDTH` | `4` | 字节使能位宽 4(对应 32 bit 的 4 个字节) |
| `INIT_EN` | `false` | **不初始化**,`INIT_FILE = NONE`,上电内容不确定 |

`WRITE_MODE` 可选值:`NORMAL_WRITE`(当前值)/ `TRANSPARENT_WRITE`(写数据直通输出)/ `READ_BEFORE_WRITE`(输出旧值)。

### 3.3 端口定义

| 端口 | 方向 | 位宽 | 说明 |
| :-- | :-- | :-- | :-- |
| `addr` | input | `[9:0]` | 地址(读写共用) |
| `wr_data` | input | `[31:0]` | 写入数据 |
| `wr_en` | input | 1 | 写使能(1 = 写,0 = 读) |
| `wr_byte_en` | input | `[3:0]` | 字节使能,每 bit 对应 8 bit 字节 |
| `clk` | input | 1 | 时钟 |
| `rst` | input | 1 | 复位(同步,高有效) |
| `rd_data` | output | `[31:0]` | 读出数据 |

例化模板:

```verilog
data_ram the_instance_name (
  .wr_data(wr_data),          // input  [31:0]
  .addr(addr),                // input  [9:0]
  .wr_en(wr_en),              // input
  .wr_byte_en(wr_byte_en),    // input  [3:0]
  .clk(clk),                  // input
  .rst(rst),                  // input
  .rd_data(rd_data)           // output [31:0]
);
```

---

## 4. 两个 IP 核对比

| 对比项 | inst_rom | data_ram |
| :-- | :-- | :-- |
| 功能 | 只读 | 读 / 写 |
| 底层原语 | `GTP_DRM36K_E1`(`RAM_MODE="ROM"`) | `GTP_DRM36K_E1`(单口) |
| 容量 | 1024 × 32 bit | 1024 × 32 bit |
| 地址位宽 | 10 | 10 |
| 数据位宽 | 32 | 32 |
| 端口数 | 4 | 7 |
| 初始化 | 有(HEX 文件) | 无 |
| 读延迟 | 1 周期 | 1 周期 |
| 时钟 | 单时钟、同步 | 单时钟、同步 |
| 复位 | 同步,输出 0 | 同步,输出 0 |
| 级联 | 无(1 个 DRM 块) | 无(1 个 DRM 块) |

**层次关系**(两者同构):

```
inst_rom  / data_ram            ← 用户层封装(参数声明)
   └── ipm2l_rom_v1_8_*         ← ROM 包装层(仅 ROM,把写端口接 0)
        └── ipm2l_spram_v1_8_*  ← 存储原语封装(参数拼接、级联逻辑)
             └── GTP_DRM36K_E1  ← 实际 36Kb 存储块
```

由于 `ADDR_WIDTH(10) == DRM_ADDR_WIDTH(10)`,`CS_ADDR_WIDTH = 0`、`ADDR_LOOP_NUM = 1`,只占用**一个** DRM 块,不存在地址级联,因此不会引入额外读延迟。

---

## 5. 时序说明

### 5.1 总体特性

两个 IP 核都是**同步、单时钟、单端口**存储器,时序行为完全一致:

1. **读延迟 = 1 个时钟周期**
   地址在 `clk` 上升沿被采样,`rd_data` 在**下一个**上升沿更新。
   即:地址出现在第 N 拍,数据在第 N+1 拍有效。

2. **写与采样同拍**
   `wr_en = 1` 的那个上升沿把 `wr_data` 写入 `addr` 指定的位置。

3. **`NORMAL_WRITE` 行为**
   写操作期间 `rd_data` **保持不变**(既不输出新写入的值,也不输出旧值)。如果希望写数据直接反映到输出,需改用 `TRANSPARENT_WRITE`。

4. **字节写**
   `wr_byte_en[3:0]` 按字节掩码,`wr_byte_en[0]` 对应 `wr_data[7:0]`,依次类推;某位为 1 则对应字节被写入。

5. **复位**
   同步复位(`RESET_TYPE = SYNC`),复位期间/之后 `rd_data` 输出 `0`。

6. **单端口约束**
   读写共用 `addr`,同一拍只能执行一种操作,由 `wr_en` 选择。

### 5.2 逐拍时序表(以"读 → 读 → 写 → 读回 → 读"为例)

| 时钟周期 | `addr` | `wr_en` | `wr_data` / `wr_byte_en` | `rd_data` | 说明 |
| :--: | :--: | :--: | :-- | :-- | :-- |
| 1 | A0 | 0 | X | X | 发起读 A0 |
| 2 | A1 | 0 | X | **D(A0)** | A0 数据输出;同时发起读 A1 |
| 3 | A2 | 1 | W2 / `4'hF` | D(A1) | 写 A2 ← W2;读输出保持不变 |
| 4 | A2 | 0 | X | D(A1) | 发起读 A2(输出仍保持上一拍值) |
| 5 | A3 | 0 | X | **W2** | 读回刚写入的 W2;同时发起读 A3 |
| 6 | A3 | 0 | X | **D(A3)** | A3 数据输出 |

> `X` 表示该拍信号为无关值(don't care)。

要点复述:
- 读操作的 `addr` 与对应 `rd_data` **固定相差 1 个周期**;
- 写操作**不占用额外周期**,与读一样在上升沿完成;
- 写完后的下一拍发起读,再下一拍即可读回写入值(共 2 拍后可见)。

### 5.3 修改参数会如何影响时序(重要)

| 参数 | 若改为 1 | 影响 |
| :-- | :-- | :-- |
| `OUTPUT_REG` | 打开输出寄存器 | 读延迟由 **1 周期变为 2 周期** |
| `FAB_REG` | 打开 fabric 侧寄存器 | 再增加 1 周期延迟 |
| `CLK_EN` | 打开时钟使能 | 增加 `clk_en` 端口,读操作受其控制 |
| `ADDR_STROBE_EN` | 打开地址选通 | 增加 `addr_strobe` 端口 |
| `RD_OCE_EN` | 打开读输出使能 | 增加 `rd_oce` 端口,读输出可控 |
| `RESET_TYPE` | `ASYNC` | 复位变为异步 |

> 自动生成的 `inst_rom_tb.v` / `data_ram_tb.v` 中,校验逻辑正是按 `OUTPUT_REG` 的取值决定在 1 拍还是 2 拍后比对数据(`inst_rom_tb.v` 第 140-142 行、`data_ram_tb.v` 第 241-243 行)。修改 `OUTPUT_REG` 后需同步复核 tb。

---

## 6. ip_backup 目录说明

`ip_backup` 下**只有 1 个文件**:

```
ip_backup/20260905123122/inst_rom/inst_rom.idf
```

它是**旧版 `inst_rom` 的配置快照**,与当前版本的关键差异:

| 参数 | 备份版本 | 当前版本 |
| :-- | :-- | :-- |
| `ADDR_WIDTH` | 9(512 深度) | 10(1024 深度) |
| `DATA_WIDTH` | 18 | 32 |
| `CAS_MODE` | `18K` | `36K` |
| `RESET_TYPE` | `ASYNC` | `SYNC` |
| `INIT_FORMAT` | `BIN` | `HEX` |

结论:`ip_backup` **不包含第二个 RAM**,只是 ROM 的历史配置备份,"两个 IP 核"的说法仅适用于 `ipcore` 目录。

---

## 7. 使用注意事项

1. **两个 IP 均未接入 CPU 顶层**
   `myriscv/` 目录下的源码(含 `topcpu.v`)中**没有** `inst_rom` / `data_ram` 的例化,目前 IP 是独立生成的,尚未与 CPU 相连。后续需要在顶层(或 `ifu` / `memu`)中例化并处理地址译码。

2. **`data_ram` 上电内容不确定**
   `INIT_EN = false`,仿真时若直接读未写过的地址会得到未知值;自动生成的 `data_ram_tb.v` 也是先写满再读回来校验的。

3. **`inst_rom` 的初始化文件路径**
   `INIT_FILE` 指向 `D:/riscv/tbtb/rom_test.dat`,这是**生成时**用的路径。实际初始化数据已固化在 `rtl/inst_rom_init_param.v` 的 `INIT_xx` 参数中,换机器编译不会因为该路径不存在而失败,但若要更新 ROM 内容需重新生成 IP。

4. **读延迟需在流水线中考虑**
   1 周期读延迟意味着取指/访存阶段需要相应的流水寄存或旁路处理;若为了时序余量打开 `OUTPUT_REG`,延迟会变成 2 周期,流水线逻辑需同步调整。

5. **`rst` 为同步复位**
   复位信号需与 `clk` 同步释放,避免亚稳态。

---

## 附录:文件清单速查

```
ipcore/
├── inst_rom/                     ← IP 核 1(只读 ROM)
│   ├── inst_rom.idf              IP 配置
│   ├── inst_rom.v                用户层封装
│   ├── inst_rom_tmpl.v/.vhdl     例化模板
│   ├── inst_rom_tb.v             测试文件
│   ├── generate.log              生成日志
│   ├── init_param_hex_exmp.dat   初始化格式示例(HEX)
│   ├── init_param_bin_exmp.dat   初始化格式示例(BIN)
│   └── rtl/
│       ├── ipm2l_rom_v1_8_inst_rom.v
│       ├── ipm2l_spram_v1_8_inst_rom.v
│       ├── inst_rom_init_param.v
│       └── inst_rom_Reset_Value.v
└── data_ram/                     ← IP 核 2(单口 RAM)
    ├── data_ram.idf              IP 配置
    ├── data_ram.v                用户层封装
    ├── data_ram_tmpl.v/.vhdl     例化模板
    ├── data_ram_tb.v             测试文件
    ├── generate.log              生成日志
    ├── init_param_hex_exmp.dat
    ├── init_param_bin_exmp.dat
    └── rtl/
        ├── ipm2l_spram_v1_8_data_ram.v
        ├── data_ram_init_param.v
        └── data_ram_Reset_Value.v

ip_backup/
└── 20260905123122/inst_rom/inst_rom.idf   ← 旧版 ROM 配置快照(9×18 / 18K / 异步复位)
```
