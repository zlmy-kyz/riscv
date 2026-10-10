# .gitignore 配置记录

日期：2026-10-04。目的：按用户要求创建根目录 `.gitignore`，排除可重建产物，同时保留上板和仿真输入。

改动：新增 `.gitignore` 和本文。规则覆盖 PDS 构建目录、隔离验证项目中的构建目录、ModelSim 编译库、仿真可执行文件/波形、Python 缓存、IP 生成元信息、根目录临时日志、`difftest/build/`、`tmp/` 及脚本生成的 DDR 模型副本。

保留 `RISCV.pds`、RTL、IP 配置与初始化 RTL、DDR `sim_lib/`、脚本/TB、镜像/清单、文档/配图及代表验证日志/CSV。特别保留 PDS 正在引用的 `constraint_check/temp_constraint_file.fdc`。没有使用全局 `*.log`、`*.dat`、`*.dump`、`*.csv` 等规则。旧开发资料、备份和 `impl.tcl` 的排除规则仅作为注释，待迁出有用材料并修复引用后启用。

复现命令：

```powershell
git check-ignore -v --no-index -- compile/cmr.db RISCV.pds.lock sim/board_top_physical_work/_lib.qdb
# 下列保留输入应无匹配输出，退出码 1 表示未被忽略：
git check-ignore -v --no-index -- RISCV.pds constraint_check/temp_constraint_file.fdc MyCpu_test/board_selftest/boot_rom.dat sim/board_main_selftest/compile.tcl
git ls-files -ci --exclude-standard
```

实测效果：从 PDS setup 段提取文件引用，并加入代表脚本、镜像、清单、黄金模型、日志、CSV 和图片，使用 `git check-ignore --no-index` 检查，共 119 个唯一保留路径均未被排除；12 个代表产物路径均按预期忽略。检查采用命令行路径参数，避免 PowerShell 将 CRLF 写入 Git stdin 时把 CR 解释为文件名字符。

当前有 49 个已跟踪路径匹配新规则。`.gitignore` 不会自动取消跟踪；本次没有修改索引、删除文件、提交或推送。以后整理索引可用 `git ls-files -ci --exclude-standard` 查看确切范围。

未覆盖：没有重跑 RTL/DDR 仿真、PDS 构建、CoreMark 或实板测试；本步只修改版本管理规则。构建目录中的历史验证证据仍需按发布清单归档；本步没有清理历史提交或解决脚本绝对路径。
