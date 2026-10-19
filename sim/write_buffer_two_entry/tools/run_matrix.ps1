# Sealed re-run of the bridge-level matrix on the xsim backend.
# One tag per configuration; every tag is a frozen directory that cannot be reused.
$ErrorActionPreference = 'Continue'
$sim = 'D:\riscv\RISCV\sim\write_buffer_two_entry'
Set-Location $sim

$jobs = @(
    @{ t = 'xs_key_20261018_c';              top = 'tb_wb2_key';                short = $false; leg = $false },
    @{ t = 'xs_short_new_d2_20261018_c';     top = 'tb_wb2_short_new_d2';       short = $true;  leg = $false },
    @{ t = 'xs_short_new_d1_20261018_c';     top = 'tb_wb2_short_new_d1';       short = $true;  leg = $false },
    @{ t = 'xs_short_old_20261018_c';        top = 'tb_wb2_short_old';          short = $true;  leg = $true  },
    @{ t = 'xs_compat_noposted_20261018_c';  top = 'tb_wb2_compat_noposted';    short = $true;  leg = $false },
    @{ t = 'xs_compat_noturnover_20261018_c';top = 'tb_wb2_compat_noturnover';  short = $true;  leg = $false },
    @{ t = 'xs_compat_no_forward_20261018_c';top = 'tb_wb2_compat_no_forward';  short = $true;  leg = $false },
    @{ t = 'xs_compat_linebuf_off_20261018_c';top = 'tb_wb2_compat_linebuf_off';short = $true;  leg = $false }
)

$lines = @()
foreach ($j in $jobs) {
    $a = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', '.\run_xsim.ps1', '-Tag', $j.t, '-Top', $j.top)
    if ($j.short) { $a += '-Short' }
    if ($j.leg) { $a += '-Legacy' }
    $o = & powershell @a 2>&1 | Out-String
    $status = if ($o -match 'RESULT: PASS') { 'PASS' } elseif ($o -match 'RESULT: FAIL') { 'FAIL' } else { 'ERROR' }
    $resLine = ($o -split "`n" | Where-Object { $_ -match 'RESULT:' } | Select-Object -Last 1)
    $chk = ($o -split "`n" | Where-Object { $_ -match 'check  :' } | Select-Object -Last 1)
    $line = "{0,-30} {1}  {2}  {3}" -f $j.t, $status, ($resLine -replace '\s+', ' '), ($chk -replace '\s+', ' ')
    $lines += $line
    Write-Output $line
}
$lines | Set-Content -Path (Join-Path $sim 'matrix_summary.txt') -Encoding ASCII
Write-Output 'DONE'
