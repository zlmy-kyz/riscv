param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/write_buffer_turnover/board/coremark_i64_d64_zmmul_wturn_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$turnoverClosureTool = Join-Path $PSScriptRoot 'run_write_buffer_turnover_irq_closure_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($turnoverClosureApp in @('performance_300','validation_300')) {
    $turnoverClosureArgs = @('-B',$turnoverClosureTool,'--application',$turnoverClosureApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$turnoverClosureApp.json"))
    if ($PlanOnly) { $turnoverClosureArgs += '--plan-only' }
    & 'C:/python/python.exe' @turnoverClosureArgs
    if ($LASTEXITCODE -ne 0) { throw "$turnoverClosureApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Task031 closure offline plans prepared: $LogDirectory" }
else { Write-Host "Task031 closure P300/V300 completed: $LogDirectory" }
