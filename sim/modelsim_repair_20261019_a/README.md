# ModelSim -c / IPv6回环阻断定位（2026-10-19）

用户询问如何修复。延续`../modelsim_health_20261018_a`的最小工具证据，本次不运行工程HDL、不改RTL/PDS/IP/成功镜像，不修改系统或代理配置。

## 已定位的直接阻断条件

经Windows UAC批准，`read_admin.ps1`以管理员身份只读导出WFP规则。`admin_context.json`确认administrator=true；`admin_loopback.json`中IPv4 listen/connect成功，IPv6监听成功但connect阶段SocketException10013，说明不只是Codex普通进程权限问题。

`ipv6_filters.xml`包含：

- 名称`Meta`、描述`block ipv6`，filterId=71204，filterKey=`{7414857f-66a4-461d-b48b-bbd6e272dac7}`。
- 层`FWPM_LAYER_ALE_AUTH_CONNECT_V6`，action=`FWP_ACTION_BLOCK`，filterCondition为空，weight=12；覆盖IPv6回环连接。
- 同一sublayer=`{3eba4fb2-1b99-49ad-9165-f2e79cfaf1c8}`的`protect ipv6`只允许`clash-verge-service/cores/verge-mihomo.exe`（weight13，filterId71200）。该例外不匹配ModelSim或诊断程序。

经授权仅提取Clash Verge本地`clash-verge.yaml`网络开关：顶层ipv6=false，tun.enable=true，tun.auto-route=true，tun.strict-route=true，tun.stack=gvisor，device=Mihomo；没有复制订阅节点、密钥或完整配置。

上游MetaCubeX/sing-tun的[Windows实现](https://raw.githubusercontent.com/MetaCubeX/sing-tun/master/tun_windows.go)在AutoRoute且StrictRoute时创建动态WFP规则；无Inet6Address时创建`block ipv6`。当前宿主规则与此路径一致。不是依据进程名猜测代理冲突，也没有证据指向Tailscale。

## 修复操作与验收边界

可在Clash Verge的TUN设置关闭“严格路由”（strict-route），保存并重启TUN/内核，使内核撤销这组动态过滤。此操作也会取消该模式的DNS防泄漏过滤；若需要保留严格路由，应改为正确启用IPv6支持并确保TUN实际获得IPv6地址。仅修改DNS的ipv6开关或添加普通DIRECT规则不能消除本次已发现的WFP拦截条件。

操作前记录原开关，网络重载可能短暂中断代理。本次只定位和准备步骤，**未执行上述配置修改、未验证修改后-c恢复**，不得标修复PASS。关闭整个Windows防火墙、重置网络、改hosts、重装ModelSim都不是本轮的必要修复操作。

修改后复核只需：IPv6 ::1连接成功；同一最小`work.tool_health`用-c运行至1ns，输出`TOOL_KERNEL_OK time=1000`、退出0、Errors/Warnings0。新输出使用新目录/日志，不覆盖20261018失败证据，不运行043或其他工程功能测试。

只读管理员采集命令：

```powershell
# 在管理员PowerShell执行已保存脚本；脚本只读系统网络状态，写本目录诊断文件。
& 'D:\riscv\RISCV\sim\modelsim_repair_20261019_a\read_admin.ps1'
```

`wfpstate.xml`为netsh原始输出，保留原文；末尾存在额外内容，不能直接作为单个XML文档解析。完整WFP导出仅为本地诊断，不包含在最终答复中。
