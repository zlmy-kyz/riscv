param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/mini_board_migration/board/coremark_i64_d64_zmmul_dread_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$dataReadOverlapTool = Join-Path $PSScriptRoot 'run_data_read_overlap_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($dataReadOverlapApp in @('performance_300','validation_300')) {
    $dataReadOverlapArgs = @('-B',$dataReadOverlapTool,'--application',$dataReadOverlapApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$dataReadOverlapApp.json"))
    if ($PlanOnly) { $dataReadOverlapArgs += '--plan-only' }
    & 'C:/python/python.exe' @dataReadOverlapArgs
    if ($LASTEXITCODE -ne 0) { throw "$dataReadOverlapApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "D-read overlap offline plans prepared: $LogDirectory" }
else { Write-Host "D-read overlap P300/V300 completed: $LogDirectory" }
