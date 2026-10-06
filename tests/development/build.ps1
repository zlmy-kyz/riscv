$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$toolBin = Join-Path $projectRoot 'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
$buildDir = Join-Path $PSScriptRoot 'build'
$gcc = Join-Path $toolBin 'riscv-none-elf-gcc.exe'
if (-not (Test-Path -LiteralPath $gcc)) {
    throw "Compiler not found: $gcc"
}
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null

function Invoke-Tool {
    param([string]$Name, [string[]]$ToolArgs)
    $output = & (Join-Path $toolBin $Name) @ToolArgs 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed (exit $LASTEXITCODE):`n$($output -join [Environment]::NewLine)"
    }
    $output
}

$elf = Join-Path $buildDir 'main.elf'
$map = Join-Path $buildDir 'main.map'
$flags = @(
    '-march=rv32i', '-mabi=ilp32', '-O2', '-g',
    '-Wall', '-Wextra', '-ffreestanding', '-fno-builtin',
    '-fno-pic', '-fno-pie', '-msmall-data-limit=0',
    '-nostdlib', '-nostartfiles', '-Wl,--no-relax', '-Wl,--build-id=none',
    (Join-Path $PSScriptRoot 'startup.S'),
    (Join-Path $PSScriptRoot 'main.c'),
    (Join-Path $PSScriptRoot 'uart_printf.c'),
    '-T', (Join-Path $PSScriptRoot 'linker.ld'),
    "-Wl,-Map=$map", '-o', $elf, '-lgcc'
)
Invoke-Tool 'riscv-none-elf-gcc.exe' $flags |
    Tee-Object -FilePath (Join-Path $buildDir 'compile.log')
Invoke-Tool 'riscv-none-elf-readelf.exe' @('-h', '-A', '-l', $elf) |
    Set-Content -Encoding ascii (Join-Path $buildDir 'main.readelf.txt')
Invoke-Tool 'riscv-none-elf-objdump.exe' @('-d', '-S', $elf) |
    Set-Content -Encoding ascii (Join-Path $buildDir 'main.dis')
Invoke-Tool 'riscv-none-elf-objcopy.exe' @('-O', 'binary', $elf, (Join-Path $buildDir 'main.bin'))
Invoke-Tool 'riscv-none-elf-size.exe' @($elf) |
    Tee-Object -FilePath (Join-Path $buildDir 'size.txt')
Write-Host "Built: $elf"

# Independent RAM candidate; the user selects/regenerates the main storage IP.
$pythonExe = 'C:/python/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    $pythonExe = (Get-Command python -ErrorAction Stop).Source
}
$datDir = $buildDir
& $pythonExe (Join-Path $PSScriptRoot 'bin_to_dat.py') `
    (Join-Path $buildDir 'main.bin') $datDir
if ($LASTEXITCODE -ne 0) { throw 'BIN to DAT conversion failed' }
Write-Host "RAM candidate: $(Join-Path $datDir 'main.dat')"
