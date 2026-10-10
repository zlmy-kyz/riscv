# Build separate candidates; preserve the accepted single-iteration DATs.
param()
$ErrorActionPreference = 'Stop'
$performance = Join-Path $PSScriptRoot 'build/performance_60'
$validation = Join-Path $PSScriptRoot 'build/validation_60'
& (Join-Path $PSScriptRoot 'build.ps1') -Mode performance -Iterations 60 -OutputDirectory $performance
& (Join-Path $PSScriptRoot 'build.ps1') -Mode validation -Iterations 60 -OutputDirectory $validation
Write-Host 'Candidates built. Next run: C:/python/python.exe sim/coremark/run.py --iterations 60 --audit-only'
Write-Host 'Then Full Boot: C:/python/python.exe sim/coremark/run.py --iterations 60'
Write-Host 'Do not deploy a candidate until its Full Boot acceptance succeeds.'
