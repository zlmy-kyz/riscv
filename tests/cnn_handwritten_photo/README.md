# 固定手写模型CAM2应用

由`tests/cnn_digits_photo`成功控制流程另建，使用训练模型`4c8b5aca`，保留原成功源码/固件和全部证据。CPU只执行ABI1装载、相机所有权、PP/CNN控制、UART导出及CRC，不执行软件CNN代替FPGA。

固定应用`build/handwritten_20261017_b/program.bin`，42568byte，入口/装载地址0x40000000，SHA256 `5b3364b064a4687a2e141bef504031fdc31a09d1e681b8cd1518133d4ee9f49c`，CRC32 `2157dd62`。RISC-V RV32I编译/指令静态审计及模型word逐字节嵌入检查通过，静态栈界368byte，未运行真实CPU/HDL。最初`build/handwritten_20261017_a`仅为准备过程的静态构建，BIN字节相同；正式PC绑定b版完整依赖清单，不直接部署a版。

模型头在构建目录生成，由已复核训练包生成全部6222word，编译后核ELF中`model_words`区域与原24888byte装载流完全相同。源码不包含零占位参数，不改变ABI/权重布局/类别顺序。Loader仍从原ROM驻留执行，经UART下载新BIN；不替换ROM/RAM IP、生成新位流或从数据RAM执行。

新应用banner为`CNN_HANDWRITTEN_APP=1`，协议CN03。一次运行领取A帧、STOP/排空、PP、CNN，等待PC命令`d`快速导出RGB96或`D`完整同源RGB96+720p；两模式均保持源帧CPU所有权到导出完成，再释放所有发布帧，读取10个signed32分数并核argmax。每次新运行需KEY0回到Loader。

操作命令、标签/session记录、快速模式边界及只读复核见[PC入口](../../tools/cnn_handwritten_photo/README.md)。本应用尚无新模型实板PASS。

仅在后续明确修改新源码时用新tag构建，不覆盖已封存b目录：

```powershell
python -X utf8 tests/cnn_handwritten_photo/build.py --tag your_new_tag
```

源码/API变更后需绑定新PC manifest、重新做相关检查与封存，不能把重建BIN当作已验收的原固定文件。仿真/检查/native模型/日志全部在`sim/cnn/handwritten_photo_20261017_a/`。
