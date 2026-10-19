# 单目相机关键测试（Sol封存，DeepSeek执行）

本轮用户已确认PDS时序通过。执行范围与判据见[唯一任务](../../../DeepSeek/相机首版_精简关键测试_2026-10-15.md)。

```powershell
Set-Location 'D:\riscv\RISCV'
python sim/camera/key/run.py --check-inputs
python sim/camera/key/run.py
```

`inputs.json`绑定`sealed_20261015_a/`；唯一正式新目录为`build/ds_camera_key_20261015_a/`。运行副本编译49个源、递归include和3个厂家原语；每顶层有GRS实例。首败停止保留；不重建、不重封、不修改输入、不覆盖或重试。

三个job：SCCB正常/NACK/读回错；采集/自然溢出/短帧/ABORT/复位及原生仲裁与窗口边界；真实完整SoC两次720p采集和逐字CPU CRC。输入图案独立参考CRC为AD4E00C3/68C5601B。完整DVP输入、DDR AW/W/AR/R、CPU每字load及DONE/元数据/CRC报告保留并由独立checker复核。

`prepare.py`、`seal.py`仅供Sol准备本身份，不是DeepSeek执行步骤。`static_check.py`是离线输入/编码后的CPU CRC核检查；`preparation_20261015_a/`保留Sol静态原始记录，未run HDL。实际CPU程序在`generated/cpu.S`、`cpu.dat`，无外部交叉工具链依赖。该镜像用DDR预装测试入口、不是Loader Full Boot或实板部署BIN。

DDR控制器/PHY在原生用户口边界用模型替换；CPU/缓存/总线/相机/FIFO/仲裁均真实RTL/IP。仅配置时钟计数加速，core/PCLK及正常帧尺寸不缩小。已有032证据复用，不跑CoreMark、ISA、PHY，不改设计/PDS/IP/成功镜像。

本轮当前只有静态准备结论。DeepSeek执行成功还须Sol复核原证据，不能据此直接写实板PASS。
