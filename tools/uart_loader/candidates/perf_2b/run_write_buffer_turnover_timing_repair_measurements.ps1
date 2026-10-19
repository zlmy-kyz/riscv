param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/write_buffer_turnover/board/coremark_i64_d64_zmmul_wturn_timing_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$timingRepairTool = Join-Path $PSScriptRoot 'run_write_buffer_turnover_timing_repair_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($timingRepairApp in @('performance_300','validation_300')) {
    $timingRepairArgs = @('-B',$timingRepairTool,'--application',$timingRepairApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$timingRepairApp.json"))
    if ($PlanOnly) { $timingRepairArgs += '--plan-only' }
    & 'C:/python/python.exe' @timingRepairArgs
    if ($LASTEXITCODE -ne 0) { throw "$timingRepairApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Task031 timing repair offline plans prepared: $LogDirectory" }
else { Write-Host "Task031 timing repair P300/V300 completed: $LogDirectory" }
