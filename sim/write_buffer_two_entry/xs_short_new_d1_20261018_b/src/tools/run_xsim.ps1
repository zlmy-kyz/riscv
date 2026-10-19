# Task043 bridge-level runner, Vivado xsim backend.
#
# Why this exists: ModelSim DE-64 10.6c cannot start on this machine any more.
# Its launcher announces the kernel RPC endpoint as an IPv6 literal and then
# fails to connect:
#
#   RPC_Init: TCL_ERROR: set rpc_port [split {::1:<port>} :]
#     -> couldn't open socket: invalid argument
#
# Measured without ModelSim: bind/listen ::1 OK, connect ::1 -> WinError 10013,
# connect 127.0.0.1 OK. That block survives with all three sandbox firewall rules
# disabled and it also happens in a separate elevated shell, so it is a machine
# level loopback policy, not a firewall rule, and not a problem of the RTL or the
# testbench.  xsim runs in-process and needs no loopback socket at all, so the
# same testbench and the same DUT are used here.
#
# One tag = one frozen run directory, never reused. Everything compiled is first
# copied into <run>/src/ with its work-tree relative path, hashed, then compiled
# from the copies, and re-hashed afterwards.
#
#   run_xsim.ps1 -Tag k2 -Top tb_wb2_key
#   run_xsim.ps1 -Tag s_new_d1 -Top tb_wb2_short_new_d1 -Short
#   run_xsim.ps1 -Tag s_old    -Top tb_wb2_short_old    -Short -Legacy
#
param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [Parameter(Mandatory = $true)][string]$Top,
    [switch]$Short,
    [switch]$Legacy,
    [string]$Root = 'D:\riscv\RISCV',
    [string]$Sim = 'D:\riscv\RISCV\sim\write_buffer_two_entry',
    [string]$XilinxBin = 'D:\Xilinx\Vivado\2019.2\bin',
    [string]$LegacyBridge = 'D:\riscv\RISCV\sim\write_buffer_two_entry\preparation_20261018_a\before\dual_sram_to_pango_ddr_bridge.v'
)

$ErrorActionPreference = 'Stop'
foreach ($dup in @('https_proxy', 'http_proxy', 'all_proxy', 'no_proxy')) {
    [Environment]::SetEnvironmentVariable($dup, $null, 'Process')
}

$run = Join-Path $Sim $Tag
if (Test-Path $run) { throw "run directory already exists, refusing to reuse: $run" }
$sealDir = Join-Path $run 'src'
New-Item -ItemType Directory -Path $run | Out-Null
New-Item -ItemType Directory -Path $sealDir | Out-Null

$pango = 'C:\pango\PDS_2022.2-SP6.4\arch\vendor\pango\verilog\simulation'
$ipdir = Join-Path $Root 'ipcore'
$bridgeSrc = if ($Legacy) { $LegacyBridge } else { Join-Path $Root 'myriscv\dual_sram_to_pango_ddr_bridge.v' }
if (-not (Test-Path $bridgeSrc)) { throw "missing bridge source: $bridgeSrc" }

$sources = @(
    @{ Rel = 'vendor\GTP_GRS.v'; Src = (Join-Path $pango 'GTP_GRS.v') },
    @{ Rel = 'vendor\GTP_DRM36K_E1.v'; Src = (Join-Path $pango 'GTP_DRM36K_E1.v') },
    @{ Rel = 'ipcore\icache\rtl\ipm2l_sdpram_v1_10_icache.v'; Src = (Join-Path $ipdir 'icache\rtl\ipm2l_sdpram_v1_10_icache.v') },
    @{ Rel = 'ipcore\icache\icache.v'; Src = (Join-Path $ipdir 'icache\icache.v') },
    @{ Rel = 'ipcore\dcache\rtl\ipm2l_sdpram_v1_10_dcache.v'; Src = (Join-Path $ipdir 'dcache\rtl\ipm2l_sdpram_v1_10_dcache.v') },
    @{ Rel = 'ipcore\dcache\dcache.v'; Src = (Join-Path $ipdir 'dcache\dcache.v') },
    @{ Rel = 'myriscv\dual_sram_to_pango_ddr_bridge.v'; Src = $bridgeSrc },
    @{ Rel = 'tb\tb_wb2_bridge.sv'; Src = (Join-Path $Sim 'tb_wb2_bridge.sv') },
    @{ Rel = 'tb\tb_wb2_variants.sv'; Src = (Join-Path $Sim 'tb_wb2_variants.sv') },
    @{ Rel = 'tools\check_wb2.py'; Src = (Join-Path $Sim 'check_wb2.py') },
    @{ Rel = 'tools\run_xsim.ps1'; Src = (Join-Path $Sim 'run_xsim.ps1') }
)
foreach ($s in $sources) { if (-not (Test-Path $s.Src)) { throw "missing source: $($s.Src)" } }
foreach ($s in $sources) {
    $dst = Join-Path $sealDir $s.Rel
    New-Item -ItemType Directory -Path (Split-Path $dst -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $s.Src -Destination $dst -Force
}

function Get-Identity {
    param([string]$Dir, [string[]]$Rels)
    $rows = foreach ($rel in $Rels) {
        $p = Join-Path $Dir $rel
        $h = (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLower()
        "$h  $((Get-Item -LiteralPath $p).Length)  $rel"
    }
    return $rows
}
$rels = $sources | ForEach-Object { $_.Rel }
$idBefore = Get-Identity -Dir $sealDir -Rels $rels
$idBefore | Set-Content -Path (Join-Path $run 'inputs_before.sha256') -Encoding ASCII

$xvlog = Join-Path $XilinxBin 'xvlog.bat'
$xelab = Join-Path $XilinxBin 'xelab.bat'
$xsim = Join-Path $XilinxBin 'xsim.bat'
foreach ($t in @($xvlog, $xelab, $xsim)) { if (-not (Test-Path $t)) { throw "missing tool: $t" } }
$py = 'C:\Users\z''l''m''y''k\.workbuddy\binaries\python\versions\3.13.12\python.exe'
if (-not (Test-Path $py)) { $py = (Get-Command python -ErrorAction Stop).Source }

# The checker takes the effective configuration from run_meta.json, so each
# wrapper must declare exactly the parameters it instantiates. An unknown top is
# a hard error: silently defaulting would check the trace against the wrong depth.
$topParams = @{
    'tb_wb2_key'                = [ordered]@{ Dq = 32; Posted = 1; Depth = 2; Turnover = 1; Forward = 1; Ruw = 1; Icache = 1; Dcache = 1; Camera = 0; Preproc = 0; Plane = 0 }
    'tb_wb2_short_new_d2'       = [ordered]@{ Dq = 32; Posted = 1; Depth = 2; Turnover = 1; Forward = 1; Ruw = 1; Icache = 1; Dcache = 1; Camera = 0; Preproc = 0; Plane = 1 }
    'tb_wb2_short_new_d1'       = [ordered]@{ Dq = 32; Posted = 1; Depth = 1; Turnover = 1; Forward = 1; Ruw = 1; Icache = 1; Dcache = 1; Camera = 0; Preproc = 0; Plane = 1 }
    'tb_wb2_short_old'          = [ordered]@{ Dq = 32; Posted = 1; Depth = 1; Turnover = 1; Forward = 1; Ruw = 1; Icache = 1; Dcache = 1; Camera = 0; Preproc = 0; Plane = 1 }
    'tb_wb2_compat_noposted'    = [ordered]@{ Dq = 32; Posted = 0; Depth = 2; Turnover = 1; Forward = 1; Ruw = 1; Icache = 1; Dcache = 1; Camera = 0; Preproc = 0; Plane = 1 }
    'tb_wb2_compat_noturnover'  = [ordered]@{ Dq = 32; Posted = 1; Depth = 2; Turnover = 0; Forward = 1; Ruw = 1; Icache = 1; Dcache = 1; Camera = 0; Preproc = 0; Plane = 1 }
    'tb_wb2_compat_no_forward'  = [ordered]@{ Dq = 32; Posted = 1; Depth = 2; Turnover = 1; Forward = 0; Ruw = 1; Icache = 1; Dcache = 1; Camera = 0; Preproc = 0; Plane = 1 }
    'tb_wb2_compat_linebuf_off' = [ordered]@{ Dq = 32; Posted = 1; Depth = 2; Turnover = 1; Forward = 1; Ruw = 1; Icache = 0; Dcache = 0; Camera = 0; Preproc = 0; Plane = 1 }
}
if (-not $topParams.ContainsKey($Top)) { throw "no parameter set declared for top '$Top' (add it to `$topParams)" }

$meta = [ordered]@{
    tag            = $Tag
    status         = 'RUNNING'
    backend        = 'xsim'
    started        = (Get-Date).ToString('s')
    root           = $Root
    sealed_src     = $sealDir
    top            = $Top
    short          = [bool]$Short
    legacy         = [bool]$Legacy
    bridge         = $bridgeSrc
    bridge_sha256  = (Get-FileHash -Algorithm SHA256 -LiteralPath $bridgeSrc).Hash.ToLower()
    params         = $topParams[$Top]
    tools          = [ordered]@{ xvlog = $xvlog; xelab = $xelab; xsim = $xsim; python = $py }
    commands       = @()
    exits          = [ordered]@{}
    timeline       = @()
    sim_result     = $null
    check_status   = 'NOT_RUN'
    identity_drift = 0
    error          = $null
    finished       = $null
    modelsim_note  = 'ModelSim 10.6c unavailable on this machine: machine-level block on IPv6 loopback prevents its kernel RPC ("RPC_Init ... ::1"). Same TB/DUT executed on Vivado xsim 2019.2.'
}
$metaPath = Join-Path $run 'run_meta.json'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
function Save-Meta {
    [System.IO.File]::WriteAllText($metaPath, ($meta | ConvertTo-Json -Depth 6), $utf8NoBom)
}
Save-Meta

$timeline = New-Object System.Collections.Generic.List[string]

function Step {
    param([string]$Name, [string]$Exe, [string[]]$ArgList, [string]$WorkDir)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $t0 = Get-Date
    Push-Location $WorkDir
    try {
        $out = & $Exe @ArgList 2>&1
        $code = $LASTEXITCODE
    } finally { Pop-Location; $ErrorActionPreference = $prev }
    $dt = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    $out | ForEach-Object { $_.ToString() } |
        Set-Content -Path (Join-Path $run ("log_{0}.txt" -f $Name)) -Encoding ASCII
    $script:timeline.Add(("{0} exit={1} {2}s :: {3} {4}" -f
            $Name, $code, $dt, (Split-Path $Exe -Leaf), ($ArgList -join ' ')))
    $script:meta.exits[$Name] = $code
    $script:meta.commands += ("{0} {1}" -f $Exe, ($ArgList -join ' '))
    return [pscustomobject]@{ Code = $code; Text = ($out | ForEach-Object { $_.ToString() }) }
}

$compiled = $rels | Where-Object { $_ -like '*.v' -or $_ -like '*.sv' } |
    ForEach-Object { Join-Path $sealDir $_ }

$vlogArgs = @('--sv')
if ($Legacy) { $vlogArgs += @('--define', 'LEGACY_BRIDGE') }
$vlogArgs += $compiled

try {
    "EFFECTIVE TOP: $Top  SHORT=$([bool]$Short) LEGACY=$([bool]$Legacy)"
    "BRIDGE: $bridgeSrc"
    "BRIDGE SHA256: $($meta.bridge_sha256)"

    $r = Step 'xvlog' $xvlog $vlogArgs $run
    if ($r.Code -ne 0) { throw "xvlog failed with exit $($r.Code) (see log_xvlog.txt)" }
    if (($r.Text -join "`n") -match '(?m)^ERROR:') { throw 'xvlog reported ERROR:' }

    $r = Step 'xelab' $xelab @($Top, '-s', 'snap', '-debug', 'off') $run
    if ($r.Code -ne 0) { throw "xelab failed with exit $($r.Code) (see log_xelab.txt)" }

    $r = Step 'xsim' $xsim @('snap', '-runall') $run
    if ($r.Code -ne 0) { throw "xsim failed with exit $($r.Code) (see log_xsim.txt)" }
    $simText = $r.Text -join "`n"
    $resLine = ($r.Text | Where-Object { $_ -match 'RESULT:' } | Select-Object -Last 1)
    $meta.sim_result = if ($resLine) { $resLine.Trim() } else { $null }
    if ($simText -match '(?m)^ERROR:') { throw 'xsim reported ERROR:' }
    if ($simText -match 'FATAL_ERROR|Fatal:') { throw 'xsim reported a fatal error' }
    if (-not $resLine) { throw 'no RESULT line in the simulation output' }
    if ($resLine -notmatch 'RESULT:\s+PASS') { throw "simulation did not report RESULT: PASS (got: $resLine)" }
    if ($resLine -match 'FAIL') { throw "simulation reported a FAIL: $resLine" }

    $checkArgs = @('-B', (Join-Path $sealDir 'tools\check_wb2.py'))
    if ($Short) { $checkArgs += '--short' }
    $checkArgs += $run
    $t0 = Get-Date
    Push-Location $Root
    try {
        $cout = & $py @checkArgs 2>&1
        $ccode = $LASTEXITCODE
    } finally { Pop-Location }
    $cout | ForEach-Object { $_.ToString() } |
        Set-Content -Path (Join-Path $run 'log_check.txt') -Encoding ASCII
    $timeline.Add(("check exit={0} {1}s :: check_wb2.py {2}" -f $ccode,
            [math]::Round(((Get-Date) - $t0).TotalSeconds, 1), ($checkArgs -join ' ')))
    $meta.exits['check'] = $ccode
    $meta.commands += ("{0} {1}" -f $py, ($checkArgs -join ' '))
    $checkName = if ($Short) { 'check_short.json' } else { 'check_key.json' }
    $checkPath = Join-Path $run $checkName
    $meta.check_status = if (Test-Path $checkPath) {
        (Get-Content -Raw -Path $checkPath | ConvertFrom-Json).status
    } else { 'MISSING' }
    if ($ccode -ne 0) { throw "checker rejected the trace (see log_check.txt / $checkPath)" }
    if ($meta.check_status -ne 'PASS') { throw "checker status is $($meta.check_status)" }

    $meta.status = 'PASS'
} catch {
    $meta.status = 'FAIL'
    $meta.error = $_.Exception.Message
    throw
} finally {
    $idAfter = Get-Identity -Dir $sealDir -Rels $rels
    $idAfter | Set-Content -Path (Join-Path $run 'inputs_after.sha256') -Encoding ASCII
    $drift = @(Compare-Object $idBefore $idAfter | ForEach-Object { $_.InputObject })
    $meta.identity_drift = $drift.Count
    $meta.timeline = $timeline
    $meta.finished = (Get-Date).ToString('s')
    if ($drift.Count -ne 0 -and $meta.status -eq 'PASS') {
        $meta.status = 'FAIL'
        $meta.error = "sealed inputs changed during the run: $($drift -join '; ')"
    }
    Save-Meta
}

"RESULT: $($meta.status) tag=$Tag top=$Top $($meta.sim_result)"
"check  : $($meta.check_status)"
$timeline | ForEach-Object { "  $_" }
