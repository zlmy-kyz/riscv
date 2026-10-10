# CoreMark 裸机构建与短迭代 CRC

日期：2026-10-07（Asia/Shanghai）。工程 `D:/riscv/RISCV`。
用户授权接续裸机移植，先验证构建尺寸和短迭代 CRC。

最新状态：两组60次镜像已完成Full Boot及用户实板CRC/至少10秒运行验收。
performance ticks=1664676818（17.75655秒）、final=a14c；validation ticks=1758636430
（18.75879秒）、final=6770，均Correct operation validated且无错误。
成功镜像及证据见[实板60次验收](CoreMark实板60次验收_2026-10-07.md)。
以下单迭代、待构建、实板待验证描述保留为历史阶段记录，当前状态以最新验收为准。

## 最新validation短迭代UART反馈

用户提供validation输出，保存于sim/coremark/board/validation_iter1_user_20261007.txt。
seed/list/matrix/state/final=18f2/e3c1/0747/8d84/e3c1，ITERATIONS=1，
Total ticks与PORT_DONE ticks同为29302693；CRC全匹配，唯一ERROR仍是时间不足。
按93750000Hz换算0.3125620587秒，整数秒为0正常；证据来自用户粘贴文本，
不新增本机仿真或独立位流/时钟证明。与此前performance输出合并，已完成两组短迭代CRC检查，
不作为正式CoreMark分数或完整实板PASS。

后续performance与validation可先准备各60次候选，单次线性估计分别17.7551776和
18.75372352秒，以真实新运行ticks为准。新DAT须独立构建、检查尺寸、验收后再部署，
不覆盖此前成功短DAT；多迭代final CRC另核，不能套用单迭代final。
正式运行需各至少10秒且不超过约45.81秒的32位计时上限，保存全部串口文本。
本轮exec与Node辅助进程启动失败，未获得最新git/IP读回，未构建或仿真；
仅使用文件补丁保存本轮文本和更新相关记录，没有修改RTL、IP配置、深度或已有DAT。
以下performance反馈和构建/仿真章节为各步骤历史范围，validation待验证的旧描述已由本节更新。

## 后续实板performance短迭代反馈

用户按上板短迭代步骤提供完整performance串口文本，原样保存于
`sim/coremark/board/performance_iter1_user_20261007.txt`。
按用户提供文本记录 **performance实板短迭代CRC功能通过**，证据不是本机新仿真。
seed/list/matrix/state/final=e9f5/e714/1fd7/8e3a/e714，ITERATIONS=1，
Total ticks和PORT_DONE ticks均27742465；唯一ERROR仍为时间不足，之后Errors detected。
CoreMark Size=666是2000字节总数据分给三个算法后的单算法大小，属于正常输出。

按93750000Hz换算本轮耗时0.2959196267秒，所以整数秒输出0正常。
这不是独立时钟校准，也不报告正式分数。实板DDR等待与仿真模型不同，ticks与仿真
12271801不同不构成CRC功能失败；没有据此修改RTL/桥或仿真模型。
下一步先上板已有validation单迭代DAT，核18f2/e3c1/0747/8d84及final=e3c1。
performance正式候选可先考虑60次，按单次线性外推约17.755秒；只是估计，
最终必须以实际ticks确认>=10秒、<32位计时上限并且所有CRC匹配。
新迭代镜像仍需隔离构建、尺寸检查和适当仿真验收，不能直接覆盖这份已验收短DAT。

本轮读git状态/diff及IP配置，主RAM IDF/wrapper/IP TB已由用户侧切到performance/main.dat，
ADDR_WIDTH=12、DATA_WIDTH=32仍为16KiB，无深度变更。当前DAT SHA256仍为
52b8b8eafa58bc924c1497e1ff2ba49d071c81e4c0b2bb563a338ee4b04de075，与Full Boot凭据一致。
用户要求任何RAM/ROM深度调整先告知容量缺口、建议深度和原因；本轮无需调整。
PDS/impl/IP生成初始化等用户侧新改动保留，本轮仅保存文本/核对/记录，没有重构建或仿真。
还没有validation实板短测、至少10秒正式performance/validation或独立位流哈希凭据。
以下构建与仿真章节保留为先前步骤范围，其中实板NOT_TESTED属于那次仿真记录。

## 恢复状态与改动范围

已读 `AGENTS.md`、`doc/CODEX_HANDOFF.md` 和最新源码移植交接，检查
`git status --short`、`git diff --stat` 和实际 diff。开始时 `.gitignore`、AGENTS、
README、HANDOFF已有CoreMark入口增补，coremark-main和两份CoreMark文档未跟踪；
PDS/impl.tcl/DDR日志/multiseed_summary.csv另有既有改动，zongxian.md已删除。
保留这些改动，没有清理、重置、提交或推送。

新增 `tests/coremark_baremetal/`：core_portme.c/.h、从官方模板适配的整数ee_printf.c、
startup.S、linker.ld、build.ps1、独立BIN→DAT转换器。五个算法/主程序源和coremark.h
仍从用户 `coremark-main/` 直接编译，未改字节。core_main.c自带main，因此没有另建main.c。
新增 `sim/coremark/` 的runner、TB、同步BRAM与Pango DDR用户口模型；从Echo复制模型，
不修改共用TB或生产RTL。仿真库、日志、原始UART与验收JSON留在sim/coremark/build。

## 平台实现

- 静态2000字节，单线程、volatile种子，无argc，无libc或浮点；RV32I/ILP32 libgcc软乘除。
- UART先读TX_READY再SB写TX_DATA，初始化CONTROL=0x203（清sticky error并禁RX IRQ）。
- 计时MMIO=0x10000008、93.75MHz，不使用rdcycle；起止ee_u32差，一次运行必须小于45.81秒。
- 原版整数秒截断和至少10秒检查完整保留；portable_fini追加PORT_DONE ticks/iterations/hz。
  该行仅表示完成，main返回0、该行、LED均不能单独作为PASS依据。
- DDR入口0x40000000，链接范围64KiB，栈0x4000f000–0x40010000。
  .data LMA=VMA由原ROM loader装入；BSS NOLOAD由startup清零。

## 构建尺寸：已通过现有装载范围

工具链为本机xPack GCC15.2.0；算法/平台源同一调用统一编译，无LTO。
关键参数 `-march=rv32i -mabi=ilp32 -Os -ffreestanding -fno-builtin -fno-pic -fno-pie
-msmall-data-limit=0 -ffunction-sections -fdata-sections -nostdlib -nostartfiles`，
链接 `--no-relax --build-id=none --gc-sections -lgcc`，生成debug和stack-usage资料。
完整构建命令见build.ps1，段表/map/反汇编/.su位于每组build目录。

首次统一-O2的performance BIN为17108字节，超出16368上限740字节，转换器拒绝DAT。
随后统一改-Os，两组均满足装载上限，不扩RAM/DDR窗口或loader。
另以sim/coremark/build/size_o2隔离复现超限；该目录保留ELF/BIN/size/compile.log，无DAT。

| 配置（ITERATIONS=1） | text | data | BSS | BIN | 剩余装载空间 | 清单字数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| performance -Os | 13204 | 12 | 2020 | 13216 | 3152 | 3304 |
| validation -Os | 13204 | 20 | 2012 | 13224 | 3144 | 3306 |

两组main=0x40000ccc，main返回停留program_return=0x40000038。
performance BSS=0x400033a0–0x40003b84，validation=0x400033a8–0x40003b84。
链接ASSERT保证BSS不占4KiB栈，BSS结束到栈底还有46204字节。
ELF32小端RISC-V、入口正确、flags=0/soft-float、Tag_RISCV_arch=rv32i2p1；
每组最终可执行反汇编2766条指令逐条审查opcode/funct，包括链接的libgcc，无M/C/F/A。
nm -u为空，无memcpy/memset/libc未解析引用。ELF载入段逐字节匹配BIN，DAT解码/填零/
尾部清单一致。候选boot_rom.dat与现有ROM loader逐字节一致。

编译有官方ee_printf未使用precision/两处fallthrough和原链接RWE段warning，
无编译/链接error。本核未实现内存执行权限，RWE警告不代表已做权限隔离。

## 短迭代 Full Boot

真实SoC从PC=0执行原ROM loader，从本实验最终DAT搬到A5毒化的DDR后跳转。
检查loader每次地址/内容/strobe、跳转前全部loadable字、BSS原始毒化及main前清零。
最初TB误把LA SP的AUIPC中间值当最终SP，约56227周期失败；已修正为允许startup
0x40000008中间写入，0x4000000c必须为0x40010000，此后所有SP写必须在栈内。
这是TB验收修正，没有修改CPU或软件。日志中的第一次失败不作为CRC运行结果。

TB独立从UART TXD按115200/8N1采样，字节逐个对比接受的SB请求，保存原始LF文本。
无CPU同步异常/IRQ、总线错误、UART重复/漏字节、超时；栈底64字节guard和DDR写区间受检查。
两次CYCLE接受周期差与报告ticks精确一致，末尾等待TX空闲。
runner核对seed/list/matrix/state/final CRC、模式、数据大小、iterations、编译器/参数、
唯一的时间不足ERROR和PORT_DONE；任何其他错误拒绝验收。

performance已完成CRC_FUNCTIONAL_PASS：e9f5/e714/1fd7/8e3a，final=e714；
ticks=12271801，UART537字节，17,201,411周期，退休1,209,161条，min SP=0x4000fa40，
实测栈占用1472字节（保留栈2624字节），ModelSim编译/运行Errors0/Warnings0。
validation也完成CRC_FUNCTIONAL_PASS：18f2/e3c1/0747/8d84，final=e3c1；
ticks=12974244，UART536字节，17,892,520周期，退休1,260,881条，min SP同为0x4000fa40，
栈占用1472字节，ModelSim编译/运行Errors0/Warnings0。

两组ITERATIONS=1，计时分别约0.131秒和0.138秒，原版Total time(secs)截断为0，
唯一ERROR是时间不足，随后Errors detected。三种已知CRC和seedcrc全部匹配，
单迭代crcfinal与crclist一致；不推广这一final关系到其他迭代数。
两组最终验收为 **2/2 CRC_FUNCTIONAL_PASS，正式分数无效，实板NOT_TESTED**。
额外在内存中篡改CRC、删时间错误、改ticks，验收脚本全部拒绝（3/3），
脚本留在sim/coremark/build/check_parser.py，未修改原始UART/镜像。

| DAT | SHA-256 |
| --- | --- |
| build/performance/main.dat | 52b8b8eafa58bc924c1497e1ff2ba49d071c81e4c0b2bb563a338ee4b04de075 |
| build/validation/main.dat | 6226c170f6bbe734aa7b20039b46d39b4161b3d57fb04ab936b00fd040e615f4 |

## 复现

从工程根目录：

```powershell
& ./tests/coremark_baremetal/build.ps1 -Mode performance -Iterations 1
& ./tests/coremark_baremetal/build.ps1 -Mode validation -Iterations 1
& C:/python/python.exe sim/coremark/run.py --audit-only
& C:/python/python.exe sim/coremark/run.py
# 可选的隔离-O2尺寸反例：预期转换失败，不覆盖已验收-Os产物
& ./tests/coremark_baremetal/build.ps1 -Mode performance -Optimization O2 `
  -OutputDirectory D:/riscv/RISCV/sim/coremark/build/size_o2
```

验收后部署必须用同一DAT，不能重建另一DAT直接上板。
本次没有切换主RAM IP、重生成IP/PDS、下载或实板CoreMark运行。

## 证据与边界

五个算法.c的MD5与随包清单一致，coremark.h仍为b0ec69b6c8e75853d06accb3b1bcf534；
其与清单的历史差异维持源码核对文档中的说明，不修算法/清单。
运行保护哈希包括生产RTL、CoreMark算法/头/清单、PDS/FDC、RAM/ROM初始化、
原loader和成功DAT。Echo SHA256仍2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20，
输出30仍e240a9bff8fe79b387b6814315b043214fcec7eeb5d1d6b9fa76a56abce80ff5。

证据路径：sim/coremark/build/<mode>/{compile.log,modelsim.log,uart.txt,validated_image.json}，
总结果sim/coremark/build/results.json；tests/coremark_baremetal/build/<mode>/保存尺寸/镜像资料。
新仿真是有背压/延迟的用户口模型，不包含物理DDR训练、board_top消抖/LED或USB-TTL。
生产RTL和共用TB未改，因此本步未重跑原完整DDR物理模型/全CPU/UART回归，历史PASS不冒充本次。
尚未校准实板计时、运行至少10秒performance/validation、验证32位跨界或给出正式分数。
后续先部署同一已验收短DAT并捕获UART，再按实板速度选10–30秒的固定迭代重新验收；
报告精确速率用iterations*93750000/ticks，只有正式规则满足后才可作为分数。
