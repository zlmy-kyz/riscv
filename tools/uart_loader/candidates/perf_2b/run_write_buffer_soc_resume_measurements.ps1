param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/mini_board_migration/board/coremark_i64_d64_zmmul_wbuf_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$writeBufferResumeTool = Join-Path $PSScriptRoot 'run_write_buffer_soc_resume_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($writeBufferResumeApp in @('performance_300','validation_300')) {
    $writeBufferResumeArgs = @('-B',$writeBufferResumeTool,'--application',$writeBufferResumeApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$writeBufferResumeApp.json"))
    if ($PlanOnly) { $writeBufferResumeArgs += '--plan-only' }
    & 'C:/python/python.exe' @writeBufferResumeArgs
    if ($LASTEXITCODE -ne 0) { throw "$writeBufferResumeApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Write buffer resume offline plans prepared: $LogDirectory" }
else { Write-Host "Write buffer P300/V300 completed: $LogDirectory" }
