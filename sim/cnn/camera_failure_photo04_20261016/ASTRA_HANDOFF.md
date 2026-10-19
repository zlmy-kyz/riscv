# 相机连续格式失败：Astra最小定位交接

2026-10-16，Sol只读复核，未修改RTL/IP/FDC/PDS/固件，未启动HDL/PDS/串口。根因未证实，不能认定已经找到RTL缺陷。固定程序仍为`tests/cnn_digits_photo/build/photo_20261016_a/program.bin`，SHA256 `2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4`；当前39项RTL+csr_defs.vh与原封存一致。

先读`doc/CODEX_HANDOFF.md`顶部及同目录`review.json`。原始证据不复制、不覆盖，位置：

- `sim/cnn/board/photo_20261016_01/`：完整源/PP/CNN比较一致，但源PNG已有密集绿紫点；捕获CRC→源DDR→CPU→PC CRC闭合，优先关注捕获CRC之前的传感器/DVP链路。
- `sim/cnn/board/photo_20261016_02/`：CAM_ERR3、SEQ0、CLAIMS0、BUFSTATE100，未发布帧。
- `sim/cnn/board/photo_20261016_03/`：CAM_ERR3、A/SEQ1已领取、BUFSTATE123，B在途采集错误；A仍CPU持有，不能套用“无领取”。既有复核在`sim/cnn/camera_failure_photo03_20261016/review.json`。
- `sim/cnn/board/photo_20261016_04/`：用户再次重拍仍CAM_ERR3、SEQ0、CLAIMS0、BUFSTATE100；模型VALID，PP/CNN未启动。337条Loader逐条响应、GC及唯一失败文本已从原RX/TX复核，全部原文件哈希有效，无重传/重试。

用户曾重新插拔摄像头，但仍出现格式错，不把插拔视为修复。各次实际供电/线缆状态未被工具测量。现有PDS报告满足“下降沿launch、上升沿capture、输入0–3ns预算”，10个DVP首级FF已实际打包I/O；这不证明真实相机推出相位或信号质量。

下一步定位应停止无改动盲拍。优先核实际PCLK/DATA/HREF/VSYNC相位、连接与供电，或使用传感器固定测试图。需要RTL观测时，请Astra最小化增加首次format_error的子原因、line_bytes、lines和当拍HREF/VSYNC/字节相位；首错锁存，不能被后续排空/复位覆盖而失去证据，跨域读取必须有一致性保护。由Astra决定合适的导出方式，不覆盖ABI2既有寄存器语义，不仅凭同步后单个format位猜原因。

保持严格2560字节×720行、原DONE/所有权/STOP排空规则；不忽略坏帧继续CNN、不自动重试、不延长等待来掩盖格式错误、不盲翻采样沿或放宽输入约束。若提出设计修改，先静态审查及用户PDS时序，再按有效阶段授权做最小相关测试；不启动历史全套。Sol随后接诊断程序/参考/封存和原证据复核。本交接文件不会自动向其他对话发送消息或授权PDS执行。
