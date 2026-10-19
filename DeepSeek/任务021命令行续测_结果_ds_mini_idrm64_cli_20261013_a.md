# 任务021命令行续测 结果：CLI_RESUME_STOPPED —— 单顶层命令行加载同样被 RPC/IPv6 故障拦住（tag ds_mini_idrm64_cli_20261013_a）

**结论：`CLI_RESUME_STOPPED`，`functional_status=INCOMPLETE`。**
本次唯一一次获授权的命令行续测执行完毕，**vsim 在 180 秒上限处被终止**。关键新事实：**恢复成“单顶层命令行加载、不在 do 里调用 `vsim`”并没有绕开故障——本入口同样打印 `RPC_Init: … ::1 … couldn't open socket: invalid argument` 并挂住。** 因此上一轮诊断中那条“do 脚本 Tcl `vsim` 路径特有”的解释被本轮证据推翻；**这一工具/环境阻塞同时命中命令行路径**。

HDL 依然一次未执行：**0/2449 项检查**，无 `RESULT`、无 `$finish`、无任何 `IPSpecCheck`。没有出现任何功能 FAIL 文本（见第 5 节），故**不能记 PASS，也不能据此判 RTL/TB 功能 FAIL**。

## 1. 输入身份与只读检查

| 项目 | 值 |
| --- | --- |
| 主桥（I64=2KiB / D32=1KiB） | `myriscv/dual_sram_to_pango_ddr_bridge.v` SHA256 `a0c4e2f6eef67f31333e5e350c5cf84b50025a4141e0fb03a6ce51540c96601b` |
| 原 021 清单（未刷新） | `inst_drm64_inputs.json` SHA256 `9e74eb569e075bb9b64e7ebc852b2bcc2baf9d9e7f3dbc42cf6c23d08cd2d68c` |
| 诊断清单（未刷新） | `inst_drm64_resume_inputs.json` SHA256 `d1b0b468223a42e164c6998ac397d13a334ac362bce174b33e7ede404c63df6d` |
| 本 CLI 清单 | `inst_drm64_cli_inputs.json` SHA256 `b0640ab8b08f2676b1ab4f916862c757bbf27ed20e9eea44f4ef4c4031f682c8` |

只读检查（执行前，退出 0，逐字匹配预期）：

```text
INPUTS_MATCH_NOT_SIMULATED 210 original=179 vendor=2 tools=5 checks=2449 ISA=0 vsim_limit=180s entry=CLI_SINGLE_TOP
```

固定 tag `ds_mini_idrm64_cli_20261013_a` 在启动前确认**不存在**（未换 tag、未清目录）；`pds_shell` 计数 0，未与用户 PDS 并行。开始时间 2026-10-13 08:51:07。

## 2. 三条命令、退出码、用时与上限

| 步骤 | 上限 | 用时 | exit_code | 说明 |
| --- | ---: | ---: | ---: | --- |
| vlib | 60 s | 0.17 s | 0 | 新 work 库 |
| vlog | 60 s | 0.21 s | 0 | 原 **8 模块**（真实 `GTP_GRS`/`GTP_DRM36K_E1` + I/D 四生成源 + 当前主桥 + 原 TB），单顶层 `tb_inst_drm64_x32`，`Errors: 0, Warnings: 0` |
| vsim | 180 s | **180.36 s** | **−1（超时哨兵）** | `timed_out=true`，`native_exit_after_wait=1`，pid 27100 |

vsim 实际 argv（`command.json`，与 019/020/原021 的入口结构一致，仅多了显式 `-l`）：

```text
vsim.exe -c -lib <tag>\work tb_inst_drm64_x32 -l <tag>\transcript -do "run -all; quit -f"
```

超时清理：`taskkill.exe /PID 27100 /T /F` **exit 0**，输出显示终止了 4 进程树（PID 27100 及其子 54452、39852、19040）——挂起是**真实存活进程**。执行后复查：**0** 个残留 `vsim/vish/vlm/vlog/vlib/mti` 进程。清理输出按原样保留（含编码替换字符，未重写）。

## 3. 原始 `simulation.log` 全文（原生直写，520 字节）

```text
Reading D:/modelsim/tcl/vsim/pref.tcl

# 10.6c

Errors: 0, Warnings: 0
RPC_Init: TCL_ERROR: set rpc_port [split {::1:65511} :]
if {[llength $rpc_port]>1} {
  set VsimHost [join [lrange $rpc_port 0 end-1] :]
  set VsimPort [lindex $rpc_port end]
} else {
  set VsimHost localhost
  set VsimPort $rpc_port
}
set client [mti_MakeRPCClient -sigio true $VsimHost $VsimPort -onclose {CloseRPCClient client}]
set VsimPort
 -> couldn't open socket: invalid argument
RPC_Init: Invalid argument

RUNNER TIMEOUT
```

- **`transcript` 为 0 字节**（`-l` 已指定、路径正确、cwd 正确）——本入口验收明确要求“显式 transcript 必须非空”，这一条**未满足**（进程在写出前被终止），与超时结论一致，不额外解读。
- `result.json` 的 `evidence`：`console_bytes=520`、`transcript_bytes=0`、`check_groups=[]`、`pass_checks=[]`、`finish_seen=false`、`run_echo_seen=false`、`rpc_error_seen=true`。
- 本轮 RPC 端口为 `::1:65511`（上一轮诊断是 `::1:49689`），**同一台机、同一入口结构、每次重新选端口**，失败现象一致。

## 4. 本轮的定位价值：命令行路径也被同一故障命中

- 上一轮诊断失败时，候选解释是“do 脚本里的 Tcl `vsim` 命令会拉起子内核并需经 RPC 套接字通信，而命令行顶层加载不需要”。**本轮直接否证了这个区分**：入口已恢复为单顶层命令行加载、`-do` 原文只有 `run -all; quit -f`、不编译探针、不生成 diagnostic.do、不在 Tcl 里加载设计，**仍然**出现同样的 `RPC_Init` 失败与挂起。
- 由此得到的事实链：**2026-10-12 18:19/18:53 的 019/020 成功运行日志里完全没有 RPC 行**；**自 2026-10-13 01:31 起，三次尝试（原 021、诊断续测、本 CLI 续测）全部命中同一 RPC/IPv6 故障**，跨越两种不同的加载入口（命令行 / do 脚本 `vsim`）。
- 因此这是**宿主/会话层面的条件变化**（ModelSim 的 RPC 初始化需要 IPv6 环回套接字 `::1`，而本会话禁止该套接字），不是本次入口选择的产物，也不是 RTL/TB/判据的产物。
- 关于原始 60 秒超时：本轮证据使其成为**最可能的解释**（同一工具、同一台机、同一现象、时间相邻），但原 021 的 64 字节级残缺产物**没有捕获到 RPC 文本**，所以严格说仍是**强推断而非证明**；如需闭环仍需单独的宿主侧证据。
- 另需提醒：既然该阻塞当前命中命令行路径，**同一环境下重新运行任何此前成功的 ModelSim 测试也会同样失败**——不要把这类失败误判为 RTL 回归。

（上一轮报告中的 IPv6/IPv4 环回套接字对照属于该轮已执行的测试，本报告只引用其结果；按本任务“不再启动第二次定位/套接字实验”的要求，本轮**未做**任何新的套接字实验。）

## 5. 已出现 / 未出现的证据逐项

**已出现**：

- `vlib`/`vlog` 退出 0，编译 `Errors: 0, Warnings: 0`，8 模块齐全，单顶层正确；
- vsim 启动、读入 `pref.tcl`、打印版本行、然后 `RPC_Init` Tcl 错误；
- 超时后 runner 的 `taskkill /T /F` 实际清理结果（exit 0，进程树可见）；
- 输入清单 210 项 + 5 个模拟器文件在执行前校验通过。

**未出现**（因此完整验收未满足）：

- 八组 `CHECK:`（645/147/207/139/480/515/294/22）——**0 项**；
- 唯一 `RESULT: PASS inst_drm64_x32 tests=2449`；`$finish`；`# run -all` 回显；
- 两条厂家 `IPSpecCheck: 04030130`（HDL 未跑，谈不上保留）；
- 非空 `transcript`；`git_after.json`；8 份冻结副本（失败发生在 runner 这些步骤之前，属未完成，**不补写、不伪造快照相等**）。

**明确不存在功能 FAIL**：日志中无 `RESULT: FAIL`、无 `** Error`/`** Fatal`、无 `ERROR:`、无 `FATAL`。runner 的断言是被“超时 + `RUNNER TIMEOUT`”触发的（`command()` 内的超时分支），不是在功能判据上失败。**2449 项检查与 I64 功能仍未被验证。**

## 6. 我未执行的操作（按任务约定）

未重试、未更换 tag（固定 tag 保持）、未清理或改写旧目录/旧报告、未修源码/TB/判据/清单/timeout、未改文件/套接字权限、首选项、`modelsim.ini` 或宿主策略、未启动第二次定位或套接字实验、未运行 prepare/review 脚本、未终止用户 `pds` 进程、未执行 PDS/串口/上板、未提交或推送 Git、未追加历史测试；除本报告外未写入任何文件。

## 7. 交回 Codex 的要点（决定权在 Codex/用户）

1. **本轮把问题收敛到宿主/会话的 ModelSim RPC + IPv6 环回条件**：入口结构已证明不是变量。在修复该宿主条件之前，任何 ModelSim 入口（命令行或 do 脚本）都不预期能跑完。
2. 需要宿主侧动作（例如调整 `localhost`/IPv6 解析偏好、ModelSim 套接字/RPC 相关设置或会话网络策略）——属用户侧决定，我不自行修改。
3. 修复后建议仍用**本 CLI 入口**（单顶层命令行 + 直写日志 + 180 秒）再单次执行；它是与 019/020 成功路径一致的功能入口。
4. 若届时出现真正的功能 FAIL（`RESULT: FAIL` 或断言不满足），再按功能问题定位；本轮证据不支持任何功能结论。
5. I64 关键功能通过前，不衔接用户 PDS/实板，也不开始 M/D64、写缓冲、提频等其他改动。
