"""Probe why vsim cannot start: run it under controlled environments and report
the native exit code plus the first bytes of stdout/stderr. Diagnostic only."""
import os
import subprocess
import sys
from pathlib import Path

VSIM = r"D:\modelsim\win64pe\vsim.exe"
CWD = r"D:\riscv\RISCV\sim\write_buffer_two_entry\tmp_probe"
ARGS = [VSIM, "-c", "-quiet", "work.tb_wb2_bridge", "-do", "run -all; quit -f"]


def show(name, env):
    p = subprocess.run(ARGS, cwd=CWD, env=env, capture_output=True, text=True,
                       errors="replace", timeout=180)
    out = (p.stdout or "").replace("\r", "").strip().splitlines()
    err = (p.stderr or "").replace("\r", "").strip().splitlines()
    print("== %s exit=%s out=%d err=%d" % (name, p.returncode, len(out), len(err)))
    for line in (out + err)[:6]:
        print("   " + line[:160])


base = dict(os.environ)                      # normalised by Python (no case dups)
minimal = {k: v for k, v in os.environ.items()
           if k.upper() in ("SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "PATH", "TEMP",
                            "TMP", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE",
                            "COMPUTERNAME", "USERNAME", "PATHEXT")}
no_proxy = {k: v for k, v in base.items()
            if k.lower() not in ("http_proxy", "https_proxy", "all_proxy", "no_proxy")}

print("env keys:", len(base))
show("base", base)
show("no_proxy", no_proxy)
show("minimal", minimal)
