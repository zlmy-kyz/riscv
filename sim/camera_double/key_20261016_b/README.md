# ABI2 发布后复位计数期望修复，仅SoC续测

2026-10-16。A原始目录、639c6ace…fda7a清单、封存副本和全部设计/固件保持不变。A结果仍STOPPED_FIRST_FAILURE：compile native0/Errors0/Warnings0，unit native0/12.7170516秒/Errors0/Warnings40（3017×3、3722×37），unit_check native1，无soc命令。不能重写A结果或往其目录补checked.json。

首败是Sol检查器取样期望错误。camera_mmio在发布边沿将busy清0，使capture_resetn=resetn&&busy清0，wr_reset_pipe及ov5640_capture异步复位；TB在#0.001后的PUB记录中，采集器内部dropped已清0，不能期待预热前的10。首PUB为cycle724182、SEQ1/A/CRC e9ee1be4，实际末W724173，前面有11个真实外部VSYNC起点；当帧数据/地址/CRC正确。

新检查器明确要求发布后dropped=0，同时保留外部EDGE判据：新流首帧11个起点（丢10+有效1），同流后续1个起点。soc也有相同后取样字段，修同一错误。字节/地址/strobe/CRC、末W后发布、元数据/所有权/权限/错误及实际读写并发判据均不改。报告目录可另指定，以只读原轨迹、把复核结果写到新目录；不放宽预热规则。

Sol已核A三份308输入、原语/工具/INI/Git、58历史保护文件及原始证据哈希；[复核收据](review_a/review.json)SHA686231a7b9628d6bbc8a7fe2b3de45d0a43f020f5411108015c72d4647f1ae98。新独立检查器离线重放A全部unit：8发布、19非法MMIO应答、132权限/边界检查、15个DVP帧、STOP/ABORT/满队列/短帧/overflow/缺PCLK/复位用例通过；成功发布边界数11/1/1/1/11/11/11/11。额外构造缺预热边界、错误发布后dropped、错CRC、发布不晚于W和损坏DMA字节，五个反例全部拒收。unit范围可复用，不需要重跑HDL。仍无SoC/整体ABI2、Full Boot、PHY或实板PASS，未创建board_release.json，不提供实板命令。

B清单inputs.json、封存sealed_20261016_b、新目录build/ds_abi2_soc_resume_20261016_b，SHA见CODEX_HANDOFF顶部/预检查。B从冻结副本先unit_recheck（旧unit原轨迹复用），再vlib/compile/soc/soc_check。DUT/TB/模型/CPU DAT/两份程序/采集参数及超时全同A；只换检查器及续测调度，不重复unit仿真或历史全套。新目录存在即停，首败保留，新问题先交Sol分类。详见DeepSeek新的仅SoC任务。
