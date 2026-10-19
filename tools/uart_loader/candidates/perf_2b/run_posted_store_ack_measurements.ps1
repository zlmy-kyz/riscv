param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/cpu_store_ack/board/coremark_store_ack_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$storeAckTool = Join-Path $PSScriptRoot 'run_posted_store_ack_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($storeAckApp in @('performance_300', 'validation_300')) {
    $storeAckArgs = @('-B', $storeAckTool, '--application', $storeAckApp, '--port', $Port,
        '--log', (Join-Path $LogDirectory "$storeAckApp.json"))
    if ($PlanOnly) { $storeAckArgs += '--plan-only' }
    & 'C:/python/python.exe' @storeAckArgs
    if ($LASTEXITCODE -ne 0) { throw "$storeAckApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Task034 offline plans prepared: $LogDirectory" }
else { Write-Host "Task034 direct board P300/V300 trial completed: $LogDirectory" }
