import os
import subprocess

ARGS = [r"D:\modelsim\win64pe\vsim.exe", "-c", "-quiet", "work.tb_wb2_bridge",
        "-do", "run -all; quit -f"]
CWD = r"D:\riscv\RISCV\sim\write_buffer_two_entry\tmp_probe"

print("A: inherit stdio, no capture", flush=True)
try:
    rc = subprocess.call(ARGS, cwd=CWD)
    print("A rc=%s" % rc, flush=True)
except Exception as e:                         # noqa: BLE001
    print("A !! %r" % (e,), flush=True)
