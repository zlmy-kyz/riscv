# Read-only Windows network diagnosis. No firewall, proxy or network settings change.
$ErrorActionPreference = 'Continue'
$diagnosticRoot = $PSScriptRoot
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
@{ administrator = $isAdmin; time = (Get-Date).ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $diagnosticRoot 'admin_context.json') -Encoding utf8
if (-not $isAdmin) { exit 5 }
& netsh wfp show filters "file=$diagnosticRoot\ipv6_filters.xml" protocol=6 remoteaddr=::1 verbose=ON *> (Join-Path $diagnosticRoot 'wfp_export.log')
& netsh wfp show state "file=$diagnosticRoot\wfpstate.xml" *> (Join-Path $diagnosticRoot 'wfp_state_export.log')
$loopbackResults = foreach ($address in @('127.0.0.1', '::1')) {
    $listener = $null
    $client = $null
    $accepted = $null
    $step = 'listen'
    try {
        $ip = [Net.IPAddress]::Parse($address)
        $listener = [Net.Sockets.TcpListener]::new($ip, 0)
        $listener.Start()
        $step = 'connect'
        $client = [Net.Sockets.TcpClient]::new($ip.AddressFamily)
        $pending = $client.ConnectAsync($ip, $listener.LocalEndpoint.Port)
        if (-not $pending.Wait(2000)) { throw 'connect timeout after 2000 ms' }
        $step = 'accept'
        $accepted = $listener.AcceptTcpClient()
        @{ address = $address; result = 'listen_connect_ok' }
    } catch {
        @{ address = $address; result = 'failed'; step = $step; error = $_.Exception.ToString() }
    } finally {
        if ($accepted) { $accepted.Dispose() }
        if ($client) { $client.Dispose() }
        if ($listener) { $listener.Stop() }
    }
}
$loopbackResults | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $diagnosticRoot 'admin_loopback.json') -Encoding utf8
Get-WinEvent -FilterHashtable @{LogName='Security';Id=5157;StartTime=(Get-Date).AddMinutes(-30)} -MaxEvents 50 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match 'vsim|vish|::1' } |
    Select-Object TimeCreated,Id,Message | ConvertTo-Json -Depth 4 |
    Set-Content -LiteralPath (Join-Path $diagnosticRoot 'admin_blocked_events.json') -Encoding utf8
'READ_ONLY_DIAGNOSIS_COMPLETE' | Set-Content -LiteralPath (Join-Path $diagnosticRoot 'admin_done.txt') -Encoding utf8
