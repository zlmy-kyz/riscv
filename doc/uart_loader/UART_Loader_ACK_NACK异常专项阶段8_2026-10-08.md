# UART Loader 阶段⑧ ACK/NACK 异常专项

日期：2026-10-08（Asia/Shanghai）。阶段⑦固定 64-byte DDR CRC32 两轮实板 PASS 为前置；本阶段只验收诊断协议的异常、恢复与副作用，不实现正式 LOAD/VERIFY/RUN。

## 最新结果：阶段⑧主机可注入异常两轮实板PASS（2026-10-08）

用户用PC工具r2在COM11提交首轮与after_reset轮；独立struct/zlib逐帧核验两份原始日志、请求矩阵、响应全部字段/CRC、时序、额外RX检查记录与终端输出，每轮108/108 PASS：73ACK、35个预期NACK、37个DDR CRC ACK。合计216帧、146ACK、70个预期NACK、74个CRC ACK，实际DDR CRC均23C3E508；错误后的合法PING/CRC恢复全部通过。两轮均接受新SEQ1并完成至SEQ73；未独立观察KEY0，未采集板上位流文件身份。

现行板级汇总为sim/uart_loader/board/ack_nack_stage8_pc_r2_board_result.json，board_result=PASS_HOST_INJECTABLE_ONLY；UART帧错/FIFO溢出实板仍NOT_TESTED，阶段⑧完整实板范围NOT_COMPLETE。旧ack_nack_stage8_board_result.json及原首轮误报FAIL保留为历史证据，不覆盖；旧仿真报告内NOT_TESTED也保留生成时状态。详见[两轮验收记录](UART_Loader_ACK_NACK主机可注入异常两轮实板验收_2026-10-08.md)。

成功ELF/ROM/RAM、阶段⑦37项快照、阶段⑧27项候选、PC原/r2的11项输入档案及全矩阵221项保护文件/25项仿真输入哈希均匹配。未重建DAT、修改C/RTL/IP/PDS或重新仿真；Codex仅离线核验/归档，所有上板操作继续由用户负责。本轮未启动⑨随机BIN或正式LOAD/VERIFY/RUN；后续须保留上述实板覆盖边界并使用隔离候选。

## 历史记录：首轮PC时序误报与r2复验准备（2026-10-08）

用户已运行首轮：终端94条PASS后停止，第95条truncated_magic_recover_ping记录FAIL。独立struct/zlib核对全部已收95个原始响应及请求矩阵，字段/CRC/预期状态全部一致；truncated_magic正确NACK8004为207.309ms，随后SEQ64合法PING ACK为10.289ms。错误来自PC工具：startswith('truncated_')把恢复PING/CRC也要求>=195ms；旧离线fixture同样给这些恢复ACK加延迟，掩盖了误判。原FAIL日志/终端和输入副本保留，不改写PASS；最后一帧没有完成额外RX检查，整轮仅记录94个完整工具PASS，第二轮尚未提交。

修正版在tools/uart_loader/candidates/ack_nack_stage8_r2/acceptance.py，仅对negative且预期status8004的真正截断包施加195ms下限；独立核验器sim/uart_loader/stage8/check_board_r2.py同步修正。12项时序回归复现旧95帧失败、修正版108帧快速ACK通过，且4类早到超时NACK仍拒绝；另8项通用PC离线检查PASS。成功C/RTL/IP/DAT和原仿真输入不变，不需要新位流/重建DAT。Codex未打开COM11，实板操作仍由用户负责。

板级门控sim/uart_loader/board/ack_nack_stage8_board_result.json为INCOMPLETE_RETEST_REQUIRED_PC_TIMING_FIX，不是阶段⑧实板PASS。详见[PC时序误报及r2复验](UART_Loader_ACK_NACK实板首轮时序误报与PC工具r2_2026-10-08.md)。下一步用户KEY0复位并等DDR后，使用r2工具和新日志ack_nack_stage8_first_pc_r2.json；再复位后另跑ack_nack_stage8_after_reset_pc_r2.json。每轮108/108 PASS再离线核验。不得继续阶段⑨，UART帧错/溢出实板仍未覆盖。

## 隔离和镜像身份

候选在 `tests/uart_loader/candidates/ack_nack_stage8/`，从 `verified/ddr_crc_stage7/` 逐字节复制 27 个软件/构建文件，未重新编译。复制记录 `sim/uart_loader/stage8/candidate_receipt.json`。

| 文件 | SHA256 |
| --- | --- |
| loader.elf | 49744ef735f2c14461594969004641f318f62991589aadf2209f9e15cf6de178 |
| loader_rom.dat | 21a590346a9a433cade6a4e85c34829620f86ae8ea0238b7be514ff78fa2376a |
| loader_ram.dat | 59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a |

生产 RTL、主 IP/PDS、成功 `build/ddr_crc`、Echo/CoreMark/旧阶段镜像和实板证据不改。候选里的 build.ps1 为成功源码快照，保留原字节，不作为此隔离目录的重新构建入口；本阶段直接读取同一成功 ELF/DAT。

## 本轮实现

- `tools/uart_loader/candidates/ack_nack_stage8/cases.py`：原始报文、预期 CMD/SEQ/status/实际 DDR CRC，仿真与 PC 工具共用。
- 同目录 `acceptance.py`：108 帧、35 个普通串口可注入负例；每个错误后合法 PING 和只读固定 DDR CRC，失败立即停止，不自动重试；JSON 每步保存输入/响应原始字节、预期/实际字段及 CRC、耗时和镜像身份。日志独占创建，拒绝覆盖旧证据。
- `sim/uart_loader/stage8/prepare.py`：复制隔离候选并从原 TB 生成独立扩展 TB；不修改原 runner/TB。
- `sim/uart_loader/stage8/run.py`：逐条 ISA/Harvard/ELF/DAT 审查、阶段⑦门控和档案哈希、三次 ROM 启动前置，再真实 CPU/UART/互连/DDR 桥专项。
- `sim/uart_loader/stage8/check_board.py`：实板结果用独立 struct/zlib 逐帧核验后独占归档，不覆盖旧证据；检查完整 108 帧、73 ACK/35 NACK/37 CRC ACK，以及请求矩阵、响应全部字段/CRC、耗时和元数据。工具不能独立证明用户实际按过 KEY0 或板上位流身份。
- `sim/uart_loader/stage8/check_pc_tool.py`：8 项离线工具检查，产物 `sim/uart_loader/build/ack_nack_stage8/pc_tool_results.json`，已 PASS。fixture 用独立 struct/zlib 编码；不是 CPU 仿真或实板证据。

## 用例和约定

| 错误类别 | 用例 | 预期 |
| --- | --- | --- |
| Header CRC | 坏 Header；坏 Header 后附合法 RUN/DDR_TEST 报文，要求整体排空 | 8001，响应 SEQ/CMD=0/0，无 DDR 操作或跳转 |
| DATA CRC | 64-byte DATA 尾 CRC；CMD12 空 DATA 的非零 CRC | 8001 |
| 地址 | base-4、base+1/+2/+4、60000000、FFFFFFFC | 8002，含非对齐和对齐但非固定 base |
| 长度/total | 0/63/65/256/257/FFFFFFFF；total 非零 | 8003，不按非法长度接收或写 DDR |
| 版本 | 0、2 | 8006 |
| 命令/flags | flags 低/高字节；正式 LOAD2/VERIFY3/RUN4；未知 FF | 8007 |
| 状态/向量 | 非 CRC 命令 image_crc 非零；CRC 有效但固定数据错误 | 8008 / 800A |
| 序号 | 旧 SEQ、同 SEQ 换命令、同 CRC SEQ 换预期 | 8009，成功序号/计数不变 |
| DDR CRC | 错 PC 预期；同 SEQ 正确预期重试 | 8001 返回实际 23C3E508；正确重试 ACK64 |
| 接收超时 | RV 半个 magic；18-byte Header；部分 DATA；部分 DATA_CRC | 8004；Header 未可信时 SEQ/CMD=0/0，已解析 Header 时保留请求身份 |
| UART 帧错 | 真实 RX 引脚低停止位；错误后恢复 | 8005，仅仿真 |
| FIFO 溢出 | 暂停 UART 总线握手，真实 RX 输入 17 bytes 填满 16-byte FIFO，丢弃第 17 byte | 8005，仅仿真服务饥饿注入 |

坏 Header 不能返回其中未经 CRC 验证的 SEQ/CMD。接收/校验错误排空后连续 100ms idle 再回 NACK；序号拒绝和 DDR CRC 失配已经消费完整合法包，不额外排空。接收超时加恢复等待约 200ms。CMD12 请求只有 36 bytes，LENGTH64 描述 DDR，不含 UART DATA。

全矩阵 114 帧、37 个负例。TIME_SCALE64 仅在隔离 TB force MMIO CYCLE 计时源，不改成功二进制、CPU/总线/UART/DDR 时钟或波特率；该矩阵用于覆盖全部分支/副作用，不作为原速 100ms 计时证据。另 native 8 帧、2 个负例，TIME_SCALE1，无 force 计时源，独立验证坏 Header 连续 idle 与截断 body 的接收+恢复等待。

TB 保留原始 RX→FIFO→MMIO→退休 LBU、TX MMIO→TXD 中心采样逐字节比较；逐帧检查 NACK/成功计数与最后 SEQ、RAM 分区/栈/哨兵、物理 DDR CRC、SW/LW/Pango 命令/退休值与越界哨兵。格式/地址/长度/序号等预先拒绝的包禁止 DDR 请求；有效CMD12的PC预期CRC失配仅允许16次LW、没有SW；任何 DDR 取指、trap/IRQ、总线 error 或不期望 UART error 均 FAIL。注入错误必须由 CPU 实际 CONTROL W1C 清 sticky、排空 FIFO 后恢复；不直接 force 错误状态位。

## 复现与状态

用户分工（2026-10-08）：实板下载、供电、KEY0复位和COM11串口验收由用户自行操作；Codex提供脚本/命令，并在用户提交日志后进行离线核验与归档。本阶段不由Codex打开COM11。每轮预期108帧全部PASS（73ACK/35个预期NACK，37个CRC ACK）；预期NACK本身是通过条件，任何RESULT: FAIL/超时/字段或CRC异常均须保留日志后停止。UART帧错/溢出实板仍未覆盖。

```powershell
cd D:/riscv/RISCV
& C:/python/python.exe sim/uart_loader/stage8/prepare.py
& C:/python/python.exe sim/uart_loader/stage8/check_pc_tool.py
& C:/python/python.exe sim/uart_loader/stage8/run.py --suite full
& C:/python/python.exe sim/uart_loader/stage8/run.py --suite native
# 检查器修复后的UART专项及完整新证据目录：
& C:/python/python.exe sim/uart_loader/stage8/run.py --suite uart
& C:/python/python.exe sim/uart_loader/stage8/run_repaired.py --suite full
```

runner 拒绝覆盖已有 results.json；复测应先在 runner 中选择新的隔离输出目录，保留原证据。prepare 不重建 ELF/DAT，候选不同内容时拒绝覆盖。前置或专项 FAIL 不产生新的成功凭据，停止下一层。

native 原速专项已 PASS：三次 ROM 启动前置、8 帧和 2 个负例，Errors/Warnings 0，保护/镜像/输入哈希全部不变。坏 Header 应答 113.941ms；截断 body 应答 209.509ms；16 SW/64 LW、429 RX/pop/MMIO/LBU、480 TX/解码，最低 SP=3F40，墙钟 853.32s。证据 sim/uart_loader/build/ack_nack_stage8/native/results.json 和 native/native/{modelsim.log,timing.csv}。首次 full 长矩阵在第113项最后 CRC 恢复请求处 FAIL：检查器把已退休 LBU 总数（丢字节后少1）与原始线缆字节位置比较，错误拦截合法 DDR 读；首次报告/日志保留 FAIL，不作为完整 PASS。原输入已逐文件按报告哈希保存 attempt1_sources/receipt.json。仅修正隔离 TB 一行：完整包门控由 cpu_lbu>=frame_end 改为 lbu_index>=frame_end；LBU 值、丢字节事件、原始 RX/FIFO/MMIO/退休映射检查仍保留。C/RTL/二进制均未改。新增 --suite uart 重跑8帧：真实低停止位与真实FIFO17-byte溢出、各自 NACK8005、CONTROL清错、PING及只读CRC恢复全部 PASS，Errors/Warnings0；16 SW/64 LW，FIFO峰值16。run_repaired.py 已在新目录 sim/uart_loader/build/ack_nack_stage8_repaired/full 从头完成114帧并 PASS，退出0、Errors/Warnings0、无FAIL，保护/镜像/输入哈希全部不变。完整有效矩阵不是首次FAIL的前缀拼接；本轮使用修正后的检查器从头到尾重验。离线 PC 工具 8 项 PASS；108 帧 board_plan.json 已生成，无串口操作。

仿真 PASS 后实板沿用阶段⑦成功位流与同一 DAT，不需要新 IP/位流。关闭串口助手，KEY0 复位并等 DDR 初始化，再从工程根运行：

```powershell
& C:/python/python.exe tools/uart_loader/candidates/ack_nack_stage8/acceptance.py --port COM11 --log sim/uart_loader/board/ack_nack_stage8_first.json
# 再次 KEY0 复位、等 DDR 初始化后，另存第二轮：
& C:/python/python.exe tools/uart_loader/candidates/ack_nack_stage8/acceptance.py --port COM11 --log sim/uart_loader/board/ack_nack_stage8_after_reset.json
```

仅计划可用 `--plan-only --log <新文件>`，不会打开串口。实板 108/108 字段与原始应答比较 PASS 后仅记 `PASS_HOST_INJECTABLE_ONLY`；`stage8_full_board_result=NOT_COMPLETE`，UART 帧错/溢出实板仍 NOT_TESTED，不能以 fixture/仿真替代板级证据。完整专项覆盖范围明确并验收前不推进阶段⑨。

## 最终结果：仿真PASS，实板待验

机器门控 `sim/uart_loader/build/ack_nack_stage8/stage8_sim_result.json`：`STAGE8_ACK_NACK_SIM_PASS`，`board_result=NOT_TESTED`。本轮没有打开 COM11、生成/下载位流或重建 DAT。

| 验证层 | 结果与证据 |
| --- | --- |
| 完整矩阵（修复后从头重跑） | 114帧、37负例；77ACK/37NACK，其中39个只读CRC ACK，40次实际CRC读取；1983.46s；结果在 `sim/uart_loader/build/ack_nack_stage8_repaired/full/results.json`，SHA256 `b8ec6becb8817ec37302081abda0b84c8a225ae072037c9056c086e432e959db` |
| 原始路径和DDR | RX6000，pop/MMIO/LBU5999（真实溢出丢1）；TX/引脚解码6840；16SW/656LW，Pango AW/W16、AR656；FIFO峰值16；最低SP3F40；42365567退休、110835491周期 |
| 原速超时 | native8帧/2负例，未加速；坏Header113.941ms、截断body209.509ms；853.32s；历史检查器输入有准确归档，原速用例没有丢字节，计数修复不影响其逻辑 |
| UART重测 | uart8帧/2负例；真实低停止位+真实FIFO17字节输入；RX297/消费296、480TX、16SW/64LW，FIFO峰值16；121.25s |
| PC工具 | 8项离线检查PASS；108帧计划已准备；独立核验器5项离线防篡改/缺帧检查PASS，fixture不能作为实板证据 |
| 保存规则 | 原首次FAIL与输入归档保留；最终输入副本在 `build/ack_nack_stage8/final_sources/receipt.json`；阶段⑦37个原始/归档文件重新逐字节哈希核对一致，成功ELF/DAT未重建 |

原TB最终RESULT行中的pings=3是旧21帧套件遗留硬编码显示，不用于验收；真实计数逐帧与RAM强制核对，full最后CHECK RX显示37、native/uart显示2。正式统计以cases/decoded_responses、逐帧CHECK及机器门控为准。保留验收过的原输入和日志，不事后改写显示字段。

原速报告生成时的检查器/runner/prepare输入绑定在 `attempt1_sources` 中；修复后的当前源对应新full/uart报告。最终门控保存历史与当前输入映射，不修改旧报告来消除FAIL或改写其输入哈希。

用户已说明阶段⑦验收后板子断电、串口关闭；尚未收到重新上电/阶段⑦成功位流就绪的确认，因此没有贸然发送测试。下一步先恢复板子和原成功位流（如上电后未保留配置则重新下载已有成功位流，不能重建未验收DAT），关闭串口助手、KEY0复位并等DDR初始化，再跑COM11专项首轮和复位后第二轮。

## 未覆盖

没有 DDR PHY 训练、永久 DDR 事务停顿 watchdog、随机/大程序/全部 DDR 地址、任意 BIN、LOAD/VERIFY/RUN、下载后 DDR 执行。UART 溢出仿真注入代表软件服务暂停，不是普通 USB 串口在正常轮询时可靠制造溢出的证据。序号回绕、任意噪声/长时压力和所有多错误优先级组合不在本矩阵。两项UART故障注入均在等待新Header时；有效Header后各位置UART错误注入没有逐点覆盖。


实板原始结果独立核验/归档（取得实际日志后再执行）：

```powershell
& C:/python/python.exe sim/uart_loader/stage8/check_board.py sim/uart_loader/board/ack_nack_stage8_first.json --output sim/uart_loader/board/ack_nack_stage8_first_result.json
& C:/python/python.exe sim/uart_loader/stage8/check_board.py sim/uart_loader/board/ack_nack_stage8_after_reset.json --output sim/uart_loader/board/ack_nack_stage8_after_reset_result.json
```
