param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/write_buffer_turnover/board/coremark_i64_d64_zmmul_wturn_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$turnoverTool = Join-Path $PSScriptRoot 'run_write_buffer_turnover_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($turnoverApp in @('performance_300','validation_300')) {
    $turnoverArgs = @('-B',$turnoverTool,'--application',$turnoverApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$turnoverApp.json"))
    if ($PlanOnly) { $turnoverArgs += '--plan-only' }
    & 'C:/python/python.exe' @turnoverArgs
    if ($LASTEXITCODE -ne 0) { throw "$turnoverApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Task031 offline plans prepared: $LogDirectory" }
else { Write-Host "Task031 P300/V300 completed: $LogDirectory" }
