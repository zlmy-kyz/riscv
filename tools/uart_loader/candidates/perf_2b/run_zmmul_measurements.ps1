param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01/zmmul',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$zmmulRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$zmmulTool = Join-Path $PSScriptRoot 'run_zmmul_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) {
    throw "Log directory already exists. Preserve it and choose a new directory: $LogDirectory"
}
foreach ($zmmulApp in @('performance_120', 'validation_120')) {
    $zmmulArgs = @('-B', $zmmulTool, '--application', $zmmulApp, '--port', $Port,
                   '--log', (Join-Path $LogDirectory "$zmmulApp.json"))
    if ($PlanOnly) { $zmmulArgs += '--plan-only' }
    & 'C:/python/python.exe' @zmmulArgs
    if ($LASTEXITCODE -ne 0) {
        throw "$zmmulApp failed. Further tests stopped; preserve original logs."
    }
}
Write-Host "Zmmul fixed120 selected measurements completed: $LogDirectory"
