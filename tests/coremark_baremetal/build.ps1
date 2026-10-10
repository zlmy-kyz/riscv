param(
    [ValidateSet('performance','validation')][string]$Mode = 'performance',
    [ValidateRange(1,2147483647)][int]$Iterations = 1,
    [ValidateSet('O2','Os')][string]$Optimization = 'Os',
    [string]$OutputDirectory = ''
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$toolBin = Join-Path $projectRoot 'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
$buildDir = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $PSScriptRoot "build/$Mode" }
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
function Invoke-Tool {
    param([string]$Name, [string[]]$ToolArgs)
    $output = & (Join-Path $toolBin $Name) @ToolArgs 2>&1
    if ($LASTEXITCODE -ne 0) { throw "$Name failed: $($output -join [Environment]::NewLine)" }
    $output
}
$elf = Join-Path $buildDir 'main.elf'
$map = Join-Path $buildDir 'main.map'
$modeFlag = if ($Mode -eq 'performance') { '-DPERFORMANCE_RUN=1' } else { '-DVALIDATION_RUN=1' }
$flags = @('-march=rv32i','-mabi=ilp32',"-$Optimization",'-g','-Wall','-Wextra',
    '-ffreestanding','-fno-builtin','-fno-pic','-fno-pie','-msmall-data-limit=0',
    '-ffunction-sections','-fdata-sections','-fstack-usage',
    '-nostdlib','-nostartfiles','-Wl,--no-relax','-Wl,--build-id=none','-Wl,--gc-sections',
    '-DTOTAL_DATA_SIZE=2000','-DCLOCKS_PER_SEC=93750000',"-DITERATIONS=$Iterations",$modeFlag,
    "-DFLAGS_STR=`"-$Optimization -march=rv32i -mabi=ilp32; no LTO`"",
    '-I',$PSScriptRoot,'-I',(Join-Path $projectRoot 'coremark-main'),
    (Join-Path $PSScriptRoot 'startup.S'),(Join-Path $PSScriptRoot 'core_portme.c'),
    (Join-Path $PSScriptRoot 'ee_printf.c'))
foreach ($name in @('core_main','core_list_join','core_matrix','core_state','core_util')) {
    $flags += Join-Path $projectRoot "coremark-main/$name.c"
}
$flags += @('-T',(Join-Path $PSScriptRoot 'linker.ld'),"-Wl,-Map=$map",'-o',$elf,'-lgcc')
Push-Location $buildDir
try {
    Invoke-Tool 'riscv-none-elf-gcc.exe' $flags | Set-Content -Encoding ascii 'compile.log'
    Invoke-Tool 'riscv-none-elf-readelf.exe' @('-h','-A','-l','-S',$elf) | Set-Content -Encoding ascii 'main.readelf.txt'
    Invoke-Tool 'riscv-none-elf-objdump.exe' @('-d',$elf) | Set-Content -Encoding ascii 'main.dis'
    Invoke-Tool 'riscv-none-elf-nm.exe' @('-n',$elf) | Set-Content -Encoding ascii 'symbols.txt'
    Invoke-Tool 'riscv-none-elf-size.exe' @($elf) | Tee-Object -FilePath 'size.txt'
    Invoke-Tool 'riscv-none-elf-objcopy.exe' @('-O','binary',$elf,(Join-Path $buildDir 'main.bin'))
    & C:/python/python.exe (Join-Path $PSScriptRoot 'bin_to_dat.py') (Join-Path $buildDir 'main.bin') $buildDir
    if ($LASTEXITCODE -ne 0) { throw 'BIN to DAT conversion failed' }
    @{mode=$Mode;iterations=$Iterations;optimization=$Optimization;clock_hz=93750000;data_size=2000} | ConvertTo-Json | Set-Content -Encoding ascii 'config.json'
} finally { Pop-Location }
