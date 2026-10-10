param([string]$OutputDirectory = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$toolBin = Join-Path $projectRoot 'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
$buildDir = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $PSScriptRoot 'build/ddr_fixed' }
if ($buildDir.TrimEnd('/','\') -in @((Join-Path $PSScriptRoot 'build'),(Join-Path $PSScriptRoot 'build/rx_fixed'))) {
    throw 'PING and rx_fixed contain board-verified images; use build/ddr_fixed or another isolated output.'
}
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
function Invoke-Tool {
    param([string]$Name, [string[]]$ToolArgs)
    $output = & (Join-Path $toolBin $Name) @ToolArgs 2>&1
    if ($LASTEXITCODE -ne 0) { throw "$Name failed: $($output -join [Environment]::NewLine)" }
    $output
}
$elf = Join-Path $buildDir 'loader.elf'
$flags = @('-march=rv32i','-mabi=ilp32','-Os','-g','-Wall','-Wextra','-Werror',
    '-ffreestanding','-fno-builtin','-fno-pic','-fno-pie','-msmall-data-limit=0',
    '-fstack-usage','-nostdlib','-nostartfiles','-Wl,--no-relax','-Wl,--build-id=none',
    '-Wl,--no-check-sections','-T',(Join-Path $PSScriptRoot 'linker.ld'),
    "-Wl,-Map=$buildDir/loader.map",'-o',$elf)
foreach ($name in @('startup.S','main.c','uart_loader.c','uart_io.c','crc32.c','ddr_test.c')) {
    $flags += Join-Path $PSScriptRoot $name
}
$flags += '-lgcc'
Push-Location $buildDir
try {
    Invoke-Tool 'riscv-none-elf-gcc.exe' $flags | Set-Content -Encoding ascii 'compile.log'
    Invoke-Tool 'riscv-none-elf-readelf.exe' @('-h','-A','-l','-S',$elf) | Set-Content -Encoding ascii 'loader.readelf.txt'
    Invoke-Tool 'riscv-none-elf-objdump.exe' @('-d',$elf) | Set-Content -Encoding ascii 'loader.dis'
    Invoke-Tool 'riscv-none-elf-nm.exe' @('-n',$elf) | Set-Content -Encoding ascii 'symbols.txt'
    Invoke-Tool 'riscv-none-elf-size.exe' @($elf) | Tee-Object -FilePath 'size.txt'
    & C:/python/python.exe (Join-Path $PSScriptRoot 'image_to_dat.py') $elf $buildDir
    if ($LASTEXITCODE -ne 0) { throw 'Loader Harvard image audit/extraction failed' }
} finally { Pop-Location }
