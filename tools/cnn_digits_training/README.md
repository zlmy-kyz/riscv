# 手写数字训练与ABI1导出

用户2026-10-17确认由打印改为手写。数值合同沿用`digits10_int8_v1`及SoC ABI1，详情见[阶段记录](../../doc/cnn/手写数字数据准备与INT8训练_2026-10-17.md)。

当前按用户要求停止，等待其自行安装PyTorch/CUDA；数据已准备并复核，脚本仅做语法检查与不依赖PyTorch的参考检查，未训练或完成端到端模型验收。以下为后续复现入口，不代表全部已执行。未完成的`*.whl.part`不是可安装包。

本工具只写指定的新数据/运行目录，不操作RTL、PDS、IP、串口、成功固件或旧证据。输出参数包须通过软件整数复核；本地数据集准确率不等于实拍或FPGA验收。

```powershell
Set-Location D:\riscv\RISCV
python -m venv --system-site-packages sim/cnn/training_env
.\sim\cnn\training_env\Scripts\python.exe -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128 --disable-pip-version-check --no-cache-dir
python -X utf8 tools/cnn_digits_training/prepare.py --dataset 'D:\riscv\80bfd\经典手写数字数据集' --out sim/cnn/training/handwritten_data_20261017_a
.\sim\cnn\training_env\Scripts\python.exe -X utf8 tools/cnn_digits_training/train.py --data sim/cnn/training/handwritten_data_20261017_a --out sim/cnn/training/handwritten_run_20261017_a
```

源图按解码像素哈希分组、类别分层60/20/20；同源增强不跨split。没有原始writer/session身份，不宣称书写者隔离。训练数据通过白底RGB96画布与合同RGB96→灰度32适配生成，不直接使用28→32默认resize冒充相机采样。原图像素不反色、不二值化、不自适应归一化。

训练先100轮浮点，验证集校准幂二尺度，然后40轮固定尺度QAT。只按验证集选checkpoint。最终模型冻结后测试一次，报告浮点/整数十类召回和混淆矩阵；本地测试失败也保存，不自动据最终测试调参。训练日志为`float.jsonl`/`qat.jsonl`，模型包在`model/`，输入身份为`input_identity.json`，结果为`metrics.json`，完整产物哈希为`sealed_manifest.json`。

新模型目的为`TRAINED_HANDWRITTEN_DIGITS_LOCAL_DATASET`，新MODEL_ID与旧诊断包区分；包含6152byte权重、264byte bias、每层Fin/Fw/Fout/shift、6222word/24888byte小端装载及CRC。旧诊断工具有严格目的/ID校验，不能将本包直接覆盖到旧诊断目录或原成功BIN。

独立标量参考仅依赖Python标准库，不导入PyTorch或训练实现：

```powershell
python -X utf8 tools/cnn_digits_training/integer_reference.py --model sim/cnn/training/handwritten_run_20261017_a/model --rgb96 sim/cnn/training/handwritten_run_20261017_a/reference_cases/uniform128/rgb96.bin --out sim/cnn/training/independent_replay_20261017_a
```

`reference_review.json`记录标量整数/向量INT64/QAT前向逐层完整元素对照；`reference_cases/`保存输入及各层输出。软件对照不能替代HDL与实板。

数据与最终封存复核（输出文件必须为新路径）：

```powershell
python -X utf8 tools/cnn_digits_training/review.py --data sim/cnn/training/handwritten_data_20261017_a --out sim/cnn/training/handwritten_data_review_20261017_a.json
python -X utf8 tools/cnn_digits_training/review.py --data sim/cnn/training/handwritten_data_20261017_a --run sim/cnn/training/handwritten_run_20261017_a --out sim/cnn/training/handwritten_model_review_20261017_a.json
```
