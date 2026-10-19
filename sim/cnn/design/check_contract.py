"""Static topology accounting only; does not validate a model or RTL."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
profile = root / "doc/cnn/desktop4_int8_v1.json"
p = json.loads(profile.read_text(encoding="utf-8"))
shape = p["input"]["shape_hwc"]
assert shape == [96, 96, 3]
assert p["input"]["bytes"] == 96 * 96 * 3
weight_end = bias_end = macs = 0
for layer in p["layers"]:
    op = layer["op"]
    if op == "conv_relu":
        assert layer["input_hwc"] == shape
        h, w, ci = shape
        k, s, pad = layer["kernel"], layer["stride"], layer["pad_each_side"]
        oh, ow, co = layer["output_hwc"]
        assert [oh, ow] == [(h + 2 * pad - k) // s + 1, (w + 2 * pad - k) // s + 1]
        weights = k * k * ci * co
        assert layer["macs"] == oh * ow * weights
        shape = [oh, ow, co]
    elif op == "gap":
        assert layer["input_hwc"] == shape
        assert layer["divisor"] == shape[0] * shape[1]
        assert layer["output_elements"] == shape[2]
        shape = [shape[2]]
        continue
    else:
        assert op == "fc"
        assert shape == [layer["input_elements"]]
        co = layer["output_elements"]
        weights = layer["input_elements"] * co
        assert layer["macs"] == weights
        shape = [co]
    assert layer["weight_offset"] == weight_end
    assert layer["weight_bytes"] == weights
    assert layer["bias_offset"] == bias_end
    assert layer["bias_count"] == co
    assert layer["weight_fraction_bits"] is None
    assert layer["output_fraction_bits"] is None
    weight_end += weights
    bias_end += co * 4
    macs += layer["macs"]
assert shape == [len(p["classes"])] == [4]
assert weight_end == p["total_weight_bytes"] == 6104
assert bias_end == p["total_bias_bytes"] == 240
assert macs == p["total_macs"] == 1824896
assert p["activation_bank_bytes"] == [96 * 96 * 3, 48 * 48 * 8]
assert p["trained_model"] is None
print(json.dumps({
    "status": "STATIC_TOPOLOGY_CHECKED_NOT_MODEL_OR_RTL_PASS",
    "profile_sha256": hashlib.sha256(profile.read_bytes()).hexdigest(),
    "weight_bytes": weight_end, "bias_bytes": bias_end, "macs": macs,
    "ideal_one_mac_per_clock_ms_at_93750000": macs / 93750,
}, indent=2))
