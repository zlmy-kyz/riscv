param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/cpu_branch_turnover/board/coremark_i64_d64_zmmul_bturn_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$branchIsaTool = Join-Path $PSScriptRoot 'run_branch_isa_port_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($branchIsaApp in @('performance_300','validation_300')) {
    $branchIsaArgs = @('-B',$branchIsaTool,'--application',$branchIsaApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$branchIsaApp.json"))
    if ($PlanOnly) { $branchIsaArgs += '--plan-only' }
    & 'C:/python/python.exe' @branchIsaArgs
    if ($LASTEXITCODE -ne 0) { throw "$branchIsaApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Branch ISA closure offline plans prepared: $LogDirectory" }
else { Write-Host "Branch ISA closure P300/V300 completed: $LogDirectory" }
