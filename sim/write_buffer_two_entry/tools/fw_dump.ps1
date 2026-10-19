$rules = Get-NetFirewallRule -ErrorAction SilentlyContinue |
    Where-Object { $_.Action -eq 'Block' -and $_.Enabled -eq 'True' -and $_.Direction -eq 'Outbound' }
"enabled outbound block rules: $($rules.Count)"
foreach ($r in $rules) {
    $addr = ($r | Get-NetFirewallAddressFilter).RemoteAddress
    $port = ($r | Get-NetFirewallPortFilter)
    "$($r.DisplayName) | profile=$($r.Profile) | remote=$($addr -join ',') | proto=$($port.Protocol) | dport=$($port.RemotePort)"
}
"--- WFP / profiles ---"
Get-NetFirewallProfile | ForEach-Object { "$($_.Name) enabled=$($_.Enabled) defaultOut=$($_.DefaultOutboundAction) defaultIn=$($_.DefaultInboundAction)" }
