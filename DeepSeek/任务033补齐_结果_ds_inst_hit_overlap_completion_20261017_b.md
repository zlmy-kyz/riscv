# 任务033补齐结果：三个未触发场景与统计修正

2026-10-17。按 `DeepSeek/任务033补齐_三个未触发场景与统计修正.md` 执行：只补三个未触发场景、修正离线判据，不重跑旧桥 on/off、CPU、CoreMark、PHY 或历史全套，未改设计。

**状态：`TASK033_COMPLETION_PASS_PENDING_CODEX_REVIEW`**

---

## 1. 结论

| 复核项 | 原状态 | 本次实测 |
|---|---|---|
| 性能差 | 报告称省 19 拍（只算 I 末响应） | **省 6 拍**：`max(D R, 全部 I R) − D AR` = on 19 / off 25；以 D 接受为起点为 20 / 26 |
| 独立 I hit 待消费时复位 | 未触发（363 沿主槽是旧 D 响应） | **已触发**：I 接受 19、复位 20、取消 I=1/D=1；POST 于接受沿即显示响应 |
| 停放 miss 提升 AR 后复位 | 未触发（424 复位把 D 一起取消） | **已触发**：D 响应 75 → 保存地址 I AR 76 → 80 复位（AR 后 4 个边沿）；取消 I=1/D=0 |
| 无缓存 D 读与真实 I hit 并行 | 未触发（490 实际发 I AR，是 miss） | **已触发**：Camera/PP 各 2 次真实 I hit，一次落在延迟 D R 沿，双响应同沿 |

未发现已证实的 RTL 错误：被测桥 SHA256 前后一致，本次未改任何 RTL/IP/约束。

## 2. 固定输入与证据复用

被测桥 `myriscv/dual_sram_to_pango_ddr_bridge.v` = `7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933`（本次无 RTL 变化，不要求重新 PDS）。

| 复用证据 | SHA256 |
|---|---|
| 原运行 `build/ds_inst_hit_overlap_20261017_a/manifest.json` | `8a055333872a3ce30befeb1c99f432b9fec682cffa801ffc2bc2cdb46fc53f0f` |
| 原封存 `sealed_ds_inst_hit_overlap_20261017_a/manifest.json` | 同上（两份清单逐字节相同） |
| 复核回执 `review_20261017_01/review.json` | `3602fe4eaa6ef05114ac631e32e951b77e5e27afe79637f118dac3627d5e36fda` |
| `bridge_on.edges.log` | `b8d3259055aad4f1de70c95ada7f88dabfe4f4a6b64f738e80967d483540b3968` |
| `bridge_off.edges.log` | `6bb4c136ccfbe49ea62fd7a4cf6aead4d20875cffa93eda142f464d8da98dc6b3` |
| `soc.edges.log` | `6ea89325aa4845b07fa5ecccac988edcd194020c0acf2582a448b44d02758f7b3` |
| `soc.mem.log` | `aa368f7d9987fc2b0a22ea3872dd24179589bf2910375a55cd3744bee4f8f7439` |

新输入/模型/TB/checker/runner（全部 `completion` 命名，旧实现逐字节未动）：

| 文件 | SHA256 |
|---|---|
| `tb_inst_hit_completion.sv` | `d706ecc31a5dab513c0b69d2b1cfe78ea1cac01406113ed3b9006b1c72cb774a` |
| `ddr_model_completion.sv` | `8039d8ce074aa6544e2491bba2fbe81ba8e22fde5f0568a74b54e8ede6ba1ebb` |
| `check_completion.py` | `436d5217e3f7490f1afa04e401db1ff41f7837aae6e04a91de01867f5ecb7cdd` |
| `selftest_completion.py` | `d404e393668e3838fcf0e72637b9fa48b526a533f175f5e83a85854906d46614` |
| `prepare_completion.py` | `11076e821e51d1c9968fccef7624a843a0435b575080a774a56f0f3f52c2a8ca` |
| `seal_completion.py` | `5752f5c48fadc55d55ee4cffbbbad899e10718c5fe11bf5f0a0d4c59ed06a982` |
| `run_completion.py` | `c01ade947b955b7abeb05c66fdaefa7110883e42b6da3158600578c601cbf8b3` |
| `inputs_completion.json` | `daae6e040b2982a11ca85c8cf2d637a31e8d728bff66d134f0f8258414d9d89e` |
| `completion_plan.txt` | `f3804c1ae43c2f51d0118c77f1e3fa9f2af6c22091688e273bca0a817d295e03` |
| 封存清单 / 运行副本清单 | `fc80eacad2ccde784c4aef9b4f0c2b4207d740af02a0f27de12b691e61efb236`（两份逐字节相同） |

工具与厂家源身份：`D:/modelsim/win64pe`（vsim 10.6c，vsim `95fd675a…`、vlog `5e1aed9a…`、vlib `521c7dcf…`）；厂家原语 `C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation`（`GTP_GRS.v`、`GTP_DRM36K_E1.v` 进编译）；Python 3.13.0。本次作业的 9 个源文件递归 `include` 闭合为 0 项（icache/dcache/桥/GTP 均无 `include`），`$readmem` 运行期文件读为 0 项。

## 3. 执行

```powershell
Set-Location D:\riscv\RISCV
python -B sim/cpu_inst_hit_overlap/prepare_completion.py
python -B sim/cpu_inst_hit_overlap/run_completion.py --check-inputs
python -B sim/cpu_inst_hit_overlap/run_completion.py --run --tag ds_inst_hit_overlap_completion_20261017_b
```

`--check-inputs` 时正式目录不存在；`--run` 只编译 `build/<tag>/src` 副本，顺序为「旧证据离线核验 → vlib → vlog → 一个桥顶层一次 vsim → 补测 checker → 合成负例」，首败即停。正式运行 2026-10-17T18:58:55Z 开始，18:59:02Z 结束。

| job | 退出 | 超时 | 耗时 | Errors/Warnings | 结论 |
|---|---|---|---|---|---|
| check_legacy | 0 | 否 | 0.50 s | — | PASS（旧 on/off/SoC 离线复核） |
| vlib_work | 0 | 否 | 0.17 s | 无 `** Error` | PASS |
| vlog_work | 0 | 否 | 0.42 s | Errors: 0, Warnings: 0 | PASS（9 个模块） |
| sim_completion | 0 | 否 | 1.67 s | Errors: 0, Warnings: 0 | PASS，`$finish` 正常（tb 第 329 行） |
| check_completion | 0 | 否 | 0.32 s | — | PASS（`"status": "PASS"`） |
| selftest_completion | 0 | 否 | 0.58 s | — | PASS 10/10 |

`RESULT: PASS inst_hit_completion edges=196`；`# IPSpecCheck: 04030130 … c_WR_ADDR_WIDTH` 为两个 DRM 实例各一条已声明 IP note（`#` 注释，非 `** Warning`），与旧运行一致。

## 4. 三个场景的实测边沿

### 4.1 独立 I hit 待消费时复位（epoch 1）

| 事件 | 边沿 |
|---|---|
| I 行真实填充：接受 / I AR / R / 响应 | 6 / 8 / 12 / 13 |
| D 冷 miss：接受 / D AR（AR 背压 2 拍） | 15 / 18 |
| 独立 I hit（0x104）接受，**D AR 已握手、R 未到** | **19**（`ia=00000104`，主槽在 RDATA，`inst_req_ready` 只由并行槽给出） |
| 该接受沿 POST 采样 | `ip=1`，`id=7e714b5d`（下一沿响应已成立） |
| 复位 | **20**（= 原定 E1 消费沿），`rst=0`，响应记为取消不记有效 |
| 取消账 | I=1（0x104）、D=1（0x1000） |
| 复位后冷读：接受 / I AR / 响应 | 26 / 29 / 42（行 `0x100` 重新真实读，证明 valid 已清） |

复位沿 `ip=1` 是组合残留，checker 明确「复位沿只记不判」，只作为 `reset_edge_rsp` 记录。

### 4.2 停放 miss 已提升 AR、尚未 R 时复位（epoch 2）

| 事件 | 边沿 |
|---|---|
| 第二个 I 行真实填充（毒化目标 0x120）：接受 / AR / R | 43 / 46 / 58 |
| D 冷 miss：接受 / AR / R / **响应消费** | 61 / 62 / 74 / **75** |
| D miss 期间接受 I miss（0x140） | **63**（parked，未发 AR） |
| 毒化 live 地址 → `00000120`（该行此刻确实在缓存中） | 63 |
| 保存地址的唯一 I AR 真实握手 | **76**，`ara=0000050`（=0x140），`ari=0` |
| 复位 | **80**（AR 后 4 个完整边沿，其间无 I R） |
| 取消账 | I=1、**D=0**（旧 D 已响应） |
| 复位后冷读：接受 / 响应 | 86 / 100 |

关键点：AR 用的是 `inst_overlap_addr`（0x140），不是 live 地址 0x120；若按 live 地址比较，该拍本会命中并立刻给出错误响应。checker 从外部 `ia` 与 AR 地址的差异、以及「live 地址当时是有效缓存行」两点证明这一点，不依赖内部 pending。

### 4.3 无缓存 D 读与真实 I hit 并行（epoch 3）

Camera（局部 `0x01000000`，窗口 `0x01000000–0x013fffff`）：

| 事件 | 边沿 |
|---|---|
| I 行真实预热：接受 / AR / R / 响应 | 102 / 105 / 115 / 116 |
| 无缓存 D 冷读：接受 / D AR（背压 2 拍）/ R / 响应 | 117 / 120 / 130 / 131 |
| I hit #1（`0x01000008`，lane 2）：接受 / 响应 | 121 / 122（D 仍在等 R，**无 I AR**） |
| I hit #2（`0x0100000c`，lane 3）：**恰在 D R 沿接受** | **130**（该沿 `rv=1, rid=1`，与 AR 沿 120 不同沿） |
| 双响应同沿 | **131**（`ip=1, dp=1`，`dd=878d3af2`） |
| 合法 model poke 同址 | 132 |
| 再读 D：接受 / AR / 响应=新值 | 133 / 136 / 147（`a5c30f1e`，与旧值不同；**仍发 AR，无缓存行未被 I 填**） |

Preprocess（局部 `0x02000000`，窗口精确 `0x02000000–0x0200ffff`）：

| 事件 | 边沿 |
|---|---|
| I 行真实预热：接受 / AR / R / 响应 | 148 / 151 / 161 / 162 |
| 无缓存 D 冷读：接受 / AR / R / 响应 | 163 / 166 / 176 / 177 |
| I hit #1（lane 2）：接受 / 响应 | 167 / 168 |
| I hit #2（lane 3）：恰在 D R 沿接受 | 176 |
| 双响应同沿 | 177（`dd=44ddd3c8`） |
| poke / 再读 D：接受 / AR / 响应 | 178 / 179 / 182 / 193（`5e1f2d7b`） |

对照复核要求：旧 checker 的 PP 判定是 4 MiB 宽比较（`addr>>22 == 0x008`），新 checker 改为精确 `0x02000000–0x0200ffff`；Camera 保持 `0x01000000–0x013fffff`（与 RTL 的 `data_req_addr[31:22]` 一致）。

### 4.4 逐 epoch 守恒（196 条边沿）

| epoch | I 接受/响应/取消 | D 接受/响应/取消 | AR | R |
|---|---|---|---|---|
| 1 | 2 / 1 / **1** | 1 / 0 / **1** | 2 | 1 |
| 2 | 3 / 2 / **1** | 1 / 1 / **0** | 4 | 3 |
| 3 | 7 / 7 / 0 | 4 / 4 / 0 | 7 | 7 |

每 epoch 满足 `接受 = 响应 + 取消`；全程 DDR 在途读 ≤ 1；无请求在复位沿被接受；无响应在无请求时出现。

## 5. 统计修正与 CPU 绑定

旧 on/off 轨迹由新 checker 逐事件重放（92 次接受/参数组、逐 AR 行地址、逐 R beat、逐响应数据、写通道字节使能与转发全部重算）：

| 量 | on | off |
|---|---|---|
| D 接受 | 545 | 575 |
| D AR | 546 | 576 |
| D 响应 | 565 | 595 |
| 末 I 响应 | 552 | 601 |
| 全部完成 `max(D R, 全部 I R)` | **565** | **601** |
| 完成 − D AR | **19** | **25** |
| 完成 − D 接受 | **20** | **26** |

`19` 与 `25`、`20` 与 `26` 是固定预期常量（写在 checker 里，不由实测生成）；差值由 checker 自己重算并断言等于 **6**。原报告的「省 19」是把 on 窗口算到末 I 响应（552−546=6）、off 算到末 I 响应（601−576=25）后相减所致，本次明确更正；绝对 552/601 含前面场景的 30 拍偏移，不作为本场景收益。两版接受的逻辑请求序列（type+addr，92 对）逐项相同。

CPU 真实并行 I 的 token 绑定（从旧 `soc.edges.log` 的 E/F/R 行独立重取）：D 读接受 **45** → I 接受 **46**（`ia=00000024`）→ I 响应 **47**（`id=02008093`）→ 响应缓冲 **48…61** 保持同一 `pc=40000024` → **62** 唯一 pop → **66** 该次退休（`inst=02008093`、`rd=01`、`wdata=40001020`）。8 次循环各一次接受/一次 pop，一一对应。错误路径证据复用：原分支错误路径与两个权限 trap 不重跑；旧 SoC 镜像中错误路径 store 地址 `0x1140` 所在 DDR 拍（beat 138）与参考镜像逐字节一致，且整条轨迹无该地址的 D 请求、无该地址的 AW。

## 6. 独立 checker 的硬门（任一未触发即 FAIL）

- 场景一：`epoch1 i_cancel==1 && d_cancel==1`；独立接受是**缓存命中**且无自己的 AR；接受时 D 的 AR 已握手、响应未到；复位沿 == 接受沿+1；该接受沿 POST `ip=1`；该行仅 1 次 AR（预热）；复位后首次访问同址必为 miss 且重新发 AR。
- 场景二：`epoch2 i_cancel==1 && d_cancel==0`；停放的请求是 miss 且 `D AR < 接受 < D 响应`；存在自己的 AR 且 `AR > D 响应`；`复位沿 − AR ≥ 2`；AR 行 == 保存地址行（≠ live 毒化地址），且 live 地址当时是有效缓存行；D 响应后该 epoch 恰有 1 条 I AR；复位后同址冷读成功。
- 场景三（每窗口）：D 接受 2 次（首读+poke 后重读），均为 miss 且各自有 AR；I 预热 1 次真实填充且早于 D 读接受；命中恰 2 次，hit#1 在 `D AR < 接受 < D R`、响应=接受+1；hit#2 接受沿 == D R 沿且该沿 `rv=1, rid=1`；两响应同沿（`ip&&dp`）；两次命中 word lane 不同；D AR 存在 ≥1 拍背压且 R 晚于 AR ≥2 拍；窗口内 I AR 只有预热那一条；poke 恰 1 次且早于重读；重读值与首读值不同。
- 全局：期望接受序列 18 条（side/addr/hit|miss/epoch）逐项固定比对；X/Z 仅在复位或非有效字段上容忍，复位释放后控制信号必须已知、有效握手/响应的地址与数据必须已知（保留原值，不静默改 0）。

## 7. 合成负例（离线，10/10 拒收）

| 负例 | 拒收理由 |
|---|---|
| main_slot_hit（把独立 hit 换成普通主槽 hit） | `epoch 1 cancels: I=0 D=1` |
| promoted_ar_missing（删掉提升后的 I AR） | `the parked I miss was never promoted to its own AR` |
| reset_before_d_done（D 未完成即复位） | `epoch 2 cancels: I=1 D=1` |
| parallel_i_miss（并行 I 实为 miss 却立即响应） | `I miss response edge 122 is not R+1` |
| perf_claim_19（沿用只算末 I 响应的口径） | `all-done minus D AR is 6, expected 19` |
| cancel_split（取消数记到错误的侧） | `epoch 1 cancels: I=0 D=2` |
| valid_byte_x（有效响应字节为 X） | `I response data is unknown while valid` |
| cpu_double_pop（同一响应被消费两次） | `9 pops but 8 accepts of the same PC` |
| store_escape（年轻错误路径 store 逃逸） | `the wrong-path store changed DDR beat 138` |
| control（未改动轨迹） | 仍 PASS，证明负例非空转 |

合成只用离线数据，不计入 HDL 覆盖。

## 8. 与旧结果的关系

- 更正：性能差 19 → **6**（口径见 §5）；场景一二三原本未触发，本次补齐；checker 的 X 静默归零、复位无状态到达条件、跨版本只输出不断言、CPU 只做全局计数，均在新的 `check_completion.py` 里改为硬门。
- 复用不改：原 `build/ds_inst_hit_overlap_20261017_a`、`sealed_…_a`、`aborted_run_20261017_a`、`review_20261017_01`、两份 preparation 目录与三份任务/结果文档全部只读；原报告与旧 checker/日志未改一字。
- 保护行 **311 行、0 漂移**，分两类（口径与 `--check-inputs`、after 快照一致）：
  - **295 行严格逐字节比对**（旧运行/封存/首败/复核全部产物、旧 TB/模型/checker/runner、任务与结果文档、桥/IP/CPU 源、P300/V300 成功 BIN）：运行前后 SHA256 全部相同，`_drift_rows = 0`；桥 `7ab9d34c…52d933` 一致。
  - **16 行 `metadata_only`**（PDS 工程会话与 IP 生成元数据：`RISCV.pds`、`constraint_check/temp_constraint_file.fdc`、`ipcore/{i,d}cache` 下 `.last_generated`/`.settings`/`.idf`/`generate.log`/`*_Reset_Value.v`/`*_init_param.v`/`ipm2l_sdpram_*`），只核存在性、不做字节相等断言。其中 `RISCV.pds` 的前后值确实不同（`cc5aa75a…b2573f` → `cad3dd20…34d10a`），**不是本次运行造成的**：该差异在准备阶段 `preparation_20261017_b/identity.json` 里已以 `match:false, metadata_only:true` 记录，且文件 `LastWriteTime = 2026-10-17 10:40:01`，早于准备与本轮运行（12:58 开始），属打开 PDS 工程重写会话元数据所致。同理其余 15 行在 after 快照中保持 `match:true`，无一例被误判为设计改动。
- 未再走「首败后改 runner 复跑同 tag」：本次正式目录首次创建即跑完，`build/ds_inst_hit_overlap_completion_20261017_b` 此前不存在。

## 9. 未覆盖 / 未运行

PDS 综合与实现、时序、物理 DDR/PHY、串口、实板、Full Boot、CoreMark、相机/CNN 数据通路、x16 配置、`INST_HIT_UNDER_DATA_MISS_ENABLE=0` 的补测版本全部 NOT_RUN。本任务只跑 x32 + I/D cache + posted 写开启 + 并行参数 1 的一个桥顶层、一次 vsim；不生成 Codex 门。

## 10. 交付位置

- 证据根：`sim/cpu_inst_hit_overlap/build/ds_inst_hit_overlap_completion_20261017_b/`
  （`completion.edges.log` 196 条 PRE/POST、`completion.tok.log` 阶段与 poke、`completion.mem.log` 8256 拍、`logs/` 六份控制台、`run_meta.json`、`manifest.json`、`tools.json`、`git_*`）
- 封存树：`sim/cpu_inst_hit_overlap/sealed_ds_inst_hit_overlap_completion_20261017_b/`
- 入口：`prepare_completion.py` / `run_completion.py`；判据：`check_completion.py` / `selftest_completion.py`
- 轨迹/内存 SHA：edges `c6786614f21e5e801486b2bf03a662aa2e224f448dabf298e3f38a2f116e430a8`、tok `2b9748a29f0952aca61d5a317586f37b40a9f2201d08ce3d8fdb0aa634550674d`、mem `07ba4928f411eaeed19fbed09cf7a45700be992bfeb807860060bc7b48f7fe744f`
- `run_meta.json` = `10ad16e2924c489126391676473a9708c862b69a02a8fd469b3334c3313f69dc`

Git：HEAD `4ee48abbe75f8a6609e961ef7858568be1ed6f5a`，运行前后 head/status/diff 逐字节相同，未提交、未推送。
