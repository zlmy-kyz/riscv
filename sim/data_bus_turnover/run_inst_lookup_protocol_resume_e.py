"""Task032 B-only protocol resume, re-run E.

Re-run D executed cleanly end to end: vlib/vlog passed, the protocol simulation passed
its own checks (43 accepts = 40 responses + 3 cancels over 188 edges) and the
independent reference passed the whole trace on offline replay. The only failure was a
runner assertion on a key the reference does not return; that redundant line is removed.
"""
import run_inst_lookup_protocol_resume_b as base

base.MANIFEST = base.HERE / 'inputs_inst_lookup_protocol_resume_e.json'
base.TAG = 'ds_data_bus_inst_lookup_protocol_resume_e_20261014_a'
base.PREVIOUS = 'sim/data_bus_turnover/inputs_inst_lookup_protocol_resume_d.json'

require_inputs = base.require_inputs
plan_summary = base.plan_summary


def main():
    print('ENTRY tag=%s manifest=%s previous=%s' % (base.TAG, base.MANIFEST.name, base.PREVIOUS))
    base.main()


if __name__ == '__main__':
    main()
