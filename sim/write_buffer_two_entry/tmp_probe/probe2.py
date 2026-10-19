import os
import subprocess
import sys


def step(tag, fn):
    print("STEP %s ..." % tag, flush=True)
    try:
        print("  -> %r" % (fn(),), flush=True)
    except Exception as e:                     # noqa: BLE001
        print("  !! %s: %r" % (type(e).__name__, e), flush=True)


step("python-echo", lambda: subprocess.run([sys.executable, "-c", "print(42)"],
                                           capture_output=True, text=True).stdout.strip())

step("vsim-help", lambda: subprocess.run([r"D:\modelsim\win64pe\vsim.exe", "-h"],
                                         capture_output=True, text=True,
                                         errors="replace", timeout=60).returncode)
print("done", flush=True)
