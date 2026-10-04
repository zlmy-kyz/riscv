"""Audit promoted images, synthesis initialization, and preserved board files."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "MyCpu_test"))
from prepare_board_selftest_ip import verify

OUT = Path(__file__).resolve().parent
netlist = (ROOT / "synthesize/board_top_syn.vm").read_text()
report = {}
for name, image_name in (("inst_rom", "boot_rom.dat"), ("data_ram", "ddr_selftest.dat")):
    folder = ROOT / "ipcore" / name
    verify(name, folder, ROOT / "MyCpu_test/board_selftest" / image_name)
    before = ET.parse(OUT / "before/ipcore" / name / f"{name}.idf")
    after = ET.parse(folder / f"{name}.idf")
    maps = [{p.findtext("name"): p.findtext("value") for p in tree.findall("./param_list/param")}
            for tree in (before, after)]
    changes = {key: [maps[0].get(key), maps[1].get(key)] for key in maps[0].keys() | maps[1].keys()
               if maps[0].get(key) != maps[1].get(key)}
    assert set(changes) == {"INIT_FILE"}, changes
    source = (folder / "rtl" / f"{name}_init_param.v").read_text()
    params = {(int(block, 16), int(bank), int(lane)): int(value, 16)
              for block, bank, lane, value in re.findall(
                  r"localparam INIT_([0-9A-Fa-f]+)_(\d+)_(\d+)\s*=\s*288'h([0-9A-Fa-f]+)", source)}
    bank_lanes = sorted({(bank, lane) for _, bank, lane in params})
    expected = Counter(tuple(params[block, bank, lane] for block in range(128)) for bank, lane in bank_lanes)
    module = re.search(r"module ipm2l_spram_v1_8_" + name + r"\b.*?endmodule", netlist, re.S)[0]
    values = [int(value, 2) for _, value in re.findall(r"\.INIT_([0-9A-F]{2})\(288'b([01]+)\)", module)]
    assert len(values) == 512, (name, len(values))
    actual = Counter(tuple(values[start:start + 128]) for start in range(0, len(values), 128))
    assert actual == expected, f"{name}: synthesized memory contents differ from generated IP"
    print(f"CHECK: {name} 4 DRM initialization banks in synthesized netlist match board image")
    report[name] = changes

for entry in json.loads((OUT / "before/hashes.json").read_text(encoding="utf-8-sig")):
    path = Path(entry["Path"])
    if path.suffix == ".sbit":
        continue
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == entry["Hash"]
    print("CHECK: unchanged", path.relative_to(ROOT))

bitstream = ROOT / "generate_bitstream/board_top.sbit"
report["bitstream"] = {"path": str(bitstream), "sha256": hashlib.sha256(bitstream.read_bytes()).hexdigest().upper(),
                       "bytes": bitstream.stat().st_size}
(OUT / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("PASS: live IP, synthesis initialization and unchanged board/DDR/FDC audit")
