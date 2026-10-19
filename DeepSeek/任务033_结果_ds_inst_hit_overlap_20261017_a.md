# 任务033 结果：D 读 miss 期间 I 缓存查询并行（关键仿真）

状态：**TASK033_KEY_SIMULATION_PASS_PENDING_CODEX_REVIEW**
执行：2026-10-17，ModelSim DE-64 10.6c；未改主 RTL/CPU/IP/PDS/约束/成功 BIN/历史测试，未跑 PDS、串口、实板，未提交 Git。

被测对象：`myriscv/dual_sram_to_pango_ddr_bridge.v`，SHA256
`7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933`（与执行书一致），
参数 `INST_HIT_UNDER_DATA_MISS_ENABLE=1` 默认开启、仅 x32 且 I 缓存开启生效；`-gOVERLAP=0` 只作同一新桥的因果对照。

## 1. 最终可复现命令

```powershell
Set-Location D:\riscv\RISCV
python -B sim/cpu_inst_hit_overlap/prepare_program.py
python -B sim/cpu_inst_hit_overlap/seal_inputs.py
python -B sim/cpu_inst_hit_overlap/run.py --check-inputs
python -B sim/cpu_inst_hit_overlap/run.py --run --tag ds_inst_hit_overlap_20261017_a
```

`prepare_program.py` 输出：`plan tokens=190 groups=188 scenes=190`、
`soc program words=115 sha=697f6a1d704a74ac`。
`--check-inputs` 结果：`CHECK-INPUTS: PASS`（ModelSim 版本、桥 SHA、70 条设计/IP/BIN 身份、
正式目录此前不存在；唯一差异为 PDS 元数据 `RISCV.pds`，按执行书只记录、不作为放行前置条件）。

## 2. 身份与封存

| 对象 | SHA256 |
| --- | --- |
| `myriscv/dual_sram_to_pango_ddr_bridge.v` | `7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933` |
| `sim/cpu_inst_hit_overlap/tb_inst_hit_overlap.sv` | `79811a51fb800c6ff888f008a09e3438df90f939afbf7fc1628b411706ccb030` |
| `sim/cpu_inst_hit_overlap/tb_inst_hit_overlap_soc.sv` | `36eeb96859c8ce24f8213262194978b6b056edf358b076eef8f7241d9ab51487` |
| `sim/cpu_inst_hit_overlap/ddr_model.sv` | `42e35282b70a741dacbe850bb1faff0461cd5855fe0c6c8121268669b7e537ad` |
| `prepare_program.py` / `check_evidence.py` | `3aa1edf60c0959ec0f420177a44e5c7ce4ae70896280de5d47a78d700ad09c28` / `9ba9ee82e3a8ca4b17e62cc1a8f39f955e0c380b5698dcd9dc71e1a890b553a7` |
| `selftest.py` / `seal_inputs.py` / `run.py` | `f714cbcb55cb6d1c5516d14e6a9cd0411303c234785970801f34b36eac9998a4` / `87f49a40874989c380eefc15f592749f47c66edbe9b3b3e8156ee4bf6bbe687a` / `50a91879a75aa622df426e88613e2f63204992b958864f1ffd0cb3f6412a54a3` |
| `inputs.json` | `1323268b3ef9316b71d91152681a188c9b615bef2913bdca45c6c63b5706a975` |
| `plan_bridge.txt` | `72ecad920e17d2fc097f814bf6ed0b20702e0430f51e1767c37a6cf0cbbe7480` |
| `soc_program.hex` | `697f6a1d704a74acff03cf733397e05d6fb0bedd804621eacd9fae8cedfb783d` |
| `soc_fault_camera.hex` / `soc_fault_pp.hex` | `1d95a85ddf7722efd29ae3a0d932311cc24e9d7bc15038b0a774478cfc1088d0` / `767b7fced54230420f67a2e9be7bdb72165e2ab074bb35b1cc7ea5a9f5e209fe` |
| 封存清单 `manifest.json`（= 运行副本清单） | `8a055333872a3ce30befeb1c99f432b9fec682cffa801ffc2bc2cdb46fc53f0f` |
| 运行记录 `run_meta.json` | `bf21cb60a329ae39a930950c8f54908d61439c47be17439ee1c6abeb273bd756` |

封存目录 `sim/cpu_inst_hit_overlap/sealed_ds_inst_hit_overlap_20261017_a/`：50 个文件（37 个 RTL/TB/模型、
3 个 Verilog include、6 个脚本、4 个冻结输入），`src/` 保留工作树相对路径，
`+incdir+` 覆盖 `src/ipcore/data_ram/rtl`、`src/ipcore/inst_rom/rtl`、`src/myriscv`。
递归 include 闭包为 `inst_rom_init_param.v`、`data_ram_init_param.v`、`csr_defs.vh`
（IP 初值内容即以 localparam 形式封存，故不读外部初始化文件；`$readmem*` 只出现在
`GTP_DRM36K_E1.v`、`ipm2l_apm_distributed_sdpram.v` 的 `INIT_FILE != "NONE"` 分支，
本设计保持 `"NONE"`，模型侧 `preload_hex` 路径由 `+PROG/+FAULT_*` 指向已封存镜像）。
厂家原语 `GTP_GRS.v`、`GTP_DRM36K_E1.v`、`GTP_APM_E2.v` 从
`C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation/` 原样封存副本，
绝对路径与 SHA 见 `tools.json`/`manifest.json`。运行只从 `build/ds_inst_hit_overlap_20261017_a/src` 副本编译，
不读工作树原文件（`run.py` 复制后逐文件复核 SHA，不一致即停）。

工具身份：`Model Technology ModelSim DE-64 vsim 10.6c Simulator 2017.07`；
Python 3.13.0。`vsim/vlog/vlib` 绝对路径与二进制 SHA 记入 `tools.json`。

## 3. 执行序列与每 job 记录

固定顺序：vlib → vlog → bridge_on+独立检查 → bridge_off+独立检查/周期比较 → 合成自检 → vlib → vlog → soc+独立检查。
vlib/vlog 上限 60 s，vsim 上限 180 s，checker 上限 60 s；每个 HDL 顶层另有 100000 周期 watchdog（`n > 100000` 即 `$fatal`）。

| job | 类型 | native exit | 超时 | 耗时(s) | 判定 |
| --- | --- | --- | --- | --- | --- |
| vlib_work | vlib | 0 | no | 0.18 | PASS |
| vlog_work | compile | 0 | no | 0.39 | PASS |
| sim_bridge_on | sim | 0 | no | 1.64 | PASS |
| check_bridge_on | check | 0 | no | 0.32 | PASS |
| sim_bridge_off | sim | 0 | no | 1.61 | PASS |
| check_bridge_off | check | 0 | no | 0.34 | PASS |
| selftest | check | 0 | no | 1.37 | PASS |
| vlib_soc | vlib | 0 | no | 0.16 | PASS |
| vlog_soc | compile | 0 | no | 0.56 | PASS |
| sim_soc | sim | 0 | no | 1.83 | PASS |
| check_soc | check | 0 | no | 0.39 | PASS |

全部 ModelSim 作业 `Errors: 0, Warnings: 0`；`bridge_on` 568 边沿、`bridge_off` 604 边沿、`soc` 407 边沿，
均为 `RESULT: PASS` 后 `$finish`，无 `** Error/** Fatal/** Warning`。
`IPSpecCheck: 04030130 ipm2l_flex_sdpram ...` 出现 2 次（两个 cache 实例各一条），按执行书作已声明的 IP note 单列，不计 warning。

## 4. 桥定向组：逐场景真实边沿与计数

`on` = 开启版（`-gOVERLAP=1`），`off` = 同一 TB/同一数据/同一逻辑请求序列、仅关参数。
单元为**上升沿边沿号**，"accept/resp" 为 checker 从握手轨迹重算的接受边沿与响应边沿。

计入账目：`on` accepts=92 responses=87 cancels=5
（AR 44、AW 6、W 6、模型 poke 2、复位沿上响应 1）；
`off` accepts=92 responses=89 cancels=3。
两侧均满足 `接受 = 响应 + 明确复位取消 + 当前在途`，结束在途 0；每个 token 至多一个响应。

| 场景 | 类型 | on accept/resp | off accept/resp |
| --- | --- | --- | --- |
| `warm_i0_fill_lane0` | I | 5/11 | 5/11 |
| `warm_i0_lane1_hit` | I | 11/12 | 11/12 |
| `warm_i0_lane2_hit` | I | 12/13 | 12/13 |
| `warm_i0_lane3_hit` | I | 13/14 | 13/14 |
| `warm_i0_lane4_hit` | I | 14/15 | 14/15 |
| `warm_i0_lane5_hit` | I | 15/16 | 15/16 |
| `warm_i0_lane6_hit` | I | 16/17 | 16/17 |
| `warm_i0_lane7_hit` | I | 17/18 | 17/18 |
| `warm_i1_fill` | I | 18/24 | 18/24 |
| `warm_i1_lane1_hit` | I | 24/25 | 24/25 |
| `warm_i0_alias_fill` | I | 25/31 | 25/31 |
| `warm_i0_alias_lane1_hit` | I | 31/32 | 31/32 |
| `warm_i0_alias_lane2_hit` | I | 32/33 | 32/33 |
| `warm_i2_fill` | I | 33/39 | 33/39 |
| `warm_i3_fill` | I | 39/45 | 39/45 |
| `warm_i4_fill` | I | 45/51 | 45/51 |
| `warm_i5_fill` | I | 51/73 | 51/73 |
| `s1_d_miss_ar_backpressure` | D | 73/95 | 73/95 |
| `s1_i_hit_under_ar_stall` | I | 77/78 | 95/96 |
| `s1_d_rsp` | WAIT | -/- | -/- |
| `s1b_d_miss_r_wait` | D | 95/111 | 96/112 |
| `s1b_i_hit_under_r_wait_1` | I | 99/100 | 112/113 |
| `s1b_i_hit_under_r_wait_2` | I | 100/101 | 113/114 |
| `s1b_d_rsp` | WAIT | -/- | -/- |
| `s2a_d_ar_r_same_edge` | D | 111/113 | 114/116 |
| `s2a_i_accept_on_ar_r_edge` | I | 112/113 | 116/117 |
| `s2a_d_rsp` | WAIT | -/- | -/- |
| `s2b_d_late_r` | D | 113/123 | 117/127 |
| `s2b_i_hit_during_late_r` | I | 118/119 | 127/128 |
| `s2b_d_rsp` | WAIT | -/- | -/- |
| `s2c_d_r_on_i_rsp_edge` | D | 123/129 | 128/134 |
| `s2c_i_rsp_on_r_edge` | I | 127/128 | 134/135 |
| `s2c_d_rsp` | WAIT | -/- | -/- |
| `s2d_d_double_response` | D | 129/135 | 135/141 |
| `s2d_i_double_response` | I | 134/135 | 141/142 |
| `s2d_d_rsp` | WAIT | -/- | -/- |
| `s3_d_miss_window` | D | 135/153 | 142/160 |
| `s3_i_hit_burst_1` | I | 136/137 | 160/161 |
| `s3_i_hit_burst_2` | I | 137/138 | 161/162 |
| `s3_i_hit_burst_3` | I | 138/139 | 162/163 |
| `s3_i_hit_burst_4` | I | 139/140 | 163/164 |
| `s3_i_miss_parked` | I | 140/171 | 164/182 |
| `s3_probe_slot_full` | PI | -/- | -/- |
| `s3_d_rsp` | WAIT | -/- | -/- |
| `s3_parked_promote_hit_lane1` | I | 171/172 | 182/183 |
| `s3_i_rsp` | WAIT | -/- | -/- |
| `s4_d_miss_window` | D | 172/192 | 183/203 |
| `s4_i_miss_parked` | I | 175/214 | 203/223 |
| `s4_live_addr_poison` | X | -/- | -/- |
| `s4_probe_poisoned_hit` | PI | -/- | -/- |
| `s4_d_rsp` | WAIT | -/- | -/- |
| `s4_new_d_1` | D | 192/193 | 223/224 |
| `s4_new_d_2` | D | 193/194 | 224/225 |
| `s4_promote_rsp` | WAIT | -/- | -/- |
| `s4_parked_line_hit_after_fill` | I | 214/215 | 225/226 |
| `s4_i_rsp` | WAIT | -/- | -/- |
| `s4b_d_miss_window` | D | 215/229 | 226/240 |
| `s4b_i_miss_parked` | I | 218/243 | 240/254 |
| `s4b_d_rsp` | WAIT | -/- | -/- |
| `s4b_promote_rsp` | WAIT | -/- | -/- |
| `s5_d_miss_window` | D | 243/255 | 254/266 |
| `s5_new_d_at_completion` | D | 255/267 | 266/278 |
| `s5_i_blocked_at_completion` | I | 256/257 | 278/279 |
| `s5_new_d_rsp` | WAIT | -/- | -/- |
| `s5_i_rsp` | WAIT | -/- | -/- |
| `s6_old_i_hit_before_store` | I | 267/268 | 279/280 |
| `s6_store_hits_i_line` | W | 268/269 | 280/281 |
| `s6_young_i_blocked_on_store` | I | 269/279 | 281/291 |
| `s6_store_rsp` | WAIT | -/- | -/- |
| `s6_i_rsp` | WAIT | -/- | -/- |
| `s6_byte_store` | W | 279/280 | 291/292 |
| `s6_byte_store_i_miss` | I | 280/290 | 292/302 |
| `s6_i_rsp_b` | WAIT | -/- | -/- |
| `s6_half_store` | W | 290/291 | 302/303 |
| `s6_half_store_i_miss` | I | 291/301 | 303/313 |
| `s6_i_rsp_c` | WAIT | -/- | -/- |
| `s6_zero_strobe_store` | W | 301/302 | 313/314 |
| `s6_zero_strobe_i_miss` | I | 302/312 | 314/324 |
| `s6_i_rsp_d` | WAIT | -/- | -/- |
| `s7_old_write_aw_pending` | W | 312/313 | 324/325 |
| `s7_i_hit_under_write_busy` | I | 313/314 | 325/326 |
| `s7_i_rsp_a` | WAIT | -/- | -/- |
| `s7_i_miss_waits_drain` | I | 314/345 | 326/357 |
| `s7_probe_d_miss_blocked` | PD | -/- | -/- |
| `s7_i_rsp_b` | WAIT | -/- | -/- |
| `s7_d_after_drain` | D | 345/351 | 357/363 |
| `s8_d_line_warm` | D | 351/352 | 363/364 |
| `s8_d_rsp` | WAIT | -/- | -/- |
| `s8_pending_partial_store` | W | 352/353 | 364/365 |
| `s8_forward_same_word` | D | 354/355 | 366/367 |
| `s8_fwd_rsp` | WAIT | -/- | -/- |
| `s8_adjacent_word_no_forward` | D | 356/357 | 368/369 |
| `s8_adj_rsp` | WAIT | -/- | -/- |
| `s8_write_done` | WAIT | -/- | -/- |
| `s8_after_drain_merged` | D | 362/363 | 374/375 |
| `s8_merged_rsp` | WAIT | -/- | -/- |
| `s9a_i_hit_pending_consume` | I | 363/- | 375/- |
| `s9a_reset_on_hit` | R | -/- | -/- |
| `s9a_release` | R | -/- | -/- |
| `s9a_cold_after_reset` | I | 367/377 | 379/389 |
| `s9a_rsp` | WAIT | -/- | -/- |
| `s9b_d_miss_window` | D | 377/- | 389/409 |
| `s9b_i_miss_parked` | I | 380/- | 409/- |
| `s9b_reset_on_parked` | R | -/- | -/- |
| `s9b_release` | R | -/- | -/- |
| `s9b_cold_after_reset` | I | 384/404 | 413/433 |
| `s9b_rsp` | WAIT | -/- | -/- |
| `s9c_d_miss_window` | D | 404/- | 433/453 |
| `s9c_i_miss_parked` | I | 407/- | 453/- |
| `s9c_d_rsp` | WAIT | -/- | -/- |
| `s9c_reset_awaiting_r` | R | -/- | -/- |
| `s9c_release` | R | -/- | -/- |
| `s9c_cold_after_reset` | I | 427/447 | 457/477 |
| `s9c_rsp` | WAIT | -/- | -/- |
| `s10_camera_first_read` | D | 447/454 | 477/484 |
| `model_poke` | M | -/- | -/- |
| `s10_camera_second_read` | D | 454/461 | 484/491 |
| `s10_cam_rsp` | WAIT | -/- | -/- |
| `s10_pp_first_read` | D | 461/468 | 491/498 |
| `model_poke` | M | -/- | -/- |
| `s10_pp_second_read` | D | 468/475 | 498/505 |
| `s10_pp_rsp` | WAIT | -/- | -/- |
| `s10_camera_under_i_hit` | D | 475/489 | 505/519 |
| `s10_i_hit_no_camera_fill` | I | 479/496 | 519/526 |
| `s10_cam2_rsp` | WAIT | -/- | -/- |
| `perf_warm_1` | I | 496/497 | 526/527 |
| `perf_warm_2` | I | 497/504 | 527/534 |
| `perf_warm_3` | I | 504/511 | 534/541 |
| `perf_warm_4` | I | 511/518 | 541/548 |
| `perf_warm_5` | I | 518/525 | 548/555 |
| `perf_warm_6` | I | 525/545 | 555/575 |
| `perf_d_miss` | D | 545/565 | 575/595 |
| `perf_i_hit_1` | I | 546/547 | 595/596 |
| `perf_i_hit_2` | I | 547/548 | 596/597 |
| `perf_i_hit_3` | I | 548/549 | 597/598 |
| `perf_i_hit_4` | I | 549/550 | 598/599 |
| `perf_i_hit_5` | I | 550/551 | 599/600 |
| `perf_i_hit_6` | I | 551/552 | 600/601 |
| `perf_d_rsp` | WAIT | -/- | -/- |
| `perf_i_rsp` | WAIT | -/- | -/- |

### 各覆盖类实际命中的事实

- **预热与 D 长 miss**：8 个 I word lane 全部覆盖（`warm_i0_lane0..7`），至少两个不同 index
  （`warm_i0` index 0、`warm_i1` index 8、`warm_i2..i5` index 16/24/32/40）及同 index 不同高 tag 的 miss
  （`warm_i0_alias_fill` 的 AR 地址为 `0x00002000`，index 仍为 0、tag 256，与前次 `0x00000000` 区分）。
  AR 背压窗口内接受 I hit：`s1_i_hit_under_ar_stall`（on 在 77/78 返回，D 于 95 才返回）；等 R 窗口内接受 I hit：
  `s1b_i_hit_under_r_wait_1/2`（99/100、100/101，D 于 111 返回）。D 地址/lane/归属在 22 拍与 16 拍窗口内保持（AR 字段背压稳定、W lane 与 AW 逐项一致）。
- **接受/返回边界**：`s2a`（111 接受 D，112 接受 I，D 响应 113 —— AR/R 同拍且接受 I）、
  `s2b`（D 晚 R：113 接受、123 响应，I hit 118/119 落在窗口内）、
  `s2c`（D 于 123 接受、129 响应，I 127/128 在 D 响应沿前被消费，区分 R 总线边沿与 D 侧响应边沿）、
  `s2d`（129 接受 D、134 接受 I、135 两侧同沿各自响应）。
- **连续 I 接续**：`s3` 在 136..139 连续 4 笔已缓存 I hit（消费旧 I 同时接受新 I，地址/index/lane 各不相同），
  第 5 笔 `s3_i_miss_parked`（140）为 miss 进独立槽；随后 `s3_probe_slot_full` 证明槽满不再接受 I。
- **停放 miss 与地址毒化**：`s4_i_miss_parked`（175 接受，on 在 214 由保存地址提升返回）、
  `s4_live_addr_poison` 把 live 地址改成预热 hit/不同 lane 后，`s4_probe_poisoned_hit` 未变假 hit；
  D 返回前无 I AR（AR 序列中 175..214 无对应 I AR）；`s4_new_d_1/2`（192/193）先接受两笔新 D；
  解除竞争后用保存地址发唯一 I AR，返回正确 word，`s4_parked_line_hit_after_fill`（214/215）同行 hit。
  `s4b` 覆盖无竞争时 earliest 提升（D 229 返回、I miss 243 返回）。
- **主槽 D 优先**：`s5_new_d_at_completion`（255）在 D 完成沿接受新 D，`s5_i_blocked_at_completion`（256）被推迟且未被旁路覆盖，256/257 完成。
- **store 与 I 失效**：`s6_old_i_hit_before_store`（267/268 返回旧 I 数据）、同一沿 `s6_store_hits_i_line`（268）接受命中该 I 行的 D store，
  `s6_young_i_blocked_on_store`（269/279）该沿新 I 在 on 版不能被接受（off 版 281/291 为对照）；
  随后 `s6_byte_store`、`s6_half_store`、`s6_zero_strobe_store` 各以 1 字节/半字/零 strobe 更新独立内存，
  对应 I 请求均 miss 并在排空后读到按 strobe 合并的新数据。
- **旧写排空**：`s7_old_write_aw_pending`（AW 尚未被接受，312 期间）与 AW 已接受、W 仍在等待的窗口分别给 I hit（`s7_i_hit_under_write_busy` 313/314 完成）
  与 I miss（`s7_i_miss_waits_drain` 314 接受、345 等排空后才返回）；
  `s7_probe_d_miss_blocked` 证明 D miss 在旧写忙时不被接受；`s7_d_after_drain`（345/351）排空后接受并进入新的 I 并行查询窗口。
- **转发保持**：`s8_forward_same_word`（354/355）同 word 部分字节转发、`s8_adjacent_word_no_forward`（356/357）同行邻 word 不转发、
  `s8_after_drain_merged`（362/363）排空后按独立内存合并值返回；未用整 wdata 覆盖未选字节（W strobe 逐 lane 核对）。
- **复位取消**：`s9a`（I hit 待消费）、`s9b`（I miss 停放）、`s9c`（I 提升后等 R）各复位一次，
  每个 epoch 账目守恒（取消数由复位前 token 重算，`s9a/s9b/s9c` 的 `*_cold_after_reset` 只得到冷数据）；
  复位期间 `ddr_init_done=0` 不接受新请求。
- **无缓存边界**：`s10_camera_first_read`/`second_read` 之间由模型合法外部更新内存（`model_poke`），两次均发 DDR 且读到新值（454/461）；
  PP 区同（461/468）；`s10_i_hit_no_camera_fill`（479/496）确认 I 并行 hit 不误填 Camera 区。

## 5. 受控性能子场景与两版周期差

计时边界固定：同一预热后一次 D 长 miss（`perf_d_miss`）加 6 笔真实 I hit（`perf_i_hit_1..6`），
以 D AR 接受为相对基准；逻辑完成 = 两侧全部请求响应收齐。

| 指标 | 开启版 | 关闭版 |
| --- | --- | --- |
| D accept / resp | 545 / 565 | 575 / 595 |
| D AR 接受边沿 | 546 | 576 |
| 6 笔 I hit accept | [546, 547, 548, 549, 550, 551] | [595, 596, 597, 598, 599, 600] |
| 6 笔 I hit resp | [547, 548, 549, 550, 551, 552] | [596, 597, 598, 599, 600, 601] |
| `span_from_ar`（末 I hit resp − D AR） | 6 | 25 |
| D 响应前完成的 I hit 数 | 6 / 6 | 0 / 6 |
| 末 I hit resp − D resp | -13 | 6 |

结论：开启版全部 I hit 在 D 响应之前返回（最晚 552 < D 响应 565），
关闭版第一笔 I hit 要到 D 响应之后才被接受（595 ≥ 595），
末笔 I hit 落在 601。**同一物理窗口内开启版比关闭版少 19 个边沿**
（`span_from_ar` 6 vs 25）；
整条 perf 组末笔 I 响应绝对边沿 552 vs 601（差 49）。
隐藏等待的具体边沿：开启版 D 在 545 接受、546 发 AR，
I hit 于 547..552 逐拍返回（每拍 1 笔，accepted 于前一拍）；
关闭版 D 在 575 接受、576 才发 AR，I hit 全部被推迟到 595 之后。
此为人工构造的场景差，不代表 CoreMark 收益。

## 6. 最小真实 CPU 集成（SoC）

顶层 `tb_inst_hit_overlap_soc` → `soc_top`：x32、posted 写、真实 `mycpu_sync` 五级流水、
真实 `icache`/`dcache`（DRM 原语）、片内 `inst_rom`/`data_ram`、`simple_mmio`、`uart_*`；
`RESET_PC=0x4000_0000` 指向 DDR 程序入口（非 Full Boot），Camera/PP/CNN 参数开启但接口常量为空闲，
`uart_rx=1'b1`。三个复位 epoch 在同一 job 内顺序执行（主程序 → Camera 非法取指 → PP 非法取指）。

- 编译：37 个模块，`Errors: 0, Warnings: 0`；`IPSpecCheck: 04030130` 2 条（两 cache 各一）。
- 主 epoch：`EPOCH1 pass edge=339`；桥侧 `i_acc=135`、`i_rsp=134`、
  `d_acc=10`、`d_rsp=10`、AR 12、AW 1、W 1、
  取消 I 1/D 0、I 行填充 12、写字节 4。
  D miss 窗口 8 个，其中 1 个窗口内有 I 响应被服务
  （窗口内最多 1 笔）。
- 响应缓冲只消费一次：单入口缓冲 `fills == pops + discards + residual`（fills/pops/discards 由 `bufv` 与 `pop` 边沿序列重算），
  实测 pops=9、drops=0；退休流 63 条由独立 RV32I 解释参考逐条核
  PC/inst/rf_we/rd/wdata/next PC，全部一致，参考停止后只剩 STOP_PC 自环，无重复退休。
- 错误路径：taken branch（`0x34`）与 `jal`（`0x110`）分别留下顺序候选 `0x38`、`0x114`，
  两者都在 I 通道被真实接受；`0x38` 的指令字 `0x0460A023`（`sw x6,0x40(x1)`）确实出现在 I 响应通道上，
  却从未进入响应缓冲也未退休 —— 旧响应被冲刷丢弃。错误路径 store 无请求接受、无 AW/写数据、无退休，
  对应 DDR 行 `0x1140` 与初始镜像逐字节一致。错误路径指令集 `40000038`、`4000003c`、`40000040`、`40000044`、`40000048`、`40000114` 无一条退休。
- 非法取指：`EPOCH2 camera trap cause=1 tval=41000000`、`EPOCH3 pp trap cause=1 tval=42000000`，
  精确 `mcause=1`（instruction access fault）与 `mtval`=目标 PC；两个 epoch 均无指向目标窗口的 DDR 取指 AR
  （各 epoch 只有 1 笔 AR，指向程序入口），两条 setup 指令退休与参考一致。
  外层权限检查未因桥 `rsp_error` 恒 0 而省略。
- 内存：时序序参考与程序序参考逐 beat 全等，且与模型 `soc.mem.log` 全 8256 beat 逐字节一致。
- 周期只记录（407 边沿 / 4070 ns），未套 032 的 617/415，也未要求真实 CPU 达到人工桥场景的提速比例。

## 7. checker 合成负例自检（不计 HDL 覆盖）

`selftest.py` 先把运行副本的真实桥轨迹重排为规范化单行记录（对照用例仍必须 PASS），
再逐项植入故障并要求 checker 拒收，9/9 全部拒收：

```
SELFTEST control: PASS the normalised trace is still accepted
SELFTEST duplicate_response       PASS  I miss response edge 19 != R+1 (warm_i1_fill r=None)
    planted: a response was delivered twice
SELFTEST missing_response         PASS  I miss response edge 12 != R+1 (warm_i0_fill_lane0 r=10)
    planted: an instruction response was lost
SELFTEST cross_source_rid         PASS  R id 1 does not match owner I at edge 10
    planted: the response id was swapped between the two owners
SELFTEST wrong_store_lane         PASS  W data/strobe differ from the accepted AW at edge 271
    planted: the store byte strobe shifted inside the beat
SELFTEST parked_miss_readdressed  PASS  AR 00000240 matches 0 pending misses at edge 34
    planted: the parked miss was re-addressed
SELFTEST second_physical_read     PASS  second physical read in flight at edge 7
    planted: the same line was read twice
SELFTEST read_before_write_drain  PASS  AR asserted while the posted write is draining at edge 269
    planted: an instruction read started before the store drained
SELFTEST wrong_read_beat          PASS  R beat mismatch for warm_i0_fill_lane0 at edge 10 (line 00000000, bytes [1]: got ['81'] want ['7e'])
    planted: the read beat did not match the reference memory
SELFTEST response_across_reset    PASS  I response without outstanding request at edge 4
    planted: a response outlived the reset that cancelled it
SELFTEST: PASS 9 of 9 planted faults were rejected
```

## 8. 首败与偏差记录

- **第 1 次 `--run` 调用（2026-10-17T18:18:50Z）在第一个 job 即停止，未执行任何 HDL 作业。**
  原因是我方 runner 的判定缺陷：`vlib` 只创建库、不打印 `Errors: 0, Warnings: 0` 汇总行，
  却被按 `vlog` 规则判定，`vlib_work`（exit=0，0.17 s）被判 FAIL，状态记为 `STOPPED_FIRST_FAILURE`。
  该次尝试的完整目录与 `run_meta.json` 原样保留在
  `sim/cpu_inst_hit_overlap/aborted_run_20261017_a/`（未删除、未被后续运行覆盖），其封存清单 SHA 为
  `f030bb85f1deb55684d04e9baacafe266d0094df40e1032fe36150bf712ad8b1`。
- 处置：把 `vlib` 改为按 native exit + 无 `** Error/** Fatal` 判定（`vlog`/`vsim` 规则不变），
  并用**已有**控制台日志离线校验判定逻辑（5 个真实日志 + 11 个植入用例，全部符合预期）后才重新封存执行。
  该修复只动 runner 自身的判定函数，未改 RTL/TB/模型/参考/判据/超时/seed/tag；
  中止的那次没有产生任何 HDL 证据，因此不存在"试跑到成功再挑一次"的情形。
- 正式运行 `2026-10-17T18:21:26Z` → `2026-10-17T18:21:38Z`，11 个 job 全部 PASS，无重试、无换 tag、无延长超时。
- 与旧快照的差异：PDS 实现使 `RISCV.pds` 元数据变化（`--check-inputs` 记为 metadata-only），
  不影响被测 RTL 配置，按执行书只记录。

## 9. 保护证据与 Git

- Git HEAD 前后一致：`4ee48abbe75f8a6609e961ef7858568be1ed6f5a`；`git status --porcelain` 与 `git diff` 前后 SHA 一致（`run_meta.json` 的 `git.before/after`）。
- 93 个只读准备/历史文件（`preparation_20261017_a/`、`preparation_20261017_b/`）前后 SHA 逐文件一致，0 处不符。
- 桥 RTL 前后 SHA 均为 `7ab9d34c...52d933`。
- 未执行 `git commit/push`。

## 10. 未覆盖 / NOT_RUN

- PDS 综合、实现、时序（本轮未跑，不填造 WNS/TNS）；未把静态多配置展开当功能 PASS。
- 物理 DDR/PHY/训练、串口、实板比较：NOT_RUN。
- Loader Full Boot、ISA 抽测、CoreMark、相机采帧、CNN 推理、历史 032 全套：NOT_RUN（按执行书范围）。
- 历史 032 与 CAM2/CNN 的 PASS 未移用。
- 本组 DDR 为带独立背压/延迟的 Pango 用户口模型，只证明该模型下的功能与协议，不代表真实 PHY 或全部应用兼容性。
- SoC 作业中"并行 I 服务"落在 8 个 D miss 窗口中的 1 个：
  最小程序冷启动后 I 缓存很快吸收后续取指，桥级 I 流量以冷填充为主；9 类并发场景的强证据由桥定向组承担。
- 两版周期差由两份独立 checker 输出重算并在本报告列出（`on`/`off` 是同一 TB 的两次独立 job），
  未在单次 checker 进程内做跨版本断言。

## 11. 运行目录

完整证据：`sim/cpu_inst_hit_overlap/build/ds_inst_hit_overlap_20261017_a/`

- 轨迹：`bridge_on.edges.log` / `bridge_on.tok.log` / `bridge_on.mem.log`、
  `bridge_off.edges.log` / `bridge_off.tok.log` / `bridge_off.mem.log`、`soc.edges.log` / `soc.mem.log`
  （每拍 I/D valid/ready/addr/size/write/wdata/strobe、响应 data/error、AR/AW/W/R/ID/地址/数据/背压、
  reset/init、场景/epoch/token，CPU 取指接受/响应/缓冲消费或丢弃/退休；PRE 与 POST 两相并标 phase）
- 编译与仿真控制台、ModelSim transcript：`logs/`
- checker 判定与账目：`logs/check_bridge_on.console.txt`、`logs/check_bridge_off.console.txt`、`logs/check_soc.console.txt`
- 运行记录：`run_meta.json`（argv/cwd/开始时间/pid/native exit/耗时/超时/cleanup/git before-after/保护哈希）
- 封存清单与工具身份：`manifest.json`、`tools.json`；运行副本源码：`src/`
- 中止的第 1 次调用：`sim/cpu_inst_hit_overlap/aborted_run_20261017_a/`
