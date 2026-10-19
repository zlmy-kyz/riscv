param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/data_bus_turnover/board/coremark_i64_d64_zmmul_dturn_registered_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$registeredLookupTool = Join-Path $PSScriptRoot 'run_data_bus_registered_lookup_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($registeredLookupApp in @('performance_300','validation_300')) {
    $registeredLookupArgs = @('-B',$registeredLookupTool,'--application',$registeredLookupApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$registeredLookupApp.json"))
    if ($PlanOnly) { $registeredLookupArgs += '--plan-only' }
    & 'C:/python/python.exe' @registeredLookupArgs
    if ($LASTEXITCODE -ne 0) { throw "$registeredLookupApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Task032 registered lookup offline plans prepared: $LogDirectory" }
else { Write-Host "Task032 registered lookup P300/V300 completed: $LogDirectory" }
