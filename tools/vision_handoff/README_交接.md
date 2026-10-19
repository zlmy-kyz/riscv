# 视觉识别交接包：先复核，再接板，再改进模型

日期：2026-10-19。对象：接手本项目视觉识别的同学。本包保存当前可复现状态，不把错识别隐藏为PASS。

## 1. 先知道现在能做到什么

- 硬件：Pango PG2L200H、FBB676、速度级-6，PDS 2022.2-SP6.4；设计顶层`board_top`，125MHz参考、core_clk 93.75MHz。
- 摄像头：DOUBLE-DVP载板只接一只OV5640，在CAM2/J5，载板接底板J10。A/B是DDR双缓冲，不是两只摄像头。COLORBAR及DVP_TEST均为0。
- 真实链路：720p RGB565 → 固定中心720方形 → FPGA PP输出96×96 RGB888 → CNN适配32×32单通道INT8 → FPGA CNN输出10个整数分数。
- 模型：已训练手写模型`4c8b5aca`，6222个加载word、CRC32 `b9749177`。本地测试1045/1069=97.7549%，不等于实拍准确率。
- 当前真实拍摄：0的一张完整源采样识别正确；多张8和一张1误识别为0。板端全部10分数与PC独立整数参考一致，不代表数字识别通过。
- 第三次纸上8及最新1的输入统计存在明显训练/实拍分布差异。黑底白8又有极性差异；简单反色/缩放没有普遍解决，不要把建议当已实现功能。
- 自适应定位、背景校正、自动反色、拒识目前都没有实现。现有10分类对空白也会强制给某一类，最高logit不是概率。

包内历史README/ready可能仍写“待训练/待实拍/KEY0”，因为它们属于原封存；**本README与最新阶段记录优先说明当前用法，不修改历史封存来伪造当时状态**。

## 2. 包的结构

```text
README.md                       当前操作说明
package_manifest.json           全部交接文件SHA256/大小、PDS输入、采样目录
verify_package.py               标准库校验；可只读回放真实串口，不碰板
make_pds_workspace.py            生成独立、可迁移PDS源码副本，不启动PDS
dataset_source/                 5339张原始28×28灰度BMP及原来源README/LICENSE
project/
  RISCV.pds                     当前工程原样快照
  myriscv/、ipcore/              PDS引用源码、IP及递归include/初始化参数
  constraint_check/             有效CAM2 FDC
  generate_bitstream/board_top.sbit  当前生成文件快照，身份限制见第6节
  tools/cnn_handwritten_perf46/  当前唯一识别采集入口
  tools/cnn_digits_training/    数据准备/训练/独立整数参考
  tests/cnn_handwritten_photo/  固定C固件源码、BIN/ELF/模型头及审计
  sim/cnn/board/                原始RX/TX、图像/张量、标签、分数和收尾证据
  sim/cnn/training/             数据NPZ、训练checkpoint、量化参数及参考轨迹
  sim/cnn/handwritten_perf46_20261019_a/  ready、板试收据及离线诊断
  doc/cnn/、doc/camera/          数值合同/ABI/阶段文档
```

没有复制Python虚拟环境、CUDA、PDS安装、GCC工具链或整仓库历史。不要直接运行`build_bundle_source.py`，它是封装来源记录，运行环境是原工程而非包顶层。

## 3. 第一件事：离线验包和复核，不需要板子/显卡

解压到路径较短的位置，例如`D:\vision_handoff_20261019_a`；在包含本README的目录打开PowerShell。需要Python 3.13（原环境版本；脚本使用现代Path API）。不要只用GitHub网页预览ZIP，需下载解压。

```powershell
python -X utf8 verify_package.py --plan --replay --out peer_package_review_01.json
```

这条命令只使用Python标准库：核所有文件SHA256/大小、5339张源图身份、PDS setup的153项输入存在，执行当前工具`--plan-only`并回放7次已存真实串口。**不会打开串口、JTAG、PDS或重训**。报告路径必须不存在。完整源那一轮复核会比快速轮慢一些。

验包的PASS仅表示文件/身份与对应原始计算证据一致；报告中多个`label_match=false`必须保留，不能将总状态解读成识别准确率PASS。

数据原记录`dataset_root`还是最初的`D:\riscv\80bfd\经典手写数字数据集`，现源图已经按SHA逐张确认后放在包顶层`dataset_source`。不要为迁移路径改旧JSON哈希。验包器按包内路径检查，重新准备数据时使用第8节新目录。

## 4. 独立查看一次采样

```powershell
Set-Location .\project
python -X utf8 tools/cnn_handwritten_perf46/run.py --verify sim/cnn/board/handwritten_perf46_trial01_1_01
```

图像就在该采样目录：`rgb96.png`是彩色PP输出，`gray32.png`是CNN输入灰度预览；`rgb96.bin`是实际RGB字节，`integer_reference/gray32.bin`是signed INT8的原始补码字节。`comparison.json`给全部板/PC分数，`sample.json`给操作者标签/session/sample，`result.json`给控制/包/释放账本，`uart.rx.bin`和`uart.tx.bin`是完整原始串口。

|采样目录后缀|sample|记录标签→预测|范围|
|---|---:|---|---|
|`trial01_0_01`|1|0→0|完整720p源、源CRC、PP逐字节和10分数|
|`trial01_0_02`|2|0→0|快采；真实纸张标签未另行确认，不用它扩大准确率|
|`trial01_8_02`|3|8→0|快采，细小纸上8|
|`trial01_8_03`|4|8→0|快采，纸上8|
|`trial01_8_04`|5|8→0|快采，纸上8|
|`trial01_8_05`|6|8→0|快采，黑底白字，不符合原白底黑字约定|
|`trial01_1_01`|7|1→0|快采，纸上细小1|

全部目录均带`handwritten_perf46_`前缀。历史原标签不回填、不删除错例，不按同一session几个探索样本宣称总体准确率。

## 5. 输入、权重及固定BIN的精确约定

```text
RGB96坐标：(3*x+1, 3*y+1)，x/y=0..31
Y = (77*R + 150*G + 29*B + 128) >> 8
q = Y - 128，signed INT8；训练浮点输入=q/128
网络：Conv8/16/32（3×3、stride2、pad1）→ GAP16 → FC10
```

不是先把720p随便resize成32，也不是3×3平均；不自动反色、二值化或按图归一化。完整量化/布局/舍入参见`doc/cnn/digits10_int8_v1.json`及中文合同，SoC见ABI1文档。参数包在`sim/cnn/training/handwritten_run_20261017_a/model`，含weights/bias/load_words/model.json。

固定上板应用：`tests/cnn_handwritten_photo/build/handwritten_20261017_b/program.bin`，42568字节，SHA256：

```text
5b3364b064a4687a2e141bef504031fdc31a09d1e681b8cd1518133d4ee9f49c
```

Loader应用CRC32 `2157dd62`，装载/入口`0x40000000`。权重已编入该BIN，不是运行采集脚本时从PC替换；`--label`只记录正确答案，不参与推理。旧诊断模型05a032af未训练，不与此模型混用。

## 6. 上板复现：先对准，再JTAG恢复，KEY0不按

必需：相同器件板卡/接线、JTAG和驱动、OV5640、USB-TTL、串口号、PDS Programmer。包中当前`sbit`的SHA在`package_manifest.json`。它是原目录当前生成文件的原样快照；**没有FPGA回读来独立证明本包`sbit`就是此前实际下载版本，也不补记其完整时序/关键HDL验收**。不要下载`share/mini_ddr3`、厂家Demo或旧CAM1位流冒充当前版本。

1. 白纸黑笔写单个0–9，正向居中，固定镜头和纸张，照明稳定。当前模型不保证任意字体/屏幕反色/任意位置。
2. 用户/同学自行JTAG重新下载当前匹配位流。KEY0全程保持释放，不再按键，等DDR就绪；KEY0暖复位问题仍未解决。
3. 关闭串口助手。激活电脑Python环境；采集只额外需要`pyserial==3.5`，离线原始复核不需要它。先安装后再操作板，避免程序因缺包停止。
4. 在`project`目录运行；COM9必须改为实际端口，日志目录必须不存在。这里使用全新peer session，不覆盖原证据。

```powershell
python -m pip install pyserial==3.5
python -X utf8 tools/cnn_handwritten_perf46/run.py --port COM9 --label 8 --session peer_session01 --sample 1 --full-source --log-dir sim/cnn/board/peer_session01_8_001
```

5. 确认画面已摆好、JTAG恢复完成、KEY0保持释放，再在提示处Enter。Enter后工具装载BIN、核CRC/RUN、配置/检查相机、采一帧并导出。看见SCORES后无新文字不一定卡死，完整源1,843,200字节通过115200 8N1导出约3分钟或更久；`source.partial`应增长。等终端正常结束，异常则保留全部目录交回分析。
6. 首张建议完整模式核源到PP。以后省略`--full-source`可快采，只有RGB96/28包，仍比较10分数但不核源到PP。每次应用结束后停住，**下一次仍先JTAG恢复**；换新目录、递增sample、按纸张真值改label。错误预测不自动重试。

无需为每张照片重新PDS实现。只有换硬件源码/IP/约束或需重建时才走第7节。若硬件身份或已封存文件被改，当前脚本会拒绝；不要删除检查强行跑新设计。

## 7. PDS工程与迁移

`project/RISCV.pds`为当前原样工程，6个IP为inst_rom/data_ram/ddr3/icache/dcache/mul。包内有其setup引用、递归include和`*_init_param.v`，以及Loader的ROM/RAM独立DAT；不把一个BIN同时塞ROM/RAM。初始化常量包含在生成IP文件中，原IP参数还记录原电脑的绝对DAT路径。

**不要运行根目录旧`impl.tcl`**：它含历史器件/绝对路径/旧顶层命令，不是当前工程入口。PDS安装及厂家原语库需自行准备，不能只凭包内RTL认为工具已安装。

在其他路径重建时，先回到包顶层，建立包外的新工作目录：

```powershell
python -X utf8 make_pds_workspace.py --out D:\vision_pds_peer01
```

此脚本只复制PDS源码依赖并替换工作副本内原`D:/riscv/RISCV/`路径；写`relocation_review.json`列出改动哈希，不碰原封存、不启动PDS、不生成新位流。然后由同学在PDS中打开新目录的`RISCV.pds`，核PG2L200H/FBB676/-6、顶层board_top、有效CAM2 FDC、独立ROM/RAM Loader DAT、125MHz及core_clk93.75MHz，重新实现检查时序。模拟器绝对路径/库另按本机配置，不能用存在的TB推定已验收。

新的实现和位流必须记录为新身份，不能凭源文件相同继承历史PASS；若要沿用采集软件，按新硬件身份建立新封存入口，不能直接改旧清单。硬件设计修改交Astra/硬件负责人，Sol/软件负责人做测试方案及参考；PDS/JTAG/KEY0/串口由操作者执行。

## 8. 训练复现（需要数据环境，不是上板前置条件）

原环境身份在`project/sim/cnn/training/handwritten_run_20261017_a/input_identity.json`：Python3.13、PyTorch2.7.1+cu128、CUDA12.8、NumPy2.4.4、Pillow12.2.0、RTX4070 Laptop。没有打包安装文件；按同学显卡/驱动安装兼容环境。不要为只读回放要求CUDA。

原始5339张均28×28灰度，0类839、其他各500，3203/1067/1069的60/20/20划分基于像素哈希，无可信writer/session身份。准备过程为28灰度放大80、居中白底96RGB再合同采样；训练增强side72..84、位移±4、旋转±8°、有限亮度/对比变化，没有覆盖所有真实环境。

数据来源README/LICENSE原样附在`dataset_source`；原README的来源说法未独立确认，LICENSE含占位作者/年份，公开附带不等于本项目保证其来源、权利或商业使用条件。继续使用前自行核实来源授权。

使用包内源码重新准备新目录，避免原dataset.json的绝对路径问题：

```powershell
Set-Location .\project
python -m pip install numpy==2.4.4 Pillow==12.2.0
python -X utf8 tools/cnn_digits_training/prepare.py --dataset ..\dataset_source --out sim/cnn/training/peer_data_01 --seed 20261017 --variants 4
python -X utf8 tools/cnn_digits_training/train.py --data sim/cnn/training/peer_data_01 --out sim/cnn/training/peer_run_01
python -X utf8 tools/cnn_digits_training/review.py --data sim/cnn/training/peer_data_01 --run sim/cnn/training/peer_run_01 --out sim/cnn/training/peer_run_review_01.json
```

训练命令前需安装原记录或兼容的PyTorch/CUDA，不自动联网安装；参考原README的固定环境命令。训练会耗时，以上只是复现入口，不代表交接时又训练了一遍。GPU重训不承诺权重字节与原模型一致，检查划分/合同/指标/独立整数轨迹。

新训练包要新MODEL_ID/新固件和新验证，**不能用peer_run覆盖固定4c8b5aca包或重建固定BIN后直接上板**。固件重建另需RISC-V GCC工具链，原编译命令/flags/链接布局随BIN审计保存；只采图无需装GCC。

## 9. 接手后优先做什么

已有`input_diagnosis_01/review.json`记录3张实拍各7个固定变换和训练控制；同一模型能识别选定训练1/8，实拍1仍错误。实拍1灰度均值146.416，增强训练1单图均值196.288–250.677，输入分布差异明显。空白灰192也预测8，因此某张裁剪后猜中8不等于修复。

如需重现诊断，先用包内完整数据，在`project`中执行诊断脚本的**副本**并给它新的输出名；原脚本固定`input_diagnosis_01`会拒绝覆盖。不要修改已封存数据。原结论和脚本源/张量/分数已附，不需要为验包重跑。

优先建立分session的实拍开发/验证数据，检查定位、去外围背景、尺度和亮度策略。若采用自适应预处理，先PC副本验证，再同步冻结训练、独立整数参考和板端新版本；当前合同禁止擅自反色/二值化/自适应归一化。最终独立测试另留新session，现有错例不能被反复调参后再当独立验收。

## 10. 常见问题和交回材料

- `new --log-dir required`：目录已经存在。换新目录，不删除旧数据或只改label。
- 看到SCORES后暂时没有输出：完整导出无进度打印；看source.partial是否增长，等待正常结束，保留异常原证据。
- `ModuleNotFoundError: serial`：采集环境缺pyserial。先安装好，再JTAG恢复后使用新目录。
- Loader首次PING失败/超时：检查COM口、串口助手占用、JTAG新鲜恢复、KEY0释放、DDR就绪和匹配硬件；不要放宽协议或无限重试。
- 预测错误但分数一致：如实记识别错误；不是通信PASS就等于分类PASS。不要据十个logit自称置信概率。
- 硬件身份/hash错误：不要关闭校验；提供改动清单、原始日志及新设计身份，按新阶段准备。

交回完整新采样目录（不要只有终端截图）、纸上真值/session、接线、是否换光照/距离、具体命令及JTAG恢复方法。严禁以模拟/PC参考替代硬件层输出。KEY0暖复位、CAM1具体根因、关键HDL/全部异常并发/长稳/正式实拍准确率等未覆盖范围仍保持。
