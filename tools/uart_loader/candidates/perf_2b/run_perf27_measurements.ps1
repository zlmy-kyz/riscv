param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/cpu_cache_perf/board/perf27_fixed_300_01',
    [string]$BuildTag = 'measure_perf27_fixed_20261018_a',
    [int]$CoreClockHz = 93750000,
    [switch]$PlanOnly,
    [ValidateSet('key0', 'jtag')]
    [string]$ResetMethod = 'key0'
)
$ErrorActionPreference = 'Stop'
$perf27Tool = Join-Path $PSScriptRoot 'run_perf27_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) {
    throw "Log directory already exists; preserve original logs: $LogDirectory"
}
foreach ($perf27App in @('performance_300', 'validation_300')) {
    $perf27Args = @('-B', $perf27Tool, '--application', $perf27App,
        '--port', $Port, '--log', (Join-Path $LogDirectory "$perf27App.json"),
        '--build-tag', $BuildTag, '--core-clock-hz', "$CoreClockHz",
        '--reset-method', $ResetMethod)
    if ($PlanOnly) { $perf27Args += '--plan-only' }
    & 'C:/python/python.exe' @perf27Args
    if ($LASTEXITCODE -ne 0) { throw "$perf27App failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "PERF27 offline plans completed: $LogDirectory" }
else { Write-Host "PERF27 P300/V300 application trials completed: $LogDirectory" }
