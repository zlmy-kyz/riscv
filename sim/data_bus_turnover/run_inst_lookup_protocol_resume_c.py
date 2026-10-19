"""Task032 B-only protocol resume, re-run C: independent reference address fix.

The previous attempt's protocol simulation passed its own checks (43 accepts = 40
responses + 3 cancels, matching the sealed plan) but the independent reference stopped
at edge 6 because `line_base` was fed a raw CPU address. The helper now converts the
CPU byte address into the DDR user address space first; line_index/lane_of are already
mask-based and unchanged. Only the manifest, tag and previous-manifest binding differ
from the re-run B entry.
"""
import run_inst_lookup_protocol_resume_b as base

base.MANIFEST = base.HERE / 'inputs_inst_lookup_protocol_resume_c.json'
base.TAG = 'ds_data_bus_inst_lookup_protocol_resume_c_20261014_a'
base.PREVIOUS = 'sim/data_bus_turnover/inputs_inst_lookup_protocol_resume_b.json'

require_inputs = base.require_inputs
plan_summary = base.plan_summary


def main():
    print('ENTRY tag=%s manifest=%s previous=%s' % (base.TAG, base.MANIFEST.name, base.PREVIOUS))
    base.main()


if __name__ == '__main__':
    main()
