# CoreMark 短迭代 Full Boot

根目录执行 `C:/python/python.exe sim/coremark/run.py`，或用 `--mode performance` /
`--mode validation` 选单组。runner仅读取已构建的DAT，不重编译CPU软件或转换镜像。
`--audit-only` 核对已有ELF/BIN/DAT、入口、段布局、ABI、最终RV32I指令和未解析符号。
默认短验收要求2000字节、ITERATIONS=1，两组配置匹配。
`--iterations N`支持1..100次，N>1读取tests/coremark_baremetal/build/<mode>_N，
保存到sim/coremark/build/<mode>_N及results_N.json，不覆盖单迭代凭据。
2026-10-07两组60次完整RTL仿真已CRC_FUNCTIONAL_PASS，ModelSim Errors0/Warnings0，
墙钟分别5540.29/5387.02秒（约92/90分钟）；ModelSim10.6c运行时长使用整数微秒。
结果在build/results_60.json，final CRC分别a14c/6770，供对应DAT实板比较。
模型计时约7.85/8.31秒，时间不足错误预期保留；模型JSON保留原值。
随后用户两组实板60次CRC/运行时长验收PASS，ticks分别1664676818/1758636430，
按93.75MHz为17.75655/18.75879秒，CRC与模型一致。文本/凭据在board/*iter60_user_20261007*，
与模型结果分别保留；成功DAT在tests/coremark_baremetal/verified/{performance_60,validation_60}/。
详见doc/coremark/CoreMark实板60次验收_2026-10-07.md。

独立ModelSim库/脚本/日志/原始UART在 `build/<mode>/`，总结果为 `build/results.json`，
每组 `validated_image.json` 绑定接受过的ELF/BIN/DAT SHA-256。
CRC通过记作CRC_FUNCTIONAL_PASS，单迭代分数状态为NOT_VALID_SHORT_RUN，
多迭代模型结果为NOT_A_BOARD_SCORE，不报告实板分数。

测试使用真实 `soc_top/mycpu_sync`、原ROM loader、同步片内ROM/RAM模型、
从A5毒化状态启动的64 KiB DDR用户口模型，不能替代DDR PHY训练或实板验证。
DDR模型由Echo已验收单拍Pango用户口模型复制，AW/AR/W/R分别有独立背压/延迟；
本目录BRAM模型也从Echo复制，独立运行，不改共用TB。

检查逐笔loader地址/数据/strobe，跳转前逐字比较DDR与最终DAT；BSS开始为A5，
main之前全部清零；SP位于4 KiB栈且最低64字节guard未碰；DDR写限制在BSS/栈。
无CPU同步异常、IRQ、总线error或超时，UART只能SB lane0发送。
TXD按115200/8N1独立中心采样，字节与MMIO接受序列一致，保存原始LF文本。
两次CYCLE读的接受周期差与UART报告ticks必须一致。
主程序返回并等TX空闲后结束；低于10秒时原版时间错误必须是唯一ERROR行，
达到10秒时必须有Correct operation validated且没有Errors detected/ERROR。
种子/三种已知CRC必须匹配；单迭代final必须等于crclist，多迭代final保存为对应DAT参考。

保护哈希包含生产RTL、官方算法/头/清单、PDS/FDC、主IP初始化、ROM loader和
输出30/Echo成功DAT。仿真失败看对应日志，不改算法或放宽CRC检查制造PASS。
ModelSim使用D:/modelsim/win64pe，本次新建TB不含物理DDR或LED watchdog。
