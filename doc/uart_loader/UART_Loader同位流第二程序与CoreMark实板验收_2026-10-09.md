# 同位流第二程序与 CoreMark 实板验收

日期：2026-10-09。用户完成五步脚本，Codex直接读取工程内真实串口JSON并重新运行独立检查。**本次要求的两步全部实板PASS：不重新生成FPGA位流更换第二程序；UART下载CoreMark，先通过两组短迭代算法CRC，再通过两组60次正式运行。**

## 实测结果

| 程序 | 文件字节 / 下载CRC32 | 实际响应 | 应用结果 |
| --- | --- | --- | --- |
| second | 587 / 280DE354 | 9 | 精确31字节SECOND_PROGRAM_PASS sum=11440，data/BSS检查通过 |
| performance_1 | 13216 / 6DB0C502 | 107 | seed e9f5，list e714，matrix 1fd7，state 8e3a，final e714 |
| validation_1 | 13224 / C9F9D302 | 107 | seed 18f2，list e3c1，matrix 0747，state 8d84，final e3c1 |
| performance_60 | 13220 / 984A86DF | 107 | 全部算法CRC正确，final a14c，Correct operation validated，无ERROR |
| validation_60 | 13228 / 92DCDC4B | 107 | 全部算法CRC正确，final 6770，Correct operation validated，无ERROR |

正式performance：60次，1664675013 ticks / 93.75 MHz = **17.756533472秒**，约3.379037924迭代/秒。正式validation：60次，1758638525 ticks = **18.758810933秒**，约3.198496974迭代/秒。两组均超过10秒；实际主机观察应用间隔17.8200273/18.8219919秒，均小于40秒，且程序ticks与主机观察相容，满足32位cycle单周期约45.81秒的计时边界。

程序为HAS_FLOAT=0的既有端口，UART中的整数Iterations/Sec均为3；以上吞吐用原始ticks计算，validation结果用于另一组种子正确性检查。保留原GCC15.2.0、-Os、RV32I/ILP32、无LTO、静态2000-byte总缓冲、DDR代码/数据构建；未修改成功BIN以改变显示精度，不扩展为EEMBC认证分数。

两组1次ticks分别27742170和29303360，约0.29591648/0.31256917秒。短迭代输出的唯一ERROR为不足10秒，算法CRC全部正确，故仅记CRC_FUNCTIONAL_PASS；它们不是正式跑分。两个60次日志分别绑定此前对应模式的实际1次CRC日志及同一部署门控身份。

合计437/437响应：226 ACK、211 READY、0 NACK；5次唯一成功RUN。实际TX61611字节、协议RX26220字节、应用RX2223字节，响应双CRC、全部字段及应用完整输出均独立核验；零重试、零响应CRC错误、零额外RX。五份不同BIN的下载/VERIFY/RUN顺序正确。

## 同位流身份与归档

五份实际日志与此前Hello实板成功绑定同一位流文件：

`D:/riscv/RISCV/sim/uart_loader/build/verify_run_hello/pds_candidate/generate_bitstream/board_top.sbit`

SHA256：`31386f785e59f3de2a3499202fb404fc39dde6bbc4a2e5ecb906d754acc02eb0`。

独立报告 `D:/riscv/RISCV/sim/uart_loader/board/applications_stage3_independent_result.json` 为SECOND_PROGRAM_AND_COREMARK_ACTUAL_BOARD_PASS，与用户脚本生成的board_result.json内容完全一致。收据 `D:/riscv/RISCV/sim/uart_loader/board/applications_stage3_submission_result.json` 为SECOND_PROGRAM_AND_COREMARK_ACTUAL_BOARD_ARCHIVE_PASS。

**279项完整成功快照**保存在 `D:/riscv/RISCV/sim/uart_loader/board/applications_stage3_success/`，镜像原相对路径，包含196项冻结输入、74项证据、部署门控、原始五日志/用户汇总及新增独立报告。源文件与副本SHA256逐项匹配。196项冻结源副本、旧Hello170项成功快照、18项PDS来源/副本及五组仿真保护文件均检查一致。新门控生成时的board_result=NOT_TESTED保留为历史，以新增实板报告/收据为当前结果。

Codex没有打开COM11、重建软件、生成或下载位流，也没有改Loader/RTL/IP。用户完成现场操作；独立证据是实际串口协议/应用输出、BIN身份和已核验位流文件哈希，没有独立观察JTAG下载、KEY0或读回FPGA配置。板级执行成功不等同于新的内部指令退休测量，内部退休和data/BSS/栈监视来自已有仿真。

## 复现与范围

用户原始日志：`D:/riscv/RISCV/sim/uart_loader/board/applications_stage3_first/`。只读核验可选择新的输出文件名，不覆盖现有报告：

```powershell
& C:/python/python.exe D:/riscv/RISCV/sim/uart_loader/applications_stage3/check_all.py --directory D:/riscv/RISCV/sim/uart_loader/board/applications_stage3_first --output D:/riscv/RISCV/sim/uart_loader/board/applications_stage3_check_repeat.json
```

重新实板测试必须使用同一冻结BIN和成功Loader位流，日志选新目录，按五步脚本提示KEY0；准备过程和原失败保留见 [准备记录](UART_Loader同位流第二程序与CoreMark准备_2026-10-09.md)。

本次用户选定两步已完成；原宽范围第③关的额外至少10轮复位未包含在本次请求，仍未执行。没有新增掉电恢复、物理UART故障或DDR损坏注入验收，不扩展为任意未经审查BIN运行能力。
