param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/data_bus_turnover/board/coremark_i64_d64_zmmul_dturn_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$dataTurnoverTool = Join-Path $PSScriptRoot 'run_data_bus_turnover_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($dataTurnoverApp in @('performance_300','validation_300')) {
    $dataTurnoverArgs = @('-B',$dataTurnoverTool,'--application',$dataTurnoverApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$dataTurnoverApp.json"))
    if ($PlanOnly) { $dataTurnoverArgs += '--plan-only' }
    & 'C:/python/python.exe' @dataTurnoverArgs
    if ($LASTEXITCODE -ne 0) { throw "$dataTurnoverApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Task032 offline plans prepared: $LogDirectory" }
else { Write-Host "Task032 P300/V300 completed: $LogDirectory" }
