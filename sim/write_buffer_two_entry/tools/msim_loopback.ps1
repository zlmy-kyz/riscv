# Repair / verify the local loopback path that ModelSim's RPC needs.
#
# Why this exists: this machine has three persistent Windows Firewall rules left
# behind by the sandbox. Two of them block outbound loopback TCP/UDP, and the
# block covers ::1. ModelSim (DE-64 10.6c) announces its kernel RPC endpoint as
# an IPv6 literal and then fails to connect to it:
#
#   RPC_Init: TCL_ERROR: set rpc_port [split {::1:62343} :]
#     -> couldn't open socket: invalid argument
#
# Measured directly, without ModelSim:
#   bind/listen on ::1  -> OK
#   connect    to ::1   -> WinError 10013 (WSAEACCES, blocked by policy)
#   connect    to 127.0.0.1 -> OK
#
# Scope of the change made by -Open: it only disables the two *loopback* rules,
# by exact DisplayName. The outbound-to-the-world rule is left untouched, so the
# machine stays offline. -Close re-enables them. Nothing else is modified.
#
#   msim_loopback.ps1 -Status   # read-only: show rules and test ::1 connect
#   msim_loopback.ps1 -Open     # admin: disable the two loopback block rules
#   msim_loopback.ps1 -Close    # admin: re-enable them
#   msim_loopback.ps1 -UnblockV6   # admin: also disable the blanket outbound block
#   msim_loopback.ps1 -RestoreV6   # admin: re-enable it (back to offline)
#
# Note: the two loopback rules are already disabled on this machine, yet ::1 is
# still refused. The remaining suspect is codex_sandbox_offline_block_outbound,
# whose remote-address list contains "::" (any IPv6). Windows gives block filters
# precedence over allow filters, so adding an allow rule does not help; the block
# rule itself has to be switched off while simulating, then restored.
param(
    [switch]$Status,
    [switch]$Open,
    [switch]$Close,
    [switch]$UnblockV6,
    [switch]$RestoreV6
)

$ErrorActionPreference = 'Stop'
$loopback = @(
    'codex_sandbox_offline_block_loopback_tcp',
    'codex_sandbox_offline_block_loopback_udp'
)
$blanket = 'codex_sandbox_offline_block_outbound'

function Show-Rules {
    foreach ($n in $loopback) {
        $r = Get-NetFirewallRule -DisplayName $n -ErrorAction SilentlyContinue
        if ($r) {
            "rule {0,-42} Enabled={1} Action={2} Direction={3}" -f $n, $r.Enabled, $r.Action, $r.Direction
        } else {
            "rule {0,-42} (absent)" -f $n
        }
    }
}

function Test-Loopback {
    # IPv6 loopback listen + connect, no external network touched.
    $ok = $false
    $detail = 'not run'
    $l = $null; $c = $null
    try {
        $l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::IPv6Loopback, 0)
        $l.Start()
        $port = ([System.Net.IPEndPoint]$l.LocalEndpoint).Port
        $c = [System.Net.Sockets.TcpClient]::new([System.Net.Sockets.AddressFamily]::InterNetworkV6)
        $c.Connect([System.Net.IPAddress]::IPv6Loopback, $port)
        $ok = $true
        $detail = "connect ::1:$port OK"
    } catch {
        $err = $_.Exception
        if ($err.InnerException) { $err = $err.InnerException }
        $detail = "::1 probe FAILED: $($err.Message)"
    } finally {
        if ($c) { $c.Dispose() }
        if ($l) { $l.Stop() }
    }

    $v4 = 'not run'
    $l4 = $null; $c4 = $null
    try {
        $l4 = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
        $l4.Start()
        $c4 = [System.Net.Sockets.TcpClient]::new([System.Net.Sockets.AddressFamily]::InterNetwork)
        $c4.Connect([System.Net.IPAddress]::Loopback, ([System.Net.IPEndPoint]$l4.LocalEndpoint).Port)
        $v4 = 'connect 127.0.0.1 OK'
    } catch {
        $err = $_.Exception
        if ($err.InnerException) { $err = $err.InnerException }
        $v4 = "connect 127.0.0.1 FAILED: $($err.Message)"
    } finally {
        if ($c4) { $c4.Dispose() }
        if ($l4) { $l4.Stop() }
    }

    Write-Host "  ::1      : $detail"
    Write-Host "  127.0.0.1: $v4"
    return $ok
}

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)

$anyAction = $Open -or $Close -or $UnblockV6 -or $RestoreV6
if ($Status -or (-not $anyAction)) {
    "administrator: $admin"
    Show-Rules
    "loopback probe:"
    $ok = Test-Loopback
    if (-not $anyAction) { return }
}

if (-not $admin) { throw 'this action needs an elevated (administrator) PowerShell' }

if ($Open) {
    foreach ($n in $loopback) {
        if (Get-NetFirewallRule -DisplayName $n -ErrorAction SilentlyContinue) {
            Set-NetFirewallRule -DisplayName $n -Enabled False
            "disabled $n"
        }
    }
    "after -Open:"
    Show-Rules
    "loopback probe:"
    $ok = Test-Loopback
    if (-not $ok) { throw '::1 still blocked after disabling the loopback rules' }
    'RESULT: LOOPBACK OPEN (ModelSim RPC should start)'
}

if ($Close) {
    foreach ($n in $loopback) {
        if (Get-NetFirewallRule -DisplayName $n -ErrorAction SilentlyContinue) {
            Set-NetFirewallRule -DisplayName $n -Enabled True
            "enabled $n"
        }
    }
    "after -Close:"
    Show-Rules
    "loopback probe:"
    $ok = Test-Loopback
}

if ($UnblockV6) {
    $r = Get-NetFirewallRule -DisplayName $blanket -ErrorAction SilentlyContinue
    if (-not $r) { throw "rule $blanket not found" }
    Set-NetFirewallRule -DisplayName $blanket -Enabled False
    "disabled $blanket (it blocked every IPv6 destination, including ::1)"
    "loopback probe:"
    $ok = Test-Loopback
    if (-not $ok) { throw '::1 is still blocked with all three rules off: the block comes from something else (check WFP filters / security software)' }
    'RESULT: LOOPBACK OPEN (ModelSim RPC should start)'
    'run  tools\msim_loopback.ps1 -RestoreV6   to go back offline'
}

if ($RestoreV6) {
    if (Get-NetFirewallRule -DisplayName $blanket -ErrorAction SilentlyContinue) {
        Set-NetFirewallRule -DisplayName $blanket -Enabled True
        "enabled $blanket (machine offline again)"
    }
}
