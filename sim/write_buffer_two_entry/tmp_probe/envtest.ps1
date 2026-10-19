"start"
foreach ($dup in @('https_proxy', 'http_proxy', 'all_proxy', 'no_proxy')) {
    [Environment]::SetEnvironmentVariable($dup, $null, 'Process')
}
"removed"
$p = Start-Process -FilePath 'D:\modelsim\win64pe\vlib.exe' -ArgumentList 'work' -WorkingDirectory 'D:\riscv\RISCV\sim\write_buffer_two_entry\tmp_probe\chk' -WindowStyle Hidden -PassThru -RedirectStandardOutput 'D:\riscv\RISCV\sim\write_buffer_two_entry\tmp_probe\chk\vlib_sp.txt' -RedirectStandardError 'D:\riscv\RISCV\sim\write_buffer_two_entry\tmp_probe\chk\vlib_sp.err'
$null = $p.WaitForExit(30000)
"exit=$($p.ExitCode)"
