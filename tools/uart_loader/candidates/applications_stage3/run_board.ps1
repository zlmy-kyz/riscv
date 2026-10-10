param([string]$LogDirectory = 'D:/riscv/RISCV/sim/uart_loader/board/applications_stage3_first')
$ErrorActionPreference = 'Stop'
$python = 'C:/python/python.exe'
$root = 'D:/riscv/RISCV'
$tool = "$root/tools/uart_loader/candidates/applications_stage3/upload.py"
$names = @('second','performance_1','validation_1','performance_60','validation_60')
if (!(Test-Path -LiteralPath "$root/sim/uart_loader/build/applications_stage3/deployment_gate.json")) { throw 'Simulation deployment gate is missing.' }
foreach ($name in $names) {
    if (Test-Path -LiteralPath (Join-Path $LogDirectory "$name.json")) { throw "Preserve existing log: $name.json. Choose a new -LogDirectory." }
}
Write-Host 'Keep the successful VERIFY/RUN/Hello FPGA bitstream. Close the serial terminal.'
Write-Host 'Five downloads use COM11 115200 8N1. No FPGA rebuild or programming is performed.'
foreach ($name in $names) {
    Read-Host "[$name] Press KEY0, release, wait for DDR initialization, then press Enter" | Out-Null
    $parameters = @($tool,'--application',$name,'--port','COM11','--log',(Join-Path $LogDirectory "$name.json"))
    if ($name.EndsWith('_60')) {
        $mode = $name.Substring(0,$name.Length-3)
        $parameters += @('--crc-log',(Join-Path $LogDirectory "${mode}_1.json"))
    }
    & $python @parameters
    if ($LASTEXITCODE -ne 0) { throw "Stopped at $name. Preserve the failure log; no retry or RUN repetition." }
}
& $python "$root/sim/uart_loader/applications_stage3/check_all.py" --directory $LogDirectory --output (Join-Path $LogDirectory 'board_result.json')
if ($LASTEXITCODE -ne 0) { throw 'Independent board audit failed; preserve all raw logs.' }
Write-Host "All requested board checks PASS. Logs: $LogDirectory"
