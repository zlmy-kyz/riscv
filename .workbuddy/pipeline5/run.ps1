param(
    [string]$Test = "A"
)
$iv   = "D:\iverilog\bin\iverilog.exe"
$vvp  = "D:\iverilog\bin\vvp.exe"
$dir  = "D:\riscv\RISCV\.workbuddy\pipeline5"
$srcs = @(
  "$dir\tb_pipe5.v",
  "D:\riscv\RISCV\myriscv\mycpu_sync.v",
  "D:\riscv\RISCV\myriscv\regfile.v",
  "D:\riscv\RISCV\myriscv\alu.v",
  "D:\riscv\RISCV\myriscv\l_alu.v",
  "D:\riscv\RISCV\myriscv\br_alu.v"
)
$vvpfile = "$dir\tb_$Test.vvp"
$cargs = @("-g2012","-Wall","-DTEST_$Test","-DSIM_ASSERT","-o",$vvpfile) + $srcs
$log = ""
$log += "### compile TEST_$Test`n"
$log += (& $iv @cargs 2>&1 | Out-String)
$log += "EXIT_COMPILE=$LASTEXITCODE`n"
if ($LASTEXITCODE -eq 0) {
    $log += "### run`n"
    $log += (& $vvp $vvpfile 2>&1 | Out-String)
    $log += "EXIT_RUN=$LASTEXITCODE`n"
}
Set-Content -Path "$dir\run_$Test.log" -Value $log -Encoding ASCII
Write-Output "done $Test"
