param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/mini_board_migration/board/coremark_i64_d64_zmmul_dwh_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$dataHitTool = Join-Path $PSScriptRoot 'run_data_write_hit_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($dataHitApp in @('performance_300','validation_300')) {
    $dataHitArgs = @('-B',$dataHitTool,'--application',$dataHitApp,'--port',$Port,
                    '--log',(Join-Path $LogDirectory "$dataHitApp.json"))
    if ($PlanOnly) { $dataHitArgs += '--plan-only' }
    & 'C:/python/python.exe' @dataHitArgs
    if ($LASTEXITCODE -ne 0) { throw "$dataHitApp failed; stop and preserve logs." }
}
Write-Host "Data write-hit P300/V300 measurements completed: $LogDirectory"
