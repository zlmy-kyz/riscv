from pathlib import Path
import json
R=Path('D:/riscv/RISCV')
p=R/'doc/UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md';s=p.read_text(encoding='utf-8-sig')
s=s.replace('run_repaired.py 正在新目录 sim/uart_loader/build/ack_nack_stage8_repaired/full 从头重跑114帧。最终状态以该新目录 results.json 为准，未获得完整最终 PASS 前不进行实板专项。', 'run_repaired.py 已在新目录 sim/uart_loader/build/ack_nack_stage8_repaired/full 从头完成114帧并 PASS，退出0、Errors/Warnings0、无FAIL，保护/镜像/输入哈希全部不变。完整有效矩阵不是首次FAIL的前缀拼接；本轮使用修正后的检查器从头到尾重验。')
insert='''## 最终结果：仿真PASS，实板待验

机器门控 `sim/uart_loader/build/ack_nack_stage8/stage8_sim_result.json`：`STAGE8_ACK_NACK_SIM_PASS`，`board_result=NOT_TESTED`。本轮没有打开 COM11、生成/下载位流或重建 DAT。

| 验证层 | 结果与证据 |
| --- | --- |
| 完整矩阵（修复后从头重跑） | 114帧、37负例；77ACK/37NACK，其中39个只读CRC ACK，40次实际CRC读取；1983.46s；结果在 `sim/uart_loader/build/ack_nack_stage8_repaired/full/results.json`，SHA256 `b8ec6becb8817ec37302081abda0b84c8a225ae072037c9056c086e432e959db` |
| 原始路径和DDR | RX6000，pop/MMIO/LBU5999（真实溢出丢1）；TX/引脚解码6840；16SW/656LW，Pango AW/W16、AR656；FIFO峰值16；最低SP3F40；42365567退休、110835491周期 |
| 原速超时 | native8帧/2负例，未加速；坏Header113.941ms、截断body209.509ms；853.32s；历史检查器输入有准确归档，原速用例没有丢字节，计数修复不影响其逻辑 |
| UART重测 | uart8帧/2负例；真实低停止位+真实FIFO17字节输入；RX297/消费296、480TX、16SW/64LW，FIFO峰值16；121.25s |
| PC工具 | 8项离线检查PASS；108帧计划已准备；独立核验器5项离线防篡改/缺帧检查PASS，fixture不能作为实板证据 |
| 保存规则 | 原首次FAIL与输入归档保留；最终输入副本在 `build/ack_nack_stage8/final_sources/receipt.json`；阶段⑦37个原始/归档文件重新逐字节哈希核对一致，成功ELF/DAT未重建 |

原速报告生成时的检查器/runner/prepare输入绑定在 `attempt1_sources` 中；修复后的当前源对应新full/uart报告。最终门控保存历史与当前输入映射，不修改旧报告来消除FAIL或改写其输入哈希。

用户已说明阶段⑦验收后板子断电、串口关闭；尚未收到重新上电/阶段⑦成功位流就绪的确认，因此没有贸然发送测试。下一步先恢复板子和原成功位流（如上电后未保留配置则重新下载已有成功位流，不能重建未验收DAT），关闭串口助手、KEY0复位并等DDR初始化，再跑COM11专项首轮和复位后第二轮。

'''
s=s.replace('## 未覆盖\n',insert+'## 未覆盖\n')
s=s.replace('不在本矩阵。','不在本矩阵。两项UART故障注入均在等待新Header时；有效Header后各位置UART错误注入没有逐点覆盖。')
s += '''\n实板原始结果独立核验/归档（取得实际日志后再执行）：\n\n```powershell\n& C:/python/python.exe sim/uart_loader/stage8/check_board.py sim/uart_loader/board/ack_nack_stage8_first.json --output sim/uart_loader/board/ack_nack_stage8_first_result.json\n& C:/python/python.exe sim/uart_loader/stage8/check_board.py sim/uart_loader/board/ack_nack_stage8_after_reset.json --output sim/uart_loader/board/ack_nack_stage8_after_reset_result.json\n```\n'''
p.write_text(s,encoding='utf8')
entry='''## 最新进展：阶段⑧ACK/NACK专项仿真PASS，实板待验（2026-10-08）

阶段⑦成功源/ELF/DAT逐字节复制到tests/uart_loader/candidates/ack_nack_stage8，未重建镜像；PC专项工具在tools/uart_loader/candidates/ack_nack_stage8。主IP继续引用原build/ddr_crc，生产C/RTL/IP/PDS不改，阶段⑦37个原始/归档文件哈希全部一致。

完整114帧/37负例从头重跑PASS：77ACK/37NACK、39CRC ACK，16SW/656LW；RX6000/消费5999（真实FIFO溢出丢1）、TX/解码6840、FIFO峰值16，Errors/Warnings0、退出0，全部保护/镜像/输入哈希不变。全矩阵仅隔离TB的MMIO计时源TIME_SCALE64；另外native8帧原速PASS，坏Header113.941ms、截断body209.509ms；UART8帧独立重测PASS。首次长矩阵因检查器漏计丢字节而FAIL，原日志/输入保留；只修复隔离TB一行计数，已有全矩阵干净重跑，未改C/RTL。

机器门控sim/uart_loader/build/ack_nack_stage8/stage8_sim_result.json为STAGE8_ACK_NACK_SIM_PASS、board_result=NOT_TESTED；完整新日志在sim/uart_loader/build/ack_nack_stage8_repaired/full，最终输入副本在ack_nack_stage8/final_sources。PC工具8项及独立实板核验器5项离线检查PASS，不能当作实板证据。详见[阶段⑧记录](UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md)。

用户说明阶段⑦验收后板子已断电且串口关闭；本轮未打开COM11或生成/下载位流。下一步唯一动作：恢复板子及已有阶段⑦成功位流，关闭串口助手、KEY0复位并等DDR初始化，运行候选acceptance.py的108帧/35个主机可注入负例，首轮与复位后第二轮各用新日志名。仿真已经通过，不需要重建DAT/更换IP。UART帧错/溢出实板无法用普通串口可靠注入的部分继续单独标明未覆盖，不能记作专项实板全PASS；尚不推进⑨随机BIN或LOAD/VERIFY/RUN。

'''
p=R/'doc/CODEX_HANDOFF.md';s=p.read_text(encoding='utf-8-sig')
s=s.replace('最新结论是下方阶段⑦实板 PASS；历史小节里的', '最新实板结论仍为阶段⑦PASS，新增阶段⑧仿真PASS/实板待验见下方最新进展；历史小节里的')
s=s.replace('## 当前结果：阶段⑦DDR读回CRC32实板PASS，两轮各100次CRC32 PASS',entry+'## 当前结果：阶段⑦DDR读回CRC32实板PASS，两轮各100次CRC32 PASS',1)
p.write_text(s,encoding='utf8')
p=R/'doc/UART_Loader换对话交接_2026-10-08.md';s=p.read_text(encoding='utf-8-sig')
s=s.replace('## 新对话先读', '''## 新增阶段⑧结果（2026-10-08）

阶段⑧专项仿真已PASS，实板仍待验：修复隔离检查器的丢字节计数后从头完整114帧/37负例PASS，另有native8帧原速超时和uart8帧故障恢复PASS；Errors/Warnings0。机器门控为sim/uart_loader/build/ack_nack_stage8/stage8_sim_result.json。详情、原FAIL保留、成功输入归档、候选目录及实板命令见[阶段⑧记录](UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md)。

成功ELF/DAT只是逐字节复制至tests/uart_loader/candidates/ack_nack_stage8，未重建；主IP仍引用原build/ddr_crc。PC工具tools/uart_loader/candidates/ack_nack_stage8/acceptance.py为108帧/35个主机可注入负例，每项后PING/DDR CRC恢复。用户说明板子已经断电，本轮未操作COM11；先恢复原成功位流、KEY0复位并等DDR初始化，再进行两轮实板测试，保留UART帧错/溢出实板未覆盖边界。不推进⑨或LOAD/VERIFY/RUN。下方原阶段⑦交接内容继续作为成功基线说明。

## 新对话先读''',1)
s=s.replace('| ⑧ ACK/NACK 异常专项 | 待专项验收 | 仿真已有部分负例，不能视为实板异常路径 PASS |', '| ⑧ ACK/NACK 异常专项 | 专项仿真PASS / 实板待验 | 完整114帧/37负例、原速超时8帧、UART故障8帧；下一步COM11实板 |')
s=s.replace('先对照现有 C/PC/TB 实现列出专项用例，在隔离目录开发最小所需测试', '本段原方案的仿真/工具开发已完成，见上方新增阶段⑧结果；当前推进实板验收。原要求：对照现有 C/PC/TB 实现列出专项用例，在隔离目录开发最小所需测试')
p.write_text(s,encoding='utf8')
for rel in ['tests/uart_loader/README.md','sim/uart_loader/README.md','tools/uart_loader/README.md']:
    p=R/rel;s=p.read_text(encoding='utf-8-sig');first,tail=s.split('\n',1)
    note='''
2026-10-08新增：阶段⑧ACK/NACK专项仿真PASS，实板待验。完整114帧/37负例修复检查器后从头重跑PASS，另有原速超时与UART故障各8帧PASS；生产C/RTL/IP及成功DAT不改。见[阶段⑧记录](../../doc/UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md)。独立仿真入口sim/uart_loader/stage8/run_repaired.py；成功机器门控sim/uart_loader/build/ack_nack_stage8/stage8_sim_result.json。PC实板专项工具tools/uart_loader/candidates/ack_nack_stage8/acceptance.py为108帧/35负例。先恢复已有阶段⑦成功位流、KEY0复位并等DDR初始化，串口助手保持关闭；本轮未打开COM11。下方阶段⑦成功记录和旧入口继续保留，不能用旧runner冒充阶段⑧验收。
'''
    p.write_text(first+'\n'+note+tail,encoding='utf8')
p=R/'tests/uart_loader/candidates/ack_nack_stage8/README.md'
p.write_text('''# 阶段⑧隔离镜像候选

本目录从阶段⑦成功快照逐字节复制，源码/ELF/DAT未重建。镜像与主IP当前build/ddr_crc相同。阶段⑧仿真已PASS，实板待验；详见[专项记录](../../../../doc/UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md)。

build.ps1只是原成功源码快照，不是本隔离路径的构建入口，不运行它重建DAT。现阶段使用已验收同一ROM/RAM DAT；PC专项工具在tools/uart_loader/candidates/ack_nack_stage8，测试不要求换IP或新位流。
''',encoding='utf8')
print('Updated stage8 final record, handoff and README entrances; board remains NOT_TESTED')
