# CPU -> 数据互连 -> MMIO/RAM 端到端测试。
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Proj  = Split-Path -Parent $Root
$Build = Join-Path $Root 'build\mmio_e2e'
$Iverilog = 'D:\iverilog\bin\iverilog.exe'
$Vvp      = 'D:\iverilog\bin\vvp.exe'
$Py = "C:\Users\z'l'm'y'k\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if (-not (Test-Path $Py)) { $Py = 'python' }

New-Item -ItemType Directory -Force -Path $Build | Out-Null

& $Py (Join-Path $Root 'golden\rvtool.py') asm `
    (Join-Path $Root 'prog\mmio_test.S') $Build
if ($LASTEXITCODE -ne 0) { throw 'MMIO测试程序汇编失败' }

$srcs = @(
    (Join-Path $Proj 'myriscv\mycpu_sync.v'),
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
    (Join-Path $Root 'tb\tb_mmio_test.v')
)

$Out = Join-Path $Build 'mmio_e2e.vvp'
& $Iverilog -g2012 -Wall -s tb_mmio_test `
    -I (Join-Path $Proj 'myriscv') -o $Out @srcs 2>&1 |
    Tee-Object -FilePath (Join-Path $Build 'compile.log')
if ($LASTEXITCODE -ne 0) { throw 'MMIO端到端测试编译失败' }

Push-Location $Build
try {
    & $Vvp 'mmio_e2e.vvp' 2>&1 | Tee-Object -FilePath 'sim.log'
} finally {
    Pop-Location
}

$simText = Get-Content (Join-Path $Build 'sim.log') -Raw
if ($simText -match 'RESULT: PASS mmio_e2e') {
    Write-Host '########  MMIO端到端测试 PASS  ########' -ForegroundColor Green
    exit 0
}

Write-Host "########  MMIO端到端测试 FAIL（见 $Build\sim.log） ########" -ForegroundColor Red
exit 1
