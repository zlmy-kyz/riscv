"""Static design accounting, not RTL simulation or model acceptance."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
path = root / "doc/cnn/digits10_int8_v1.json"
p = json.loads(path.read_text(encoding="utf-8"))
assert p["contract"] == "digits10_int8_v1"
assert p["classes"] == [str(i) for i in range(10)]
assert p["input"]["shape_hwc"] == [32, 32, 1]
assert p["input"]["source_bytes"] == 96 * 96 * 3
assert p["input"]["bytes"] == 32 * 32
shape = [32, 32, 1]
weights = biases = macs = 0
sizes = [1024]
for l in p["layers"]:
    if l["op"] == "gap":
        assert l["input_hwc"] == shape
        assert l["divisor"] == shape[0] * shape[1] == 16
        assert l["output_elements"] == shape[2]
        shape = [shape[2]]
        continue
    if l["op"] == "conv_relu":
        assert l["input_hwc"] == shape
        h, w, ci = shape
        oh, ow, co = l["output_hwc"]
        k, s, pad = l["kernel"], l["stride"], l["pad_each_side"]
        assert (k, s, pad) == (3, 2, 1)
        assert [oh, ow] == [(h+2*pad-k)//s+1, (w+2*pad-k)//s+1]
        count = k*k*ci*co
        assert l["macs"] == oh*ow*count
        sizes.append(oh*ow*co)
        shape = [oh, ow, co]
    else:
        assert l["op"] == "fc" and shape == [l["input_elements"]]
        co = l["output_elements"]
        count = l["input_elements"]*co
        assert l["macs"] == count
        shape = [co]
    assert l["weight_offset"] == weights and l["weight_bytes"] == count
    assert l["bias_offset"] == biases and l["bias_count"] == co
    assert l["weight_fraction_bits"] is None and l["output_fraction_bits"] is None
    weights += count
    biases += co*4
    macs += l["macs"]
assert shape == [10]
assert weights == p["total_weight_bytes"] == 6152
assert biases == p["total_bias_bytes"] == 264
assert macs == p["total_macs"] == 166208
assert max(sizes) <= min(p["activation_bank_bytes"])
assert p["trained_model"] is None
coords = [3*i+1 for i in range(32)]
assert coords[0] == 1 and coords[-1] == 94 and len(set(coords)) == 32
assert 77+150+29 == 256 and 255*256+128 < 65536
for gray in range(256):
    assert (77*gray+150*gray+29*gray+128)>>8 == gray
assert max((s+8)>>4 for s in range(16*127+1)) == 127
print(json.dumps({"status":"STATIC_DIGITS_DESIGN_CHECKED_NOT_RTL_OR_MODEL_PASS",
    "profile_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
    "weight_bytes":weights,"bias_bytes":biases,"macs":macs},indent=2))
