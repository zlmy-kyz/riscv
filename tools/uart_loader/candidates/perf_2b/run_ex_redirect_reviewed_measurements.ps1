param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/cpu_ex_redirect/board/ex_redirect_reviewed_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$reviewedExTool = Join-Path $PSScriptRoot 'run_ex_redirect_reviewed_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing logs: $LogDirectory" }
foreach ($reviewedExApp in @('performance_300', 'validation_300')) {
    $reviewedExArgs = @('-B', $reviewedExTool, '--application', $reviewedExApp, '--port', $Port,
        '--log', (Join-Path $LogDirectory "$reviewedExApp.json"))
    if ($PlanOnly) { $reviewedExArgs += '--plan-only' }
    & 'C:/python/python.exe' @reviewedExArgs
    if ($LASTEXITCODE -ne 0) { throw "$reviewedExApp failed; stop and preserve original logs." }
}
if ($PlanOnly) { Write-Host "Reviewed EX offline plans prepared: $LogDirectory" }
else { Write-Host "Reviewed EX fixed P300/V300 board trials completed: $LogDirectory" }
