param(
    [string]$Port = 'COM11',
    [string]$LogDirectory = '',
    [switch]$PlanOnly,
    [ValidateSet('hello', 'crc32', 'performance_1', 'validation_1', 'performance_60', 'validation_60', 'performance_120', 'validation_120')]
    [string[]]$Applications = @('performance_120', 'validation_120')
)
$ErrorActionPreference = 'Stop'
$measureRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$measureTool = Join-Path $PSScriptRoot 'run_measurement.py'
if (!$LogDirectory) {
    $measureStamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $LogDirectory = Join-Path $measureRoot "sim/inst_line_buffer/board/measure_$measureStamp"
}
if (Test-Path -LiteralPath $LogDirectory) {
    throw "Log directory already exists. Choose a new directory: $LogDirectory"
}
Write-Host "Log directory: $LogDirectory"
foreach ($measureApp in $Applications) {
    $measureArgs = @('-B', $measureTool, '--application', $measureApp, '--port', $Port,
                    '--log', (Join-Path $LogDirectory "$measureApp.json"))
    if ($PlanOnly) { $measureArgs += '--plan-only' }
    & 'C:/python/python.exe' @measureArgs
    if ($LASTEXITCODE -ne 0) {
        throw "$measureApp failed. Further tests stopped; original logs preserved."
    }
}
Write-Host "Selected tests completed: $LogDirectory"
