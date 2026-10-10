# 文档导航

先读 [开发交接](CODEX_HANDOFF.md)；摄像头/CNN同学从[接入交接](project/摄像头与CNN开发交接_2026-10-10.md)开始，再核对[当前 SoC 结构](SoC结构说明_2026-10-04.md)和[CPU 性能优化起点](CPU性能优化起点与验收约定_2026-10-10.md)。交接中的最新结论优先于阶段文档里的历史“待验证”描述；实板、仿真和准备状态分别核对。

| 目录 | 内容 | 推荐入口 |
| --- | --- | --- |
| [`board/`](board/) | 板级约束、时钟、复位、位流和实板复验 | [主工程新位流六轮实板验收](board/主工程新位流六轮实板验收_2026-10-10.md) |
| [`cpu/`](cpu/) | CPU 流水线、异常中断、ROM/RAM 时序和性能测量 | [2B主RTL集成与重建](cpu/CPU性能计数器2B并入主RTL_2026-10-10.md)、[2B计数器设计](cpu/CPU性能计数器2B_MMIO与隔离候选_2026-10-10.md)、[2A物理性能基线](cpu/CPU_DDR性能测量2A与首批物理基线_2026-10-10.md) |
| [`异常和中断/`](异常和中断/) | 异常与中断十二步实现记录 | [步骤清单](异常和中断/异常与中断实现步骤清单.md) |
| [`ddr/`](ddr/) | DDR 桥、用户口与集成仿真 | [Pango DDR3 用户口](ddr/Pango_DDR3用户口与转接桥说明.md) |
| [`uart/`](uart/) | UART 模块、MMIO、Echo 和板级回显证据 | [Echo 实板确认](uart/UART_Echo实板基本回显确认_2026-10-07.md) |
| [`uart_loader/`](uart_loader/) | Loader 各阶段的开发、仿真和实板记录 | [Loader 换对话交接](uart_loader/UART_Loader换对话交接_2026-10-08.md) |
| [`software/`](software/) | 裸机 C、BSP、构建和目录迁移 | [统一 BSP 十轮实板验收](software/统一BSP与十轮复位下载实板验收_2026-10-10.md) |
| [`coremark/`](coremark/) | CoreMark 移植、构建、CRC 和正式实板结果 | [60 次实板验收](coremark/CoreMark实板60次验收_2026-10-07.md) |
| [`reference/`](reference/) | 研究方案、外部资料与参考图 | [AI 加速方案](reference/AI加速多方案比较与推荐实施方案.md) |
| [`project/`](project/) | 仓库发布、目录整理和过程记录 | [本次文档整理](project/文档目录整理_2026-10-10.md) |
| [`assets/`](assets/) | 结构图、源图和生成脚本 | [UART 阶段 3 结构图](assets/SoC结构图_UART阶段3_2026-10-05.svg) |

日期命名的阶段文件保留原名和原始验证范围；移动只改变路径，不改变 PASS/FAIL 结论或镜像身份。仓库 `.gitignore` 继续只发布精选文档，其他记录保留在本地 `doc/` 中。
