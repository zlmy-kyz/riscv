param(
    [string]$Port = 'COM9',
    [string]$LogDirectory = 'sim/cpu_branch_turnover/board/coremark_i64_d64_zmmul_bturn_300_01',
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$branchResumeTool = Join-Path $PSScriptRoot 'run_branch_loaduse_resume_measurement.py'
if (Test-Path -LiteralPath $LogDirectory) { throw "Preserve existing log directory: $LogDirectory" }
foreach ($branchResumeApp in @('performance_300','validation_300')) {
    $branchResumeArgs = @('-B',$branchResumeTool,'--application',$branchResumeApp,'--port',$Port,
        '--log',(Join-Path $LogDirectory "$branchResumeApp.json"))
    if ($PlanOnly) { $branchResumeArgs += '--plan-only' }
    & 'C:/python/python.exe' @branchResumeArgs
    if ($LASTEXITCODE -ne 0) { throw "$branchResumeApp failed; stop and preserve logs." }
}
if ($PlanOnly) { Write-Host "Branch resume offline plans prepared: $LogDirectory" }
else { Write-Host "Branch resume P300/V300 completed: $LogDirectory" }
