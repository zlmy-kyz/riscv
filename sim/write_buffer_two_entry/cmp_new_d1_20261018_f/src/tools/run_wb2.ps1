# Task043 bridge-level runner for the two-entry ordered posted write buffer.
#
# One tag = one frozen run directory. The directory is never reused: if it already
# exists the run is refused, so a failing attempt stays on disk as evidence.
#
# Everything that is compiled is first copied into  <run>/src/  with its work-tree
# relative path, then hashed, then compiled FROM THE COPIES. The checker, the runner
# itself, the DDR model (inside the TB) and the Pango simulation models are part of
# that sealed set, so a trace can later be tied to exact bytes.
#
#   run_wb2.ps1 -Tag key_a                            # depth2, PLANE=0 (key group)
#   run_wb2.ps1 -Tag cmp_new_d1 -Depth 1 -Plane 1     # new bridge, depth 1, short
#   run_wb2.ps1 -Tag cmp_old_d1 -Legacy -Plane 1      # old bridge copy, short
#
param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [int]$Dq = 32,
    [int]$Posted = 1,
    [int]$Depth = 2,
    [int]$Turnover = 1,
    [int]$Forward = 1,
    [int]$Ruw = 1,
    [int]$Icache = 1,
    [int]$Dcache = 1,
    [int]$Camera = 0,
    [int]$Preproc = 0,
    [int]$Plane = 0,
    [switch]$Legacy,
    [string]$Root = 'D:\riscv\RISCV',
    [string]$Sim = 'D:\riscv\RISCV\sim\write_buffer_two_entry',
    [string]$ModelsimBin = 'D:\modelsim\win64pe',
    [string]$LegacyBridge = 'D:\riscv\RISCV\sim\write_buffer_two_entry\preparation_20261018_a\before\dual_sram_to_pango_ddr_bridge.v'
)

$ErrorActionPreference = 'Stop'

$run = Join-Path $Sim $Tag
if (Test-Path $run) { throw "run directory already exists, refusing to reuse: $run" }
$sealDir = Join-Path $run 'src'
New-Item -ItemType Directory -Path $run | Out-Null
New-Item -ItemType Directory -Path $sealDir | Out-Null
New-Item -ItemType Directory -Path (Join-Path $run 'work') | Out-Null

$pango = 'C:\pango\PDS_2022.2-SP6.4\arch\vendor\pango\verilog\simulation'
$ipdir = Join-Path $Root 'ipcore'

# rel path inside the seal directory  ->  absolute source
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
    @{ Rel = 'tools\check_wb2.py'; Src = (Join-Path $Sim 'check_wb2.py') },
    @{ Rel = 'tools\run_wb2.ps1'; Src = (Join-Path $Sim 'run_wb2.ps1') }
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

$vlib = Join-Path $ModelsimBin 'vlib.exe'
$vlog = Join-Path $ModelsimBin 'vlog.exe'
$vsim = Join-Path $ModelsimBin 'vsim.exe'
foreach ($t in @($vlib, $vlog, $vsim)) { if (-not (Test-Path $t)) { throw "missing tool: $t" } }
$py = 'C:\Users\z''l''m''y''k\.workbuddy\binaries\python\versions\3.13.12\python.exe'
if (-not (Test-Path $py)) { $py = (Get-Command python -ErrorAction Stop).Source }

# Parameter names must match the TB exactly; a silent mismatch would run defaults.
$gArgs = @(
    "-gDQ=$Dq", "-gPOSTED=$Posted", "-gDEPTH=$Depth", "-gTURNOVER=$Turnover",
    "-gFORWARD=$Forward", "-gRUW=$Ruw", "-gICACHE=$Icache", "-gDCACHE=$Dcache",
    "-gCAMERA=$Camera", "-gPREPROC=$Preproc", "-gPLANE=$Plane"
)

$meta = [ordered]@{
    tag        = $Tag
    status     = 'RUNNING'
    started    = (Get-Date).ToString('s')
    root       = $Root
    sealed_src = $sealDir
    legacy     = [bool]$Legacy
    bridge     = $sources[6].Src
    params     = [ordered]@{
        Dq = $Dq; Posted = $Posted; Depth = $Depth; Turnover = $Turnover;
        Forward = $Forward; Ruw = $Ruw; Icache = $Icache; Dcache = $Dcache;
        Camera = $Camera; Preproc = $Preproc; Plane = $Plane
    }
    tools      = [ordered]@{ vlib = $vlib; vlog = $vlog; vsim = $vsim; python = $py }
    commands   = @()
    exits      = [ordered]@{}
    timeline   = @()
    vsim_result   = $null
    vsim_attempts = 0
    check_status  = 'NOT_RUN'
    identity_drift = 0
    error      = $null
    finished   = $null
}
# The checker reads <run>/run_meta.json for the effective parameters, so the meta
# file is written before anything runs and rewritten on the way out, success or not.
$metaPath = Join-Path $run 'run_meta.json'
$meta | ConvertTo-Json -Depth 6 | Set-Content -Path $metaPath -Encoding UTF8

$timeline = New-Object System.Collections.Generic.List[string]
$compiled = $rels | Where-Object { $_ -like '*.v' -or $_ -like '*.sv' } |
    ForEach-Object { Join-Path $sealDir $_ }

function Step {
    param([string]$Name, [string]$Exe, [string[]]$ArgList, [string]$WorkDir)
    $t0 = Get-Date
    Push-Location $WorkDir
    try {
        $out = & $Exe @ArgList 2>&1
        $code = $LASTEXITCODE
    } finally { Pop-Location }
    $dt = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    $out | ForEach-Object { $_.ToString() } |
        Set-Content -Path (Join-Path $run ("log_{0}.txt" -f $Name)) -Encoding ASCII
    $script:timeline.Add(("{0} exit={1} {2}s :: {3} {4}" -f
            $Name, $code, $dt, (Split-Path $Exe -Leaf), ($ArgList -join ' ')))
    $script:meta.exits[$Name] = $code
    $script:meta.commands += ("{0} {1}" -f $Exe, ($ArgList -join ' '))
    if ($code -ne 0) { throw "$Name failed with exit $code (see log_$Name.txt)" }
    return ($out | ForEach-Object { $_.ToString() })
}

$vlogArgs = @('-sv', '-work', 'work')
if ($Legacy) { $vlogArgs += '+define+LEGACY_BRIDGE' }
$vlogArgs += $compiled

$vsimArgs = @('-c', '-quiet') + $gArgs + @('work.tb_wb2_bridge',
    '-do', 'run -all; quit -f', '-l', 'vsim.log')

try {
    "EFFECTIVE PARAMS: DQ=$Dq POSTED=$Posted DEPTH=$Depth TURNOVER=$Turnover FORWARD=$Forward RUW=$Ruw ICACHE=$Icache DCACHE=$Dcache CAMERA=$Camera PREPROC=$Preproc PLANE=$Plane LEGACY=$([bool]$Legacy)"
    Step 'vlib' $vlib @('work') $run | Out-Null
    $vlogOut = Step 'vlog' $vlog $vlogArgs $run
    $vlogText = $vlogOut -join "`n"
    if ($vlogText -match '\*\* (Error|Fatal)') { throw 'vlog reported ** Error/** Fatal (see log_vlog.txt)' }
    if ($vlogText -notmatch 'Errors:\s*0\s*,\s*Warnings:\s*0') {
        throw "vlog did not report 'Errors: 0, Warnings: 0' (see log_vlog.txt)"
    }

    # ModelSim 10.6c occasionally cannot create its kernel RPC socket ("RPC_Init:
    # TCL_ERROR ... couldn't open socket"), which is a local IPv6-loopback policy
    # problem, not a result. Each attempt is logged and counted; anything other than
    # that exact signature fails immediately, and a run only passes on a real result.
    $vsimAttempt = 0
    $vsimOut = $null
    $vsimOk = $false
    while ($vsimAttempt -lt 3 -and -not $vsimOk) {
        $vsimAttempt++
        try {
            $vsimOut = Step ("vsim{0}" -f $vsimAttempt) $vsim $vsimArgs $run
            $vsimOk = $true
        } catch {
            $attemptLog = Join-Path $run ("log_vsim{0}.txt" -f $vsimAttempt)
            $attemptText = if (Test-Path $attemptLog) { Get-Content -Raw $attemptLog } else { '' }
            if ($attemptText -match 'RPC_Init') {
                $timeline.Add(("vsim{0} exit=environment :: RPC_Init, IPv6 loopback blocked" -f $vsimAttempt))
                continue
            }
            throw
        }
    }
    $meta.vsim_attempts = $vsimAttempt
    if (-not $vsimOk) { throw "vsim never started: RPC_Init on all $vsimAttempt attempt(s)" }
    $vsimText = $vsimOut -join "`n"
    $resLine = ($vsimOut | Where-Object { $_ -match 'RESULT:' } | Select-Object -Last 1)
    if (-not $resLine) {
        $vsimLog = Join-Path $run 'vsim.log'
        if (Test-Path $vsimLog) {
            $resLine = (Get-Content $vsimLog | Where-Object { $_ -match 'RESULT:' } | Select-Object -Last 1)
        }
    }
    $meta.vsim_result = if ($resLine) { $resLine.Trim() } else { $null }
    if ($vsimText -match '(?m)^# \*\* (Fatal|Error)') {
        throw "vsim reported a fatal/error line: $(($vsimText -split "`n" | Where-Object { $_ -match '(?m)^# \*\* (Fatal|Error)' } | Select-Object -First 1))"
    }
    if ($vsimText -notmatch 'Errors:\s*0\s*,\s*Warnings:\s*0') {
        throw 'vsim did not report Errors: 0, Warnings: 0 (see log_vsim.txt / vsim.log)'
    }
    if ($resLine -notmatch 'RESULT:\s+PASS') { throw "vsim did not report RESULT: PASS (got: $resLine)" }
    if ($resLine -match 'FAIL') { throw "vsim reported a FAIL: $resLine" }

    # ---- independent checker (mandatory: there is no skip switch by design) ----
    $checkArgs = @('-B', (Join-Path $sealDir 'tools\check_wb2.py'))
    if ($Plane -ne 0) { $checkArgs += '--short' }
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
    $checkName = if ($Plane -ne 0) { 'check_short.json' } else { 'check_key.json' }
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
    $meta | ConvertTo-Json -Depth 6 | Set-Content -Path $metaPath -Encoding UTF8
}

"RESULT: $($meta.status) tag=$Tag $($meta.vsim_result)"
"check  : $($meta.check_status)"
"timeline:"
$timeline | ForEach-Object { "  $_" }
