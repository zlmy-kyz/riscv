# digits10 ABI1 单次实板诊断

2026-10-16：**用户授权板优先诊断、关键HDL未完成、时序待确认**。本软件不要求先补HDL关键组；用户负责重新生成并下载包含最新片内RAM响应增加1拍、DVP首级FF `syn_useioff=1` 修改的CNN位流。旧成功预处理位流不包含本版CNN，旧CNN修复前位流也不能作为本版。没有启动PDS、下载、串口或板测。

固定应用：[build/diag_20261016_c/program.bin](build/diag_20261016_c/program.bin)，41940字节，入口/装载地址 `0x40000000`，SHA256 `d08909dd14a5226c4a8ae58a6d07b8f3c7d31e46b4d66d6a9e9917a44153bff4`，Loader CRC `a608d0f6`。固定参数包：[model/diag_20261016_a/model.json](model/diag_20261016_a/model.json)，MODEL_ID `05a032af`，6222个word、24888字节小端装载流，CRC32 `0ca5949e`，装载流SHA256 `fa210d89f4ef30a4f26e90f556f7ce3e351756df6f22f982b8081335da7fccfd`。参数已经编进BIN，不另发压缩字节包。

这是未训练的确定性诊断包，6152个权重全非零（3176负、2976正），66个bias全非零，shift `[5,5,4,0]`。MODEL_ID由合同/诊断域分隔符及装载流SHA256前4字节小端生成，ID不是训练质量证明。四层F分别为 `(7,1,3)/(3,3,1)/(1,4,1)/(1,0,1)`；参考检查逐通道INT32精确上界及ABI保守bias界。权重每个字节零扩展成word，负数不做32bit符号扩展；CRC覆盖6222个word，不能使用紧凑权重CRC。

## 执行

用户重新生成并下载本次修复后的CNN位流；不修改ROM/RAM Loader初始化镜像，不替换历史成功BIN。关闭串口助手，执行以下命令，按工具提示按下/释放KEY0、等待DDR就绪，再按Enter。COM9按实际端口替换。日志目录必须不存在；首败不重试、不续跑，不清串口积压。

```powershell
Set-Location D:\riscv\RISCV
python tools/cnn_digits_diag/run.py --port COM9 --log-dir sim/cnn/board/diag_20261016_01
```

Python环境已有pyserial 3.5，工具沿用现有Loader 115200 8N1。一次41940字节固件下载后，CPU检查三个ABI ID，装载/提交模型并核数量、CRC、MODEL_ID和MODEL_VALID；实际STREAM_START采A并领取，立即STOP并等待尾帧结束，完成PP后记录BUF/SEQ，CNN只执行一次。CPU检查864读拍、1024灰度字节、10个signed分数、最低索引argmax、错误状态及周期。正常CNN硬超时3秒、软件轮询4秒，模型装载/采集/PP/ACK均有独立上限。

同一PP输出保持到完整导出结束：CPU读实际DDR RGB96做CRC，再分27个1024字节CN01 DATA包及1个END包导出。PC核包头/载荷/整幅CRC和序号地址，按合同从该实际RGB96采样32灰度、执行全部整数CNN，逐项比较10分数及argmax。CNN耗时按CYCLES/93.75MHz换算。参考不读取RTL计算数据作为输入，也不由分数反推张量。固件不执行卷积。

导出后释放A，若STOP产生B尾帧，使用B自己的SEQ令牌领取/登记DISCARD/释放；两块FREE、采集停止、所有发布帧都进入领取/释放账本后才输出CNN_RELEASED。PC比较成功才发送Q，CPU核终态并结束。若PC发现分数错误，此时Camera已停止且账本已关闭，不发送Q、不重试，全部证据保留。未完成的异常作业不声明所有权闭环；板端错误诊断保存当时账本，必须由用户KEY0开始新目录复测。

日志目录保存完整 `uart.rx.bin` / `uart.tx.bin`、Loader/数据包RX/TX偏移账本、总壁钟耗时、固定BIN/manifest/参数副本、`rgb96.partial`（导出进度证据，成功时也保留）、`rgb96.bin/.png`、`gray32.png`、PC参考gray/三层卷积/GAP/10分数、`board_scores.json`、`comparison.json`、`result.json`及成功后的`verified.json`。部分导出或板端先失败时，只保留实际收到的数据，不能补造完整图像/参考。复核命令：

```powershell
python tools/cnn_digits_diag/run.py --verify sim/cnn/board/diag_20261016_01
```

失败时保留整个目录，不只给PASS/FAIL摘要。工具无串口刷新、重传、自动复位或自动重试。发Q前PC等待上限30秒；一般参考执行远小于该上限，暂停调试可能导致固件COMMAND_TIMEOUT，应保留该首败。

## 已做检查与边界

离线收据：`sim/cnn/board_diag_20261016_a/checks_02/review.json`。7种图案（黑/白/128灰/红/绿/蓝/非对称空间图案），Python宽整数与独立C int64实现的全部参考层字节和10分数一致，含INT32最小值、正负半值舍入检查。原生设备模型编译实际固件C，检查所有6222次模型DATA写入与外部包逐word一致，独立逐bit CRC；12个正常/故障场景及28个拒绝检查，覆盖尾帧有/无、模型无效/数量错、CNN错误/超时/身份/拍数/灰度计数错、ACK错、释放失败，以及类别不变但一个分数错误。分片回放校验完整Loader与CN01串口交换；合成日志必须标OFFLINE_SYNTHETIC_TEST，默认实板复核拒绝该来源。

RV32I交叉构建检查所有代码指令合法、ELF/BIN字节一致、程序/BSS小于60KiB、保留4KiB栈，静态最深调用栈368字节。原生模型不是RTL，也不执行RISC-V指令；这些检查不能证明RAM新增响应级、DDR读仲裁、CNN实际算术或时序正确。未运行HDL、Full Boot、CoreMark、ISA或DDR PHY。

首次交叉构建 `build/diag_20261016_a` 因C代码误导缩进告警失败，日志保留；修复后b通过，随后PC参考身份检查加强，新身份c及checks_02为最终入口。b及checks_01保留但不用于本次上板。固件b/c字节相同，最终manifest绑定c对应的PC代码。

复现开发入口（仅在确需修改/复验时使用新tag，不覆盖已封存产物）：

```powershell
python tests/cnn_digits_diag/build.py --tag NEW_BUILD_TAG
python sim/cnn/board_diag_20261016_a/check_software.py --tag NEW_CHECK_TAG
python tools/cnn_digits_diag/run.py --plan-only
```

`make_model.py`为一次性确定性生成器，禁止覆盖已存在包；`prepare.py`只保留最初脚手架来源，不可用它覆盖最终源文件。`seal.py`产生唯一软件输入副本与放行收据，不编译/执行HDL。设计身份复用时序修复收据中的39项RTL：仅两项修复后的哈希更新，其余不变；原43项清单中另外4项PDS/约束/报告不在本轮复核范围。本轮不审PDS/位流，不将源码身份一致写成时序通过。该封存不是完整厂家HDL运行包，未提供HDL执行入口。

**实板成功最多证明同一次实际RGB96输入与此诊断参数包的整网10分数/类别一致。没有逐层硬件导出，不能写逐层验证通过、全部异常/并发通过或真实数字识别成功。**
