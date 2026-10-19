# Task043 bridge-level and SoC-level runner, Vivado xsim backend.
#
# Why xsim: at the time this runner was created, ModelSim DE-64 10.6c could not
# start on this machine. Its launcher announced the kernel RPC endpoint as an
# IPv6 literal and then failed to connect:
#
#   RPC_Init: TCL_ERROR: set rpc_port [split {::1:<port>} :]
#     -> couldn't open socket: invalid argument
#
# Measured without ModelSim: bind/listen ::1 OK, connect ::1 -> WinError 10013,
# connect 127.0.0.1 OK. That block survived with all three sandbox firewall
# rules disabled and it also happened in a separate elevated shell, so it was a
# machine level loopback policy, not a firewall rule, and not a problem of the
# RTL or the testbench.  xsim runs in-process and needs no loopback socket at
# all, so the same testbench and the same DUT are used here.
# The operator later restored ModelSim -c mode (loopback OK, empty module twice
# to 1 ns, exit 0, 0 errors/warnings). That restoration is recorded as a fact
# only: Task043 补正02 keeps this round on xsim and on the sealed model so the
# whole evidence chain stays on one re-checkable backend. ModelSim re-computation
# belongs to a later, independent step.
#
# One tag = one frozen run directory, never reused. Everything compiled is first
# copied into <run>/src/ with its work-tree relative path, hashed, then compiled
# from the copies, and re-hashed afterwards.
#
#   run_xsim.ps1 -Tag k2 -Top tb_wb2_key
#   run_xsim.ps1 -Tag s_new_d1 -Top tb_wb2_short_new_d1 -Short
#   run_xsim.ps1 -Tag s_old    -Top tb_wb2_short_old    -Short -Legacy
#   run_xsim.ps1 -Tag soc_a    -Top tb_wb2_soc -Soc
#
param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [Parameter(Mandatory = $true)][string]$Top,
    [switch]$Short,
    [switch]$Legacy,
    [switch]$Soc,
    [ValidateSet('key', 'short', 'fair', 'edge', 'x16', 'noposted', 'ruw0', 'soc')]
    [string]$CheckMode = 'key',
    [string]$Root = 'D:\riscv\RISCV',
    [string]$Sim = 'D:\riscv\RISCV\sim\write_buffer_two_entry',
    [string]$XilinxBin = 'D:\Xilinx\Vivado\2019.2\bin',
    [string]$LegacyBridge = 'D:\riscv\RISCV\sim\write_buffer_two_entry\preparation_20261018_a\before\dual_sram_to_pango_ddr_bridge.v'
)

$ErrorActionPreference = 'Stop'
$mode = if ($Short) { 'short' } elseif ($Soc) { 'soc' } else { $CheckMode }
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

# The SoC fragment additionally needs the real CPU, both interconnects, the
# on-chip ROM/RAM IPs, the M-extension IP, UART/MMIO and the include file; the
# DDR user port stays the functional model. This list is the same set the
# Task033 SoC job used, so the composition is already proven on this machine.
if ($Soc) {
    $sources += @(
        @{ Rel = 'vendor\GTP_APM_E2.v'; Src = (Join-Path $pango 'GTP_APM_E2.v') },
        @{ Rel = 'ipcore\inst_rom\rtl\ipm2l_spram_v1_8_inst_rom.v'; Src = (Join-Path $ipdir 'inst_rom\rtl\ipm2l_spram_v1_8_inst_rom.v') },
        @{ Rel = 'ipcore\inst_rom\rtl\ipm2l_rom_v1_8_inst_rom.v'; Src = (Join-Path $ipdir 'inst_rom\rtl\ipm2l_rom_v1_8_inst_rom.v') },
        @{ Rel = 'ipcore\inst_rom\inst_rom.v'; Src = (Join-Path $ipdir 'inst_rom\inst_rom.v') },
        @{ Rel = 'ipcore\data_ram\rtl\ipm2l_spram_v1_8_data_ram.v'; Src = (Join-Path $ipdir 'data_ram\rtl\ipm2l_spram_v1_8_data_ram.v') },
        @{ Rel = 'ipcore\data_ram\data_ram.v'; Src = (Join-Path $ipdir 'data_ram\data_ram.v') },
        @{ Rel = 'ipcore\mul\rtl\ipm2l_apm_data_pipeline\ipm2l_apm_distributed_sdpram.v'; Src = (Join-Path $ipdir 'mul\rtl\ipm2l_apm_data_pipeline\ipm2l_apm_distributed_sdpram.v') },
        @{ Rel = 'ipcore\mul\rtl\ipm2l_apm_data_pipeline\ipm2l_apm_distributed_shiftregister.v'; Src = (Join-Path $ipdir 'mul\rtl\ipm2l_apm_data_pipeline\ipm2l_apm_distributed_shiftregister.v') },
        @{ Rel = 'ipcore\mul\rtl\ipm2l_apm_data_pipeline\ipm2l_apm_data_pipeline.v'; Src = (Join-Path $ipdir 'mul\rtl\ipm2l_apm_data_pipeline\ipm2l_apm_data_pipeline.v') },
        @{ Rel = 'ipcore\mul\rtl\ipm2l_mult_v1_3_mul.v'; Src = (Join-Path $ipdir 'mul\rtl\ipm2l_mult_v1_3_mul.v') },
        @{ Rel = 'ipcore\mul\mul.v'; Src = (Join-Path $ipdir 'mul\mul.v') },
        @{ Rel = 'myriscv\alu.v'; Src = (Join-Path $Root 'myriscv\alu.v') },
        @{ Rel = 'myriscv\br_alu.v'; Src = (Join-Path $Root 'myriscv\br_alu.v') },
        @{ Rel = 'myriscv\l_alu.v'; Src = (Join-Path $Root 'myriscv\l_alu.v') },
        @{ Rel = 'myriscv\regfile.v'; Src = (Join-Path $Root 'myriscv\regfile.v') },
        @{ Rel = 'myriscv\csr_defs.vh'; Src = (Join-Path $Root 'myriscv\csr_defs.vh') },
        @{ Rel = 'myriscv\csr_file.v'; Src = (Join-Path $Root 'myriscv\csr_file.v') },
        @{ Rel = 'myriscv\mycpu_sync.v'; Src = (Join-Path $Root 'myriscv\mycpu_sync.v') },
        @{ Rel = 'myriscv\inst_bus_interconnect.v'; Src = (Join-Path $Root 'myriscv\inst_bus_interconnect.v') },
        @{ Rel = 'myriscv\data_bus_interconnect.v'; Src = (Join-Path $Root 'myriscv\data_bus_interconnect.v') },
        @{ Rel = 'myriscv\inst_bram_adapter.v'; Src = (Join-Path $Root 'myriscv\inst_bram_adapter.v') },
        @{ Rel = 'myriscv\data_bram_adapter.v'; Src = (Join-Path $Root 'myriscv\data_bram_adapter.v') },
        @{ Rel = 'myriscv\simple_mmio.v'; Src = (Join-Path $Root 'myriscv\simple_mmio.v') },
        @{ Rel = 'myriscv\uart_tx.v'; Src = (Join-Path $Root 'myriscv\uart_tx.v') },
        @{ Rel = 'myriscv\uart_rx.v'; Src = (Join-Path $Root 'myriscv\uart_rx.v') },
        @{ Rel = 'myriscv\uart_rx_fifo.v'; Src = (Join-Path $Root 'myriscv\uart_rx_fifo.v') },
        @{ Rel = 'myriscv\uart_mmio.v'; Src = (Join-Path $Root 'myriscv\uart_mmio.v') },
        @{ Rel = 'myriscv\soc_top.v'; Src = (Join-Path $Root 'myriscv\soc_top.v') },
        @{ Rel = 'tb\ddr_model_wb2.sv'; Src = (Join-Path $Sim 'ddr_model_wb2.sv') },
        @{ Rel = 'tb\tb_wb2_soc.sv'; Src = (Join-Path $Sim 'tb_wb2_soc.sv') },
        @{ Rel = 'tb\soc_wb2_a.hex'; Src = (Join-Path $Sim 'soc_wb2_a.hex') },
        @{ Rel = 'tb\soc_wb2_b.hex'; Src = (Join-Path $Sim 'soc_wb2_b.hex') },
        @{ Rel = 'tools\check_soc.py'; Src = (Join-Path $Sim 'check_soc.py') },
        @{ Rel = 'tools\prepare_soc_wb2.py'; Src = (Join-Path $Sim 'prepare_soc_wb2.py') },
        @{ Rel = 'tools\soc_wb2_inputs.json'; Src = (Join-Path $Sim 'soc_wb2_inputs.json') }
    )
}
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
    'tb_wb2_fair_d1'            = [ordered]@{ Dq = 32; Posted = 1; Depth = 1; Turnover = 1; Forward = 1; Ruw = 1; Icache = 1; Dcache = 1; Camera = 0; Preproc = 0; Plane = 2 }
    'tb_wb2_fair_d2'            = [ordered]@{ Dq = 32; Posted = 1; Depth = 2; Turnover = 1; Forward = 1; Ruw = 1; Icache = 1; Dcache = 1; Camera = 0; Preproc = 0; Plane = 2 }
    'tb_wb2_edge'               = [ordered]@{ Dq = 32; Posted = 1; Depth = 2; Turnover = 1; Forward = 1; Ruw = 1; Icache = 1; Dcache = 1; Camera = 0; Preproc = 0; Plane = 3 }
    'tb_wb2_x16'                = [ordered]@{ Dq = 16; Posted = 1; Depth = 2; Turnover = 1; Forward = 1; Ruw = 1; Icache = 0; Dcache = 0; Camera = 0; Preproc = 0; Plane = 4 }
    'tb_wb2_noposted'           = [ordered]@{ Dq = 32; Posted = 0; Depth = 2; Turnover = 1; Forward = 1; Ruw = 1; Icache = 1; Dcache = 1; Camera = 0; Preproc = 0; Plane = 5 }
    'tb_wb2_ruw0'               = [ordered]@{ Dq = 32; Posted = 1; Depth = 2; Turnover = 1; Forward = 1; Ruw = 0; Icache = 1; Dcache = 1; Camera = 0; Preproc = 0; Plane = 6 }
    'tb_wb2_soc'                = [ordered]@{ Dq = 32; Posted = 1; Depth = 2; Turnover = 1; Forward = 1; Ruw = 1; Icache = 1; Dcache = 1; Camera = 1; Preproc = 1; Plane = 7 }
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
    soc            = [bool]$Soc
    check_mode     = $mode
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
    modelsim_note  = 'ModelSim 10.6c -c mode was unusable on this machine (machine-level IPv6 loopback block hit its kernel RPC). The operator later restored it (loopback v4/v6 OK, empty module twice to 1 ns exit 0, 0 errors/warnings); that is recorded as a fact only. Task043 补正02 keeps this round on Vivado xsim 2019.2 with the sealed model so the evidence chain stays on one re-checkable backend.'
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

    if ($Soc) {
        $simArgs = @('snap', '-runall',
            ('+EDGE_LOG={0}' -f (Join-Path $run 'soc.edges.log')),
            ('+MEM_DUMP={0}' -f (Join-Path $run 'soc.mem.log')),
            ('+PROG_A={0}' -f (Join-Path $sealDir 'tb\soc_wb2_a.hex')),
            ('+PROG_B={0}' -f (Join-Path $sealDir 'tb\soc_wb2_b.hex')))
    } else {
        $simArgs = @('snap', '-runall')
    }
    $r = Step 'xsim' $xsim $simArgs $run
    if ($r.Code -ne 0) { throw "xsim failed with exit $($r.Code) (see log_xsim.txt)" }
    $simText = $r.Text -join "`n"
    $resLine = ($r.Text | Where-Object { $_ -match 'RESULT:' } | Select-Object -Last 1)
    $meta.sim_result = if ($resLine) { $resLine.Trim() } else { $null }
    if ($simText -match '(?m)^ERROR:') { throw 'xsim reported ERROR:' }
    if ($simText -match 'FATAL_ERROR|Fatal:') { throw 'xsim reported a fatal error' }
    if (-not $resLine) { throw 'no RESULT line in the simulation output' }
    if ($resLine -notmatch 'RESULT:\s+PASS') { throw "simulation did not report RESULT: PASS (got: $resLine)" }
    if ($resLine -match 'FAIL') { throw "simulation reported a FAIL: $resLine" }

    $checkArgs = if ($Soc) {
        @('-B', (Join-Path $sealDir 'tools\check_soc.py'), $run)
    } else {
        @('-B', (Join-Path $sealDir 'tools\check_wb2.py'), '--plane', $mode, $run)
    }
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
    $checkName = "check_{0}.json" -f $mode
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
