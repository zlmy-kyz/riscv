# 037改码前静态论证：并行数据地址译码和ready选择

目标是最新报告最差两条路径共用的EX地址→数据互连优先选择/ready→CPU停顿/ID分支→取指接受链。不修改CPU/分支/流水拍，第三条I失效路径保持。

旧优先级RAM>MMIO>UART>Camera>PP>CNN>DDR。对所有可配置窗口先独立求raw hit，再以更高优先级raw hit屏蔽。旧selected递归屏蔽的并集，等于对应更高优先级raw hit并集；禁用窗口raw=0。因窗口匹配mask/base的合同，对两窗口i,j，存在交集当且仅当((base_i^base_j)&mask_i&mask_j)==0。常量证明无交集的高优先级窗口，不可能在本窗口hit时同时raw hit，故可在 elaboration 时删除该屏蔽项。任意mask/BASE重叠时仍保留原优先级。

实际板RAM0/16KiB、MMIO10000000/4KiB、UART10001000/16B、Camera10002000/64B、PP10003000/64B、CNN10004000/256B、DDR40000000/512MiB两两不重叠，静态priority mask均0；物理ready路径不应再承受这些无意义的相互排除链。

frame_blocked/pp_blocked不改，仍只允许原有权限下的DDR请求。blocked DDR转错误响应仍与旧实现一致，不能绕过CPU所有权、PP输出权限或非DDR写排空。

所有selected对任意确定的二进制地址互斥；因此原优先mux（未映射默认ready=1）严格等于!(OR(selected_i && !ready_i))，对任意下游ready组合均成立。issue_allowed、req_fire、slave valid/addr/write/strobe、响应选择/valid/error和pending/target更新完全保持。

所以逐沿所有实际接受/副作用/响应及延迟保持；旧响应消费与新接受使用旧owner，ERROR不能turnover，写排空/背压/复位均不变。没有增加或延后任何寄存器。X/Z传播不作为已定义请求合同，不以四态未知输入宣称新增功能。

此为静态代数与边沿审查，非动态/形式证明。工具映射和布线决定实际收益；并行化也可能把高扇出/其他路径变成瓶颈，待用户PDS，不能由RTL写法保证提频。
