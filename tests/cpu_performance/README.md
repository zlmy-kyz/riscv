# CPU 性能微基准（独立实验）

入口：`C:/python/python.exe tests/cpu_performance/build.py --tag <新名称>`。
目录已存在时拒绝覆盖。汇编、链接脚本、ELF/BIN、反汇编、符号、DAT、命令和 SHA256 都保存在本实验 `build/<tag>/`；不修改生产 ROM/RAM 初始化或成功软件。

构建固定 RV32I、ILP32、无压缩指令、无链接松弛，入口 `0x40000000`。确定性 workload 包括：128 条顺序 ALU、小循环、未跳转分支、固定 seed 跳转块链、64-word 顺序/随机 load、依赖指针追踪、64-word store 及计时外回读、跨字节槽的 SB/SH/LB/LBU/LH/LHU。

计时开始/结束指令均读 `0x10000008`。TB 以请求被接受的边沿建立 `[S,T)`，不以函数入口或指令退休替代计时边沿。计时读本身及窗口边界的流水线重叠会影响 `instret`；解释器校验完整退休路径及每个窗口的实际退休数。

数组/置换在装载时已初始化，随机数生成不在计时区间。所有指令在 DDR 执行，数据数组也在 DDR。每个 workload 后比较 checksum，store 结果及 signed/unsigned 子字读取在计时外另验；失败上报 TEST_STATUS=3，全部通过上报 2。

默认物理测量使用仿真专用的 128-bit Pango 用户口装载及全量物理 DDR 回读，然后释放 CPU；初始化入口位于仿真派生包装器，不进入主 RTL/PDS。另保留独立 ROM CPU copy-loader，用于功能 Full Boot 或 `physical-copy`。该 ROM 不替代已验收 UART Loader，不提供实板部署门控。

运行、口径和限制见 [仿真说明](../../sim/cpu_performance/README.md)。本阶段工作集为 256-byte 数组、512-byte 节点和小代码；容量/冲突扫描、缓存一致性、DMA、正式实板跑分留在后续阶段。
