$ok = 0; $bad = 0; $other = 0
for ($i = 1; $i -le 6; $i++) {
  $args = @('-c','-quiet','-gDQ=32','-gPOSTED=1','-gDEPTH=1','-gTURNOVER=1','-gFORWARD=1','-gRUW=1',
            '-gICACHE=1','-gDCACHE=1','-gCAMERA=0','-gPREPROC=0','-gPLANE=1','work.tb_wb2_bridge',
            '-do','run -all; quit -f','-l',("try$i.log"))
  $out = & 'D:\modelsim\win64pe\vsim.exe' @args 2>&1 | Out-String
  if ($out -match 'RPC_Init') { $bad++; "try$i RPC_FAIL" }
  elseif ($out -match 'RESULT: PASS') { $ok++; "try$i PASS" }
  else { $other++; "try$i OTHER: " + (($out -split "`r?`n" | Where-Object { $_ -match 'Fatal|Error|RESULT' } | Select-Object -Last 2) -join ' | ') }
}
"ok=$ok rpc_fail=$bad other=$other"
