param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/write_buffer_turnover/board/coremark_i64_d64_zmmul_wturn_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$turnoverResumeTool = Join-Path $PSScriptRoot 'run_write_buffer_turnover_init_resume_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($turnoverResumeApp in @('performance_300','validation_300')) {
    $turnoverResumeArgs = @('-B',$turnoverResumeTool,'--application',$turnoverResumeApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$turnoverResumeApp.json"))
    if ($PlanOnly) { $turnoverResumeArgs += '--plan-only' }
    & 'C:/python/python.exe' @turnoverResumeArgs
    if ($LASTEXITCODE -ne 0) { throw "$turnoverResumeApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Task031 resume offline plans prepared: $LogDirectory" }
else { Write-Host "Task031 resume P300/V300 completed: $LogDirectory" }
