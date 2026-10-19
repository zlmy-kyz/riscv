param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/cpu_request_presample/board/task036_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$task036Tool = Join-Path $PSScriptRoot 'run_task036_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($task036App in @('performance_300', 'validation_300')) {
    $task036Args = @('-B', $task036Tool, '--application', $task036App, '--port', $Port,
        '--log', (Join-Path $LogDirectory "$task036App.json"))
    if ($PlanOnly) { $task036Args += '--plan-only' }
    & 'C:/python/python.exe' @task036Args
    if ($LASTEXITCODE -ne 0) { throw "$task036App failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Task036 offline plans prepared: $LogDirectory" }
else { Write-Host "Task036 fixed P300/V300 board trials completed: $LogDirectory" }
