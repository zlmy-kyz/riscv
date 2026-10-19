"""Standalone ModelSim environment diagnostic; no project design is compiled."""
import json
import os
from pathlib import Path
import socket
import subprocess

ROOT = Path(__file__).resolve().parent
BIN = Path(r"D:\modelsim\win64pe")
results = {"purpose": "tool health only, no RISCV verification", "commands": [], "sockets": []}


def command(name, arguments):
    entry = {"name": name, "argv": list(map(str, arguments)), "cwd": str(ROOT)}
    try:
        proc = subprocess.run(entry["argv"], cwd=ROOT, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=20)
        output = proc.stdout.decode("utf-8", errors="replace")
        entry.update(exit_code=proc.returncode, timed_out=False)
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b"").decode("utf-8", errors="replace")
        entry.update(exit_code=None, timed_out=True)
    (ROOT / (name + ".log")).write_text(output, encoding="utf-8")
    entry["kernel_marker"] = "TOOL_KERNEL_OK time=1000" in output
    entry["rpc_error"] = "RPC_Init" in output
    results["commands"].append(entry)
    print(json.dumps(entry), flush=True)
    print(output, flush=True)
    return entry


for family, address in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
    entry = {"address": address}
    try:
        with socket.socket(family, socket.SOCK_STREAM) as server:
            server.settimeout(2)
            server.bind((address, 0))
            server.listen(1)
            with socket.socket(family, socket.SOCK_STREAM) as client:
                client.settimeout(2)
                client.connect(server.getsockname())
                peer, _ = server.accept()
                peer.close()
        entry["result"] = "listen_connect_ok"
    except OSError as exc:
        entry.update(result="failed", error=str(exc), winerror=getattr(exc, "winerror", None))
    results["sockets"].append(entry)
    print(json.dumps(entry), flush=True)

command("version", [BIN / "vsim.exe", "-version"])
lib = command("vlib", [BIN / "vlib.exe", "work"])
compile_result = command("vlog", [BIN / "vlog.exe", "-work", "work", "tool_health.v"])
if compile_result["exit_code"] == 0:
    for attempt in (1, 2):
        command(f"kernel_{attempt}", [BIN / "vsim.exe", "-c", "-onfinish", "exit",
                "-l", f"transcript_{attempt}.log", "work.tool_health", "-do", "run -all; quit -f"])
(ROOT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
