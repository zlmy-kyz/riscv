# 当前测试程序开发区

这里是 `tests/` 唯一可持续修改的测试程序开发区。当前保留 UART printf 输出30的
工作副本；下一次新测试首先在此开发。成功归档在 `../fpga_uart_pc_output_30/`。

| 文件 | 作用 |
| --- | --- |
| `main.c` | a=10、b=20、c=a+b；printf发送30 CR LF，完成后上报MMIO PASS/FAIL |
| `uart_printf.c` | 轮询UART TX_READY，以SB发送字节；精简printf支持%d、%%和普通文本 |
| `uart_printf.h` | printf声明所需stdio接口与uart_flush声明 |
| `startup.S` | 设置gp/sp、清BSS、调用main，返回后停留 |
| `linker.ld` | DDR入口0x40000000、64KiB范围、顶端4KiB栈；sp=0x40010000 |
| `build.ps1` | 编译/链接、导出BIN/反汇编等，再调用本目录转换器生成DAT |
| `bin_to_dat.py` | BIN按32位小端转换为4096字RAM DAT，末四字保留loader清单；生成兼容boot候选 |
| `build/` | 当前及迁移保留的编译结果，不作为成功测试归档，由Git忽略 |

在本目录构建：

```powershell
& ./build.ps1
```

顺序为 C/Assembly → RV32I/ILP32 ELF → objcopy BIN → main.dat。
最终当前DAT为 `build/main.dat`；ELF/BIN、`.dis`、readelf、map、size、编译日志、
`manifest.json` 和参考 `boot_rom.dat` 也在build。迁移保留的旧build/uart_printf/
只是历史产物，不是当前构建输出入口。

只做BIN到DAT转换时：

```powershell
& C:/python/python.exe ./bin_to_dat.py ./build/main.bin ./build
```

RAM DAT每行一个8位HEX字，总4096字；payload至多16368字节，末16字节为
`[payload_words,0,0,0]`。实际装载来源是RAM，CPU由ROM loader搬至DDR后跳转。
BIN必须已链接在0x40000000，不是自动重定位。BSS由startup清零，不占BIN。

要试用开发镜像，可将data_ram IP的INIT_FILE指向此build/main.dat，保持HEX、
32位数据和12位地址及原时序配置，重新生成存储IP再构建位流。
当前主RAM引用的是成功归档 `../fpga_uart_pc_output_30/main.dat`，构建脚本不会改它。
现有ROM loader与本工作副本兼容；不要用payload替换ROM启动代码。

仿真从仓库根目录运行，产物保留在sim：

```powershell
& C:/python/python.exe sim/baremetal_c/run.py --case uart_printf
```

修改程序、入口、链接布局或输出后，须同步调整相应验收条件，不能沿用旧PASS。
