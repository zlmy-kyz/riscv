# =============================================================================
# run.ps1 -- 差分验证一键脚本
# -----------------------------------------------------------------------------
#   .\run.ps1 -Prog prog0_alu            # 汇编 + 出黄金轨迹 + 跑 RTL + 比终值
#   .\run.ps1 -Prog prog1_mem -Wave      # 额外导出 wave.vcd 便于看波形
#   .\run.ps1 -Prog prog1_mem -Dut <file># 换一份 CPU 源码（如修复版）再跑同一套黄金轨迹
#
# 每次运行都在 difftest\build\<程序名>\ 下自成一套，互不覆盖：
#   rom.hex ram.hex trace.txt itrace.txt rf_golden.txt mem_golden.txt prog.lst
#   out.vvp sim.log rf_dut.txt mem_dut.txt
# =============================================================================
param(
    [string]$Prog    = 'prog0_alu',
    [string]$Dut     = 'D:\riscv\RISCV\myriscv\mycpu_sync.v',
    [string]$Tag     = '',
    [switch]$Wave,
    [switch]$SkipGolden
)

# 注意：必须用 Continue。原生程序（iverilog/vvp）的 stderr 经管道会被
# PowerShell 包成 ErrorRecord，ErrorActionPreference=Stop 时会把一行普通的
# 编译告警直接当异常抛出。所以这里靠显式 throw + $LASTEXITCODE 判断成败。
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Proj  = Split-Path -Parent $Root
$Build = Join-Path $Root "build\$Prog$Tag"
$Iverilog = 'D:\iverilog\bin\iverilog.exe'
$Vvp      = 'D:\iverilog\bin\vvp.exe'

# 找 python：优先用 WorkBuddy 托管版本，其次 PATH 里的 python
$Py = "C:\Users\z'l'm'y'k\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if (-not (Test-Path $Py)) { $Py = 'python' }

New-Item -ItemType Directory -Force -Path $Build | Out-Null

# ---------------------------------------------------------------- 1) 黄金模型
Write-Host ""
Write-Host "=== [1/3] 黄金模型：汇编 + 指令级仿真 -> 黄金轨迹 ===" -ForegroundColor Cyan
$src = Join-Path $Root "prog\$Prog.S"
if (-not (Test-Path $src)) { throw "找不到测试程序 $src" }
if (-not $SkipGolden) {
    & $Py (Join-Path $Root 'golden\rvtool.py') build $src $Build 2>&1 | Tee-Object -FilePath (Join-Path $Build 'golden.log')
    if ($LASTEXITCODE -ne 0) { throw "黄金模型生成失败" }
}

# ---------------------------------------------------------------- 2) 编译
Write-Host ""
Write-Host "=== [2/3] 编译 RTL（DUT + 行为级存储器模型 + 比对测试台）===" -ForegroundColor Cyan

$srcs = @(
    $Dut,
    (Join-Path $Proj 'myriscv\soc_top.v'),
    (Join-Path $Proj 'myriscv\inst_bram_adapter.v'),
    (Join-Path $Proj 'myriscv\inst_bus_interconnect.v'),
    (Join-Path $Proj 'myriscv\data_bram_adapter.v'),
    (Join-Path $Proj 'myriscv\data_bus_interconnect.v'),
    (Join-Path $Proj 'myriscv\simple_mmio.v'),
    (Join-Path $Proj 'myriscv\regfile.v'),
    (Join-Path $Proj 'myriscv\alu.v'),
    (Join-Path $Proj 'myriscv\l_alu.v'),
    (Join-Path $Proj 'myriscv\br_alu.v'),
    (Join-Path $Proj 'myriscv\csr_file.v'),
    (Join-Path $Root 'model\inst_rom.v'),
    (Join-Path $Root 'model\data_ram.v'),
    (Join-Path $Root 'tb\tb_difftest.v')
)
foreach ($f in $srcs) { if (-not (Test-Path $f)) { throw "缺源文件：$f" } }

$vp = Join-Path $Build 'out.vvp'
$defs = @()
if ($Wave) { $defs += '-DWAVE' }

& $Iverilog -g2012 -Wall -I (Join-Path $Proj 'myriscv') @defs -o $vp @srcs 2>&1 |
    Tee-Object -FilePath (Join-Path $Build 'compile.log')
if ($LASTEXITCODE -ne 0) { throw "iverilog 编译失败，见 $Build\compile.log" }

# ---------------------------------------------------------------- 3) 仿真
Write-Host ""
Write-Host "=== [3/3] 差分仿真 ===" -ForegroundColor Cyan
Push-Location $Build
try {
    & $Vvp 'out.vvp' 2>&1 | Tee-Object -FilePath 'sim.log'
} finally {
    Pop-Location
}

# ---------------------------------------------------------------- 4) 终值比对
$verdict = ''
$simTxt = Get-Content (Join-Path $Build 'sim.log') -Raw -ErrorAction SilentlyContinue
if     ($simTxt -match 'RESULT: PASS') { $verdict = 'PASS' }
elseif ($simTxt -match 'RESULT: FAIL') { $verdict = 'FAIL' }

Write-Host ""
Write-Host "=== 寄存器堆 / 数据存储器 终值比对 ===" -ForegroundColor Cyan
if ($verdict -eq 'PASS') {
    & $Py (Join-Path $Root 'golden\rvtool.py') check $Build
    $rc = $LASTEXITCODE
} else {
    Write-Host "  轨迹比对未通过，跳过终值比对（终值此时必然也不一致）" -ForegroundColor Yellow
    $rc = 1
}

Write-Host ""
if ($verdict -eq 'PASS' -and $rc -eq 0) {
    Write-Host "########  差分验证 PASS：$Prog  ########" -ForegroundColor Green
    exit 0
} else {
    Write-Host "########  差分验证 FAIL：$Prog  （日志 $Build\sim.log）  ########" -ForegroundColor Red
    exit 1
}
