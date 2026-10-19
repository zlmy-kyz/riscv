# 任务031续测：ROM/RAM初始化参数封存补齐

**任务已执行，不再领取或重跑**：四原生命令均正常完成，runner在独立IRQ参考比对处STOP；原结果与日志保持。Codex已按TB实际pin时序/CPU排空契约独立修正参考并离线核完整430EV/BUS，通过新独立功能门，没有重跑HDL或倒写旧STOP。当前待用户实际DDR测量，见[同阶段顶部](../doc/cpu/MINI_写缓冲完成同拍接续_2026-10-14.md)；本文以下为派发时历史。

2026-10-14。当前唯一可领取入口。沿用用户已授权的任务031收尾范围，**本任务明确允许DeepSeek只执行下面的新入口一次**，不自动调用DeepSeek。Codex负责设计/准备/原证据审查；DeepSeek负责仿真/测试执行及结果整理。旧tag `ds_write_buffer_turnover_20261014_a`已编译失败，目录、清单、日志和结果报告全部保留，禁止清理、复用或倒写PASS。

## Codex原始失败复核与修复

Codex已核[原失败收据](../sim/write_buffer_turnover/build/init_resume_preparation_20261014_a/failure_review.json)，状态TASK031_MISSING_INIT_INCLUDE_RAW_FAILURE_CONFIRMED。vlib exit/native0（实际0.2483402秒，旧报告0.192文字误记），vlog exit/native2、0.4814925秒、未超时，Errors258/Warnings0。258错误均是两个找不到include及两组128个INIT_xx未定义。control/key未派发，git_after/EV/BUS缺失仍保留，不补造。

问题是Codex准备的副本漏收include依赖，未构成RTL功能FAIL。修复只在新的封存清单加入：

- `ipcore/inst_rom/rtl/inst_rom_init_param.v`，SHA `77fdcc689dcfdfac13258f3754ae1f60351f806b055e7f4ae0e75e130a3af3a0`；
- `ipcore/data_ram/rtl/data_ram_init_param.v`，SHA `ad79a0fe32e541c0ec03f05fa44c4fd9870b9cd6bc3686815b4e25c222b550d3`。

两文件原内容不改，各128项INIT_00—INIT_7F定义核对；原incdir已覆盖，无需改编译源/参数。为保留失败身份，原`simulation_completion_inputs.json` SHA513b578c…13c96不重写，新的清单是`simulation_completion_init_resume_inputs.json` SHA **a891161f231a0ac81784432d2054d0941f655a2de240e57f2717ade3f3309763**；原Codex inputs SHA仍1b19dad3…403b692。

[静态收据](../sim/write_buffer_turnover/build/init_resume_preparation_20261014_a/static_review.json)=TASK031_INIT_INCLUDE_RESUME_STATIC_PREPARATION_PASS_HDL_NOT_RUN。207工程输入、3厂家源、3工具；原197项、CPU b1114fa3、桥2dfa96ca、TB/include/模型/参考/镜像/全部判据/检查数/超时保持。209份原失败文件/报告逐SHA保护。新入口复用原执行与审查实现，仅切换清单/tag，并在启动前与复制后递归核include闭合；静态复制演练证明6条include都存在，两个参数文件SHA一致。未运行HDL/PDS/串口。

## DeepSeek单次执行

```powershell
Set-Location 'D:\riscv\RISCV'
python -B sim/write_buffer_turnover/simulation_completion_init_resume.py --check-inputs
python -B sim/write_buffer_turnover/simulation_completion_init_resume.py --tag ds_write_buffer_turnover_init_resume_20261014_a
```

第一条已由Codex静态通过，第二条仅DeepSeek执行一次。新目录`sim/write_buffer_turnover/build/ds_write_buffer_turnover_init_resume_20261014_a`必须不存在。vlib/vlog各60秒、control/key各vsim-batch180秒；只跑先前未完成的同一组control/key，不扩历史030/029/ISA/CoreMark/Loader/PHY测试。不运行旧run.py/旧runner/prepare脚本/review脚本，不改任何RTL/TB/include/模型/参考/清单/判据/超时，不换tag或修权限/RPC重试；首败停止保留，未执行记NOT_RUN。

实际编译207封存输入中同样的36模块，两个初始化参数文件经include解析，不额外当模块编译。control6检查/49拍，key八组889检查/44拍（10/7/6/407/12/7/10/430）、430精确EV（428普通/1IRQ/1MRET）、143 CPU数据请求（64load/79store，其中73 DDR），原key覆盖字段保持。独立BUS核完整6筆短程序AW/W数据与strobe、5机会省5拍、旧W与新store所有权、响应/取消/字节更新/排空守恒。SOC_TURNOVER69为SoC机会，OP另外核实际接受和唯一late的前端状态，不把69直接当成功接续数。

runner自动保存实际argv/cwd/exit/native/elapsed/timeout、console/transcript、输入副本、Git前后、EV/BUS/result。必须Errors/Warnings0、正常finish、console/transcript归一全文相同，无FAIL/Fatal/RPC/timeout；厂家四条04030130原文每job保持。报告`DeepSeek/任务031续测_结果_ds_write_buffer_turnover_init_resume_20261014_a.md`，记录真实命令/所有检查/轨迹/输入与旧失败保持；正常状态WRITE_BUFFER_TURNOVER_COMPLETION_KEY_AND_CONTROL_PASS，失败STOPPED_FIRST_FAILURE。DeepSeek不得生成Codex PASS门。

Codex收到后用`review_completion_init_resume.py`核原证据，通过才在**新tag**目录生成WRITE_BUFFER_TURNOVER_RAW_EVIDENCE_REVIEW_PASS，并同一步直接给新上板入口`run_write_buffer_turnover_init_resume_measurements.ps1` COM9。门和证据不写进旧失败tag。沿用原固定P300/V300、成功bturn对照、新wturn_300_01日志，300次/CRC5275-8803/93.75MHz保持；不例行审PDS/位流。当前功能门仍关闭，上板与性能NOT_RUN，新实板结果前不另起优化。
