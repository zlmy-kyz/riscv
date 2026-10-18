param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/cpu_ex_redirect/board/ex_redirect_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$exRedirectTool = Join-Path $PSScriptRoot 'run_ex_redirect_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) {
    throw "Log directory already exists. Preserve original logs: $LogDirectory"
}
foreach ($exRedirectApp in @('performance_300', 'validation_300')) {
    $exRedirectArgs = @('-B', $exRedirectTool, '--application', $exRedirectApp,
                        '--port', $Port, '--log', (Join-Path $LogDirectory "$exRedirectApp.json"))
    if ($PlanOnly) { $exRedirectArgs += '--plan-only' }
    & 'C:/python/python.exe' @exRedirectArgs
    if ($LASTEXITCODE -ne 0) { throw "$exRedirectApp failed. Stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "EX-redirect offline plans prepared: $LogDirectory" }
else { Write-Host "EX-redirect fixed P300/V300 board trials completed: $LogDirectory" }
