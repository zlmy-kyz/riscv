param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/mini_board_migration/board/coremark_i64_d64_zmmul_sfwd_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$storeForwardTool = Join-Path $PSScriptRoot 'run_store_forward_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($storeForwardApp in @('performance_300','validation_300')) {
    $storeForwardArgs = @('-B',$storeForwardTool,'--application',$storeForwardApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$storeForwardApp.json"))
    if ($PlanOnly) { $storeForwardArgs += '--plan-only' }
    & 'C:/python/python.exe' @storeForwardArgs
    if ($LASTEXITCODE -ne 0) { throw "$storeForwardApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Store-forward offline plans prepared: $LogDirectory" }
else { Write-Host "Store-forward P300/V300 completed: $LogDirectory" }
