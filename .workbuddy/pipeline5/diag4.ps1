$dir = "D:\riscv\RISCV\.workbuddy\pipeline5"
$iv  = "D:\iverilog\bin\iverilog.exe"
$vvp = "D:\iverilog\bin\vvp.exe"
$srcs = @(
  "$dir\tb_diag4.v",
  "D:\riscv\RISCV\myriscv\mycpu_sync.v",
  "D:\riscv\RISCV\myriscv\regfile.v",
  "D:\riscv\RISCV\myriscv\alu.v",
  "D:\riscv\RISCV\myriscv\l_alu.v",
  "D:\riscv\RISCV\myriscv\br_alu.v"
)
$log = ""
$log += (& $iv -g2012 -Wall -o "$dir\diag4.vvp" @srcs 2>&1 | Out-String)
if ($LASTEXITCODE -eq 0) {
    $log += (& $vvp "$dir\diag4.vvp" 2>&1 | Out-String)
}
Set-Content -Path "$dir\diag4.log" -Value $log -Encoding ASCII
Write-Output "done"
