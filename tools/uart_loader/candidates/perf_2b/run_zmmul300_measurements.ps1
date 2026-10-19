param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/zmmul',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$zmmul300Tool = Join-Path $PSScriptRoot 'run_zmmul300_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) {
    throw "Log directory already exists. Preserve original logs: $LogDirectory"
}
foreach ($zmmul300App in @('performance_300', 'validation_300')) {
    $zmmul300Args = @('-B', $zmmul300Tool, '--application', $zmmul300App,
                     '--port', $Port, '--log', (Join-Path $LogDirectory "$zmmul300App.json"))
    if ($PlanOnly) { $zmmul300Args += '--plan-only' }
    & 'C:/python/python.exe' @zmmul300Args
    if ($LASTEXITCODE -ne 0) { throw "$zmmul300App failed. Stop and preserve logs." }
}
Write-Host "Zmmul300 performance/validation measurements completed: $LogDirectory"
