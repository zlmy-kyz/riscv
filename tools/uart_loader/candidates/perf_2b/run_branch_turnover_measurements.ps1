param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/cpu_branch_turnover/board/coremark_i64_d64_zmmul_bturn_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$branchTurnoverTool = Join-Path $PSScriptRoot 'run_branch_turnover_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($branchTurnoverApp in @('performance_300','validation_300')) {
    $branchTurnoverArgs = @('-B',$branchTurnoverTool,'--application',$branchTurnoverApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$branchTurnoverApp.json"))
    if ($PlanOnly) { $branchTurnoverArgs += '--plan-only' }
    & 'C:/python/python.exe' @branchTurnoverArgs
    if ($LASTEXITCODE -ne 0) { throw "$branchTurnoverApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Branch-turnover offline plans prepared: $LogDirectory" }
else { Write-Host "Branch-turnover P300/V300 completed: $LogDirectory" }
