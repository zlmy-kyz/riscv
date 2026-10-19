param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/data_bus_turnover/board/coremark_i64_d64_zmmul_dturn_tagfix_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$tagLookupRepairTool = Join-Path $PSScriptRoot 'run_data_bus_tag_lookup_repair_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($tagLookupRepairApp in @('performance_300','validation_300')) {
    $tagLookupRepairArgs = @('-B',$tagLookupRepairTool,'--application',$tagLookupRepairApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$tagLookupRepairApp.json"))
    if ($PlanOnly) { $tagLookupRepairArgs += '--plan-only' }
    & 'C:/python/python.exe' @tagLookupRepairArgs
    if ($LASTEXITCODE -ne 0) { throw "$tagLookupRepairApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Task032 tag lookup repair offline plans prepared: $LogDirectory" }
else { Write-Host "Task032 tag lookup repair P300/V300 completed: $LogDirectory" }
