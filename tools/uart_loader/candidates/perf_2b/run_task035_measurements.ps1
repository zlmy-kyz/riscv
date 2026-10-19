param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/cpu_dual_read/board/task035_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$task035Tool = Join-Path $PSScriptRoot 'run_task035_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($task035App in @('performance_300', 'validation_300')) {
    $task035Args = @('-B', $task035Tool, '--application', $task035App, '--port', $Port,
        '--log', (Join-Path $LogDirectory "$task035App.json"))
    if ($PlanOnly) { $task035Args += '--plan-only' }
    & 'C:/python/python.exe' @task035Args
    if ($LASTEXITCODE -ne 0) { throw "$task035App failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Task035 offline plans prepared: $LogDirectory" }
else { Write-Host "Task035 fixed P300/V300 board trials completed: $LogDirectory" }
