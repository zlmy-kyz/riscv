param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/cpu_inst_hit_overlap/board/coremark_i64_d64_zmmul_overlap_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$overlapTool = Join-Path $PSScriptRoot 'run_inst_hit_overlap_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($overlapApp in @('performance_300', 'validation_300')) {
    $overlapArgs = @('-B', $overlapTool, '--application', $overlapApp, '--port', $Port,
        '--log', (Join-Path $LogDirectory "$overlapApp.json"))
    if ($PlanOnly) { $overlapArgs += '--plan-only' }
    & 'C:/python/python.exe' @overlapArgs
    if ($LASTEXITCODE -ne 0) { throw "$overlapApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Task033 offline plans prepared: $LogDirectory" }
else { Write-Host "Task033 P300/V300 completed: $LogDirectory" }
