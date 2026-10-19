param([string]$Tag = 'camera_uart_20261015_a')
$ErrorActionPreference = 'Stop'
& python (Join-Path $PSScriptRoot 'build.py') --tag $Tag
if ($LASTEXITCODE -ne 0) { throw 'Camera UART application build failed; preserve the build directory.' }
