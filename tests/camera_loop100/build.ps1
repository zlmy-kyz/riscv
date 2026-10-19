param([string]$Tag = 'camera_loop100_20261015_a')
$ErrorActionPreference = 'Stop'
& python (Join-Path $PSScriptRoot 'build.py') --tag $Tag
if ($LASTEXITCODE -ne 0) { throw 'Loop100 build failed; preserve this directory and use a new tag.' }
