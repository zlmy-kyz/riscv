# 统一裸机 BSP 开发与验收

根目录放startup/linker、UART/timer/CRC32/trap驱动、Hello/CRC32/IRQ应用及CoreMark端口。build.py统一GCC→ELF→BIN→布局/ISA审查，build/各名称保存成功输出并拒绝覆盖；新开发用--tag隔离构建，须重新验证冻结后才能运行。

当前入口仅接入Hello、CRC32、CoreMark与仅仿真的IRQ探针；任意新main.c自动构建/下载/验证尚未实现，--tag不会注册新程序。讨论中的run_app.py --source/--expect是拟议接口，不是现有命令。新程序需要隔离接入构建、预期输出及新门控，不能修改成功main或工具后继续套用旧PASS。

下一任务为[CPU性能优化](../../doc/CPU性能优化起点与验收约定_2026-10-10.md)，先用本目录已成功的CoreMark BIN建立性能统计，保持软件身份固定；本轮不扩展通用C工具。

用户验收入口：

```powershell
& C:/python/python.exe D:/riscv/RISCV/tests/bsp_workflow/run.py --acceptance
```

沿用原Hello成功Loader位流，关闭串口助手，每轮按提示KEY0并等待DDR初始化后回车；十轮覆盖Hello、CRC32、CoreMark短迭代及两组60次正式运行。日志在 `D:/riscv/RISCV/sim/bsp_workflow/board/first/`；旧目录存在时改--directory，不覆盖、不重试。

2026-10-10新BSP十轮已全部实板PASS：Hello、CRC32、CoreMark短迭代与两组正式60次通过，834响应及10次RUN独立核验成功，518项成功快照保存。详见 [实板验收](../../doc/software/统一BSP与十轮复位下载实板验收_2026-10-10.md)。完整约束、仿真和输出格式见 [准备记录](../../doc/software/统一BSP与十轮复位下载验收准备_2026-10-10.md)。已成功build不重建覆盖，新程序使用隔离tag及新的验证。
