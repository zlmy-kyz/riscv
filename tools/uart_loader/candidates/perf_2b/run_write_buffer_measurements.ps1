param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/mini_board_migration/board/coremark_i64_d64_zmmul_wbuf_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$writeBufferTool = Join-Path $PSScriptRoot 'run_write_buffer_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($writeBufferApp in @('performance_300','validation_300')) {
    $writeBufferArgs = @('-B',$writeBufferTool,'--application',$writeBufferApp,'--port',$Port,
                        '--log',(Join-Path $LogDirectory "$writeBufferApp.json"))
    if ($PlanOnly) { $writeBufferArgs += '--plan-only' }
    & 'C:/python/python.exe' @writeBufferArgs
    if ($LASTEXITCODE -ne 0) { throw "$writeBufferApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Write buffer P300/V300 offline plans prepared: $LogDirectory" }
else { Write-Host "Write buffer P300/V300 completed: $LogDirectory" }
